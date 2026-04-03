# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('streamlit_app.py', '.'), ('state_dashboard.py', '.'), ('workflow.py', '.'), ('core', 'core'), ('inputs', 'inputs'), ('README.md', '.')]
binaries = [('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_avx.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_avx2.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_avx512.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_blacs_ilp64.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_blacs_intelmpi_ilp64.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_blacs_intelmpi_lp64.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_blacs_lp64.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_blacs_msmpi_ilp64.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_blacs_msmpi_lp64.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_cdft_core.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_core.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_def.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_intel_thread.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_mc.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_mc3.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_msg.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_pgi_thread.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_rt.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_scalapack_ilp64.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_scalapack_lp64.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_sequential.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_tbb_thread.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_vml_avx.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_vml_avx2.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_vml_avx512.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_vml_cmpt.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_vml_def.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_vml_mc.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\mkl_vml_mc3.2.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\libiomp5md.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\tbb12.dll', '.'), ('C:\\ProgramData\\anaconda3\\envs\\ENV2026\\Library\\bin\\tbbmalloc.dll', '.')]
hiddenimports = ['webview', 'workflow', 'state_dashboard', 'core.state', 'core.nodes', 'core.llm', 'core.prompts', 'core.project_paths']
hiddenimports += collect_submodules('core')
tmp_ret = collect_all('streamlit')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('webview')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['scripts/pyinstaller_hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ThesisLoom',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ThesisLoom',
)
