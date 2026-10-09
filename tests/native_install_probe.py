"""Observe a native installer rename without changing the installed Blender."""

import ctypes
import json
import os
import runpy
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def delete_access(path):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                  ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
    kernel.CreateFileW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.CreateFileW(str(path), 0x10000, 7, None, 3, 0x02000000, None)
    if handle == ctypes.c_void_p(-1).value:
        return {"status": "Failed", "winerror": ctypes.get_last_error()}
    kernel.CloseHandle(handle)
    return {"status": "Passed"}


def locking_processes(files):
    """Ask Windows Restart Manager; protected processes may be unavailable."""
    from ctypes import wintypes
    class UniqueProcess(ctypes.Structure):
        _fields_ = [("pid", wintypes.DWORD), ("start", wintypes.FILETIME)]
    class ProcessInfo(ctypes.Structure):
        _fields_ = [("process", UniqueProcess), ("app", wintypes.WCHAR * 256),
                    ("service", wintypes.WCHAR * 64), ("type", wintypes.DWORD),
                    ("status", wintypes.ULONG), ("session", wintypes.DWORD), ("restartable", wintypes.BOOL)]
    library = ctypes.WinDLL("rstrtmgr")
    session = wintypes.DWORD()
    key = ctypes.create_unicode_buffer(33)
    error = library.RmStartSession(ctypes.byref(session), 0, key)
    if error:
        return {"error": error}
    try:
        paths = (ctypes.c_wchar_p * len(files))(*map(str, files))
        error = library.RmRegisterResources(session, len(paths), paths, 0, None, 0, None)
        if error:
            return {"error": error}
        needed, count, reason = wintypes.UINT(), wintypes.UINT(), wintypes.DWORD()
        error = library.RmGetList(session, ctypes.byref(needed), ctypes.byref(count), None, ctypes.byref(reason))
        if error not in (0, 234):
            return {"error": error}
        if not needed.value:
            return {"processes": [], "protected_process_visibility": "Not Run"}
        entries = (ProcessInfo * needed.value)()
        count.value = needed.value
        error = library.RmGetList(session, ctypes.byref(needed), ctypes.byref(count), entries, ctypes.byref(reason))
        return {"error": error, "processes": [{"pid": item.process.pid, "app": item.app, "service": item.service}
                                                for item in entries[:count.value]]}
    finally:
        library.RmEndSession(session)


def file_handles_under(source):
    """Read accessible Windows disk handles; do not elevate or close others' handles."""
    from ctypes import wintypes
    class Entry(ctypes.Structure):
        _fields_ = [("object", ctypes.c_void_p), ("pid", ctypes.c_size_t), ("handle", ctypes.c_size_t),
                    ("access", wintypes.ULONG), ("trace", wintypes.USHORT), ("type", wintypes.USHORT),
                    ("attributes", wintypes.ULONG), ("reserved", wintypes.ULONG)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.DuplicateHandle.argtypes = [wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE,
                                      ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.GetFileType.argtypes = [wintypes.HANDLE]
    kernel.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    native = ctypes.WinDLL("ntdll").NtQuerySystemInformation
    native.argtypes = [wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG, ctypes.POINTER(wintypes.ULONG)]
    native.restype = ctypes.c_long
    # File handles include directories; hold a witness during the same snapshot.
    with Path(__file__).open("rb") as witness:
        import msvcrt
        handle = msvcrt.get_osfhandle(witness.fileno())
        size = 1024 * 1024
        while True:
            buffer = ctypes.create_string_buffer(size)
            needed = wintypes.ULONG()
            status = native(64, buffer, size, ctypes.byref(needed))
            if status == 0:
                count = ctypes.c_size_t.from_buffer(buffer).value
                used = count * ctypes.sizeof(Entry) + ctypes.sizeof(ctypes.c_size_t) * 2
                if used <= size:
                    break
            elif status != -1073741820:
                return {"ntstatus": status}
            size = max(size * 2, needed.value)
        entries = (Entry * count).from_buffer(buffer, ctypes.sizeof(ctypes.c_size_t) * 2)
        file_type = next((item.type for item in entries if item.pid == os.getpid() and item.handle == handle), None)
    if file_type is None:
        return {"error": "File handle type unavailable"}
    processes, denied, matches = {}, set(), []
    prefix = str(Path(source).resolve()).lower()
    try:
        for item in entries:
            if item.type != file_type or item.pid in denied:
                continue
            if item.pid not in processes:
                processes[item.pid] = kernel.OpenProcess(0x40, False, item.pid)
                if not processes[item.pid]:
                    denied.add(item.pid)
                    continue
            duplicate = wintypes.HANDLE()
            if not kernel.DuplicateHandle(processes[item.pid], item.handle, kernel.GetCurrentProcess(),
                                          ctypes.byref(duplicate), 0, False, 2):
                continue
            try:
                if kernel.GetFileType(duplicate) != 1:
                    continue
                name = ctypes.create_unicode_buffer(32768)
                if kernel.GetFinalPathNameByHandleW(duplicate, name, len(name), 0):
                    path = name.value.removeprefix("\\\\?\\")
                    if path.lower() == prefix or path.lower().startswith(prefix + "\\"):
                        matches.append({"pid": item.pid, "path": path, "granted_access": item.access})
            finally:
                kernel.CloseHandle(duplicate)
    finally:
        for handle in processes.values():
            if handle:
                kernel.CloseHandle(handle)
    return {"matches": matches, "inaccessible_process_ids": sorted(denied), "system_handles": count}


original, result_file, retry = sys.argv[1:4]
sys.argv = [original, *sys.argv[4:]]
records = []
native_rename = os.rename


def observe(source, destination, *args, **kwargs):
    delay = float(os.environ.get("BLENDER_MCP_PROBE_RENAME_DELAY", "0"))
    if delay:
        time.sleep(delay)
    started = time.monotonic()
    record = {"source": str(source), "destination": str(destination),
              "destination_exists": Path(destination).exists(), "pid": os.getpid(),
              "started_at": datetime.now(timezone.utc).isoformat(), "pre_rename_delay": delay,
              "administrator": bool(ctypes.windll.shell32.IsUserAnAdmin())}
    try:
        native_rename(source, destination, *args, **kwargs)
        record["status"] = "Passed"
    except OSError as error:
        record.update(status="Failed", error=str(error), winerror=error.winerror,
                      source_exists=Path(source).exists(), destination_exists=Path(destination).exists(),
                      initial_rename_seconds=round(time.monotonic() - started, 6))
        record["retry"] = []
        if retry == "bounded-retry" and error.winerror == 5:
            # This is a diagnostic wrapper around the unchanged installer.
            # Preserve the first failure even if a transient reader releases.
            for wait in (0.05, 0.1, 0.2, 0.4, 0.8):
                if not Path(source).is_dir() or Path(destination).exists():
                    record["recovery_guard"] = "source absent or destination exists"
                    break
                time.sleep(wait)
                try:
                    native_rename(source, destination, *args, **kwargs)
                except OSError as second:
                    record["retry"].append({"delay": wait, "winerror": second.winerror})
                    if second.winerror != 5:
                        raise
                else:
                    record["retry"].append({"delay": wait, "status": "Passed"})
                    record["diagnostic_recovery"] = "Passed"
                    return
        record["delete_access"] = delete_access(source)
        try:
            record["file_handles"] = file_handles_under(source)
        except (OSError, ValueError) as diagnostic_error:
            record["file_handles_error"] = str(diagnostic_error)
        files = list(Path(source).rglob("*.pyd")) + list(Path(source).rglob("*.dll"))
        record["restart_manager"] = locking_processes(files)
        if retry == "observe-recovery":
            for delay in (0, 0.01, 0.05, 0.2, 0.5):
                time.sleep(delay)
                try:
                    native_rename(source, destination, *args, **kwargs)
                except OSError as second:
                    record["retry"].append({"delay": delay, "winerror": second.winerror})
                else:
                    record["retry"].append({"delay": delay, "status": "Passed"})
                    return
        raise
    finally:
        record["seconds"] = round(time.monotonic() - started, 6)
        records.append(record)
        Path(result_file).write_text(json.dumps({"renames": records}, indent=2), encoding="utf-8")


os.rename = observe
try:
    runpy.run_path(original, run_name="__main__")
except BaseException:
    # Preserve the original exit/error semantics, with a diagnostic side channel.
    raise
