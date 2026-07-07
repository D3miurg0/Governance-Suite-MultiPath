# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — con manifiesto UAC (requireAdministrator)

block_cipher = None

UAC_MANIFEST = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">\n  <assemblyIdentity\n      version="1.0.0.0"\n      processorArchitecture="amd64"\n      name="GovernanceSuite"\n      type="win32"/>\n  <description>Governance Suite - File Governance Platform</description>\n  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">\n    <security>\n      <requestedPrivileges>\n        <requestedExecutionLevel level="requireAdministrator" uiAccess="false"/>\n      </requestedPrivileges>\n    </security>\n  </trustInfo>\n  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">\n    <application>\n      <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"/>\n    </application>\n  </compatibility>\n</assembly>'

a = Analysis(
    ['run_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets',  'assets'),
        ('locales', 'locales'),
    ],
    hiddenimports=[
        # Win32 / pywin32
        'win32net',
        'win32netcon',
        'win32security',
        'win32api',
        'pywintypes',
        # GUI
        'customtkinter',
        # Data
        'pandas',
        # Modulos internos nuevos (PyInstaller no siempre los detecta)
        'modules.share_manager',
        'gui.tab_share_manager',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['rich', 'jinja2'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GovernanceSuite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/icon.ico',
    manifest=UAC_MANIFEST,
    uac_admin=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GovernanceSuite',
)
