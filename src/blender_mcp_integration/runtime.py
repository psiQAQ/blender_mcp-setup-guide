"""Own one authenticated MCP service process for a Blender instance."""

import json
import os
import platform
import re
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


class ServiceError(RuntimeError):
    pass


def platform_id():
    system, machine = platform.system(), platform.machine().lower()
    if machine in {"amd64", "x86_64"}:
        if system == "Windows":
            return "windows-x64"
        if system == "Linux":
            return "linux-x64"
    if system == "Darwin" and machine in {"arm64", "aarch64"}:
        return "macos-arm64"
    raise ServiceError(f"Unsupported platform: {system} {machine}")


def process_options(gui=False):
    if os.name != "nt":
        return {}
    if not gui:
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    return {"startupinfo": startup}


def check_runtime():
    identifier = platform_id()
    if platform.python_implementation() != "CPython" or sys.version_info[:2] != (3, 13):
        raise ServiceError("This package requires Blender's CPython 3.13")
    provenance = Path(__file__).with_name("provenance.json")
    if provenance.exists() and json.loads(provenance.read_text(encoding="utf-8"))["platform"] != identifier:
        raise ServiceError(f"Install the {identifier} package for this runtime")


def require_free_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if os.name == "nt":
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as error:
            raise ServiceError(f"Port {port} is already in use") from error


def client_configuration(client, port, token):
    url = f"http://127.0.0.1:{port}/"
    headers = {"Authorization": f"Bearer {token}"}
    if client == "CODEX":
        return (
            '[mcp_servers.blender]\n'
            f'url = {json.dumps(url)}\n'
            f'http_headers = {{ Authorization = {json.dumps(headers["Authorization"])} }}\n'
        )
    if client == "CLAUDE":
        return json.dumps({"mcpServers": {"blender": {"type": "http", "url": url, "headers": headers}}}, indent=2)
    if client == "OPENCODE":
        return json.dumps({"mcp": {"blender": {"type": "remote", "url": url, "headers": headers}}}, indent=2)
    raise ValueError(f"Unknown MCP client: {client}")


class Service:
    def __init__(self):
        self.process = None
        self.log_handle = None
        self.directory = None
        self.config_path = None
        self.token = ""
        self.bridge_token = ""
        self.port = 0
        self.state = "Stopped"
        self.started_at = 0.0
        self.session = ""

    def start(self, directory, port, bridge_port, python_args=()):
        check_runtime()
        if self.process is not None or self.log_handle is not None or self.config_path is not None:
            raise ServiceError("Finish cleaning up the current service before starting it again")
        if port == bridge_port:
            raise ServiceError("HTTP and bridge ports must differ")
        require_free_port(port)
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.port = port
        token_path = self.directory / "http-token.txt"
        if token_path.exists():
            self.token = token_path.read_text(encoding="utf-8").strip()
        else:
            self.token = secrets.token_urlsafe(32)
            token_path.write_text(self.token, encoding="utf-8")
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,}", self.token):
            raise ServiceError("Invalid HTTP token file; remove it and start again")
        self.bridge_token = secrets.token_urlsafe(32)
        session = secrets.token_hex(16)
        self.session = session
        self.config_path = self.directory / f"session-{session}.json"
        configuration = {
            "port": port, "bridge_port": bridge_port,
            "token": self.token, "bridge_token": self.bridge_token,
            "session": session, "parent_pid": os.getpid(),
        }
        self.config_path.write_text(json.dumps(configuration), encoding="utf-8")
        self.log_handle = (self.directory / "service.log").open("a", encoding="utf-8")
        isolation_args = list(python_args)
        if "-I" not in isolation_args:
            isolation_args.append("-I")
        command = [sys.executable, *isolation_args, "-S", "-B", str(Path(__file__).with_name("server.py")), str(self.config_path)]
        environment = os.environ.copy()
        environment["BLENDER_MCP_HOST"] = "127.0.0.1"
        environment["BLENDER_MCP_PORT"] = str(bridge_port)
        environment["BLENDER_MCP_TOKEN"] = self.bridge_token
        try:
            self.process = subprocess.Popen(
                command, stdin=subprocess.DEVNULL, stdout=self.log_handle, stderr=subprocess.STDOUT,
                env=environment, **process_options(),
            )
        except OSError as error:
            try:
                self.stop()
            except Exception as cleanup_error:
                error.add_note(f"Process start rollback failed: {cleanup_error}")
            raise
        self.started_at = time.monotonic()
        self.state = "Starting"

    def poll(self):
        if self.process is None:
            return self.state
        exit_code = self.process.poll()
        if exit_code is not None:
            raise ServiceError(f"Service exited with code {exit_code}; see {self.directory / 'service.log'}")
        if self.state == "Starting":
            try:
                self.check_health()
                self.state = "Running"
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if time.monotonic() - self.started_at > 20:
                    raise ServiceError(f"Service startup timed out; see {self.directory / 'service.log'}")
        return self.state

    def check_health(self):
        if self.process is None:
            raise ServiceError("MCP service is stopped")
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/health",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=0.15) as response:
            health = json.load(response)
        if health.get("pid") != self.process.pid or health.get("session") != self.session:
            raise ServiceError("HTTP port is served by another process or session")
        return health

    def stop(self):
        errors = []
        if self.process is not None:
            try:
                if self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait(timeout=5)
                self.process = None
            except (OSError, subprocess.TimeoutExpired) as error:
                errors.append(error)
        if self.log_handle is not None:
            try:
                self.log_handle.close()
                self.log_handle = None
            except OSError as error:
                errors.append(error)
        if self.config_path is not None:
            try:
                self.config_path.unlink(missing_ok=True)
                self.config_path = None
            except OSError as error:
                errors.append(error)
        self.state = "Stopped" if self.process is None else "Stop failed"
        self.bridge_token = ""
        if errors:
            raise ExceptionGroup("Process cleanup failed: " + "; ".join(map(str, errors)), errors)

    def configuration(self, client):
        if self.state != "Running":
            raise ServiceError("Start the service before exporting its configuration")
        return client_configuration(client, self.port, self.token)
