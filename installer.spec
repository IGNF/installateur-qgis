# -*- mode: python ; coding: utf-8 -*-
import os
import tldextract

# --- fichiers UI ---
datas = [
    ('installer.ui', '.'),
    ('aproposde.ui', '.')
]

binaries = []

# --- imports nécessaires ---
hiddenimports = [
    # PyQt6
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.uic',

    # réseau
    'requests',
    'pypac',

    # divers
    'progressbar'
]

# --- fix tldextract ---
tld_path = os.path.dirname(tldextract.__file__)
snapshot_file = os.path.join(tld_path, ".tld_set_snapshot")
datas.append((snapshot_file, "tldextract"))

# --- analyse ---
a = Analysis(
    ['installer.py'],
    pathex=[os.getcwd()],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PluginHub_Installer',
    debug=False,
    strip=False,
    upx=False,        # important pour éviter bugs antivirus
    console=False      # mettre False quand tout marche
)