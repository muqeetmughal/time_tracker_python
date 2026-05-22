# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import get_package_paths

block_cipher = None

datas = [
    ("time_tracker/tracking/listener_script.py", "time_tracker/tracking"),
]

hiddenimports = [
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "sqlalchemy",
    "sqlalchemy.ext.declarative",
    "sqlalchemy.orm",
]

excludes = [
    "tkinter",
    "matplotlib",
    "scipy",
    "numpy",
    "pandas",
    "PIL",
    "Pillow",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Time Tracker",
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
    contents_directory="_internal",
)

app = BUNDLE(
    exe,
    name="Time Tracker.app",
    icon=None,
    bundle_identifier="com.timetracker.app",
    info_plist={
        "CFBundleName": "Time Tracker",
        "CFBundleDisplayName": "Time Tracker",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleIdentifier": "com.timetracker.app",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
        "LSUIElement": False,
    },
)
