# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['workflow', 'backend_api', 'core.state', 'core.nodes', 'core.llm', 'core.prompts', 'core.project_paths']
hiddenimports += collect_submodules('core')


a = Analysis(
    ['desktop_backend.py'],
    pathex=[],
    binaries=[],
    datas=[('workflow.py', '.'), ('backend_api.py', '.'), ('state_dashboard.py', '.'), ('core', 'core'), ('D:\\PycharmProjects\\2026\\ThesisLoom\\build\\package_assets\\inputs', 'inputs'), ('README.md', '.')],
    hiddenimports=hiddenimports,
    hookspath=['scripts/pyinstaller_hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['streamlit', 'streamlit_autorefresh', 'webview', 'pywebview', 'fastapi', 'uvicorn', 'matplotlib', 'seaborn', 'plotly', 'pandas', 'numpy', 'scipy', 'sklearn', 'torch', 'tensorflow', 'IPython', 'OpenSSL', 'cryptography', 'urllib3.contrib.pyopenssl'],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [('O', None, 'OPTION'), ('O', None, 'OPTION')],
    name='ThesisLoomBackend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
