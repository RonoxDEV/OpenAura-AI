#  -------------------------------------------------------------------------
#  OpenAura AI - Build Script with PyInstaller
#  -------------------------------------------------------------------------
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Fix encodage UTF-8 pour Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# --- CONFIGURATION ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MAIN_FILE = os.path.join(PROJECT_ROOT, "main.py")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
SPEC_FILE = os.path.join(PROJECT_ROOT, "build_spec.spec")

# Dossiers à inclure
FOLDERS_TO_INCLUDE = [
    ("ui", os.path.join(PROJECT_ROOT, "ui")),
    ("core", os.path.join(PROJECT_ROOT, "core")),
]

def install_dependencies():
    """Installe les dépendances depuis requirements.txt"""
    print("📦 Vérification des dépendances...")
    requirements_file = os.path.join(PROJECT_ROOT, "requirements.txt")

    if os.path.exists(requirements_file):
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file])
            print("✅ Dépendances installées")
        except subprocess.CalledProcessError:
            print("❌ Erreur lors de l'installation des dépendances")
            return False
    else:
        print("⚠️ requirements.txt introuvable")

    return True

def install_pyinstaller():
    """Installe PyInstaller si nécessaire"""
    print("📦 Vérification de PyInstaller...")
    try:
        import PyInstaller
        print("✅ PyInstaller déjà installé")
    except ImportError:
        print("📥 Installation de PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✅ PyInstaller installé")

def create_spec_file():
    """Crée le fichier spec personnalisé pour PyInstaller"""

    # Construire les data files pour les dossiers et images
    datas = []
    for folder_name, folder_path in FOLDERS_TO_INCLUDE:
        if os.path.exists(folder_path):
            # Utiliser forward slashes pour éviter les problèmes d'échappement
            folder_path_clean = folder_path.replace('\\', '/')
            datas.append((repr(folder_path_clean), repr(folder_name)))
            print(f"  ✓ Ajout du dossier: {folder_name}")

    # Chercher les images dans ui/assets
    assets_path = os.path.join(PROJECT_ROOT, "ui", "assets")
    if os.path.exists(assets_path):
        assets_path_clean = assets_path.replace('\\', '/')
        datas.append((repr(assets_path_clean), repr("ui/assets")))
        print(f"  ✓ Ajout du dossier: ui/assets")

    # Créer le contenu du spec file
    datas_str = "[" + ", ".join([f"({d[0]}, {d[1]})" for d in datas]) + "]"

    main_file_clean = MAIN_FILE.replace('\\', '/')
    project_root_clean = PROJECT_ROOT.replace('\\', '/')

    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
# Build spec for OpenAura AI

block_cipher = None

a = Analysis(
    [r'{main_file_clean}'],
    pathex=[r'{project_root_clean}'],
    binaries=[],
    datas={datas_str},
    hiddenimports=[
        'customtkinter', 'PIL', 'PIL.Image', 'PIL.ImageFilter',
        'psutil', 'keyring', 'requests', 'wmi', 'pythoncom', 'win32com',
        'watchdog', 'watchdog.observers', 'watchdog.events',
        'pypdf', 'bs4', 'bs4.element',
        'smtplib', 'email', 'email.mime', 'email.mime.text', 'email.mime.multipart',
        'sqlite3', 'base64', 'queue', 'threading', 'subprocess',
        'tkinter', 'tkinter.filedialog', 'tkinter.messagebox'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludedimports=[],
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
    name='OpenAura',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''

    with open(SPEC_FILE, 'w') as f:
        f.write(spec_content)

    print(f"✅ Fichier spec créé: {SPEC_FILE}")

def build_executable():
    """Lance PyInstaller pour créer l'exécutable"""
    print("\n🔨 Compilation de l'exécutable...")

    try:
        subprocess.check_call([
            sys.executable,
            "-m", "PyInstaller",
            SPEC_FILE,
            "--distpath", DIST_DIR,
            "--workpath", BUILD_DIR,
            "--clean"
        ])
        print("✅ Exécutable créé avec succès!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de la compilation: {e}")
        return False

def cleanup_build():
    """Nettoie les fichiers de build (garder dist et le .spec)"""
    print("\n🧹 Nettoyage...")

    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
        print(f"  ✓ Dossier build supprimé")

    # Garder dist et le spec file pour les rebuild

def show_output():
    """Affiche les informations finales"""
    exe_path = os.path.join(DIST_DIR, "OpenAura.exe")

    if os.path.exists(exe_path):
        exe_size = os.path.getsize(exe_path) / (1024 * 1024)  # En MB
        print(f"\n✨ BUILD TERMINÉ!")
        print(f"📁 Emplacement: {exe_path}")
        print(f"💾 Taille: {exe_size:.2f} MB")
        print(f"\n🎯 Vous pouvez maintenant lancer: {exe_path}")
    else:
        print(f"\n❌ L'exécutable n'a pas été créé")

def main():
    print("=" * 60)
    print("  OpenAura AI - Build avec PyInstaller")
    print("=" * 60 + "\n")

    # 1. Installer les dépendances
    if not install_dependencies():
        print("❌ Installation des dépendances échouée")
        sys.exit(1)

    # 2. Installer PyInstaller
    install_pyinstaller()

    # 3. Créer le fichier spec
    print("\n📝 Création du fichier spec...")
    create_spec_file()

    # 4. Compiler
    success = build_executable()

    if success:
        # 5. Nettoyer
        cleanup_build()

        # 6. Afficher les infos finales
        show_output()
    else:
        print("\n❌ La compilation a échoué. Vérifiez les erreurs ci-dessus.")
        sys.exit(1)

if __name__ == "__main__":
    main()
