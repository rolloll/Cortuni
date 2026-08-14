# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_all

datas = [('assets/icon.png', 'assets'), ('assets/icons', 'assets/icons'), ('assets/fonts', 'assets/fonts')]
binaries = []
hiddenimports = []
datas += collect_data_files('docx')
datas += collect_data_files('hwpx')
tmp_ret = collect_all('tkinterdnd2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
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
    name='Cortuni',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\icon.ico'],
)

# onedir(폴더) 배포 - onefile은 실행할 때마다 내용을 임시 폴더에 풀어놓는데(자기
# 압축 해제), 이 동작 패턴이 드로퍼/로더와 비슷해 보여서 일부 백신이 서명 안 된
# PyInstaller onefile 실행 파일을 오탐하는 경우가 흔하다. onedir은 그 자리에서
# 바로 실행되는 파일들의 묶음이라 이 특정 오탐 경로를 없애준다 - 다만 배포는
# exe 하나가 아니라 폴더(zip)가 된다.
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Cortuni',
)
