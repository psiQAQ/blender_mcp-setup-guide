"""Check Windows directory rename behavior with a controlled child file handle."""

import ctypes
import json
import os
import time
from pathlib import Path

from build_cache import LATEST, current_work
from check_reports import run_check, write_json


def main():
    if os.name != "nt":
        raise RuntimeError("This diagnostic requires native Windows")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                  ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
    kernel.CreateFileW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    report = {"status": "Not Run", "mode": "controlled local handles; no real scanner attribution", "cases": []}
    work = current_work("windows-rename-contract")
    for kind, share in ((kind, share) for kind in ("file", "directory") for share in (3, 7)):
        source = work / f"{kind}-share-{share}" / "staging"
        source.mkdir(parents=True)
        child = source / ("fixture.txt" if kind == "file" else "child")
        if kind == "file":
            child.write_text("owned diagnostic file", encoding="utf-8")
        else:
            child.mkdir()
        destination = source.with_name("installed")
        handle = kernel.CreateFileW(str(child), 0x80000000, share, None, 3,
                                    0x02000000 if kind == "directory" else 0, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        item = {"child_kind": kind, "share_mask": share, "file_share_delete": bool(share & 4), "attempts": []}
        try:
            folder = kernel.CreateFileW(str(source), 0x10000, 7, None, 3, 0x02000000, None)
            item["directory_delete_access"] = "Passed" if folder != ctypes.c_void_p(-1).value else "Failed"
            if item["directory_delete_access"] == "Passed":
                kernel.CloseHandle(folder)
            for delay in (0, 0.25):
                if destination.exists():
                    break
                time.sleep(delay)
                try:
                    os.rename(source, destination)
                except OSError as error:
                    item["attempts"].append({"delay": delay, "status": "Failed", "winerror": error.winerror})
                else:
                    item["attempts"].append({"delay": delay, "status": "Passed"})
        finally:
            kernel.CloseHandle(handle)
        if source.exists():
            os.rename(source, destination)
            item["after_handle_closed"] = "Passed"
        report["cases"].append(item)
    report["status"] = "Passed"
    write_json(LATEST / "windows-rename-contract-tests.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run_check("windows-rename-contract", main)
