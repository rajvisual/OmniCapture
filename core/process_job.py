"""
OmniCapture Studio - Windows Process Hygiene & Job Object Management
=====================================================================
Ensures zero orphaned child processes (ffmpeg, scrcpy, adb) remain running
after normal exit, crash, forced termination, or OS shutdown/logoff.

Architecture:
1. Windows Win32 Job Object with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE (0x2000).
   Any child process assigned to this Job Object is automatically terminated
   by the Windows OS kernel when the parent process exits or terminates.
2. Recursive process-tree cleaner fallback (taskkill /T /F /PID) for processes
   not attached to the Job Object.
"""

import os
import sys
import ctypes
from ctypes import wintypes
from typing import Optional, List
import subprocess

JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000

class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
        ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]

class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]

class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryLimit", ctypes.c_size_t),
        ("PeakJobMemoryLimit", ctypes.c_size_t),
    ]

class ProcessJobManager:
    """Manages a Win32 Job Object ensuring child processes are killed on parent close."""

    _instance: Optional["ProcessJobManager"] = None

    def __init__(self):
        self.h_job = None
        self._tracked_pids: List[int] = []
        if sys.platform == "win32":
            self._init_job_object()

    @classmethod
    def get_instance(cls) -> "ProcessJobManager":
        if cls._instance is None:
            cls._instance = ProcessJobManager()
        return cls._instance

    def _init_job_object(self):
        try:
            kernel32 = ctypes.windll.kernel32
            # Create anonymous Job Object
            self.h_job = kernel32.CreateJobObjectW(None, None)
            if not self.h_job:
                return

            # Configure JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            
            JobObjectExtendedLimitInformation = 9
            res = kernel32.SetInformationJobObject(
                self.h_job,
                JobObjectExtendedLimitInformation,
                ctypes.byref(info),
                ctypes.sizeof(info)
            )
            if res:
                # Assign current python process to job object so all spawned children inherit it
                h_current = kernel32.GetCurrentProcess()
                kernel32.AssignProcessToJobObject(self.h_job, h_current)
        except Exception:
            self.h_job = None

    def assign_process(self, proc_or_pid) -> bool:
        """Assign an active subprocess.Popen or PID to the Job Object."""
        pid = proc_or_pid.pid if hasattr(proc_or_pid, "pid") else int(proc_or_pid)
        self._tracked_pids.append(pid)

        if sys.platform != "win32" or not self.h_job:
            return False

        try:
            kernel32 = ctypes.windll.kernel32
            PROCESS_SET_QUOTA = 0x0100
            PROCESS_TERMINATE = 0x0001
            h_proc = kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, pid)
            if h_proc:
                ok = kernel32.AssignProcessToJobObject(self.h_job, h_proc)
                kernel32.CloseHandle(h_proc)
                return bool(ok)
        except Exception:
            pass
        return False

    def cleanup_all(self):
        """Forcefully terminate all tracked child processes and their descendant trees."""
        for pid in list(self._tracked_pids):
            self.terminate_process_tree(pid)
        self._tracked_pids.clear()

    @staticmethod
    def terminate_process_tree(proc_or_pid):
        """Terminate a process and all its child processes using taskkill /T /F."""
        pid = proc_or_pid.pid if hasattr(proc_or_pid, "pid") else int(proc_or_pid)
        if sys.platform == "win32":
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    timeout=3,
                    check=False
                )
            except Exception:
                pass
        else:
            try:
                import signal
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass

        if hasattr(proc_or_pid, "poll"):
            try:
                proc_or_pid.kill()
                proc_or_pid.wait(timeout=1)
            except Exception:
                pass
