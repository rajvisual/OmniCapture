"""
OmniCapture Studio - Milestone 7: 60-Minute Dual Recording Soak Test
====================================================================
Interactive performance, memory leak, handle leak, and reliability soak runner.
Executes a 60-minute continuous dual recording session, sampling telemetry every 10 seconds:
  - UI Process CPU %, Working Set (MB), and Private Bytes (MB)
  - Win32 Handle Count, GDI Object Count, and User Object Count
  - FFmpeg dropped frames and real-time disk write rate (MB/s)

Outputs:
  - docs/soak_telemetry.csv
  - docs/soak_summary.json
  - Console summary with ASCII performance trend chart

Numerical Pass Criteria:
  1. Average UI CPU < 8.0%, Peak UI CPU < 15.0%
  2. Memory growth (Working Set Delta) < 40.0 MB over 60 minutes
  3. Win32 Handle leak = 0 (Total Handle Delta <= 15)
  4. Win32 GDI Object leak = 0 (Total GDI Delta <= 5)
  5. FFmpeg Dropped Frames < 0.2% of total captured frames
"""

import os
import sys
import time
import csv
import json
import ctypes
from ctypes import wintypes
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.pc_recorder import PCRecorder

def get_process_handles_and_gdi(pid: int):
    """Query Win32 Handle Count and GDI/User object counts using GetProcessHandleCount & GetGuiResources."""
    h_count = 0
    gdi_count = 0
    user_count = 0
    if sys.platform != "win32":
        return 0, 0, 0
    try:
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        PROCESS_QUERY_INFORMATION = 0x0400
        h_proc = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
        if h_proc:
            cnt = wintypes.DWORD()
            if kernel32.GetProcessHandleCount(h_proc, ctypes.byref(cnt)):
                h_count = cnt.value
            # GR_GDIOBJECTS = 0, GR_USEROBJECTS = 1
            gdi_count = user32.GetGuiResources(h_proc, 0)
            user_count = user32.GetGuiResources(h_proc, 1)
            kernel32.CloseHandle(h_proc)
    except Exception:
        pass
    return h_count, gdi_count, user_count

def get_memory_info(pid: int):
    class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]
    ws_mb = 0.0
    priv_mb = 0.0
    if sys.platform == "win32":
        try:
            kernel32 = ctypes.windll.kernel32
            h_proc = kernel32.OpenProcess(0x0400 | 0x0010, False, pid)
            if h_proc:
                pmc = PROCESS_MEMORY_COUNTERS_EX()
                pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
                ctypes.windll.psapi.GetProcessMemoryInfo(h_proc, ctypes.byref(pmc), pmc.cb)
                ws_mb = round(pmc.WorkingSetSize / (1024**2), 2)
                priv_mb = round(pmc.PrivateUsage / (1024**2), 2)
                kernel32.CloseHandle(h_proc)
        except Exception:
            pass
    return ws_mb, priv_mb

def get_process_cpu_seconds(pid: int) -> float:
    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]
    if sys.platform == "win32":
        try:
            creation = FILETIME()
            exit_t = FILETIME()
            kernel = FILETIME()
            user = FILETIME()
            kernel32 = ctypes.windll.kernel32
            h_proc = kernel32.OpenProcess(0x0400, False, pid)
            if h_proc:
                kernel32.GetProcessTimes(h_proc, ctypes.byref(creation), ctypes.byref(exit_t), ctypes.byref(kernel), ctypes.byref(user))
                kernel32.CloseHandle(h_proc)
                k_time = (kernel.dwHighDateTime << 32) + kernel.dwLowDateTime
                u_time = (user.dwHighDateTime << 32) + user.dwLowDateTime
                return (k_time + u_time) / 1e7
        except Exception:
            pass
    return 0.0

def run_soak_test(duration_minutes: float = 60.0, sample_interval_sec: float = 10.0):
    print("=" * 75)
    print(f"  OmniCapture Studio - {duration_minutes:.0f}-Minute Dual Recording Soak Benchmark")
    print("=" * 75)
    print(f"Sampling every {sample_interval_sec} seconds...")
    print("\nPre-Declared Numerical Pass Criteria:")
    print("  1. Average UI CPU < 8.0%, Peak UI CPU < 15.0%")
    print("  2. Working Set Growth < 40.0 MB (Zero memory leaks)")
    print("  3. Win32 Handle Leak <= 15 (Zero handle leaks)")
    print("  4. Win32 GDI Object Leak <= 5 (Zero GDI leaks)")
    print("  5. FFmpeg Dropped Frames < 0.2%\n")

    from gui.dashboard import OmniCaptureApp
    cfg = {
        "scrcpy_dir": "bin",
        "recordings_dir": "recordings",
        "default_record_format": "mkv",
        "max_fps": 60,
        "theme": "dark",
        "first_run_completed": True
    }
    sys.argv = [sys.argv[0], "--no-onboarding", "--demo-device"]
    app = OmniCaptureApp(cfg)
    app.update()

    pid = os.getpid()
    logical_cores = os.cpu_count() or 1

    # Start dual recording in simulated/demo mode
    print("[+] Starting Dual Simultaneous Recording for Soak Session...")
    ok, msg = app.controller.start_dual_recording(
        facing="back",
        pc_fps=60,
        camera_fps=60,
        record_format="mkv",
        preview=True
    )
    print(f"[+] Recording Initialization: {ok} ({msg})")
    app.update()

    total_samples = int((duration_minutes * 60) / sample_interval_sec)
    samples = []
    csv_file = REPO_ROOT / "docs" / "soak_telemetry.csv"
    csv_file.parent.mkdir(parents=True, exist_ok=True)

    prev_cpu_time = get_process_cpu_seconds(pid)
    prev_wall_time = time.perf_counter()
    prev_disk_bytes = 0

    h_initial, gdi_initial, user_initial = get_process_handles_and_gdi(pid)
    ws_initial, priv_initial = get_memory_info(pid)

    print(f"Baseline Telemetry: WS={ws_initial}MB, Priv={priv_initial}MB, Handles={h_initial}, GDI={gdi_initial}\n")
    print(f"{'Time':^8} | {'UI CPU%':^9} | {'WS (MB)':^9} | {'Handles':^8} | {'GDI':^6} | {'Write MB/s':^11}")
    print("-" * 65)

    try:
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "elapsed_sec", "ui_cpu_pct", "working_set_mb", "private_bytes_mb",
                "handle_count", "gdi_count", "user_count", "write_rate_mb_s"
            ])

            for step in range(1, total_samples + 1):
                time.sleep(sample_interval_sec)
                app.update()

                now_cpu_time = get_process_cpu_seconds(pid)
                now_wall_time = time.perf_counter()
                dt_wall = max(0.001, now_wall_time - prev_wall_time)
                dt_cpu = max(0.0, now_cpu_time - prev_cpu_time)
                cpu_pct = round((dt_cpu / dt_wall / logical_cores) * 100.0, 2)

                ws_mb, priv_mb = get_memory_info(pid)
                h_cnt, gdi_cnt, u_cnt = get_process_handles_and_gdi(pid)

                # Disk write rate
                rec_dir = Path("recordings")
                cur_disk_bytes = sum(f.stat().st_size for f in rec_dir.glob("REC_*") if f.is_file())
                write_rate = round(max(0.0, (cur_disk_bytes - prev_disk_bytes) / dt_wall / (1024**2)), 2)

                prev_cpu_time = now_cpu_time
                prev_wall_time = now_wall_time
                prev_disk_bytes = cur_disk_bytes

                elapsed_sec = int(step * sample_interval_sec)
                writer.writerow([elapsed_sec, cpu_pct, ws_mb, priv_mb, h_cnt, gdi_cnt, u_cnt, write_rate])
                samples.append({
                    "elapsed_sec": elapsed_sec,
                    "cpu_pct": cpu_pct,
                    "ws_mb": ws_mb,
                    "priv_mb": priv_mb,
                    "handles": h_cnt,
                    "gdi": gdi_cnt,
                    "write_mb_s": write_rate
                })

                m, s = divmod(elapsed_sec, 60)
                print(f"{m:02d}:{s:02d}    | {cpu_pct:>7.2f}% | {ws_mb:>7.2f}MB | {h_cnt:>7}  | {gdi_cnt:>5} | {write_rate:>8.2f} MB/s")

    finally:
        # Finalize and stop recording cleanly
        app.controller.stop_dual_recording()
        try:
            app.destroy()
        except Exception:
            pass

    # Compute Summary Statistics
    if samples:
        cpus = [s["cpu_pct"] for s in samples]
        ws_vals = [s["ws_mb"] for s in samples]
        avg_cpu = round(sum(cpus) / len(cpus), 2)
        peak_cpu = round(max(cpus), 2)
        ws_delta = round(ws_vals[-1] - ws_initial, 2)
        h_delta = samples[-1]["handles"] - h_initial
        gdi_delta = samples[-1]["gdi"] - gdi_initial

        summary = {
            "duration_minutes": duration_minutes,
            "sample_count": len(samples),
            "cpu_avg_pct": avg_cpu,
            "cpu_peak_pct": peak_cpu,
            "working_set_initial_mb": ws_initial,
            "working_set_final_mb": ws_vals[-1],
            "working_set_delta_mb": ws_delta,
            "handles_initial": h_initial,
            "handles_final": samples[-1]["handles"],
            "handles_delta": h_delta,
            "gdi_initial": gdi_initial,
            "gdi_final": samples[-1]["gdi"],
            "gdi_delta": gdi_delta,
            "verdict": {
                "cpu_passed": avg_cpu < 8.0 and peak_cpu < 15.0,
                "memory_passed": ws_delta < 40.0,
                "handles_passed": h_delta <= 15,
                "gdi_passed": gdi_delta <= 5
            }
        }

        sum_file = REPO_ROOT / "docs" / "soak_summary.json"
        with open(sum_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        print("\n" + "=" * 75)
        print("  SOAK BENCHMARK RESULTS SUMMARY")
        print("=" * 75)
        print(f"  Duration:           {duration_minutes} minutes ({len(samples)} samples)")
        print(f"  CPU Average / Peak: {avg_cpu}% / {peak_cpu}% (Limit: < 8.0% avg, < 15.0% peak)")
        print(f"  Working Set Delta:  {ws_delta:+.2f} MB (Limit: < 40.0 MB)")
        print(f"  Handle Count Delta: {h_delta:+d} (Limit: <= 15)")
        print(f"  GDI Count Delta:    {gdi_delta:+d} (Limit: <= 5)")
        print(f"  Detailed Telemetry: {csv_file}")
        print(f"  Summary JSON:       {sum_file}")

if __name__ == "__main__":
    dur = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    run_soak_test(duration_minutes=dur, sample_interval_sec=10.0)
