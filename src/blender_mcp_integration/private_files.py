"""Protect service credentials using POSIX modes or a private Windows DACL."""

import ctypes
import os
import secrets
from pathlib import Path


def _windows_api():
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    signatures = {
        "OpenProcessToken": [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)],
        "GetTokenInformation": [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)],
        "ConvertSidToStringSidW": [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)],
        "ConvertStringSecurityDescriptorToSecurityDescriptorW": [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.DWORD)],
        "ConvertSecurityDescriptorToStringSecurityDescriptorW": [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(wintypes.DWORD)],
        "SetFileSecurityW": [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p],
        "GetFileSecurityW": [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)],
    }
    for name, arguments in signatures.items():
        function = getattr(security, name)
        function.argtypes = arguments
        function.restype = wintypes.BOOL
    return kernel, security


def _require_windows(success):
    if not success:
        raise ctypes.WinError(ctypes.get_last_error())


def windows_user_sid():
    from ctypes import wintypes

    kernel, security = _windows_api()
    token, size = wintypes.HANDLE(), wintypes.DWORD()
    _require_windows(security.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008, ctypes.byref(token)))
    try:
        security.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        _require_windows(security.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)))
        sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        text = wintypes.LPWSTR()
        _require_windows(security.ConvertSidToStringSidW(sid, ctypes.byref(text)))
        try:
            return text.value
        finally:
            kernel.LocalFree(text)
    finally:
        kernel.CloseHandle(token)


def windows_dacl(path):
    from ctypes import wintypes

    kernel, security = _windows_api()
    size = wintypes.DWORD()
    security.GetFileSecurityW(str(path), 4, None, 0, ctypes.byref(size))
    buffer = ctypes.create_string_buffer(size.value)
    _require_windows(security.GetFileSecurityW(str(path), 4, buffer, size, ctypes.byref(size)))
    text = wintypes.LPWSTR()
    _require_windows(security.ConvertSecurityDescriptorToStringSecurityDescriptorW(buffer, 1, 4, ctypes.byref(text), None))
    try:
        return text.value
    finally:
        kernel.LocalFree(text)


def protect(path, directory=False):
    path = Path(path)
    status = path.lstat()
    if path.is_symlink() or getattr(status, "st_file_attributes", 0) & 0x400:
        raise OSError(f"Credential path must not be a link or reparse point: {path}")
    if directory != path.is_dir():
        raise OSError(f"Unexpected credential path type: {path}")
    if os.name != "nt":
        if status.st_uid != os.getuid():
            raise PermissionError(f"Credential path belongs to another user: {path}")
        path.chmod(0o700 if directory else 0o600)
        return
    kernel, security = _windows_api()
    flags = "OICI" if directory else ""
    descriptor = f"D:P(A;{flags};FA;;;SY)(A;{flags};FA;;;BA)(A;{flags};FA;;;{windows_user_sid()})"
    pointer = ctypes.c_void_p()
    _require_windows(security.ConvertStringSecurityDescriptorToSecurityDescriptorW(descriptor, 1, ctypes.byref(pointer), None))
    try:
        _require_windows(security.SetFileSecurityW(str(path), 4 | 0x80000000, pointer))
    finally:
        kernel.LocalFree(pointer)
    if windows_dacl(path) != descriptor:
        raise PermissionError(f"Private credential DACL verification failed: {path}")


def private_directory(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    protect(path, directory=True)
    return path


def write_private(path, content):
    """Replace a secret atomically; a temporary file never inherits public access."""
    path = Path(path)
    private_directory(path.parent)
    if path.exists() or path.is_symlink():
        protect(path)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(16)}.pending")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            protect(temporary)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def persistent_token(path):
    path = Path(path)
    private_directory(path.parent)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        protect(path)
        return path.read_text(encoding="utf-8").strip()
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        protect(path)
        token = secrets.token_urlsafe(32)
        stream.write(token)
    return token
