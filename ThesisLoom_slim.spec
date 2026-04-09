# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# ── 使用纯净 venv，collect_all 不会拉入无关包 ──
from PyInstaller.utils.hooks import collect_all

st_datas, st_binaries, st_hidden = collect_all('streamlit')
wv_datas, wv_binaries, wv_hidden = collect_all('webview')

datas = [
    ('streamlit_app.py', '.'),
    ('state_dashboard.py', '.'),
    ('workflow.py', '.'),
    ('core', 'core'),
    ('inputs', 'inputs'),
    ('README.md', '.'),
]
datas += st_datas
datas += wv_datas

binaries = []
binaries += st_binaries
binaries += wv_binaries

hiddenimports = [
    'webview',
    'workflow',
    'state_dashboard',
    'core.state',
    'core.nodes',
    'core.llm',
    'core.prompts',
    'core.project_paths',
]
hiddenimports += collect_submodules('core')
hiddenimports += st_hidden
hiddenimports += wv_hidden

# ── 大量排除：这些包绝对不被 ThesisLoom 使用 ──
excludes = [
    # Deep Learning / ML
    'torch', 'torchvision', 'torchaudio',
    'tensorflow', 'keras',
    'transformers', 'accelerate', 'sentence_transformers',
    'ctranslate2', 'faster_whisper',
    'onnxruntime', 'onnx',
    'scipy', 'scikit-learn', 'sklearn',

    # Computer Vision
    'cv2', 'opencv-python', 'opencv-python-headless',

    # Browser automation
    'playwright', 'selenium', 'selenium_wire',
    'undetected_chromedriver', 'webdriver_manager',

    # Charting/plotting extras
    'kaleido', 'matplotlib', 'seaborn', 'plotly',

    # Data / Arrow
    'pyarrow',

    # Audio / Video
    'av', 'PyAudio', 'soundfile', 'pydub',

    # NLP
    'nltk', 'langchain', 'langchain_core', 'langchain_community',
    'langdetect', 'spacy',

    # Databases
    'pymongo', 'psycopg2', 'oracledb', 'pymilvus',
    'chromadb', 'qdrant_client', 'pinecone',
    'elasticsearch', 'opensearch',
    'SQLAlchemy', 'alembic', 'peewee',

    # Cloud SDKs
    'boto3', 'botocore', 's3transfer',
    'google.cloud', 'google.api_core',
    'google.generativeai', 'google_genai',
    'googleapiclient',
    'azure',
    'tencentcloud',

    # MKL / Intel
    'mkl', 'mkl_fft', 'mkl_random',

    # Web frameworks (not needed in packaged app)
    'gradio', 'gradio_client', 'flask', 'django',

    # Other heavy packages
    'huggingface_hub', 'tokenizers', 'datasets',
    'sympy', 'networkx',
    'docker', 'kubernetes',
    'moto',
    'openai',  # ThesisLoom uses volcengine, not openai directly
    'anthropic',

    # IPython / Jupyter
    'IPython', 'ipykernel', 'jupyter',

    # Testing
    'pytest',

    # Misc heavy
    'modelscope', 'open_webui',
    'unstructured', 'rapidocr_onnxruntime',
    'shapely', 'lxml',
    'grpc', 'grpcio',

    # MKL runtime DLLs (prevents bundling Intel MKL)
    'numpy.libs',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['scripts/pyinstaller_hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=2,
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
    strip=True,
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
    strip=True,
    upx=True,
    upx_exclude=[],
    name='ThesisLoom',
)
