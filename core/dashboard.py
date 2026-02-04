import customtkinter as ctk
import json
import os
import threading
import sqlite3
import time
import requests
import subprocess
from bs4 import BeautifulSoup
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

# --- CONFIGURATION GRAPHIQUE ---
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# Calcul de la racine du projet pour les chemins absolus (Gestion robuste des chemins)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(ROOT_DIR, "OpenAuraConfig.json")
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# =============================================================================
# PARTIE 1 : LE CERVEAU (BACKEND)
# =============================================================================
class AuraBrain:
    def __init__(self, log_callback):
        self.log = log_callback
        self.config = self.load_config()
        self.db_path = os.path.join(ROOT_DIR, "aura_memory.db")
        self.observers = []
        
        self.init_db()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.log(f"❌ Erreur sauvegarde config : {e}")

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                event_type TEXT,
                file_path TEXT
            )
        ''')
        conn.commit()
        conn.close()
        self.log("🧠 Mémoire SQLite initialisée (Mode WAL).")

    # --- GESTION DU MOTEUR IA (AUTO-START) ---
    def ensure_ollama_ready(self):
        """Vérifie si Ollama tourne. Si non, le lance en mode caché."""
        url = "http://localhost:11434"
        try:
            requests.get(url, timeout=0.5)
            return True
        except requests.exceptions.ConnectionError:
            self.log("⚠️ Le moteur IA est éteint. Démarrage automatique...")

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen(["ollama", "serve"], startupinfo=startupinfo, creationflags=0x08000000, 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            self.log("⏳ Initialisation du moteur neuronal...")
            for i in range(10):
                time.sleep(1)
                try:
                    requests.get(url, timeout=0.5)
                    self.log("✅ Moteur IA démarré et prêt.")
                    return True
                except: pass
            return False
        except Exception as e:
            self.log(f"❌ Erreur lancement Ollama : {e}")
            return False

    # --- SCRAPING & INTELLIGENCE ---
    def start_learning_process(self):
        if "scraping_summary" in self.config and self.config["scraping_summary"]:
            self.log("♻️ Identité entreprise chargée depuis la mémoire.")
            return

        url = self.config.get("website_url")
        if url:
            threading.Thread(target=self._scrape_and_analyze, args=(url,)).start()
        else:
            self.log("ℹ️ Pas de site web configuré. Analyse ignorée.")

    def _scrape_and_analyze(self, url):
        self.log(f"🌐 Lecture du site web : {url}...")
        try:
            headers = {'User-Agent': 'Mozilla/5.0 OpenAuraAI/1.0'}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                raw_text = ""
                for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'li']):
                    text = tag.get_text().strip()
                    if len(text) > 30: raw_text += text + ". "
                
                self.log("🧠 Analyse IA en cours (Synthèse de l'identité)...")
                self.analyze_company_with_ai(raw_text[:6000])
        except Exception as e:
            self.log(f"❌ Erreur scraping : {e}")

    def analyze_company_with_ai(self, raw_text):
        if not self.ensure_ollama_ready(): return

        # Utilisation de selected_model_tag en priorité
        model = self.config.get("selected_model_tag") or self.config.get("selected_model", "moondream")
        prompt = f"""Tu es un analyste stratégique expert. Synthétise ceci en une fiche d'identité (Activité, Produits, Valeurs) :
        {raw_text}"""
        
        try:
            payload = {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.3}}
            response = requests.post(OLLAMA_API_URL, json=payload)
            if response.status_code == 200:
                ai_summary = response.json().get("response", "").strip()
                self.config["scraping_summary"] = ai_summary
                self.save_config()
                self.log("✅ Identité générée et sauvegardée.")
        except Exception as e:
            self.log(f"❌ Erreur connexion IA : {e}")

    # --- WATCHDOG (SURVEILLANCE) ---
    def start_watchdogs(self):
        targets = self.config.get("targets", [])
        if not targets:
            self.log("⚠️ Aucune cible configurée.")
            return

        self.log("📂 Inventaire des fichiers existants...")
        threading.Thread(target=self._perform_initial_scan, args=(targets,)).start()

        self.log(f"👀 Activation des sentinelles sur {len(targets)} zones...")
        event_handler = AuraFileHandler(self.db_path, self.log)
        for target in targets:
            path = target["path"]
            if os.path.exists(path):
                observer = Observer()
                observer.schedule(event_handler, path, recursive=True)
                observer.start()
                self.observers.append(observer)

    def _perform_initial_scan(self, targets):
        count = 0
        for target in targets:
            path = target["path"]
            if os.path.exists(path):
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if self._is_ignored(file): continue
                        count += 1
                        # On ne log pas tout pour ne pas spammer au démarrage
        self.log(f"✅ Inventaire terminé : {count} fichiers suivis.")

    def _is_ignored(self, filename):
        return filename.startswith("~$") or filename.endswith((".tmp", ".log", ".ini", ".db"))

    # --- GÉNÉRATION DE RAPPORT (NOUVEAU) ---
    def generate_report(self, on_complete_callback):
        """Logique principale de génération"""
        threading.Thread(target=self._run_report_generation, args=(on_complete_callback,)).start()

    def _run_report_generation(self, callback):
        if not self.ensure_ollama_ready(): return

        self.log("📝 Récupération des logs d'activité...")
        
        # 1. Récupérer les événements depuis la BDD
        events_text = ""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # On prend les 50 derniers événements pour l'exemple
            cursor.execute("SELECT timestamp, event_type, file_path FROM file_events ORDER BY id DESC LIMIT 50")
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                self.log("⚠️ Aucune activité récente détectée.")
                callback("Rien à signaler. Le calme plat capitaine !")
                return

            for row in rows:
                # On nettoie le chemin pour ne garder que le nom du fichier et le dossier parent
                path = row[2]
                folder = os.path.basename(os.path.dirname(path))
                filename = os.path.basename(path)
                events_text += f"- {row[0]} : [{row[1]}] {folder}/{filename}\n"

        except Exception as e:
            self.log(f"❌ Erreur BDD : {e}")
            return

        # 2. Préparer le contexte
        company_context = self.config.get("scraping_summary", "Entreprise inconnue")
        personality = self.config.get("system_prompt_style", "balanced_professional")
        
        # Définition du ton selon la config du Wizard
        tone_instruction = "Tu es factuel, précis et analytique."
        if personality == "casual_engaging":
            tone_instruction = "Tu es chaleureux, utilise des émojis et un ton 'équipe/coach'."
        elif personality == "balanced_professional":
            tone_instruction = "Tu es professionnel mais accessible."

        # 3. Le Prompt Ultime
        prompt = f"""
        CONTEXTE ENTREPRISE :
        {company_context}

        TON RÔLE :
        {tone_instruction}
        Tu dois rédiger un rapport d'activité court pour l'équipe.

        ACTIVITÉ DÉTECTÉE (LOGS BRUTS) :
        {events_text}

        INSTRUCTIONS :
        1. Résume ce qui s'est passé (nouveaux fichiers, suppressions).
        2. Essaie de deviner sur quel projet l'équipe travaille vu les noms des fichiers.
        3. Si tu vois des fichiers suspects (exe, tmp), alerte.
        4. Ne liste pas tout ligne par ligne, fais une synthèse intelligente.
        """

        self.log("🤖 Rédaction du rapport par l'IA en cours...")
        
        # 4. Appel Ollama
        try:
            model = self.config.get("selected_model_tag") or self.config.get("selected_model", "moondream")
            payload = {"model": model, "prompt": prompt, "stream": False}
            response = requests.post(OLLAMA_API_URL, json=payload)
            
            if response.status_code == 200:
                report = response.json().get("response", "")
                self.log("✅ Rapport généré avec succès !")
                callback(report)
            else:
                self.log("❌ Erreur de génération.")
                callback("Erreur lors de la génération du rapport.")

        except Exception as e:
            self.log(f"❌ Erreur critique IA : {e}")

# --- GESTIONNAIRE D'ÉVÉNEMENTS (WATCHDOG) ---
class AuraFileHandler(FileSystemEventHandler):
    def __init__(self, db_path, log_callback):
        self.db_path = db_path
        self.log = log_callback

    def is_valid(self, path):
        f = os.path.basename(path)
        if f.startswith("~$") or f.endswith((".tmp", ".log", ".ini", ".db", ".dat")):
            return False
        return True

    def on_created(self, event):
        if not event.is_directory and self.is_valid(event.src_path):
            self.record_event("NOUVEAU", event.src_path)

    def on_modified(self, event):
        if not event.is_directory and self.is_valid(event.src_path):
            self.record_event("MODIFIÉ", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and self.is_valid(event.src_path):
            self.record_event("🗑️ SUPPRIMÉ", event.src_path)

    def on_moved(self, event):
        if not event.is_directory and self.is_valid(event.dest_path):
            msg = f"{os.path.basename(event.src_path)} ➡️ {os.path.basename(event.dest_path)}"
            self.record_event("DÉPLACÉ", msg, raw_path=event.dest_path)

    def record_event(self, type, display_text, raw_path=None):
        path_to_log = raw_path if raw_path else display_text
        filename = os.path.basename(display_text) if "➡️" not in type else display_text
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Log Visuel
        self.log(f"📁 [{type}] {filename}")
        
        # Log Database (Important pour le rapport)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO file_events (timestamp, event_type, file_path) VALUES (?, ?, ?)",
                           (timestamp, type, path_to_log))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"DB Error: {e}")


# =============================================================================
# PARTIE 2 : LE TABLEAU DE BORD (FRONTEND)
# =============================================================================
class DashboardApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("OpenAura - Dashboard")
        self.geometry("1100x700")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="OpenAura", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.pack(padx=20, pady=(20, 10))
        
        status_frame = ctk.CTkFrame(self.sidebar, fg_color="#DCFCE7", border_color="#10B981", border_width=1)
        status_frame.pack(padx=10, pady=10, fill="x")
        ctk.CTkLabel(status_frame, text="✅ ONLINE", text_color="#15803D", font=("Arial", 12, "bold")).pack(pady=5)

        # Boutons Menu
        ctk.CTkButton(self.sidebar, text="Vue d'ensemble", fg_color="#3B82F6").pack(padx=20, pady=10, fill="x")
        
        # BOUTON GÉNÉRER RAPPORT
        self.btn_generate = ctk.CTkButton(self.sidebar, text="⚡ Générer Rapport", 
                                          fg_color="#EF4444", hover_color="#DC2626", 
                                          command=self.action_generate_report)
        self.btn_generate.pack(padx=20, pady=20, fill="x")

        # --- MAIN VIEW ---
        self.main_view = ctk.CTkFrame(self, corner_radius=0, fg_color="white")
        self.main_view.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        # Titre + Console
        ctk.CTkLabel(self.main_view, text="Activité en Temps Réel", font=("Arial", 20, "bold"), text_color="#111827").pack(anchor="w", pady=(0, 10))

        self.console = ctk.CTkTextbox(self.main_view, width=800, height=400, font=("Consolas", 12), 
                                      fg_color="#1E1E1E", text_color="#10B981")
        self.console.pack(fill="both", expand=True, pady=(0, 20))

        # Zone de résultat du rapport (Popup interne)
        self.report_frame = ctk.CTkFrame(self.main_view, fg_color="#F3F4F6", corner_radius=10, border_color="#D1D5DB", border_width=1)
        self.report_frame.pack(fill="x", ipady=10)
        self.report_frame.pack_forget() # Caché par défaut

        self.lbl_report_title = ctk.CTkLabel(self.report_frame, text="📝 Dernier Rapport Généré", font=("Arial", 14, "bold"), text_color="#374151")
        self.lbl_report_title.pack(anchor="w", padx=20, pady=(10, 0))
        
        self.report_text_box = ctk.CTkTextbox(self.report_frame, height=150, fg_color="white", text_color="black")
        self.report_text_box.pack(fill="x", padx=20, pady=10)

        # Initialisation du cerveau
        self.brain = AuraBrain(self.log_to_console)
        self.after(1000, self.start_automation)

    def log_to_console(self, message):
        def _write():
            timestamp = datetime.now().strftime("[%H:%M:%S]")
            self.console.insert("end", f"{timestamp} {message}\n")
            self.console.see("end")
        self.after(0, _write)

    def start_automation(self):
        self.log_to_console("🚀 Démarrage du Dashboard...")
        self.brain.ensure_ollama_ready()
        self.brain.start_learning_process()
        self.brain.start_watchdogs()
        
        model = self.brain.config.get("selected_model_tag") or self.brain.config.get("selected_model", "Inconnu")
        self.log_to_console(f"🤖 Modèle IA actif : {model}")

    def action_generate_report(self):
        self.btn_generate.configure(state="disabled", text="Analyse en cours...")
        self.report_frame.pack_forget() # Cacher l'ancien
        
        # Callback appelé quand l'IA a fini
        def on_report_ready(report_text):
            self.after(0, lambda: self._display_report(report_text))

        self.brain.generate_report(on_report_ready)

    def _display_report(self, text):
        self.btn_generate.configure(state="normal", text="⚡ Générer Rapport")
        
        # Afficher la zone de rapport
        self.report_frame.pack(fill="x", ipady=10, pady=10)
        self.report_text_box.delete("0.0", "end")
        self.report_text_box.insert("0.0", text)
        self.log_to_console("📄 Nouveau rapport disponible (voir bas de page).")

if __name__ == "__main__":
    app = DashboardApp()
    app.mainloop()