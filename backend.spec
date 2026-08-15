# -*- mode: python ; coding: utf-8 -*-
"""
Freezes the FastAPI backend into a self-contained --onedir bundle for the
desktop app to spawn.

Build:
    .venv/Scripts/python.exe -m PyInstaller backend.spec --noconfirm \
        --distpath build/backend --workpath build/pyinstaller

--onedir, not --onefile: onefile unpacks the entire ~200MB bundle into a temp
directory on every single launch, which makes app startup take seconds and
leaves debris behind when the process is killed.
"""
import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = [], [], []

# curl_cffi ships a compiled libcurl and its own CA bundle; yfinance carries
# data files. Neither is reachable by PyInstaller's static import scan.
for pkg in ("yfinance", "curl_cffi"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# uvicorn picks its event loop and HTTP/websocket protocol implementations by
# string name at runtime, so nothing imports them statically to be found.
hiddenimports += collect_submodules("uvicorn")

# The frontend travels with the backend. server.py resolves it from
# sys._MEIPASS when frozen (see the HERE/STATIC block there).
datas += [(os.path.join(SPECPATH, "static"), "static")]

# The build guide ships too, so /guide works with no network and the app can
# explain its own construction offline.
datas += [(os.path.join(SPECPATH, "docs"), "docs")]

a = Analysis(
    [os.path.join(SPECPATH, "server.py")],
    pathex=[SPECPATH],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Pulled in as optional extras by pandas; none of it is reachable from this
    # app and together it is a few hundred MB.
    excludes=[
        "tkinter", "matplotlib", "IPython", "pytest", "notebook",
        "PyQt5", "PyQt6", "PySide2", "PySide6", "sphinx",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="horizon-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX-packed binaries are a reliable way to get flagged by AV
    console=True,       # keeps print() working so Electron can capture the log;
                        # Electron spawns with windowsHide so no window appears
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
    upx=False,
    upx_exclude=[],
    name="horizon-backend",
)
