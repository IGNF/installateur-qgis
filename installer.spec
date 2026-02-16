# -*- mode: python ; coding: utf-8 -*-
import os
import tldextract
from PyInstaller.utils.hooks import collect_all

# --- Collecte automatique des modules ---
datas = [('installer.ui', '.')]
binaries = []
hiddenimports = []

# PyQt5
tmp = collect_all('PyQt5')
datas += tmp[0]; binaries += tmp[1]; hiddenimports += tmp[2]

# requests
tmp = collect_all('requests')
datas += tmp[0]; binaries += tmp[1]; hiddenimports += tmp[2]

# pypac
tmp = collect_all('pypac')
datas += tmp[0]; binaries += tmp[1]; hiddenimports += tmp[2]

# --- AJOUT CRUCIAL : fichier .tld_set_snapshot ---
tld_path = os.path.dirname(tldextract.__file__)
snapshot_file = os.path.join(tld_path, ".tld_set_snapshot")
datas.append((snapshot_file, "tldextract"))

# --- Analyse ---
a = Analysis(
    ['installer.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

# --- EXE OneFile ---
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='installer',
    debug=False,
    strip=False,
    upx=True,
    console=False,   # tu veux garder la console ouverte
)

