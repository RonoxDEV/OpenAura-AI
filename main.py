import customtkinter as ctk
import json
import os
import threading
import sqlite3
import time
import requests
import subprocess
import sys
from bs4 import BeautifulSoup
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

# --- CONFIGURATION GRAPHIQUE ---
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# --- GESTION ROBUSTE DES CHEMINS (COMPATIBLE GITHUB/VENV) ---
# On récupère le dossier où se trouve dashboard.py
if getattr(sys, 'frozen', False):
    # Si on est dans un .exe (futur)
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Si on est en script python normal
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "OpenAuraConfig.json")
DB_PATH = os.path.join(BASE_DIR, "aura_memory.db")

OLLAMA_API_URL = "http://localhost:11434/api/generate"

# =============================================================================
# PARTIE 1 : LE CERVEAU (BACKEND)
# =============================================================================
class AuraBrain:
    def __init__(self, log_callback):
        self.log = log_callback
        self.config = self.load_config()
        self.db_path = DB_PATH
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
        """Crée la structure de la BDD si elle n'existe pas"""
        try:
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
            # Index pour accélérer la recherche des doublons
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_filepath ON file_events (file_path)")
            conn.commit()
            conn.close()
            self.log(f"🧠 Mémoire connectée : {os.path.basename(self.db_path)}")
        except Exception as e:
            self.log(f"❌ ERREUR CRITIQUE BDD : {e}")

    # --- GESTION OLLAMA ---
    def ensure_ollama_ready(self):
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
            for i in range(15):
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

    # --- SCRAPING ---
    def start_learning_process(self):
        if "scraping_summary" in self.config and self.config["scraping_summary"]:
            self.log("♻️ Identité entreprise chargée depuis la mémoire.")
            return

        url = self.config.get("website_url")
        if url:
            threading.Thread(target=self._scrape_and_analyze, args=(url,)).start()

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

        model = self.config.get("selected_model_tag", "moondream")
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

        # Scan initial en Thread séparé
        threading.Thread(target=self._perform_initial_scan, args=(targets,)).start()

        self.log(f"👀 Activation des sentinelles sur {len(targets)} zones...")
        # On passe le 'brain' au handler pour qu'il puisse appeler des méthodes si besoin
        event_handler = AuraFileHandler(self.db_path, self.log)
        
        for target in targets:
            path = target["path"]
            if os.path.exists(path):
                observer = Observer()
                observer.schedule(event_handler, path, recursive=True)
                observer.start()
                self.observers.append(observer)

    def _perform_initial_scan(self, targets):
        """Scanne les fichiers et les ajoute à la DB s'ils n'y sont pas déjà"""
        self.log("📂 Inventaire et synchronisation BDD...")
        count_new = 0
        count_total = 0
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for target in targets:
                path = target["path"]
                if os.path.exists(path):
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            if self._is_ignored(file): continue
                            
                            full_path = os.path.join(root, file)
                            count_total += 1
                            
                            # VÉRIFICATION EN BDD
                            cursor.execute("SELECT id FROM file_events WHERE file_path = ? LIMIT 1", (full_path,))
                            exists = cursor.fetchone()
                            
                            if not exists:
                                # On l'ajoute car inconnu
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                cursor.execute("INSERT INTO file_events (timestamp, event_type, file_path) VALUES (?, ?, ?)",
                                               (timestamp, "EXISTANT", full_path))
                                self.log(f"   [SYNC BDD] + {file}")
                                count_new += 1
                                # Petit commit tous les 10 fichiers pour être sûr
                                if count_new % 10 == 0: conn.commit()
            
            conn.commit()
            conn.close()
            
            if count_new > 0:
                self.log(f"✅ Sync terminée : {count_new} nouveaux fichiers indexés sur {count_total}.")
            else:
                self.log(f"✅ Sync terminée : Tout est à jour ({count_total} fichiers).")
                
        except Exception as e:
            self.log(f"❌ Erreur Scan Initial : {e}")

    def _is_ignored(self, filename):
        return filename.startswith("~$") or filename.endswith((".tmp", ".log", ".ini", ".db", ".dat", ".lnk"))

    # --- GÉNÉRATION DE RAPPORT ---
    def generate_report(self, on_complete_callback):
        threading.Thread(target=self._run_report_generation, args=(on_complete_callback,)).start()

    def _run_report_generation(self, callback):
        if not self.ensure_ollama_ready(): return
        self.log("📝 Analyse de la mémoire...")
        
        events_text = ""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            cursor = conn.cursor()
            # On prend tout, classé par date
            cursor.execute("SELECT timestamp, event_type, file_path FROM file_events ORDER BY timestamp ASC")
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                self.log("⚠️ Mémoire vide.")
                callback("Aucune activité enregistrée.")
                return

            self.log(f"📊 Traitement de {len(rows)} événements...")
            for row in rows:
                folder = os.path.basename(os.path.dirname(row[2]))
                filename = os.path.basename(row[2])
                events_text += f"[{row[0]}] {row[1]} : {folder}/{filename}\n"

        except Exception as e:
            self.log(f"❌ Erreur lecture BDD : {e}")
            return

        company_context = self.config.get("scraping_summary", "Non défini")
        personality = self.config.get("system_prompt_style", "balanced_professional")
        
        tone = "Tu es factuel."
        if personality == "casual_engaging": tone = "Tu es chaleureux et dynamique."

        prompt = f"""
        CONTEXTE : {company_context}
        TON : {tone}
        MISSION : Analyse ces logs fichiers et fais un résumé. Ignore les événements "EXISTANT" sauf pour donner du contexte global. Focus sur "NOUVEAU", "MODIFIÉ", "SUPPRIMÉ".
        
        LOGS :
        {events_text}
        """

        self.log("🤖 Rédaction IA...")
        try:
            model = self.config.get("selected_model_tag", "moondream")
            payload = {"model": model, "prompt": prompt, "stream": False}
            response = requests.post(OLLAMA_API_URL, json=payload)
            if response.status_code == 200:
                callback(response.json().get("response", ""))
                self.log("✅ Rapport terminé.")
            else:
                self.log("❌ Erreur IA.")
                callback("Erreur génération.")
        except Exception as e:
            self.log(f"❌ Erreur Critique : {e}")


# =============================================================================
# WATCHDOG AVEC ANTI-SPAM (DEBOUNCE)
# =============================================================================
class AuraFileHandler(FileSystemEventHandler):
    def __init__(self, db_path, log_callback):
        self.db_path = db_path
        self.log = log_callback
        # Dictionnaire pour stocker le temps de la dernière action par fichier
        # Format : { "chemin_du_fichier": time.time() }
        self.last_events = {} 

    def is_valid(self, path):
        f = os.path.basename(path)
        if f.startswith("~$") or f.endswith((".tmp", ".log", ".ini", ".db", ".dat", ".lnk")):
            return False
        return True

    def _debounce(self, path):
        """Retourne True si l'événement doit être ignoré (trop rapide)"""
        current_time = time.time()
        last_time = self.last_events.get(path, 0)
        
        # Si le même fichier est modifié en moins de 1 seconde, on ignore
        if current_time - last_time < 1.0:
            return True
        
        self.last_events[path] = current_time
        return False

    def on_created(self, event):
        if not event.is_directory and self.is_valid(event.src_path):
            # Création est prioritaire, on met à jour le timer
            self.last_events[event.src_path] = time.time()
            self.record_event("NOUVEAU", event.src_path)

    def on_modified(self, event):
        if not event.is_directory and self.is_valid(event.src_path):
            # C'est ici que le bug se produit (Création -> Modif instantanée)
            # Si on vient de créer le fichier (ou modif très récente), on ignore cette modif
            if self._debounce(event.src_path):
                return 
            self.record_event("MODIFIÉ", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and self.is_valid(event.src_path):
            self.record_event("🗑️ SUPPRIMÉ", event.src_path)
            # On nettoie le dictionnaire pour éviter que le chemin reste en mémoire
            if event.src_path in self.last_events:
                del self.last_events[event.src_path]

    def on_moved(self, event):
        if not event.is_directory and self.is_valid(event.dest_path):
            msg = f"{os.path.basename(event.src_path)} ➡️ {os.path.basename(event.dest_path)}"
            self.record_event("DÉPLACÉ", msg, raw_path=event.dest_path)

    def record_event(self, type, display_text, raw_path=None):
        path_to_log = raw_path if raw_path else display_text
        filename = os.path.basename(display_text) if "➡️" not in type else display_text
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.log(f"📁 [{type}] {filename}")
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO file_events (timestamp, event_type, file_path) VALUES (?, ?, ?)",
                           (timestamp, type, path_to_log))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"DB Error: {e}")

# =============================================================================
# FRONTEND (DASHBOARD)
# =============================================================================
class DashboardApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OpenAura - Dashboard")
        self.geometry("1100x700")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="OpenAura", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.pack(padx=20, pady=(20, 10))
        
        status_frame = ctk.CTkFrame(self.sidebar, fg_color="#DCFCE7", border_color="#10B981", border_width=1)
        status_frame.pack(padx=10, pady=10, fill="x")
        ctk.CTkLabel(status_frame, text="✅ ONLINE", text_color="#15803D", font=("Arial", 12, "bold")).pack(pady=5)

        ctk.CTkButton(self.sidebar, text="Vue d'ensemble", fg_color="#3B82F6").pack(padx=20, pady=10, fill="x")
        
        self.btn_generate = ctk.CTkButton(self.sidebar, text="⚡ Générer Rapport", 
                                          fg_color="#EF4444", hover_color="#DC2626", 
                                          command=self.action_generate_report)
        self.btn_generate.pack(padx=20, pady=20, fill="x")

        self.main_view = ctk.CTkFrame(self, corner_radius=0, fg_color="white")
        self.main_view.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        ctk.CTkLabel(self.main_view, text="Activité en Temps Réel", font=("Arial", 20, "bold"), text_color="#111827").pack(anchor="w", pady=(0, 10))

        self.console = ctk.CTkTextbox(self.main_view, width=800, height=400, font=("Consolas", 12), 
                                      fg_color="#1E1E1E", text_color="#10B981")
        self.console.pack(fill="both", expand=True, pady=(0, 20))

        self.report_frame = ctk.CTkFrame(self.main_view, fg_color="#F3F4F6", corner_radius=10, border_color="#D1D5DB", border_width=1)
        self.report_frame.pack(fill="x", ipady=10)
        self.report_frame.pack_forget() 

        self.lbl_report_title = ctk.CTkLabel(self.report_frame, text="📝 Dernier Rapport Généré", font=("Arial", 14, "bold"), text_color="#374151")
        self.lbl_report_title.pack(anchor="w", padx=20, pady=(10, 0))
        
        self.report_text_box = ctk.CTkTextbox(self.report_frame, height=150, fg_color="white", text_color="black")
        self.report_text_box.pack(fill="x", padx=20, pady=10)

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
        
        model = self.brain.config.get("selected_model_tag", "Inconnu")
        self.log_to_console(f"🤖 Modèle IA actif : {model}")

    def action_generate_report(self):
        self.btn_generate.configure(state="disabled", text="Analyse en cours...")
        self.report_frame.pack_forget()
        
        def on_report_ready(report_text):
            self.after(0, lambda: self._display_report(report_text))

        self.brain.generate_report(on_report_ready)

    def _display_report(self, text):
        self.btn_generate.configure(state="normal", text="⚡ Générer Rapport")
        self.report_frame.pack(fill="x", ipady=10, pady=10)
        self.report_text_box.delete("0.0", "end")
        self.report_text_box.insert("0.0", text)
        self.log_to_console("📄 Nouveau rapport disponible.")

if __name__ == "__main__":
    app = DashboardApp()
    app.mainloop()