import customtkinter as ctk
import json
import os
import threading
import sqlite3
import time
import requests
import subprocess
import sys
import base64
import queue
from bs4 import BeautifulSoup
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
import pypdf

# --- CONFIGURATION GRAPHIQUE ---
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# --- CHEMINS ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
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
        
        # File d'attente pour l'analyse (Optimisation Snapshot)
        self.analysis_queue = queue.Queue()
        self.stop_event = threading.Event()
        
        self.init_db()
        
        # Démarrage du Worker d'analyse (Tâche de fond)
        threading.Thread(target=self.worker_analysis_loop, daemon=True).start()

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
        """Crée la BDD et met à jour le schéma pour le Snapshot"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Création table standard
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    event_type TEXT,
                    file_path TEXT,
                    content_summary TEXT  -- Nouvelle colonne pour le Snapshot
                )
            ''')
            
            # Migration : Ajout de la colonne si elle manque (pour les anciens utilisateurs)
            try:
                cursor.execute("ALTER TABLE file_events ADD COLUMN content_summary TEXT")
            except sqlite3.OperationalError:
                pass # La colonne existe déjà

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_filepath ON file_events (file_path)")
            conn.commit()
            conn.close()
            self.log(f"🧠 Mémoire connectée (Snapshot Ready).")
        except Exception as e:
            self.log(f"❌ ERREUR CRITIQUE BDD : {e}")

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

    # --- WORKER D'ANALYSE (SNAPSHOT) ---
    def worker_analysis_loop(self):
        """Boucle infinie qui traite les fichiers en attente d'analyse"""
        while not self.stop_event.is_set():
            try:
                # On attend un fichier (timeout 1s pour vérifier stop_event)
                event_id, file_path, event_type = self.analysis_queue.get(timeout=1)
                
                # Si c'est une suppression, on ne peut rien analyser (trop tard)
                if event_type == "🗑️ SUPPRIMÉ":
                    self.analysis_queue.task_done()
                    continue

                self.log(f"👁️ Analyse approfondie : {os.path.basename(file_path)}")
                
                # 1. Extraction du contenu (OCR / Vision / Texte)
                content = self.analyze_file_content(file_path)
                
                # 2. Mise à jour de la BDD (Snapshot)
                if content:
                    self.update_db_snapshot(event_id, content)
                    self.log(f"💾 Snapshot enregistré pour {os.path.basename(file_path)}")
                
                self.analysis_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Erreur Worker: {e}")

    def update_db_snapshot(self, event_id, content):
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            cursor = conn.cursor()
            cursor.execute("UPDATE file_events SET content_summary = ? WHERE id = ?", (content, event_id))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Erreur Update DB: {e}")

    def analyze_file_content(self, path):
        """Détecte le type et lance l'analyse appropriée (Vision/Text)"""
        if not os.path.exists(path): return "[Fichier inaccessible]"
        
        ext = os.path.splitext(path)[1].lower()
        
        # --- CAS 1 : IMAGES (VISION + OCR) ---
        if ext in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
            return self._analyze_image_with_vision(path)

        # --- CAS 2 : PDF ---
        if ext == ".pdf":
            try:
                reader = pypdf.PdfReader(path)
                text = ""
                for i in range(min(3, len(reader.pages))): # Max 3 pages
                    text += reader.pages[i].extract_text()
                return "CONTENU PDF : " + text[:1500].replace("\n", " ")
            except:
                return "[Erreur lecture PDF]"

        # --- CAS 3 : TEXTE BRUT ---
        valid_exts = [".txt", ".md", ".py", ".json", ".html", ".css", ".csv", ".xml", ".ini", ".log"]
        if ext in valid_exts:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return "CONTENU TEXTE : " + f.read(2000).replace("\n", " ")
            except: return "[Erreur lecture Texte]"
            
        return "[Type de fichier non analysable]"

    def _analyze_image_with_vision(self, image_path):
        """Envoie l'image à Llama-3.2-Vision via API Ollama"""
        if not self.ensure_ollama_ready(): return "[IA non dispo]"
        
        try:
            # Encodage Base64
            with open(image_path, "rb") as f:
                img_bytes = f.read()
                img_b64 = base64.b64encode(img_bytes).decode('utf-8')

            model = "llama3.2-vision" # Force le modèle Vision
            
            prompt = """Analyze this image in detail. 
            1. If there is text (OCR), transcribe it exactly.
            2. Describe the visual content (objects, diagrams).
            3. Summarize the purpose of this document/image."""

            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "images": [img_b64]
            }
            
            response = requests.post(OLLAMA_API_URL, json=payload)
            if response.status_code == 200:
                desc = response.json().get("response", "").strip()
                return f"ANALYSE VISION (OCR) : {desc}"
            else:
                return f"[Erreur Vision: {response.text}]"

        except Exception as e:
            return f"[Erreur Vision Critique: {e}]"

    # --- SCRAPING (Inchangé) ---
    def start_learning_process(self):
        if "scraping_summary" in self.config and self.config["scraping_summary"]:
            self.log("♻️ Identité entreprise chargée.")
            return
        url = self.config.get("website_url")
        if url: threading.Thread(target=self._scrape_and_analyze, args=(url,)).start()

    def _scrape_and_analyze(self, url):
        self.log(f"🌐 Lecture site : {url}...")
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                raw = " ".join([t.get_text().strip() for t in soup.find_all(['h1', 'h2', 'p']) if len(t.get_text()) > 30])
                self.analyze_company_with_ai(raw[:6000])
        except Exception as e: self.log(f"❌ Erreur scraping: {e}")

    def analyze_company_with_ai(self, raw_text):
        if not self.ensure_ollama_ready(): return
        model = self.config.get("selected_model_tag", "moondream")
        try:
            res = requests.post(OLLAMA_API_URL, json={"model": model, "prompt": f"Synthèse fiche identité entreprise : {raw_text}", "stream": False})
            if res.status_code == 200:
                self.config["scraping_summary"] = res.json().get("response", "")
                self.save_config()
                self.log("✅ Identité générée.")
        except: pass

    # --- WATCHDOG ---
    def start_watchdogs(self):
        targets = self.config.get("targets", [])
        if not targets: return
        
        # On passe 'self' au handler pour qu'il puisse accéder à la Queue
        event_handler = AuraFileHandler(self.db_path, self.log, self.analysis_queue)
        
        for target in targets:
            path = target["path"]
            if os.path.exists(path):
                observer = Observer()
                observer.schedule(event_handler, path, recursive=True)
                observer.start()
                self.observers.append(observer)
                self.log(f"👀 Surveillance : {path}")

    # --- GÉNÉRATION DE RAPPORT ---
    def generate_report(self, on_complete_callback):
        threading.Thread(target=self._run_report_generation, args=(on_complete_callback,)).start()

    def _run_report_generation(self, callback):
        if not self.ensure_ollama_ready(): return
        self.log("📝 Compilation du rapport avec les Snapshots...")

        events_data = ""
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            cursor = conn.cursor()
            # On récupère TOUT : timestamp, type, nom, et surtout LE CONTENU DÉJÀ ANALYSÉ
            cursor.execute("SELECT timestamp, event_type, file_path, content_summary FROM file_events ORDER BY timestamp DESC LIMIT 30")
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                callback("Rien à signaler.")
                return

            self.log(f"📊 Utilisation de {len(rows)} événements mémorisés...")

            for row in rows:
                ts, ev_type, fpath, content = row
                fname = os.path.basename(fpath)
                
                # Si le contenu est vide (ex: suppression sans analyse préalable ou fichier ignoré)
                if not content: content = "[Pas de contenu analysé disponible]"
                
                events_data += f"""
                --- ÉVÉNEMENT ---
                Heure : {ts}
                Action : {ev_type}
                Fichier : {fname}
                CONTENU ANALYSÉ (SNAPSHOT) : 
                {content}
                -----------------
                """

        except Exception as e:
            self.log(f"❌ Erreur Data: {e}")
            return

        company_context = self.config.get("scraping_summary", "Non défini")
        
        prompt = f"""
        Tu es l'Analyste IA de l'entreprise.
        
        CONTEXTE ENTREPRISE :
        {company_context}

        HISTORIQUE DES FICHIERS (AVEC ANALYSE DE CONTENU/OCR) :
        {events_data}

        MISSION :
        Rédige un rapport synthétique en Français.
        1. Base-toi sur le "CONTENU ANALYSÉ" pour expliquer ce qui a été fait (ex: "Ajout d'un plan technique" et pas juste "Ajout fichier.pdf").
        2. Si des images ont été ajoutées, décris ce qu'elles contiennent grâce à l'analyse OCR fournie.
        3. Si des fichiers ont été supprimés, mentionne-le simplement.
        4. Groupe les événements par projet si possible.
        """

        self.log("🤖 Rédaction du rapport...")
        try:
            model = self.config.get("selected_model_tag", "moondream")
            # Astuce : Si on a Llama 3.2 Vision, on l'utilise aussi pour le texte, il est meilleur
            if "vision" in model or "llama" in model: model = "llama3.2-vision"

            payload = {"model": model, "prompt": prompt, "stream": False}
            response = requests.post(OLLAMA_API_URL, json=payload)
            if response.status_code == 200:
                callback(response.json().get("response", ""))
                self.log("✅ Rapport terminé.")
            else:
                callback(f"Erreur IA: {response.text}")
        except Exception as e:
            self.log(f"❌ Erreur Critique : {e}")

# --- HANDLER (WATCHDOG) ---
class AuraFileHandler(FileSystemEventHandler):
    def __init__(self, db_path, log_callback, analysis_queue):
        self.db_path = db_path
        self.log = log_callback
        self.queue = analysis_queue # On récupère la file d'attente
        self.last_events = {} 

    def is_valid(self, path):
        f = os.path.basename(path)
        if f.startswith("~$") or f.endswith((".tmp", ".log", ".ini", ".db", ".lnk", ".dat")): return False
        return True

    def _debounce(self, path):
        curr = time.time()
        if curr - self.last_events.get(path, 0) < 1.0: return True
        self.last_events[path] = curr
        return False

    def on_created(self, event):
        if not event.is_directory and self.is_valid(event.src_path):
            self.last_events[event.src_path] = time.time()
            self.record_event("NOUVEAU", event.src_path)

    def on_modified(self, event):
        if not event.is_directory and self.is_valid(event.src_path):
            if self._debounce(event.src_path): return 
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
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.log(f"📁 [{type}] {filename}")
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            cursor = conn.cursor()
            # On insère l'événement de base (sans content_summary pour l'instant)
            cursor.execute("INSERT INTO file_events (timestamp, event_type, file_path) VALUES (?, ?, ?)",
                           (ts, type, path_to_log))
            event_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # --- OPTIMISATION : ENVOI EN QUEUE POUR ANALYSE IA ---
            # On n'analyse que les créations et modifs, pas les suppressions (trop tard)
            if type in ["NOUVEAU", "MODIFIÉ", "DÉPLACÉ"] and path_to_log:
                self.queue.put((event_id, path_to_log, type))
                
        except Exception as e:
            print(f"DB Error: {e}")

# --- FRONTEND (DASHBOARD) ---
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
        self.btn_generate = ctk.CTkButton(self.sidebar, text="⚡ Générer Rapport", fg_color="#EF4444", hover_color="#DC2626", command=self.action_generate_report)
        self.btn_generate.pack(padx=20, pady=20, fill="x")

        self.main_view = ctk.CTkFrame(self, corner_radius=0, fg_color="white")
        self.main_view.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        ctk.CTkLabel(self.main_view, text="Activité en Temps Réel", font=("Arial", 20, "bold"), text_color="#111827").pack(anchor="w", pady=(0, 10))

        self.console = ctk.CTkTextbox(self.main_view, width=800, height=400, font=("Consolas", 12), fg_color="#1E1E1E", text_color="#10B981")
        self.console.pack(fill="both", expand=True, pady=(0, 20))

        self.report_frame = ctk.CTkFrame(self.main_view, fg_color="#F3F4F6", corner_radius=10, border_color="#D1D5DB", border_width=1)
        self.report_frame.pack(fill="x", ipady=10)
        self.report_frame.pack_forget() 
        self.report_text_box = ctk.CTkTextbox(self.report_frame, height=150, fg_color="white", text_color="black")
        self.report_text_box.pack(fill="x", padx=20, pady=10)

        self.brain = AuraBrain(self.log_to_console)
        self.after(1000, self.start_automation)

    def log_to_console(self, message):
        self.after(0, lambda: self._safe_log(message))
    def _safe_log(self, message):
        ts = datetime.now().strftime("[%H:%M:%S]")
        self.console.insert("end", f"{ts} {message}\n")
        self.console.see("end")

    def start_automation(self):
        self.log_to_console("🚀 Démarrage...")
        self.brain.ensure_ollama_ready()
        self.brain.start_learning_process()
        self.brain.start_watchdogs()

    def action_generate_report(self):
        self.btn_generate.configure(state="disabled", text="Analyse en cours...")
        self.report_frame.pack_forget()
        self.brain.generate_report(lambda r: self.after(0, lambda: self._display_report(r)))

    def _display_report(self, text):
        self.btn_generate.configure(state="normal", text="⚡ Générer Rapport")
        self.report_frame.pack(fill="x", ipady=10, pady=10)
        self.report_text_box.delete("0.0", "end")
        self.report_text_box.insert("0.0", text)
        self.log_to_console("📄 Rapport affiché.")

if __name__ == "__main__":
    app = DashboardApp()
    app.mainloop()