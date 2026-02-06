# 🔨 Guide de Compilation OpenAura AI

## Prérequis

1. **Python 3.10+** installé et dans le PATH
2. **Toutes les dépendances installées** :
   ```bash
   pip install -r requirements.txt
   ```

## Compilation en Exécutable

### Option 1 : Avec le script de build (Recommandé)

```bash
python build.py
```

Le script va :
1. ✅ Installer PyInstaller si nécessaire
2. ✅ Créer le fichier spec personnalisé
3. ✅ Compiler le projet
4. ✅ Nettoyer les fichiers temporaires
5. ✅ Créer `dist/OpenAura.exe`

### Option 2 : PyInstaller en ligne de commande

```bash
pyinstaller build_spec.spec --distpath dist --buildpath build --clean
```

## Structure de sortie

```
dist/
├── OpenAura.exe          # ← L'exécutable final
└── ... (fichiers internes)
```

## Lancement

```bash
# Mode développement
python main.py

# Mode production (après compilation)
dist/OpenAura.exe
```

## Fonctionnement du déploiement

1. **Première exécution** → Lance le Wizard pour créer la configuration
   - Crée le dossier `~/.OpenAura/`
   - Sauvegarde la config en `<NomEntreprise>.OpenAuraConfig.json`

2. **Exécutions suivantes** → Lance directement le Dashboard
   - Charge la config existante
   - Démarrage du système de surveillance

## Structure des fichiers inclus dans l'exécutable

```
ui/
├── wizard.py           # Interface de configuration
├── assets/
│   ├── stars.png
│   ├── folder.png
│   └── ...

core/
└── dashboard.py        # Interface principale
```

## Variables d'environnement

- `OPENATURA_CONFIG_PATH` : Chemin du fichier de configuration (passsé automatiquement par main.py)

## Résolution de problèmes

### "Le fichier spec n'existe pas"
→ Relancez `python build.py`

### "PyInstaller introuvable"
→ Installez-le : `pip install pyinstaller`

### "L'exe se ferme immédiatement"
→ Lancez depuis CMD pour voir les erreurs :
```bash
dist\OpenAura.exe
```

### "Les images ne s'affichent pas"
→ Vérifiez que `ui/assets/` contient les images
→ Vérifiez que `build_spec.spec` inclut le dossier

## Optimisations

Pour réduire la taille de l'exe :
- Modifiez `build.py` et remplacez `upx=True` par `upx=False` (enlève la compression)
- Supprimez les imports inutilisés dans le code Python

## Taille attendue

- **Avec UPX** : ~150-200 MB
- **Sans UPX** : ~250-350 MB

Cela dépend des dépendances incluses (customtkinter, requests, bs4, etc.).
