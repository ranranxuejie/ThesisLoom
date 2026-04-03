"""Custom PyInstaller hook for local workflow module.

This overrides contrib hook-workflow.py that assumes a pip package named
"workflow" with distribution metadata.
"""

from PyInstaller.utils.hooks import collect_submodules

# Ensure local core modules imported by workflow are discovered.
hiddenimports = collect_submodules("core")
