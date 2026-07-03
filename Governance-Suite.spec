# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — con manifiesto UAC (requireAdministrator)

block_cipher = None

# Manifiesto UAC embebido: el exe pedirá elevación automáticamente
UAC_MANIFEST = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity
      version="1.0.0.0"
      processorArchitecture="amd64"
      name="GovernanceSuite"
      type="win32"/>
  <description>Governance Suite - File Governance Platform</description>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="requireAdministrator" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <!-- Windows 10 / 11 -->
      <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"/>
    </application>
  </compatibility>
</assembly>
"""

# Escribir el manifiesto a disco para que PyInstaller lo lea
import os, tempfile
_manifest_path = os.path.join(tempfile.gettempdir(), "GovernanceSuite.manifest")
with open(_manifest_path, "w", encoding="utf-8") as _f:
    _f.write(UAC_MANIFEST)

a = Analysis(
    ['run_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets',  'assets'),
        ('locales', 'locales'),
    ],
    hiddenimports=[
        'pandas',
        'win32net',
        'win32netcon',
        'win32security',
        'win32api',
        'pywintypes',
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
    # Manifiesto UAC — pide elevación al abrir el exe
    manifest=_manifest_path,
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
