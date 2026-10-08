"""Run bundled official tools in a separate, isolated Python process."""

import argparse
import ctypes
import hmac
import importlib
import json
import os
import pkgutil
import site
import sys
import threading
import time
from pathlib import Path


def watch_parent(server, parent_pid, config_path, job):
    from process_control import terminate_current_tree

    def parent_exited():
        # Do not wait for an in-flight CLI task before terminating the owned tree.
        try:
            config_path.unlink(missing_ok=True)
        finally:
            terminate_current_tree(job)

    if os.name != "nt":
        while not server.should_exit and os.getppid() == parent_pid:
            time.sleep(0.2)
        if not server.should_exit:
            parent_exited()
        return
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel.WaitForSingleObject.restype = ctypes.c_uint32
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x00100000, False, parent_pid)
    if not handle:
        parent_exited()
        return
    try:
        result = kernel.WaitForSingleObject(handle, 0xFFFFFFFF)
        if result == 0:
            parent_exited()
        else:
            print(f"Parent process watch failed: {ctypes.get_last_error()}", file=sys.stderr)
            parent_exited()
    finally:
        kernel.CloseHandle(handle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))
    from process_control import contain_current_process, terminate_current_tree
    job = contain_current_process()
    site.addsitedir(str(root / "_vendor/runtime"))
    sys.path.insert(0, str(root / "_vendor"))

    import yaml
    import uvicorn
    from mcp.server.fastmcp import FastMCP
    from mcp.server.transport_security import TransportSecuritySettings
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    import blmcp.tools as tools_package

    # Verify native dependency layouts in this process, including pywin32's .pth bootstrap.
    native_modules = ("pydantic_core._pydantic_core", "cryptography.hazmat.bindings._rust", "_cffi_backend", "yaml._yaml", "rpds.rpds")
    if os.name == "nt":
        native_modules += ("win32api",)
    native_paths = {name: str(Path(importlib.import_module(name).__file__).resolve()) for name in native_modules}
    runtime_root = (root / "_vendor/runtime").resolve()
    if any(not Path(path).is_relative_to(runtime_root) for path in native_paths.values()):
        raise RuntimeError("A native dependency was imported outside the bundled runtime")

    prompts = yaml.safe_load((root / "_vendor/blmcp/data/prompts.yml").read_text(encoding="utf-8"))
    port = config["port"]
    mcp = FastMCP(
        "blender-mcp", instructions=str(prompts["initial_instructions"]),
        host="127.0.0.1", port=port, streamable_http_path="/", stateless_http=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[f"127.0.0.1:{port}", f"localhost:{port}"],
            allowed_origins=[f"http://127.0.0.1:{port}", f"http://localhost:{port}"],
        ),
    )
    for _, name, _ in pkgutil.iter_modules(tools_package.__path__):
        if name.endswith("_toolcode") or name.startswith("_template_"):
            continue
        module = importlib.import_module(f"blmcp.tools.{name}")
        if hasattr(module, "register"):
            module.register(mcp)

    async def health(request):
        return JSONResponse({"pid": os.getpid(), "session": config["session"], "native_dependencies": sorted(native_paths)})

    app = mcp.streamable_http_app()
    app.routes.append(Route("/health", health))

    class AuthenticatedApp:
        async def __call__(self, scope, receive, send):
            if scope["type"] == "http":
                headers = dict(scope["headers"])
                host = headers.get(b"host", b"").decode("ascii", "replace")
                origin = headers.get(b"origin", b"").decode("ascii", "replace")
                if host not in {f"127.0.0.1:{port}", f"localhost:{port}"} or (
                    origin and origin not in {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
                ):
                    await JSONResponse({"error": "Host or Origin rejected"}, status_code=403)(scope, receive, send)
                    return
                authorization = headers.get(b"authorization", b"")
                expected = f"Bearer {config['token']}".encode("ascii")
                if not hmac.compare_digest(authorization, expected):
                    await JSONResponse({"error": "Authentication required"}, status_code=401)(scope, receive, send)
                    return
            await app(scope, receive, send)

    server = uvicorn.Server(uvicorn.Config(AuthenticatedApp(), host="127.0.0.1", port=port, log_level="info"))
    threading.Thread(target=watch_parent, args=(server, config["parent_pid"], args.config, job), daemon=True).start()
    try:
        server.run()
    finally:
        args.config.unlink(missing_ok=True)
        if os.name != "nt":
            terminate_current_tree(job)


if __name__ == "__main__":
    main()
