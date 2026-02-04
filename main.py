import os
import subprocess
import sys

# Nom du fichier de config généré par le Wizard
CONFIG_FILE = "OpenAuraConfig.json"

def launch_wizard():
    print("⚠️ Configuration introuvable. Lancement du Wizard...")
    # On ajuste le chemin car wizard.py est dans ui/
    wizard_path = os.path.join("ui", "wizard.py")
    subprocess.run([sys.executable, wizard_path])

def launch_dashboard():
    print("✅ Configuration détectée. Lancement du Dashboard...")
    dashboard_path = os.path.join("core", "dashboard.py")
    subprocess.run([sys.executable, dashboard_path])

if __name__ == "__main__":
    if os.path.exists(CONFIG_FILE):
        launch_dashboard()
    else:
        launch_wizard()
        # Une fois le wizard fini, on vérifie si la config a été créée pour lancer le dashboard
        if os.path.exists(CONFIG_FILE):
            launch_dashboard()
