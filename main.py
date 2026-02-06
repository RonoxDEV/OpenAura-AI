#  -------------------------------------------------------------------------
#  OpenAura AI - Intelligence Artificielle Souveraine
#  Copyright (C) 2026 RonoxDEV. All rights reserved.
#
#  LICENCE : PolyForm Noncommercial 1.0.0
#
#  Usage personnel et éducatif : AUTORISÉ.
#  Contributions communautaires (Pull Requests) : BIENVENUES.
#  USAGE COMMERCIAL : STRICTEMENT INTERDIT.
#
#  Toute utilisation au sein d'une entreprise ou pour un profit monétaire
#  nécessite une licence commerciale séparée de l'auteur.
#  Contact : via GitHub <https://github.com/RonoxDEV/OpenAura-AI>
#  -------------------------------------------------------------------------

import json
import os
import sys
from tkinter import messagebox

# --- GESTION ROBUSTE DES CHEMINS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def check_existing_config():
    """Vérifie si un fichier .OpenAuraConfig.json existe dans le dossier .OpenAura à la racine du PC"""
    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, ".OpenAura")

    # Chercher tous les fichiers .OpenAuraConfig.json
    if os.path.exists(config_dir):
        for file in os.listdir(config_dir):
            if file.endswith(".OpenAuraConfig.json"):
                config_path = os.path.join(config_dir, file)
                return config_path

    return None

if __name__ == "__main__":
    # Vérifier si une config existe
    existing_config = check_existing_config()

    if existing_config:
        # Une configuration existe, lancer le dashboard
        print(f"Configuration trouvée : {existing_config}")
        try:
            # Définir la variable d'environnement
            os.environ['OPENATURA_CONFIG_PATH'] = existing_config

            # Importer et lancer le dashboard directement
            sys.path.insert(0, os.path.join(BASE_DIR, "core"))
            from dashboard import DashboardApp

            app = DashboardApp()
            app.mainloop()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de lancer le dashboard : {e}")
            sys.exit(1)
    else:
        # Pas de configuration, lancer le wizard
        print("Aucune configuration trouvée. Lancement du wizard...")
        try:
            # Importer et lancer le wizard directement
            sys.path.insert(0, os.path.join(BASE_DIR, "ui"))
            from wizard import WizardApp

            app = WizardApp()
            app.mainloop()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de lancer le wizard : {e}")
            sys.exit(1)

