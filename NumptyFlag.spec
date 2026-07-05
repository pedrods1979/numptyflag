# Build with: pyinstaller NumptyFlag.spec
# Produces dist\NumptyFlag.exe -- a single file, copy it anywhere and run it.

block_cipher = None

a = Analysis(
    ["numpty_flag\\app.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("overlay", "overlay"),
        ("config.json", "."),
    ],
    hiddenimports=[
        "irsdk",
        "webview.platforms.edgechromium",
        "webview.platforms.winforms",
        "clr_loader",
    ],
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
    a.binaries,
    a.datas,
    [],
    name="NumptyFlag",
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
