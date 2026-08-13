# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for KDP Coloring Book Generator.
Run: pyinstaller build.spec
"""

import os
import customtkinter

block_cipher = None

# Get customtkinter package path for including its assets
ctk_path = os.path.dirname(customtkinter.__file__)

a = Analysis(
    ['src/app.py'],
    pathex=[],
    binaries=[],
    datas=[
        (os.path.join(ctk_path, 'assets'), 'customtkinter/assets'),
        ('assets', 'assets'),
    ],
    hiddenimports=['customtkinter'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='KDP_Coloring_Book_Generator',
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
    icon=None,  # Add .ico file path here for custom icon
)
