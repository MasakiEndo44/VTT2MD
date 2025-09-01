# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['src/vtt2md/main.py'],
    pathex=[],
    binaries=[],
    # assetsフォルダとREADME.txtを配布物に追加
    datas=[('assets/icon.ico', 'assets'), ('README.md', '.')],
    hiddenimports=['tkcalendar', 'babel.numbers'], # babelのモジュールを明示的に追加
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [], # one-dirモードではスクリプトは含めない
    exclude_binaries=True, # one-dirモードではバイナリは含めない
    name='VTT2MD',
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
    icon=['assets/icon.ico'],
)

# one-dirモードでビルドするための設定
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VTT2MD' # 出力フォルダ名
)
