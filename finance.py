from __future__ import annotations

# One friendly command entrypoint for the finance tracker.
# Example: .venv/bin/python finance.py add account

import argparse
import os
import socket
import sys
import time
from collections.abc import Callable
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_module_main(import_path: str) -> None:
    """Import a CLI module and run its main() function."""
    module = __import__(import_path, fromlist=["main"])
    module.main()


def init_db(_args: argparse.Namespace) -> None:
    run_module_main("scripts.init_db")


def local_network_ip() -> str | None:
    """Best-effort local network IP for copying into another browser/device."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def port_is_available(address: str, port: int) -> bool:
    """Return True when Streamlit can bind to the requested address and port."""
    bind_address = "127.0.0.1" if address == "0.0.0.0" else address
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((bind_address, port))
        except OSError:
            return False
    return True


def first_available_port(address: str, preferred_port: int, max_attempts: int = 20) -> int:
    """Find a free port, starting at the preferred one."""
    for port in range(preferred_port, preferred_port + max_attempts):
        if port_is_available(address, port):
            return port

    raise RuntimeError(
        f"No free dashboard port found from {preferred_port} to {preferred_port + max_attempts - 1}."
    )


def dashboard(args: argparse.Namespace) -> None:
    """Run Streamlit without opening a browser automatically."""
    address = "0.0.0.0" if args.network else args.address
    port = first_available_port(address, args.port)
    if port != args.port:
        print(f"Port {args.port} is already in use. Using port {port} instead.", flush=True)

    port_text = str(port)
    cache_buster = f"run={int(time.time())}"
    local_url = f"http://127.0.0.1:{port_text}?{cache_buster}"
    print("Dashboard will not open automatically.", flush=True)
    print(f"Local URL:   {local_url}", flush=True)
    network_ip = local_network_ip() if address == "0.0.0.0" else None
    if network_ip is not None:
        print(f"Network URL: http://{network_ip}:{port_text}?{cache_buster}", flush=True)
    print("Copy the URL above into your browser.", flush=True)
    print("If the browser reports a failed JavaScript module, close the old tab and copy this fresh URL again.", flush=True)

    command = [
        str(PROJECT_ROOT / ".venv" / "bin" / "streamlit"),
        "run",
        str(PROJECT_ROOT / "app" / "dashboard.py"),
        "--server.headless",
        "true",
        "--server.address",
        address,
        "--server.port",
        port_text,
        "--server.fileWatcherType",
        "none",
    ]
    os.execv(command[0], command)


def dispatch(import_path: str) -> Callable[[argparse.Namespace], None]:
    """Create an argparse handler for an existing CLI module."""

    def handler(_args: argparse.Namespace) -> None:
        run_module_main(import_path)

    return handler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Monthly finance tracker command centre.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Create database tables.").set_defaults(func=init_db)
    dashboard_parser = subparsers.add_parser("dashboard", help="Start the Streamlit dashboard.")
    dashboard_parser.add_argument("--port", type=int, default=8501, help="Dashboard port. Defaults to 8501.")
    dashboard_parser.add_argument(
        "--address",
        default="127.0.0.1",
        help="Bind address. Defaults to 127.0.0.1 for local-only access.",
    )
    dashboard_parser.add_argument(
        "--network",
        action="store_true",
        help="Also make the dashboard available on your local network.",
    )
    dashboard_parser.set_defaults(func=dashboard)
    subparsers.add_parser("month-end", help="Run the guided month-end workflow.").set_defaults(
        func=dispatch("cli.month_end")
    )
    subparsers.add_parser("summary", help="Show calculated summary for a month.").set_defaults(
        func=dispatch("cli.show_monthly_summary")
    )

    add_parser = subparsers.add_parser("add", help="Add records.")
    add_subparsers = add_parser.add_subparsers(dest="record_type", required=True)
    add_commands = {
        "account": "cli.add_account",
        "snapshot": "cli.add_monthly_snapshot",
        "salary": "cli.add_salary_income",
        "income": "cli.add_monthly_income",
        "expense": "cli.add_monthly_expense",
        "transfer": "cli.add_monthly_transfer",
        "debt": "cli.add_debt_profile",
        "goal": "cli.add_goal",
        "goal-allocation": "cli.add_monthly_goal_allocation",
        "subscription": "cli.add_subscription",
    }
    for name, import_path in add_commands.items():
        add_subparsers.add_parser(name).set_defaults(func=dispatch(import_path))

    list_parser = subparsers.add_parser("list", help="View entered records.")
    list_subparsers = list_parser.add_subparsers(dest="record_type", required=True)
    list_subparsers.add_parser("accounts").set_defaults(func=dispatch("cli.list_accounts"))
    list_subparsers.add_parser("month").set_defaults(func=dispatch("cli.list_month"))

    subparsers.add_parser("edit-account", help="Edit account details.").set_defaults(
        func=dispatch("cli.edit_account")
    )
    subparsers.add_parser("delete", help="Delete a mistaken record.").set_defaults(
        func=dispatch("cli.delete_record")
    )
    subparsers.add_parser("paye", help="Run a standalone PAYE estimate.").set_defaults(
        func=dispatch("cli.calculate_paye")
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
