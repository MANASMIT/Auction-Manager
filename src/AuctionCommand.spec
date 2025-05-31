# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# The 'datas' list should be empty because we want these folders external.
# If PyInstaller automatically added some, remove them or ensure they are not 'static' or 'templates'.
# For truly external files, 'datas' in Analysis and EXE should not include them.
# PyInstaller will still bundle dependencies like .dlls or .so files.

a = Analysis(
    ['auction_UI.py'],
    pathex=[],  # Let PyInstaller determine this, or set your project root
    binaries=[],
    datas=[
        ('static/images/auction-command-icon.ico', '.'),
        ( 'assets', 'assets' ),
    ],
    hiddenimports=[
        'engineio.async_drivers.threading',
        'flask_socketio',
        'jinja2',
        'werkzeug.serving',
        # Add any other hidden imports your app needs
        # 'PIL', # If you use Pillow and it's not detected
        # 'babel.support', # Sometimes needed for Flask or Jinja extensions
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AuctionCommand_v1.7',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False, # Set to True for smaller exe, False for easier debugging
    upx=True,    # Set to False if UPX causes issues or for faster build
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # For GUI, no console window
    icon='assets/auction-command-icon.ico'
)

# If you want a one-folder bundle (recommended for easier distribution of external files):
# coll = COLLECT(exe,
#                a.binaries,
#                a.zipfiles,
#                a.datas, # This would be for other data *within* the app folder
#                strip=False,
#                upx=True,
#                upx_exclude=[],
#                name='AuctionCommand') # This creates a folder named AuctionCommand

# For a one-file executable (where static/templates are siblings to the .exe):
# The `exe = EXE(...)` part above is sufficient for --onefile.
# PyInstaller will build a single .exe if there's no COLLECT section,
# or if COLLECT is commented out.