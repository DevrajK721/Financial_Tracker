from __future__ import annotations

# Create a clickable macOS .app launcher for this local project checkout.
# The generated app stores the absolute project path, so each Mac should run
# this script after cloning/setup rather than sharing the generated .app.

import os
import plistlib
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_NAME = "Finance Tracker"
APP_DIR = PROJECT_ROOT / "dist" / f"{APP_NAME}.app"
EXECUTABLE_NAME = "FinanceTracker"


def main() -> None:
    """Build dist/Finance Tracker.app."""
    if APP_DIR.exists():
        shutil.rmtree(APP_DIR)

    contents_dir = APP_DIR / "Contents"
    macos_dir = contents_dir / "MacOS"
    resources_dir = contents_dir / "Resources"
    macos_dir.mkdir(parents=True)
    resources_dir.mkdir(parents=True)

    info = {
        "CFBundleDisplayName": APP_NAME,
        "CFBundleExecutable": EXECUTABLE_NAME,
        "CFBundleIdentifier": "local.finances-tracker.dashboard",
        "CFBundleName": APP_NAME,
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "1.0",
        "CFBundleVersion": "1",
        "LSMinimumSystemVersion": "10.15",
        "LSUIElement": False,
        "NSHighResolutionCapable": True,
    }
    with (contents_dir / "Info.plist").open("wb") as file:
        plistlib.dump(info, file)

    launcher = f"""#!/bin/zsh
PROJECT_ROOT="{PROJECT_ROOT}"

if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
  PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
  PYTHON="$(command -v python3)"
fi

exec "$PYTHON" "$PROJECT_ROOT/scripts/launch_dashboard.py"
"""
    executable = macos_dir / EXECUTABLE_NAME
    executable.write_text(launcher)
    os.chmod(executable, 0o755)

    print(f"Created: {APP_DIR}")
    print("You can drag this app into your Dock.")


if __name__ == "__main__":
    main()
