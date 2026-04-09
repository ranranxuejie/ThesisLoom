from __future__ import annotations

import runpy
import sys
from pathlib import Path


LEGACY_STREAMLIT_ENTRY = Path(__file__).resolve().parent / "history" / "legacy_frontend" / "streamlit_app_legacy.py"


def main() -> None:
    if not LEGACY_STREAMLIT_ENTRY.exists():
        raise FileNotFoundError(f"Legacy streamlit app not found: {LEGACY_STREAMLIT_ENTRY}")

    print("| [Legacy Frontend] streamlit_app has moved to history/legacy_frontend/streamlit_app_legacy.py")
    print("| [Legacy Frontend] For desktop UI, use: npm --prefix desktop_ui run tauri -- dev")

    # Keep backward compatibility for existing scripts that still run streamlit_app.py.
    runpy.run_path(str(LEGACY_STREAMLIT_ENTRY), run_name="__main__")


if __name__ == "__main__":
    sys.exit(main())
