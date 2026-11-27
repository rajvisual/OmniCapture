import os
import sys
import time
import shutil
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Tuple

from core.adb_manager import ADBManager
from core.scrcpy_engine import ScrcpyEngine
from core.pc_recorder import PCRecorder
from core.recorder import RecordingManager
from core.drive_uploader import DriveUploader
from core.resource_path import get_base_dir, get_recordings_dir

class GUIController:
    """
    Central business logic & background process controller for the OmniCapture GUI.
    Thread-safe and designed to decouple the UI from ADB, scrcpy, and FFmpeg processes.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.bin_dir = str(get_base_dir() / config.get("scrcpy_dir", "bin"))
        self.recordings_dir = get_recordings_dir()

        self.adb = ADBManager(self.bin_dir)
        self.scrcpy = ScrcpyEngine(self.bin_dir)
        self.pc_recorder = PCRecorder(bin_dir=self.bin_dir)
        self.uploader = DriveUploader(config)
        self.recorder = RecordingManager(
            str(self.recordings_dir),
            self.scrcpy,
            self.uploader,
            self.adb,
            self.pc_recorder
        )

        # Polling & state
        self._device_cache: Dict[str, Any] = {
            "status": "NO DEVICE",
            "device_id": None,
            "model": "No Device Detected",
            "is_wireless": False,
            "battery": {"level": "N/A", "status": "N/A", "powered": "N/A"},
            "wifi_ip": None,
            "raw_devices": []
        }
        self._device_listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._poll_running = False
        self._poll_thread: Optional[threading.Thread] = None

        # Active processes
        self._active_mirror_proc: Optional[subprocess.Popen] = None
        self._active_camera_proc: Optional[subprocess.Popen] = None
        self._active_screen_rec_proc: Optional[subprocess.Popen] = None
        self._active_cam_rec_proc: Optional[subprocess.Popen] = None

        # Dual recording state
        self._dual_recording_active = False
        self._dual_rec_data: Optional[Dict[str, Any]] = None
        self._dual_timer_thread: Optional[threading.Thread] = None
        self._dual_stop_event = threading.Event()

    def set_simulated_device_manager(self, sim_adb):
        """Inject simulated device manager for testing and developer mode."""
        self.adb = sim_adb
        self.recorder.adb = sim_adb
        self._device_cache["device_id"] = None
        self._device_cache["status"] = "NO DEVICE"

    # -------------------------------------------------------------------------
    # Device Poller & State
    # -------------------------------------------------------------------------

    def register_device_listener(self, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback invoked when device state changes."""
        if callback not in self._device_listeners:
            self._device_listeners.append(callback)

    def start_device_poller(self, interval_sec: float = 2.5):
        """Start the background ADB polling daemon thread."""
        if self._poll_running:
            return
        self._poll_running = True
        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            args=(interval_sec,),
            daemon=True,
            name="OmniDevicePoller"
        )
        self._poll_thread.start()

    def stop_device_poller(self):
        """Stop background ADB polling."""
        self._poll_running = False

    def _poll_loop(self, interval_sec: float):
        while self._poll_running:
            try:
                self.refresh_device_now()
            except Exception:
                pass
            time.sleep(interval_sec)

    def refresh_device_now(self) -> Dict[str, Any]:
        """Perform an instant device query and notify registered listeners."""
        devices = self.adb.list_devices()
        new_state = {
            "status": "NO DEVICE",
            "device_id": None,
            "model": "No Device Detected",
            "is_wireless": False,
            "battery": {"level": "N/A", "status": "N/A", "powered": "N/A"},
            "wifi_ip": None,
            "raw_devices": devices
        }

        if devices:
            ready_usb = [d for d in devices if not d.get("is_wireless") and d.get("state") == "device"]
            ready_any = [d for d in devices if d.get("state") == "device"]
            chosen = ready_usb[0] if ready_usb else (ready_any[0] if ready_any else devices[0])

            dev_id = chosen["id"]
            state = chosen.get("state", "unknown")

            if state == "device":
                new_state["status"] = "CONNECTED"
                new_state["device_id"] = dev_id
                new_state["model"] = chosen.get("model", "Android Device")
                new_state["is_wireless"] = chosen.get("is_wireless", False)
                try:
                    new_state["battery"] = self.adb.get_battery_info(dev_id)
                except Exception:
                    pass
                try:
                    new_state["wifi_ip"] = self.adb.get_wifi_ip(dev_id)
                except Exception:
                    pass
            elif state == "unauthorized":
                new_state["status"] = "UNAUTHORIZED"
                new_state["device_id"] = dev_id
                new_state["model"] = f"{chosen.get('model', 'Device')} (Unauthorized)"
            elif state == "offline":
                new_state["status"] = "OFFLINE"
                new_state["device_id"] = dev_id
                new_state["model"] = f"{chosen.get('model', 'Device')} (Offline)"

        state_changed = (
            self._device_cache is None or
            self._device_cache.get("status") != new_state.get("status") or
            self._device_cache.get("device_id") != new_state.get("device_id") or
            self._device_cache.get("battery", {}).get("level") != new_state.get("battery", {}).get("level")
        )
        self._device_cache = new_state
        if state_changed:
            for cb in self._device_listeners:
                try:
                    cb(new_state)
                except Exception:
                    pass
        return new_state

    def get_cached_device(self) -> Dict[str, Any]:
        return self._device_cache

    def get_target_device_id(self) -> Optional[str]:
        cache = self.get_cached_device()
        if cache.get("status") == "CONNECTED":
            return cache.get("device_id")
        return None

    # -------------------------------------------------------------------------
    # Device Actions
    # -------------------------------------------------------------------------

    def release_camera_lock(self, device_id: Optional[str] = None) -> Tuple[bool, str]:
        """Force-stop camera apps on device to release sensor locks."""
        target = device_id or self.get_target_device_id()
        if not target:
            return False, "No ready Android device connected."
        try:
            self.adb.wake_screen(target)
            self.adb.release_camera_lock(target)
            return True, f"Camera lock released on [{target}]. Screen awakened."
        except Exception as e:
            return False, f"Failed to release camera lock: {e}"

    def switch_to_wireless_adb(self, device_id: Optional[str] = None) -> Tuple[bool, str]:
        """Switch currently connected USB device to TCP/IP Wi-Fi ADB."""
        target = device_id or self.get_target_device_id()
        if not target:
            return False, "No ready Android device connected."
        ok, msg = self.adb.enable_wireless(target)
        if ok:
            self.refresh_device_now()
        return ok, msg

    def switch_to_usb_adb(self, device_id: Optional[str] = None) -> Tuple[bool, str]:
        """Switch device from TCP/IP Wi-Fi ADB back to USB-only mode."""
        target = device_id or self.get_target_device_id()
        ok, msg = self.adb.disable_wireless(target)
        self.refresh_device_now()
        return ok, msg

    def query_diagnostics(self) -> Dict[str, Any]:
        """Fetch complete system, binary, encoder, and camera diagnostics."""
        target = self.get_target_device_id()
        codec, encoder_display = self.pc_recorder.detect_best_encoder()
        diag = {
            "adb_path": str(self.adb.adb_path),
            "adb_version": self.adb.get_adb_version() or "Not detected",
            "scrcpy_path": str(self.scrcpy.scrcpy_path),
            "scrcpy_ready": self.scrcpy.scrcpy_path.is_file(),
            "ffmpeg_path": str(self.pc_recorder.ffmpeg_path) if self.pc_recorder.ffmpeg_path else "Not found",
            "ffmpeg_version": self.pc_recorder.get_ffmpeg_version() or "Not detected",
            "ffmpeg_available": self.pc_recorder.is_available(),
            "video_encoder": codec,
            "video_encoder_display": encoder_display,
            "device_id": target,
            "device_status": self._device_cache.get("status"),
            "cameras_info": "Device not connected",
            "camera_sizes": "Device not connected",
        }
        if target:
            try:
                diag["cameras_info"] = self.scrcpy.query_cameras(target)
                diag["camera_sizes"] = self.scrcpy.query_camera_sizes(target)
            except Exception as e:
                diag["cameras_info"] = f"Error querying cameras: {e}"
        return diag

    def get_active_encoder_name(self) -> str:
        """Friendly name of the detected active hardware video encoder."""
        return self.pc_recorder.detect_best_encoder()[1]

    def get_active_encoder_short(self) -> str:
        """Concise acronym for the active encoder for status bar readout."""
        codec, _ = self.pc_recorder.detect_best_encoder()
        short_names = {
            "h264_nvenc": "NVENC",
            "h264_amf": "AMD AMF",
            "h264_qsv": "Intel QSV",
            "h264_mf": "MediaFoundation",
            "libx264": "x264 CPU"
        }
        return short_names.get(codec, codec.upper())

    # -------------------------------------------------------------------------
    # Single Stream Launchers (Mirror, Camera, Direct Record)
    # -------------------------------------------------------------------------

    def launch_display_mirror(
        self,
        uhid: bool = False,
        screen_off: bool = False,
        stay_awake: bool = False,
        on_exit: Optional[Callable[[int], None]] = None
    ) -> Tuple[bool, str]:
        """Launch interactive display mirror in a background worker."""
        target = self.get_target_device_id()
        if not target:
            return False, "No ready Android device connected. Please plug in your phone via USB."

        opts = {
            "device_id": target,
            "screen_off": screen_off,
            "stay_awake": stay_awake,
            "uhid": uhid,
            "max_size": self.config.get("max_size", 1200),
            "bit_rate": self.config.get("video_bit_rate", "8M"),
            "max_fps": self.config.get("max_fps", 60),
            "window_title": f"OmniCapture - {self._device_cache.get('model', 'Phone')}"
        }
        cmd = self.scrcpy.build_command("mirror", opts)
        env = self.scrcpy.get_scrcpy_env(self.adb.adb_path)

        def _worker():
            try:
                proc = subprocess.Popen(cmd, env=env)
                self._active_mirror_proc = proc
                code = proc.wait()
                self._active_mirror_proc = None
                if on_exit:
                    on_exit(code)
            except Exception as e:
                self._active_mirror_proc = None
                if on_exit:
                    on_exit(-1)

        t = threading.Thread(target=_worker, daemon=True, name="OmniMirrorWorker")
        t.start()
        return True, "Display Mirror & Controller launched!"

    def launch_stealth_camera(
        self,
        facing: str = "back",
        audio_mic: bool = True,
        on_exit: Optional[Callable[[int], None]] = None
    ) -> Tuple[bool, str]:
        """Launch live stealth camera stream in background worker."""
        target = self.get_target_device_id()
        if not target:
            return False, "No ready Android device connected."

        # Clear locks and awaken screen
        self.adb.wake_screen(target)
        self.adb.release_camera_lock(target)

        opts = {
            "device_id": target,
            "camera_facing": facing,
            "audio_source": "mic" if audio_mic else None,
            "window_title": f"OmniCapture - Stealth {facing.capitalize()} Camera"
        }
        cmd = self.scrcpy.build_command("camera", opts)
        env = self.scrcpy.get_scrcpy_env(self.adb.adb_path)

        def _worker():
            try:
                proc = subprocess.Popen(cmd, env=env)
                self._active_camera_proc = proc
                code = proc.wait()
                self._active_camera_proc = None
                if on_exit:
                    on_exit(code)
            except Exception:
                self._active_camera_proc = None
                if on_exit:
                    on_exit(-1)

        t = threading.Thread(target=_worker, daemon=True, name="OmniCameraWorker")
        t.start()
        return True, f"Stealth {facing.capitalize()} Camera viewfinder launched!"

    def record_screen(
        self,
        record_format: str = "mp4",
        auto_upload: bool = False,
        on_complete: Optional[Callable[[Optional[Path], float, int], None]] = None
    ) -> Tuple[bool, str]:
        """Start unlimited screen recording in a background thread."""
        target = self.get_target_device_id()
        if not target:
            return False, "No ready Android device connected."

        opts = {
            "device_id": target,
            "record_format": record_format,
            "stay_awake": True,
            "audio_source": "playback"
        }

        def _worker():
            fpath, dur, sz = self.recorder.record_session("record_screen", opts, auto_upload=auto_upload)
            if on_complete:
                on_complete(fpath, dur, sz)

        t = threading.Thread(target=_worker, daemon=True, name="OmniScreenRecWorker")
        t.start()
        return True, "Screen recording started! Press [Ctrl+C] or close window to finish."

    def record_camera(
        self,
        facing: str = "back",
        record_format: str = "mp4",
        preview: bool = True,
        audio_mic: bool = True,
        auto_upload: bool = False,
        on_complete: Optional[Callable[[Optional[Path], float, int], None]] = None
    ) -> Tuple[bool, str]:
        """Start unlimited camera recording in a background thread."""
        target = self.get_target_device_id()
        if not target:
            return False, "No ready Android device connected."

        opts = {
            "device_id": target,
            "camera_facing": facing,
            "record_format": record_format,
            "screen_off": True,
            "no_playback": not preview,
            "audio_source": "mic" if audio_mic else None
        }

        def _worker():
            fpath, dur, sz = self.recorder.record_session("record_camera", opts, auto_upload=auto_upload)
            if on_complete:
                on_complete(fpath, dur, sz)

        t = threading.Thread(target=_worker, daemon=True, name="OmniCamRecWorker")
        t.start()
        return True, f"Camera recording started ({facing.capitalize()})! Close window to finish."

    # -------------------------------------------------------------------------
    # Dual Simultaneous Recording (PC Screen + Mobile Camera)
    # -------------------------------------------------------------------------

    def is_dual_recording(self) -> bool:
        return self._dual_recording_active

    def start_dual_recording(
        self,
        facing: str = "back",
        pc_fps: int = 30,
        camera_fps: int = 30,
        record_format: str = "mp4",
        preview: bool = True,
        auto_upload: bool = False,
        on_tick: Optional[Callable[[float, int, int], None]] = None,
        on_complete: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Tuple[bool, str]:
        """
        Start Dual Simultaneous Recording:
          - Stream 1: PC Desktop Screen -> recordings/REC_PC_SCREEN_*.mp4
          - Stream 2: Mobile Camera -> recordings/REC_MOBILE_CAMERA_*.mp4
        """
        if self._dual_recording_active:
            return False, "Dual recording is already in progress!"

        if not self.pc_recorder.is_available():
            return False, "FFmpeg is required for PC screen recording. Please install FFmpeg (e.g. 'winget install Gyan.FFmpeg')."

        target = self.get_target_device_id()
        if not target:
            return False, "No ready Android device connected. Mobile camera stream requires a connected device."

        # Verify device preflight
        check = self.adb.preflight_check(target)
        if check["status"] != "DEVICE CONNECTED":
            return False, f"Android device is not ready: {check['status']}"
        target = check["device_id"]

        # Wake screen & release camera lock
        self.adb.wake_screen(target)
        self.adb.release_camera_lock(target)

        pc_file, cam_file = self.recorder.generate_dual_filenames(fmt=record_format)

        cam_opts = {
            "device_id": target,
            "camera_facing": facing,
            "camera_fps": camera_fps,
            "record_file": str(cam_file),
            "record_format": record_format,
            "audio_source": "mic",
            "no_playback": not preview,
            "window_title": "OmniCapture - Mobile Camera Feed (Dual Mode)"
        }
        cam_cmd = self.scrcpy.build_command("record_camera", cam_opts)
        scrcpy_env = self.scrcpy.get_scrcpy_env(self.adb.adb_path)

        cam_log_path = self.recordings_dir / ".scrcpy_cam_last.log"
        cam_log_file = open(cam_log_path, "w", encoding="utf-8", errors="replace")

        # Launch scrcpy camera
        cam_start_ns = time.perf_counter_ns()
        try:
            cam_proc = subprocess.Popen(
                cam_cmd,
                env=scrcpy_env,
                stdout=cam_log_file,
                stderr=cam_log_file
            )
        except Exception as e:
            cam_log_file.close()
            return False, f"Failed to start mobile camera process: {e}"

        # Launch PC screen recorder
        pc_start_ns = time.perf_counter_ns()
        try:
            pc_proc, pc_log_file = self.pc_recorder.start_recording(
                pc_file, fps=pc_fps, phone_file=cam_file
            )
        except Exception as e:
            if cam_proc.poll() is None:
                cam_proc.terminate()
            cam_log_file.close()
            return False, f"Failed to start PC screen recording: {e}"

        # Assign child processes to Win32 Job Object for process hygiene (zero orphans on crash/close)
        try:
            from core.process_job import ProcessJobManager
            pjm = ProcessJobManager.get_instance()
            pjm.assign_process(cam_proc)
            pjm.assign_process(pc_proc)
        except Exception:
            pass

        # Write timeline editor sync sidecar file
        try:
            is_sim = hasattr(self, "simulated_engine") and self.simulated_engine is not None
            self.pc_recorder.generate_sync_sidecar(
                pc_file, cam_file, pc_start_ns, cam_start_ns, is_simulated=is_sim
            )
        except Exception:
            pass

        # Healthcheck (wait 1.2s to confirm neither crashed on startup)
        time.sleep(1.2)
        cam_early = cam_proc.poll()
        pc_early = pc_proc.poll()

        if cam_early is not None:
            cam_log_file.close()
            self.pc_recorder.stop_recording(pc_proc, pc_log_file)
            self.pc_recorder.verify_recording_file(pc_file)
            self.pc_recorder.verify_recording_file(cam_file)
            err_msg = ""
            if cam_log_path.exists():
                try:
                    err_msg = cam_log_path.read_text(encoding="utf-8", errors="replace").strip()
                except Exception:
                    pass
            return False, f"Mobile camera crashed on startup (Code {cam_early}): {err_msg[:200]}"

        if pc_early is not None:
            if cam_proc.poll() is None:
                cam_proc.terminate()
            cam_log_file.close()
            self.pc_recorder.stop_recording(pc_proc, pc_log_file)
            self.pc_recorder.verify_recording_file(pc_file)
            self.pc_recorder.verify_recording_file(cam_file)
            return False, f"PC screen recorder crashed on startup (Code {pc_early})."

        # Recording successfully initialized!
        start_time = time.time()
        self._dual_recording_active = True
        self._dual_stop_event.clear()
        self._disk_critical_stopped = False
        self._dual_rec_data = {
            "pc_proc": pc_proc,
            "pc_log_file": pc_log_file,
            "pc_file": pc_file,
            "cam_proc": cam_proc,
            "cam_log_file": cam_log_file,
            "cam_file": cam_file,
            "start_time": start_time,
            "auto_upload": auto_upload,
            "on_complete": on_complete
        }

        # Background ticker & safety monitor thread
        def _ticker():
            stop_bytes = int(self.config.get("disk_stop_mb", 500)) * 1024 * 1024
            while self._dual_recording_active and not self._dual_stop_event.is_set():
                elapsed = time.time() - start_time
                pc_sz = pc_file.stat().st_size if pc_file.exists() else 0
                cam_sz = cam_file.stat().st_size if cam_file.exists() else 0

                # Continuous disk safety threshold monitor
                free_bytes = self.pc_recorder.get_disk_free_bytes(self.recordings_dir)
                if free_bytes < stop_bytes:
                    self._disk_critical_stopped = True
                    self.stop_dual_recording()
                    break

                if on_tick:
                    try:
                        on_tick(elapsed, pc_sz, cam_sz)
                    except Exception:
                        pass
                # Check if mobile device was unplugged or camera window closed
                if cam_proc.poll() is not None:
                    # Finalize recording safely so PC file is not lost
                    self.stop_dual_recording()
                    break
                time.sleep(0.5)

        self._dual_timer_thread = threading.Thread(target=_ticker, daemon=True, name="OmniDualTicker")
        self._dual_timer_thread.start()

        return True, "Dual Simultaneous Recording ACTIVE!"

    def stop_dual_recording(self) -> Dict[str, Any]:
        """Stop Dual Recording, finalize files, verify integrity, and optionally upload."""
        if not self._dual_recording_active or not self._dual_rec_data:
            return {"success": False, "status": "FAILED", "error": "No dual recording active."}

        self._dual_stop_event.set()
        data = self._dual_rec_data
        self._dual_recording_active = False

        start_time = data["start_time"]
        duration = time.time() - start_time
        pc_proc = data["pc_proc"]
        pc_log_file = data["pc_log_file"]
        pc_file = data["pc_file"]
        cam_proc = data["cam_proc"]
        cam_log_file = data["cam_log_file"]
        cam_file = data["cam_file"]
        auto_upload = data.get("auto_upload", False)
        on_complete = data.get("on_complete")

        # Stop PC recorder gracefully
        self.pc_recorder.stop_recording(pc_proc, pc_log_file)

        # Stop Mobile Camera scrcpy gracefully
        if cam_proc.poll() is None:
            cam_proc.terminate()
            try:
                cam_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                cam_proc.kill()
        try:
            cam_log_file.close()
        except Exception:
            pass

        time.sleep(0.8)  # allow filesystem flush

        pc_valid, pc_size = self.pc_recorder.verify_recording_file(pc_file)
        cam_valid, cam_size = self.pc_recorder.verify_recording_file(cam_file)

        if pc_valid and cam_valid and pc_size > 0 and cam_size > 0:
            status = "SUCCESS"
            success = True
        elif (pc_valid and pc_size > 0) or (cam_valid and cam_size > 0):
            status = "PARTIAL SUCCESS"
            success = False
        else:
            status = "FAILED"
            success = False

        result = {
            "success": success,
            "status": status,
            "duration": duration,
            "duration_formatted": self.recorder.format_duration(duration),
            "pc_screen_file": pc_file if (pc_valid and pc_size > 0) else None,
            "pc_screen_size": pc_size,
            "pc_screen_size_formatted": self.recorder.format_size(pc_size),
            "mobile_camera_file": cam_file if (cam_valid and cam_size > 0) else None,
            "mobile_camera_size": cam_size,
            "mobile_camera_size_formatted": self.recorder.format_size(cam_size),
        }

        # Auto upload if requested
        if auto_upload:
            if result["pc_screen_file"]:
                self.uploader.upload_file(str(result["pc_screen_file"]))
            if result["mobile_camera_file"]:
                self.uploader.upload_file(str(result["mobile_camera_file"]))

        self._dual_rec_data = None
        if on_complete:
            try:
                on_complete(result)
            except Exception:
                pass

        return result

    # -------------------------------------------------------------------------
    # Recordings Gallery & File Operations
    # -------------------------------------------------------------------------

    def get_recordings_list(self) -> List[Dict[str, Any]]:
        """Return list of valid recording files sorted newest first using fast os.scandir."""
        items = []
        rec_dir_str = str(self.recordings_dir)
        if not os.path.exists(rec_dir_str):
            return items

        try:
            with os.scandir(rec_dir_str) as entries:
                for entry in entries:
                    if entry.is_file() and entry.name.lower().endswith((".mp4", ".mkv")):
                        try:
                            stat = entry.stat()
                            if stat.st_size == 0:
                                continue
                            mtime = stat.st_mtime
                            mtime_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
                            size_str = self.recorder.format_size(stat.st_size)

                            tag = "Recording"
                            if "REC_PC_SCREEN" in entry.name:
                                tag = "PC Screen"
                            elif "REC_MOBILE_CAMERA" in entry.name:
                                tag = "Mobile Camera"
                            elif "REC_MOBILE_SCREEN" in entry.name:
                                tag = "Mobile Screen"

                            items.append({
                                "name": entry.name,
                                "path": Path(entry.path),
                                "tag": tag,
                                "size": stat.st_size,
                                "size_str": size_str,
                                "mtime": mtime,
                                "mtime_str": mtime_str
                            })
                        except Exception:
                            pass
        except Exception:
            pass

        items.sort(key=lambda x: x["mtime"], reverse=True)
        return items

    def open_recording_file(self, file_path: Path | str) -> bool:
        """Open video file in the user's default system player."""
        p = Path(file_path)
        if not p.is_file():
            return False
        try:
            if sys.platform == "win32":
                os.startfile(str(p))
            else:
                subprocess.Popen(["xdg-open", str(p)])
            return True
        except Exception:
            return False

    def open_recordings_folder(self) -> bool:
        """Open the recordings folder in Windows Explorer."""
        try:
            if sys.platform == "win32":
                os.startfile(str(self.recordings_dir))
            else:
                subprocess.Popen(["xdg-open", str(self.recordings_dir)])
            return True
        except Exception:
            return False
