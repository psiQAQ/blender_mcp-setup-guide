"""Observe directory renames after closing child file handles but keeping mappings."""

import ctypes
import json
import os

from build_cache import LATEST, current_work
from check_reports import run_check, write_json


def rename(source, destination):
    try:
        os.rename(source, destination)
    except OSError as error:
        return {'status': 'Failed', 'winerror': error.winerror, 'error': str(error)}
    return {'status': 'Passed'}


def main():
    if os.name != 'nt':
        raise RuntimeError('This diagnostic requires Windows')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                  ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
    kernel.CreateFileW.restype = ctypes.c_void_p
    kernel.CreateFileMappingW.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32,
                                         ctypes.c_uint32, ctypes.c_uint32, ctypes.c_wchar_p]
    kernel.CreateFileMappingW.restype = ctypes.c_void_p
    kernel.MapViewOfFile.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
                                   ctypes.c_uint32, ctypes.c_size_t]
    kernel.MapViewOfFile.restype = ctypes.c_void_p
    kernel.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    work = current_work('windows-rename-sections')
    report = {'status': 'Not Run', 'cases': [],
              'scope': 'Owned files and mapping views only; no scanner attribution'}
    for number in range(3):
        for mode, protection, access in [('read', 0x02, 0x04), ('copy', 0x08, 0x01)]:
            source = work / f'{mode}-{number}' / 'staging'
            source.mkdir(parents=True)
            child = source / 'fixture.bin'
            child.write_bytes(b'owned mapping fixture' * 4096)
            destination = source.with_name('installed')
            handle = kernel.CreateFileW(str(child), 0x80000000, 7, None, 3, 0, None)
            if handle == ctypes.c_void_p(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            mapping = kernel.CreateFileMappingW(handle, None, protection, 0, 0, None)
            if not mapping:
                kernel.CloseHandle(handle)
                raise ctypes.WinError(ctypes.get_last_error())
            view = kernel.MapViewOfFile(mapping, access, 0, 0, 0)
            kernel.CloseHandle(mapping)
            kernel.CloseHandle(handle)
            if not view:
                raise ctypes.WinError(ctypes.get_last_error())
            row = {'mode': mode, 'repeat': number + 1, 'child_file_handle_closed': True,
                   'section_handle_closed': True, 'mapped_view_retained': True}
            try:
                row['with_mapping'] = rename(source, destination)
            finally:
                if not kernel.UnmapViewOfFile(view):
                    raise ctypes.WinError(ctypes.get_last_error())
            row['after_unmap'] = rename(source, destination) if source.exists() else {
                'status': 'Not Run', 'reason': 'Rename already succeeded while mapped'}
            report['cases'].append(row)
    report['status'] = 'Passed' if all(row['with_mapping']['status'] == 'Passed' or
            row['after_unmap']['status'] == 'Passed' for row in report['cases']) else 'Failed'
    write_json(LATEST / 'windows-rename-sections-tests.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    run_check('windows-rename-sections', main)
