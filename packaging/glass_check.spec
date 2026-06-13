# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Kontrola skla macOS app.

Build (on macOS):  pyinstaller --noconfirm packaging/glass_check.spec
Produces:          dist/Kontrola skla.app
"""
import os

# SPECPATH is injected by PyInstaller; resolve paths relative to the repo root
# so the build works regardless of the current working directory.
ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))

a = Analysis(
    [os.path.join(ROOT, "glass_check.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[],
    # Pillow (pulled in by pdfplumber) ships a tkinter bridge that PyInstaller
    # does not always detect automatically.
    hiddenimports=["PIL._tkinter_finder"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="KontrolaSkla",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,            # windowed GUI app, no terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,         # build for the host arch (set by the CI matrix)
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
    name="KontrolaSkla",
)
app = BUNDLE(
    coll,
    name="Kontrola skla.app",
    icon=None,
    bundle_identifier="cz.vltavaholding.kontrolaskla",
    info_plist={
        "CFBundleName": "Kontrola skla",
        "CFBundleDisplayName": "Kontrola skla",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
    },
)
