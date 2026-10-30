# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=collect_data_files('companera', includes=['assets/*', 'persona/*']),
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Sophia', debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=False, icon='companera/assets/sophia/capri.ico')
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name='Sophia')
