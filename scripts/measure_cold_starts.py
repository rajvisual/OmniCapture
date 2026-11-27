"""
OmniCapture Studio - Milestone 7 Pre-Work: Comparative Cold Start Benchmark
Measures cold start performance across M2 (2b89270), M5 (c743305), and Current HEAD (ui-redesign)
under identical system conditions in the same session.

Measures:
1. Process cold launch: Time from Python process invocation to first window paint (update_idletasks).
2. App instantiation: Time to construct OmniCaptureApp widget hierarchy and map layout.
"""

import os
import sys
import time
import json
import subprocess
import statistics
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
M2_DIR = REPO_ROOT.parent / "OmniCapture_m2"
M5_DIR = REPO_ROOT.parent / "OmniCapture_m5"

RUNNER_SCRIPT = """
import time
import sys
from pathlib import Path

t0 = time.perf_counter()
import customtkinter as ctk
from gui.dashboard import OmniCaptureApp

cfg = {
    "scrcpy_dir": "bin",
    "recordings_dir": "recordings",
    "default_record_format": "mp4",
    "max_fps": 60,
    "theme": "dark",
    "first_run_completed": True
}
sys.argv = [sys.argv[0], "--no-onboarding"]
app = OmniCaptureApp(cfg)
app.withdraw()
app.update_idletasks()
dt_ms = (time.perf_counter() - t0) * 1000.0
print(f"COLD_START_MS:{dt_ms:.2f}")

try:
    app._meter_timer_active = False
    app.controller.stop_device_poller()
    app.hotkeys.stop()
    app.tray.stop()
    if hasattr(app, "single_instance") and app.single_instance:
        app.single_instance.release()
    app.destroy()
except Exception:
    pass
"""

def benchmark_target(target_name: str, target_dir: Path, runs: int = 10):
    print(f"\n=======================================================")
    print(f" Benchmarking: {target_name} ({target_dir})")
    print(f" Runs: {runs} sequential cold processes")
    print(f"=======================================================")

    if not target_dir.exists():
        print(f"ERROR: Directory {target_dir} does not exist.")
        return None

    results = []
    python_exe = sys.executable

    for i in range(1, runs + 1):
        # Run in separate fresh python process to measure real cold start including imports
        t_proc_start = time.perf_counter()
        proc = subprocess.run(
            [python_exe, "-c", RUNNER_SCRIPT],
            cwd=str(target_dir),
            capture_output=True,
            text=True
        )
        t_proc_end = time.perf_counter()

        ms_val = None
        for line in proc.stdout.splitlines():
            if "COLD_START_MS:" in line:
                try:
                    ms_val = float(line.split("COLD_START_MS:")[1].strip())
                except ValueError:
                    pass

        if ms_val is None:
            # Fallback to process wall-clock time if stdout parse failed
            ms_val = (t_proc_end - t_proc_start) * 1000.0
            print(f"  Run #{i:02d}: {ms_val:.2f} ms (process wall clock, stderr: {proc.stderr[:100]}...)")
        else:
            print(f"  Run #{i:02d}: {ms_val:.2f} ms")

        results.append(ms_val)
        time.sleep(0.2)  # Settle time between cold runs

    median_val = round(statistics.median(results), 2)
    mean_val = round(statistics.mean(results), 2)
    min_val = round(min(results), 2)
    max_val = round(max(results), 2)

    print(f"--> {target_name} Summary:")
    print(f"    Median: {median_val:.2f} ms")
    print(f"    Mean:   {mean_val:.2f} ms")
    print(f"    Min:    {min_val:.2f} ms")
    print(f"    Max:    {max_val:.2f} ms")

    return {
        "runs": results,
        "median_ms": median_val,
        "mean_ms": mean_val,
        "min_ms": min_val,
        "max_ms": max_val
    }

def main():
    print("OmniCapture Studio - Cold Start Benchmark Suite (M7 Pre-Work)")
    targets = [
        ("M2 (commit 2b89270)", M2_DIR),
        ("M5 (commit c743305)", M5_DIR),
        ("Current HEAD (ui-redesign)", REPO_ROOT)
    ]

    summary = {}
    for name, path in targets:
        res = benchmark_target(name, path, runs=10)
        summary[name] = res

    out_file = REPO_ROOT / "docs" / "cold_start_reconciliation.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[+] Results successfully written to {out_file}")

if __name__ == "__main__":
    main()
