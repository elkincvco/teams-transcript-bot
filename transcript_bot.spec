# -*- mode: python ; coding: utf-8 -*-

# SOLUCION PARA RecursionError
import sys
sys.setrecursionlimit(sys.getrecursionlimit() * 5)

# Hidden imports necesarios
hidden_imports = [
    'whisper',
    'whisper.model',
    'whisper.decoding',
    'whisper.tokenizer',
    'soundcard',
    'psutil',
    'numpy',
    'torch',
    'torchaudio',
    'json',
    'threading',
    'queue',
    'datetime'
]

a = Analysis(
    ['transcript_bot.py'],
    pathex=[],
    binaries=[],
    datas=[],  # VACIO - Sin archivos adicionales para evitar errores
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'tkinter.test',
        'test',
        'unittest',
        'cv2',
        'PIL'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TeamsTranscriptBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
