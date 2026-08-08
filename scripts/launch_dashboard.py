from __future__ import annotations

# macOS launcher helper for the Finance Tracker dashboard.
# It starts Streamlit in the background, waits until it is ready, and opens it
# in Google Chrome. It also reuses an already-running dashboard when possible.

import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
STREAMLIT = PROJECT_ROOT / ".venv" / "bin" / "streamlit"
DASHBOARD = PROJECT_ROOT / "app" / "dashboard.py"
FINANCE_ENTRYPOINT = PROJECT_ROOT / "finance.py"
RUNTIME_DIR = PROJECT_ROOT / "data" / "runtime"
PID_FILE = RUNTIME_DIR / "dashboard.json"
LOG_FILE = RUNTIME_DIR / "dashboard.log"
DEFAULT_PORT = 8501
MAX_PORT_ATTEMPTS = 20
SOURCE_PATHS = [
    PROJECT_ROOT / "app",
    PROJECT_ROOT / "cli",
    PROJECT_ROOT / "scripts",
    PROJECT_ROOT / "src",
    PROJECT_ROOT / "finance.py",
    PROJECT_ROOT / "requirements.txt",
    PROJECT_ROOT / ".streamlit",
]


def escape_applescript_text(value: str) -> str:
    """Escape text for a simple AppleScript dialog string."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def show_dialog(title: str, message: str) -> None:
    """Show a friendly macOS dialog, falling back to terminal output."""
    script = (
        f'display dialog "{escape_applescript_text(message)}" '
        f'with title "{escape_applescript_text(title)}" '
        'buttons {"OK"} default button "OK"'
    )
    try:
        subprocess.run(["osascript", "-e", script], check=False)
    except OSError:
        print(f"{title}: {message}")


def process_is_running(pid: int) -> bool:
    """Return True if a process id still exists."""
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def source_signature() -> float:
    """Return a simple version stamp for source files used by the dashboard."""
    latest_mtime = 0.0
    for path in SOURCE_PATHS:
        if not path.exists():
            continue
        if path.is_file():
            latest_mtime = max(latest_mtime, path.stat().st_mtime)
            continue
        for child in path.rglob("*"):
            if child.is_file() and "__pycache__" not in child.parts:
                latest_mtime = max(latest_mtime, child.stat().st_mtime)
    return latest_mtime


def stop_process(pid: int) -> None:
    """Stop a dashboard process previously launched by this helper."""
    if not process_is_running(pid):
        return
    try:
        os.kill(pid, 15)
    except OSError:
        return
    deadline = time.time() + 5
    while time.time() < deadline:
        if not process_is_running(pid):
            return
        time.sleep(0.2)


def port_is_available(port: int) -> bool:
    """Return True when Streamlit can bind to a local port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def first_available_port() -> int:
    """Find a free local dashboard port."""
    for port in range(DEFAULT_PORT, DEFAULT_PORT + MAX_PORT_ATTEMPTS):
        if port_is_available(port):
            return port
    raise RuntimeError("No free dashboard port found between 8501 and 8520.")


def dashboard_url(port: int) -> str:
    """Build a cache-busting local dashboard URL."""
    return f"http://127.0.0.1:{port}?run={int(time.time())}"


def dashboard_is_ready(port: int) -> bool:
    """Check Streamlit's lightweight health endpoint."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=0.75) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def existing_dashboard_port() -> int | None:
    """Reuse the dashboard started by this launcher if it is still alive."""
    if not PID_FILE.exists():
        return None

    try:
        state = json.loads(PID_FILE.read_text())
        pid = int(state["pid"])
        port = int(state["port"])
        recorded_signature = float(state.get("source_signature", 0))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None

    if recorded_signature != source_signature():
        stop_process(pid)
        return None

    if process_is_running(pid) and dashboard_is_ready(port):
        return port
    return None


def open_in_chrome(url: str) -> None:
    """Open the dashboard in Google Chrome, falling back to the default browser."""
    try:
        subprocess.Popen(["open", "-a", "Google Chrome", url])
    except OSError:
        subprocess.Popen(["open", url])


def ensure_project_is_ready(log_file) -> None:
    """Check dependencies and create database tables before launching."""
    if not PYTHON.exists() or not STREAMLIT.exists():
        raise RuntimeError(
            "The project virtual environment is missing or Streamlit is not installed.\n\n"
            "Open Terminal in the project folder and run:\n"
            "python3 -m venv .venv\n"
            "source .venv/bin/activate\n"
            "pip install -r requirements.txt"
        )

    subprocess.run(
        [str(PYTHON), str(FINANCE_ENTRYPOINT), "init"],
        cwd=PROJECT_ROOT,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        check=True,
    )


def start_dashboard(port: int) -> subprocess.Popen:
    """Start Streamlit in the background and return the process."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log_file = LOG_FILE.open("a")
    log_file.write(f"\n\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting dashboard on port {port}\n")
    log_file.flush()

    ensure_project_is_ready(log_file)

    return subprocess.Popen(
        [
            str(STREAMLIT),
            "run",
            str(DASHBOARD),
            "--server.headless",
            "true",
            "--server.address",
            "127.0.0.1",
            "--server.port",
            str(port),
            "--server.fileWatcherType",
            "none",
        ],
        cwd=PROJECT_ROOT,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


def wait_until_ready(port: int, timeout_seconds: int = 20) -> bool:
    """Wait for Streamlit to become reachable."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if dashboard_is_ready(port):
            return True
        time.sleep(0.5)
    return False


def main() -> None:
    """Launch or reopen the Finance Tracker dashboard."""
    try:
        port = existing_dashboard_port()
        if port is None:
            port = first_available_port()
            process = start_dashboard(port)
            PID_FILE.write_text(
                json.dumps(
                    {
                        "pid": process.pid,
                        "port": port,
                        "source_signature": source_signature(),
                    },
                    indent=2,
                )
            )

            if not wait_until_ready(port):
                raise RuntimeError(
                    "The dashboard did not become ready in time.\n\n"
                    f"Check the log file here:\n{LOG_FILE}"
                )

        open_in_chrome(dashboard_url(port))
    except Exception as exc:
        show_dialog("Finance Tracker", str(exc))


if __name__ == "__main__":
    main()
