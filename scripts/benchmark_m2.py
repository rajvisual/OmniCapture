import os
import sys
import time
import json
import statistics
import ctypes
from ctypes import wintypes
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

def get_machine_specs():
    specs = {}
    try:
        import platform
        specs["os"] = f"{platform.system()} {platform.release()} (Build {platform.version()})"
        specs["arch"] = platform.machine()
        specs["python_version"] = platform.python_version()

        # CPU info via Windows Registry
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        specs["cpu_model"] = cpu_name.strip()
        winreg.CloseKey(key)

        # Core count
        specs["cpu_count_logical"] = os.cpu_count()

        # Memory via GlobalMemoryStatusEx
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", wintypes.DWORD),
                ("dwMemoryLoad", wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_uint64),
                ("ullAvailPhys", ctypes.c_uint64),
                ("ullTotalPageFile", ctypes.c_uint64),
                ("ullAvailPageFile", ctypes.c_uint64),
                ("ullTotalVirtual", ctypes.c_uint64),
                ("ullAvailVirtual", ctypes.c_uint64),
                ("ullAvailExtendedVirtual", ctypes.c_uint64),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        specs["total_ram_gb"] = round(stat.ullTotalPhys / (1024**3), 2)
        specs["avail_ram_gb"] = round(stat.ullAvailPhys / (1024**3), 2)
    except Exception as e:
        specs["error"] = str(e)
    return specs

def get_process_memory_info(pid=None):
    """Query WorkingSet and PrivateBytes using Win32 GetProcessMemoryInfo."""
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
    kernel32 = ctypes.windll.kernel32
    h_proc = kernel32.OpenProcess(0x0400 | 0x0010, False, kernel32.GetCurrentProcessId())
    pmc = PROCESS_MEMORY_COUNTERS_EX()
    pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
    ctypes.windll.psapi.GetProcessMemoryInfo(h_proc, ctypes.byref(pmc), pmc.cb)
    kernel32.CloseHandle(h_proc)
    return {
        "working_set_mb": round(pmc.WorkingSetSize / (1024**2), 2),
        "peak_working_set_mb": round(pmc.PeakWorkingSetSize / (1024**2), 2),
        "private_bytes_mb": round(pmc.PrivateUsage / (1024**2), 2),
    }

def get_process_cpu_time():
    """Query Kernel and User CPU times using GetProcessTimes."""
    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

    creation = FILETIME()
    exit_t = FILETIME()
    kernel = FILETIME()
    user = FILETIME()
    kernel32 = ctypes.windll.kernel32
    h_proc = kernel32.OpenProcess(0x0400, False, kernel32.GetCurrentProcessId())
    kernel32.GetProcessTimes(h_proc, ctypes.byref(creation), ctypes.byref(exit_t), ctypes.byref(kernel), ctypes.byref(user))
    kernel32.CloseHandle(h_proc)
    k_time = (kernel.dwHighDateTime << 32) + kernel.dwLowDateTime
    u_time = (user.dwHighDateTime << 32) + user.dwLowDateTime
    return (k_time + u_time) / 1e7  # 100ns units to seconds

def measure_cold_starts(runs=10):
    print(f"\n[+] Measuring Cold Start Time across {runs} sequential runs...")
    times_ms = []
    from gui.dashboard import OmniCaptureApp

    cfg = {
        "scrcpy_dir": "bin",
        "recordings_dir": "recordings",
        "default_record_format": "mp4",
        "max_fps": 60,
    }

    for i in range(1, runs + 1):
        t0 = time.perf_counter()
        app = OmniCaptureApp(cfg)
        app.withdraw()
        app.update_idletasks()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        times_ms.append(round(dt_ms, 2))
        print(f"    Run #{i:02d}: {dt_ms:.2f} ms")

        # Cleanup
        app._meter_timer_active = False
        app.controller.stop_device_poller()
        app.hotkeys.stop()
        app.tray.stop()
        app.single_instance.release()
        try:
            for after_id in app.tk.eval("after info").split():
                try:
                    app.after_cancel(after_id)
                except Exception:
                    pass
        except Exception:
            pass
        app.destroy()
        time.sleep(0.15)

    return {
        "runs": times_ms,
        "median_ms": round(statistics.median(times_ms), 2),
        "mean_ms": round(statistics.mean(times_ms), 2),
        "min_ms": round(min(times_ms), 2),
        "max_ms": round(max(times_ms), 2),
    }

def measure_idle_and_recording_telemetry(idle_seconds=60, rec_seconds=60):
    from gui.dashboard import OmniCaptureApp

    cfg = {
        "scrcpy_dir": "bin",
        "recordings_dir": "recordings",
        "default_record_format": "mp4",
        "max_fps": 60,
    }

    print(f"\n[+] Launching OmniCaptureApp for telemetry measurement...")
    app = OmniCaptureApp(cfg)
    app.update_idletasks()

    num_logical_cores = os.cpu_count() or 1

    # 1. Measure Idle (60 seconds)
    print(f"[+] Measuring Idle CPU & RAM for {idle_seconds} seconds (sampling every 1s)...")
    idle_cpu_samples = []
    idle_ram_samples = []

    last_cpu_time = get_process_cpu_time()
    last_wall_time = time.perf_counter()

    for sec in range(1, idle_seconds + 1):
        time.sleep(1.0)
        app.update()
        now_cpu_time = get_process_cpu_time()
        now_wall_time = time.perf_counter()

        delta_cpu = now_cpu_time - last_cpu_time
        delta_wall = now_wall_time - last_wall_time
        cpu_pct = (delta_cpu / (delta_wall * num_logical_cores)) * 100.0
        idle_cpu_samples.append(cpu_pct)

        mem = get_process_memory_info()
        idle_ram_samples.append(mem["working_set_mb"])

        last_cpu_time = now_cpu_time
        last_wall_time = now_wall_time
        if sec % 10 == 0 or sec == idle_seconds:
            print(f"    [Idle {sec:02d}s] CPU: {cpu_pct:.2f}% | RAM: {mem['working_set_mb']:.1f} MB (Peak: {mem['peak_working_set_mb']:.1f} MB, Private: {mem['private_bytes_mb']:.1f} MB)")

    # 2. Measure Recording UI Overhead (60 seconds)
    print(f"\n[+] Measuring UI Overhead during 60s active dual recording simulation...")
    # Simulate dual recording UI state (HUD visible, pulse timer active, tally ticking)
    app.cv_recording_hud.place(relx=0.5, rely=0.08, anchor="n")
    app._recording_pulse_active = True
    app.foot_status_chip.set_status("RECORDING", state="recording")

    rec_cpu_samples = []
    rec_ram_samples = []

    last_cpu_time = get_process_cpu_time()
    last_wall_time = time.perf_counter()

    for sec in range(1, rec_seconds + 1):
        # Update tally HUD tick
        m, s = divmod(sec, 60)
        time_str = f"00:{m:02d}:{s:02d}"
        pc_mb = sec * 0.95
        cam_mb = sec * 0.82
        stats_str = f"PC: {pc_mb:.1f} MB  ·  Cam: {cam_mb:.1f} MB"
        app._update_tally(time_str, stats_str)

        time.sleep(1.0)
        app.update()

        now_cpu_time = get_process_cpu_time()
        now_wall_time = time.perf_counter()

        delta_cpu = now_cpu_time - last_cpu_time
        delta_wall = now_wall_time - last_wall_time
        cpu_pct = (delta_cpu / (delta_wall * num_logical_cores)) * 100.0
        rec_cpu_samples.append(cpu_pct)

        mem = get_process_memory_info()
        rec_ram_samples.append(mem["working_set_mb"])

        last_cpu_time = now_cpu_time
        last_wall_time = now_wall_time
        if sec % 10 == 0 or sec == rec_seconds:
            print(f"    [Rec {sec:02d}s] UI CPU: {cpu_pct:.2f}% | RAM: {mem['working_set_mb']:.1f} MB")

    # Cleanup
    app._recording_pulse_active = False
    app._meter_timer_active = False
    app.controller.stop_device_poller()
    app.hotkeys.stop()
    app.tray.stop()
    app.single_instance.release()
    app.destroy()

    final_mem = get_process_memory_info()

    return {
        "idle_cpu_avg_pct": round(statistics.mean(idle_cpu_samples), 2),
        "idle_cpu_max_pct": round(max(idle_cpu_samples), 2),
        "idle_ram_avg_mb": round(statistics.mean(idle_ram_samples), 2),
        "idle_ram_peak_mb": round(final_mem["peak_working_set_mb"], 2),
        "idle_ram_private_mb": round(final_mem["private_bytes_mb"], 2),
        "rec_ui_cpu_avg_pct": round(statistics.mean(rec_cpu_samples), 2),
        "rec_ui_cpu_max_pct": round(max(rec_cpu_samples), 2),
        "rec_ram_avg_mb": round(statistics.mean(rec_ram_samples), 2),
    }

def main():
    print("=" * 70)
    print("  OMNICAPTURE STUDIO MILESTONE 2 REAL BENCHMARK SUITE")
    print("=" * 70)

    specs = get_machine_specs()
    print("\n--- HOST MACHINE SPECIFICATIONS ---")
    for k, v in specs.items():
        print(f"  {k}: {v}")

    cold_start = measure_cold_starts(runs=10)
    print("\n--- COLD START RESULTS (10 RUNS) ---")
    print(f"  Median Cold Start: {cold_start['median_ms']} ms ({cold_start['median_ms']/1000.0:.3f} s)")
    print(f"  Mean Cold Start:   {cold_start['mean_ms']} ms")
    print(f"  Min / Max Range:   {cold_start['min_ms']} ms / {cold_start['max_ms']} ms")

    telemetry = measure_idle_and_recording_telemetry(idle_seconds=60, rec_seconds=60)
    print("\n--- 60-SECOND IDLE TELEMETRY ---")
    print(f"  Idle CPU (60s Avg):   {telemetry['idle_cpu_avg_pct']}%")
    print(f"  Idle CPU (Peak):      {telemetry['idle_cpu_max_pct']}%")
    print(f"  Idle RAM (WorkingSet): {telemetry['idle_ram_avg_mb']} MB (Peak: {telemetry['idle_ram_peak_mb']} MB)")
    print(f"  Idle RAM (Private):   {telemetry['idle_ram_private_mb']} MB")

    print("\n--- 60-SECOND DUAL RECORDING UI OVERHEAD ---")
    print(f"  UI Overhead CPU (60s Avg): {telemetry['rec_ui_cpu_avg_pct']}%")
    print(f"  UI Overhead CPU (Peak):    {telemetry['rec_ui_cpu_max_pct']}%")
    print(f"  Recording RAM (Avg):       {telemetry['rec_ram_avg_mb']} MB")

    out_file = BASE_DIR / "docs" / "benchmarks_m2.json"
    result_data = {
        "machine_specs": specs,
        "cold_start": cold_start,
        "telemetry": telemetry,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    out_file.write_text(json.dumps(result_data, indent=2), encoding="utf-8")
    print(f"\n[✓] Benchmark results saved to {out_file}")

if __name__ == "__main__":
    main()
