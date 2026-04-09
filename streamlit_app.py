from __future__ import annotations

import sys


def main() -> int:
    print("| Streamlit frontend has been removed from the active runtime.")
    print("| Use desktop UI instead: npm --prefix desktop_ui run tauri -- dev")
    print("| Legacy snapshot is kept at history/legacy_frontend/streamlit_app_legacy.py")
    return 1


if __name__ == "__main__":
    sys.exit(main())
