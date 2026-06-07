from __future__ import annotations

import signal
import subprocess
import sys
from contextlib import closing
from socket import AF_INET, SO_REUSEADDR, SOCK_STREAM, SOL_SOCKET, socket
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT_BASE = 3000
STREAMLIT_PORT_BASE = 8501


def _build_command(*args: str) -> list[str]:
    return [sys.executable, *args]


def _port_is_available(host: str, port: int) -> bool:
    with closing(socket(AF_INET, SOCK_STREAM)) as probe:
        probe.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return False
        return True


def _find_free_port(host: str, starting_port: int) -> int:
    port = starting_port
    while not _port_is_available(host, port):
        port += 1
    return port


def main() -> int:
    backend_port = _find_free_port(BACKEND_HOST, BACKEND_PORT_BASE)
    streamlit_port = _find_free_port(BACKEND_HOST, STREAMLIT_PORT_BASE)

    print(f"Backend: http://{BACKEND_HOST}:{backend_port}")
    print(f"Dashboard: http://{BACKEND_HOST}:{streamlit_port}")

    backend_process = subprocess.Popen(
        _build_command("-m", "uvicorn", "backend.main:app", "--host", BACKEND_HOST, "--port", str(backend_port), "--reload"),
        cwd=PROJECT_ROOT,
    )
    dashboard_process = subprocess.Popen(
        _build_command("-m", "streamlit", "run", "app.py", "--server.address", BACKEND_HOST, "--server.port", str(streamlit_port), "--browser.gatherUsageStats", "false"),
        cwd=PROJECT_ROOT,
    )

    processes = [backend_process, dashboard_process]

    def shutdown(*_args: object) -> None:
        for process in processes:
            if process.poll() is None:
                process.terminate()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        backend_code = backend_process.wait()
        dashboard_code = dashboard_process.wait()
        return backend_code or dashboard_code
    except KeyboardInterrupt:
        shutdown()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        return 130


if __name__ == "__main__":
    raise SystemExit(main())