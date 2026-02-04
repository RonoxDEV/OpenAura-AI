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

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "OpenAuraConfig.json")
DB_PATH = os.path.join(BASE_DIR, "aura_memory.db")
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# =============================================================================
# BACKEND (CERVEAU)
# =============================================================================
class AuraBrain:
    def __init__(self, log_callback):
        self.log = log_callback
        self.config = self.load_config()
        self.db_path = DB_PATH
        self.observers = []
        
        # File d'attente (FIFO) pour l'analyse IA
        self.analysis_queue = queue.Queue()
        self.stop_event = threading.Event()
        
        self.init_db()
        
        # Démarrage du Worker (L'ouvrier qui analyse en fond)
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
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    event_type TEXT,
                    file_path TEXT,
                    content_summary TEXT
                )
            ''')
            # Patch colonne si besoin
            cursor.execute("PRAGMA table_info(file_events)")
            cols = [i[1] for i in cursor.fetchall()]
            if "content_summary" not in cols:
                cursor.execute("ALTER TABLE file_events ADD COLUMN content_summary TEXT")
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_filepath ON file_events (file_path)")
            conn.commit()
            conn.close()
            self.log(f"🧠 Mémoire connectée.")
        except Exception as e:
            self.log(f"❌ ERREUR BDD : {e}")

    def ensure_ollama_ready(self):
        url = "http://localhost:11434"
        try:
            requests.get(url, timeout=0.5)
            return True
        except:
            self.log("⚠️ Démarrage Ollama...")
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen(["ollama", "serve"], startupinfo=startupinfo, creationflags=0x08000000, 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for i in range(15):
                time.sleep(1)
                try:
                    requests.get(url, timeout=0.5)
                    self.log("✅ Ollama prêt.")
                    return True
                except: pass
            return False
        except: return False

    # --- WORKER D'ANALYSE (LE CŒUR DU SYSTÈME) ---
    def worker_analysis_loop(self):
        while not self.stop_event.is_set():
            try:
                # Récupération tâche
                event_id, file_path, event_type = self.analysis_queue.get(timeout=1)
                
                if "SUPPRIMÉ" in event_type or not os.path.exists(file_path):
                    self.analysis_queue.task_done()
                    continue

                fname = os.path.basename(file_path)
                self.log(f"👁️ Analyse IA : {fname}...")
                
                # 1. Extraction / OCR
                content = self.analyze_file_content(file_path)
                
                # 2. Sauvegarde BDD
                if content:
                    self.update_db_snapshot(event_id, content)
                    self.log(f"💾 Snapshot OK : {fname}")
                
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
        except: pass

    def analyze_file_content(self, path):
        ext = os.path.splitext(path)[1].lower()
        
        # IMAGE -> VISION
        if ext in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
            return self._analyze_image_with_vision(path)

        # PDF -> TEXTE
        if ext == ".pdf":
            try:
                reader = pypdf.PdfReader(path)
                text = ""
                for i in range(min(3, len(reader.pages))):
                    t = reader.pages[i].extract_text()
                    if t: text += t
                if len(text) < 50: return "[PDF Image/Scan - Texte illisible]"
                return f"CONTENU PDF ({len(text)} cars): " + text[:2000].replace("\n", " ")
            except: return "[Erreur PDF]"

        # TEXTE
        if ext in [".txt", ".md", ".py", ".json", ".html", ".csv", ".log", ".ini"]:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return "CONTENU TEXTE : " + f.read(2000).replace("\n", " ")
            except: return "[Erreur lecture]"
            
        return "[Fichier binaire ignoré]"

    def _analyze_image_with_vision(self, image_path):
        if not self.ensure_ollama_ready(): return "[IA Off]"
        try:
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            
            # Utilisation du modèle configuré ou fallback
            model = self.config.get("selected_model_tag", "llama3.2-vision")
            if "moondream" in model: model = "moondream" 
            else: model = "llama3.2-vision" # Force un modèle vision puissant

            payload = {
                "model": model,
                "prompt": "Describe this image. If it's a document, read the text (OCR).",
                "stream": False,
                "images": [b64]
            }
            res = requests.post(OLLAMA_API_URL, json=payload)
            if res.status_code == 200:
                return f"ANALYSE VISION : {res.json().get('response', '').strip()}"
        except: pass
        return "[Erreur Vision]"

    # --- APPRENTISSAGE WEB ---
    def start_learning_process(self):
        if self.config.get("scraping_summary"):
            self.log("♻️ Identité chargée.")
            return
        url = self.config.get("website_url")
        if url: threading.Thread(target=self._scrape, args=(url,)).start()

    def _scrape(self, url):
        self.log(f"🌐 Lecture site : {url}")
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                txt = " ".join([t.get_text().strip() for t in soup.find_all(['h1','h2','p']) if len(t.get_text())>30])
                self.analyze_company(txt[:6000])
        except: self.log("❌ Erreur Site")

    def analyze_company(self, txt):
        if not self.ensure_ollama_ready(): return
        try:
            res = requests.post(OLLAMA_API_URL, json={
                "model": self.config.get("selected_model_tag", "moondream"),
                "prompt": f"Synthèse fiche identité : {txt}", "stream": False
            })
            if res.status_code == 200:
                self.config["scraping_summary"] = res.json().get("response", "")
                self.save_config()
                self.log("✅ Identité générée.")
        except: pass

    # --- WATCHDOG & SCAN INITIAL ---
    def start_watchdogs(self):
        targets = self.config.get("targets", [])
        if not targets: return
        
        # Scan initial en Thread
        threading.Thread(target=self._perform_initial_scan, args=(targets,)).start()
        
        handler = AuraFileHandler(self.db_path, self.log, self.analysis_queue)
        for t in targets:
            if os.path.exists(t["path"]):
                Observer().schedule(handler, t["path"], recursive=True).start()
                self.log(f"👀 Surveillance : {t['path']}")

    def _perform_initial_scan(self, targets):
        self.log("📂 Scan des fichiers existants...")
        count = 0
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for t in targets:
                if not os.path.exists(t["path"]): continue
                for root, _, files in os.walk(t["path"]):
                    for f in files:
                        if f.startswith("~$") or f.endswith((".tmp",".db",".log")): continue
                        
                        full_path = os.path.join(root, f)
                        
                        # Vérif si déjà en base
                        cursor.execute("SELECT id, content_summary FROM file_events WHERE file_path = ? LIMIT 1", (full_path,))
                        row = cursor.fetchone()
                        
                        if not row:
                            # NOUVEAU (Jamais vu) -> On ajoute ET on analyse
                            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            cursor.execute("INSERT INTO file_events (timestamp, event_type, file_path) VALUES (?, ?, ?)",
                                           (ts, "EXISTANT", full_path))
                            event_id = cursor.lastrowid
                            self.analysis_queue.put((event_id, full_path, "EXISTANT")) # <--- C'EST ICI LA CORRECTION
                            count += 1
                            self.log(f"📥 Ajout & Analyse : {f}")
                        
                        elif row[1] is None or row[1] == "":
                            # DÉJÀ VU MAIS PAS ANALYSÉ -> On analyse
                            self.analysis_queue.put((row[0], full_path, "EXISTANT"))
                            self.log(f"📥 Rattrapage Analyse : {f}")
                            count += 1

            conn.commit()
            conn.close()
            self.log(f"✅ Scan terminé : {count} fichiers envoyés à l'analyse.")
        except Exception as e: self.log(f"❌ Erreur Scan: {e}")

    # --- RAPPORT ---
    def generate_report(self, cb):
        threading.Thread(target=self._gen_report, args=(cb,)).start()

    def _gen_report(self, cb):
        if not self.ensure_ollama_ready(): return
        self.log("📝 Génération du rapport...")
        
        data = ""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            # On prend TOUT, même les "EXISTANT" s'ils ont du contenu analysé
            c.execute("SELECT timestamp, event_type, file_path, content_summary FROM file_events ORDER BY timestamp DESC LIMIT 50")
            rows = c.fetchall()
            conn.close()
            
            if not rows:
                cb("Rien dans la base.")
                return

            for r in rows:
                content = r[3] if r[3] else "[En attente d'analyse...]"
                if len(content) > 600: content = content[:600] + "..."
                
                data += f"""
                FICHIER: {os.path.basename(r[2])}
                TYPE: {r[1]} (Date: {r[0]})
                ANALYSE CONTENU: {content}
                --------------------------------
                """
        except: pass

        context = self.config.get("scraping_summary", "")
        prompt = f"""
        Tu es l'IA de l'entreprise.
        CONTEXTE: {context}
        
        FICHIERS DÉTECTÉS (ET LEUR CONTENU) :
        {data}
        
        TACHE :
        Rédige un rapport détaillé en Français.
        Même si les fichiers sont marqués "EXISTANT", décris ce qu'ils contiennent et leur utilité pour l'entreprise.
        Ne dis pas "Rien de nouveau", dis plutot "Voici l'état actuel des documents surveillés".
        Fais des liens entre le contenu des documents (ex: Cahier des charges) et l'activité de l'entreprise.
        """
        
        try:
            model = self.config.get("selected_model_tag", "moondream")
            if "vision" in model or "llama" in model: model = "llama3.2-vision"
            
            res = requests.post(OLLAMA_API_URL, json={"model": model, "prompt": prompt, "stream": False})
            if res.status_code == 200:
                cb(res.json().get("response", ""))
                self.log("✅ Rapport OK.")
            else: cb("Erreur IA")
        except: cb("Erreur Critique")

# --- HANDLER ---
class AuraFileHandler(FileSystemEventHandler):
    def __init__(self, db, log, queue):
        self.db = db
        self.log = log
        self.queue = queue
        self.last = {}
    
    def _chk(self, p):
        t = time.time()
        if t - self.last.get(p, 0) < 1: return True
        self.last[p] = t
        return False

    def on_created(self, event):
        if not event.is_directory: self.rec("NOUVEAU", event.src_path)
    def on_modified(self, event):
        if not event.is_directory and not self._chk(event.src_path): self.rec("MODIFIÉ", event.src_path)
    def on_deleted(self, event):
        if not event.is_directory: self.rec("SUPPRIMÉ", event.src_path)

    def rec(self, type, path):
        if os.path.basename(path).startswith("~$") or path.endswith(".tmp"): return
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log(f"📁 [{type}] {os.path.basename(path)}")
        try:
            conn = sqlite3.connect(self.db, timeout=10)
            c = conn.cursor()
            c.execute("INSERT INTO file_events (timestamp, event_type, file_path) VALUES (?,?,?)", (ts, type, path))
            eid = c.lastrowid
            conn.commit()
            conn.close()
            
            if type != "SUPPRIMÉ": self.queue.put((eid, path, type))
        except: pass

# --- UI ---
class DashboardApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OpenAura Dashboard")
        self.geometry("1100x700")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text="OpenAura", font=("Arial", 22, "bold")).pack(pady=20)
        
        self.btn_gen = ctk.CTkButton(self.sidebar, text="⚡ Générer Rapport", fg_color="#EF4444", command=self.gen)
        self.btn_gen.pack(pady=20, padx=20)
        
        self.main = ctk.CTkFrame(self, fg_color="white")
        self.main.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        self.console = ctk.CTkTextbox(self.main, height=400, fg_color="#1E1E1E", text_color="#10B981", font=("Consolas", 12))
        self.console.pack(fill="both", expand=True)
        
        self.report_area = ctk.CTkTextbox(self.main, height=150, fg_color="#F3F4F6", text_color="black")
        self.report_area.pack(fill="x", pady=10)
        
        self.brain = AuraBrain(self.log)
        self.after(1000, self.start)

    def log(self, msg):
        self.after(0, lambda: self.console.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n") or self.console.see("end"))
    
    def start(self):
        self.brain.ensure_ollama_ready()
        self.brain.start_learning_process()
        self.brain.start_watchdogs()

    def gen(self):
        self.btn_gen.configure(state="disabled")
        self.brain.generate_report(self.show)

    def show(self, txt):
        self.btn_gen.configure(state="normal")
        self.report_area.delete("0.0", "end")
        self.report_area.insert("0.0", txt)

if __name__ == "__main__":
    app = DashboardApp()
    app.mainloop()