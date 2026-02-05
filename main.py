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

# --- GESTION ROBUSTE DES CHEMINS ---
# Pour main.py (racine)
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
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
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
            # Patch colonne si besoin (Migration)
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
            requests.get(url, timeout=1.0)
            return True
        except:
            self.log("⚠️ Moteur IA non détecté. Tentative de démarrage...")
        
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen(["ollama", "serve"], startupinfo=startupinfo, creationflags=0x08000000, 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            for i in range(15):
                time.sleep(1)
                try:
                    requests.get(url, timeout=1.0)
                    self.log("✅ Ollama prêt.")
                    return True
                except: pass
            return False
        except Exception as e:
            self.log(f"❌ Impossible de lancer Ollama : {e}")
            return False

    # --- WORKER D'ANALYSE ---
    def worker_analysis_loop(self):
        while not self.stop_event.is_set():
            try:
                # Récupération tâche (bloquant avec timeout pour pouvoir s'arrêter)
                event_id, file_path, event_type = self.analysis_queue.get(timeout=2)
                
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
        except Exception as e:
            print(f"Update DB Error: {e}")

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
                for i in range(min(5, len(reader.pages))): # On lit les 5 premières pages
                    t = reader.pages[i].extract_text()
                    if t: text += t
                if len(text) < 50: return "[PDF Image/Scan - Texte illisible sans OCR lourd]"
                return f"CONTENU PDF : " + text[:2500].replace("\n", " ")
            except Exception as e: return f"[Erreur PDF: {e}]"

        # TEXTE
        if ext in [".txt", ".md", ".py", ".json", ".html", ".csv", ".log", ".ini", ".xml", ".yaml"]:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return "CONTENU TEXTE : " + f.read(2500).replace("\n", " ")
            except Exception as e: return f"[Erreur lecture: {e}]"
            
        return "[Format non supporté pour analyse texte]"

    def _analyze_image_with_vision(self, image_path):
        if not self.ensure_ollama_ready(): return "[Moteur IA indisponible]"
        try:
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            
            # Utilisation du modèle vision
            model = self.config.get("selected_model_tag", "llama3.2-vision")
            # Forcer un modèle vision si le tag choisi n'en est pas un connu (sécurité)
            if "vision" not in model.lower() and "moondream" not in model.lower() and "llava" not in model.lower() and "qwen" not in model.lower():
                model = "llama3.2-vision" 

            payload = {
                "model": model,
                "prompt": "Décris précisément cette image ou lis le texte s'il s'agit d'un document (OCR). Sois concis.",
                "stream": False,
                "images": [b64]
            }
            res = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
            if res.status_code == 200:
                return f"ANALYSE VISION : {res.json().get('response', '').strip()}"
            else:
                return f"[Erreur Ollama: {res.status_code}]"
        except Exception as e:
            return f"[Erreur Vision: {e}]"

    # --- APPRENTISSAGE WEB ---
    def start_learning_process(self):
        if self.config.get("scraping_summary"):
            self.log("♻️ Contexte entreprise chargé.")
            return
        url = self.config.get("website_url")
        if url: threading.Thread(target=self._scrape, args=(url,), daemon=True).start()

    def _scrape(self, url):
        self.log(f"🌐 Analyse du site : {url}")
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                txt = " ".join([t.get_text().strip() for t in soup.find_all(['h1','h2','p']) if len(t.get_text())>30])
                self.analyze_company(txt[:6000])
            else:
                self.log(f"❌ Erreur Site ({r.status_code})")
        except: self.log("❌ Erreur Scraping")

    def analyze_company(self, txt):
        if not self.ensure_ollama_ready(): return
        try:
            res = requests.post(OLLAMA_API_URL, json={
                "model": self.config.get("selected_model_tag", "moondream"),
                "prompt": f"Synthèse fiche identité (Activité, Produits, Valeurs) : {txt}", 
                "stream": False
            })
            if res.status_code == 200:
                self.config["scraping_summary"] = res.json().get("response", "")
                self.save_config()
                self.log("✅ Identité entreprise générée.")
        except: pass

    # --- WATCHDOG & SCAN INITIAL ---
    def start_watchdogs(self):
        targets = self.config.get("targets", [])
        if not targets: 
            self.log("⚠️ Aucune cible configurée.")
            return
        
        threading.Thread(target=self._perform_initial_scan, args=(targets,), daemon=True).start()
        
        handler = AuraFileHandler(self.db_path, self.log, self.analysis_queue)
        for t in targets:
            path = t["path"]
            if os.path.exists(path):
                observer = Observer()
                observer.schedule(handler, path, recursive=True)
                observer.start()
                self.observers.append(observer)
                self.log(f"👀 Surveillance : {os.path.basename(path)}")
            else:
                self.log(f"❌ Chemin introuvable : {path}")

    def _perform_initial_scan(self, targets):
        self.log("📂 Inventaire de la mémoire...")
        count = 0
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for t in targets:
                path = t["path"]
                if not os.path.exists(path): continue
                for root, _, files in os.walk(path):
                    for f in files:
                        if self._is_ignored(f): continue
                        
                        full_path = os.path.join(root, f)
                        
                        # Vérif si déjà en base
                        cursor.execute("SELECT id, content_summary FROM file_events WHERE file_path = ? LIMIT 1", (full_path,))
                        row = cursor.fetchone()
                        
                        if not row:
                            # NOUVEAU -> Ajout & File d'attente
                            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            cursor.execute("INSERT INTO file_events (timestamp, event_type, file_path) VALUES (?, ?, ?)",
                                           (ts, "EXISTANT", full_path))
                            event_id = cursor.lastrowid
                            self.analysis_queue.put((event_id, full_path, "EXISTANT"))
                            count += 1
                        elif row[1] is None or row[1] == "":
                            # EXISTANT mais non analysé -> File d'attente
                            self.analysis_queue.put((row[0], full_path, "EXISTANT"))
                            count += 1

            conn.commit()
            conn.close()
            self.log(f"✅ Mémoire synchronisée : {count} analyses en attente.")
        except Exception as e: 
            self.log(f"❌ Erreur Scan: {e}")

    def _is_ignored(self, filename):
        return filename.startswith("~$") or filename.endswith((".tmp",".db",".log",".ini",".dat",".lnk"))

    # --- GÉNÉRATION DE RAPPORT ---
    def generate_report(self, cb):
        threading.Thread(target=self._gen_report, args=(cb,), daemon=True).start()

    def _gen_report(self, cb):
        if not self.ensure_ollama_ready(): 
            cb("Le moteur IA n'est pas prêt.")
            return
            
        self.log("📝 Composition du rapport final...")
        
        data = ""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT timestamp, event_type, file_path, content_summary FROM file_events ORDER BY timestamp DESC LIMIT 30")
            rows = c.fetchall()
            conn.close()
            
            if not rows:
                cb("Aucune donnée disponible pour rédiger un rapport.")
                return

            for r in rows:
                content = r[3] if r[3] else "[Analyse en cours...]"
                if len(content) > 500: content = content[:500] + "..."
                
                data += f"- {os.path.basename(r[2])} ({r[1]} le {r[0]})\n  Résumé: {content}\n\n"
        except: pass

        context = self.config.get("scraping_summary", "Non défini")
        # Nouveau Prompt Style "Journaliste Interne"
        prompt = f"""
        Tu es le Journaliste Interne d'ATMAN MANUFACTURE. 
        Ton rôle est de rédiger "Les NEWS de Atman !" de façon dynamique et concise.

        CONTEXTE : {context}
        
        DONNÉES DE LA SEMAINE (CONTENU DES DOCUMENTS) :
        {data}
        
        CONSIGNES DE RÉDACTION :
        1. Titre obligatoire : "Les NEWS de Atman !"
        2. Phrase d'accroche : "Voici les dernières nouvelles dans l'entreprise de la semaine dernière :"
        3. Pour chaque information, tu DOIS citer la source entre parenthèses comme ceci : (Source : document "nom_du_document").
        4. Ne sois pas générique. Si un document parle de "Suisse" ou de "Production", utilise ces détails concrets.
        5. Utilise des puces (•) pour chaque news.
        6. Si le document est un "Cahier des charges", explique quelle est la grande décision technique prise.

        EXEMPLE DE STYLE ATTENDU :
        • Atman va délocaliser la production en suisse suite à une étude de marché (Source: document "étude de marché")
        """
        
        try:
            model = self.config.get("selected_model_tag", "moondream")
            # Pour le rapport on préfère un modèle texte pur si possible, mais on garde le choix user
            res = requests.post(OLLAMA_API_URL, json={"model": model, "prompt": prompt, "stream": False}, timeout=90)
            if res.status_code == 200:
                cb(res.json().get("response", ""))
                self.log("✅ Rapport prêt.")
            else: cb(f"Erreur IA (Code {res.status_code})")
        except Exception as e: cb(f"Erreur Critique : {e}")

# --- HANDLER D'ÉVÉNEMENTS FICHIERS ---
class AuraFileHandler(FileSystemEventHandler):
    def __init__(self, db, log, queue):
        self.db = db
        self.log = log
        self.queue = queue
        self.last_events = {}
    
    def _is_spam(self, path):
        t = time.time()
        if t - self.last_events.get(path, 0) < 1.0: return True
        self.last_events[path] = t
        return False

    def on_created(self, event):
        if not event.is_directory: self.rec("NOUVEAU", event.src_path)
    def on_modified(self, event):
        if not event.is_directory and not self._is_spam(event.src_path): self.rec("MODIFIÉ", event.src_path)
    def on_deleted(self, event):
        if not event.is_directory: self.rec("SUPPRIMÉ", event.src_path)

    def rec(self, type, path):
        f = os.path.basename(path)
        if f.startswith("~$") or f.endswith((".tmp", ".db", ".log", ".ini", ".lnk")): return
        
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log(f"📁 [{type}] {f}")
        
        try:
            conn = sqlite3.connect(self.db, timeout=10)
            c = conn.cursor()
            c.execute("INSERT INTO file_events (timestamp, event_type, file_path) VALUES (?,?,?)", (ts, type, path))
            eid = c.lastrowid
            conn.commit()
            conn.close()
            
            if type != "SUPPRIMÉ":
                self.queue.put((eid, path, type))
        except Exception as e:
            print(f"Handler DB Error: {e}")

# --- INTERFACE (DASHBOARD) ---
class DashboardApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OpenAura Professional - Dashboard")
        self.geometry("1100x750")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="OpenAura AI", font=("Arial", 24, "bold"), text_color="#3B82F6").pack(pady=30)
        
        self.btn_gen = ctk.CTkButton(self.sidebar, text="⚡ Générer Rapport", 
                                     fg_color="#EF4444", hover_color="#DC2626",
                                     height=45, font=("Arial", 14, "bold"),
                                     command=self.gen)
        self.btn_gen.pack(pady=20, padx=20, fill="x")
        
        # Main
        self.main = ctk.CTkFrame(self, fg_color="#F9FAFB")
        self.main.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        ctk.CTkLabel(self.main, text="Flux d'Activité Sentinelle", font=("Arial", 18, "bold"), text_color="#111827").pack(anchor="w", pady=(0, 10))
        
        self.console = ctk.CTkTextbox(self.main, height=450, fg_color="#111827", text_color="#10B981", font=("Consolas", 12))
        self.console.pack(fill="both", expand=True)
        
        ctk.CTkLabel(self.main, text="Dernier Rapport IA", font=("Arial", 14, "bold"), text_color="#374151").pack(anchor="w", pady=(15, 5))
        self.report_area = ctk.CTkTextbox(self.main, height=180, fg_color="white", text_color="#1F2937", border_width=1, border_color="#D1D5DB")
        self.report_area.pack(fill="x")
        
        self.brain = AuraBrain(self.log)
        self.after(1000, self.start)

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.after(0, lambda: self.console.insert("end", f"[{ts}] {msg}\n") or self.console.see("end"))
    
    def start(self):
        self.brain.ensure_ollama_ready()
        self.brain.start_learning_process()
        self.brain.start_watchdogs()
        
        model = self.brain.config.get("selected_model_tag", "Inconnu")
        self.log(f"🤖 Intelligence active : {model}")

    def gen(self):
        self.btn_gen.configure(state="disabled", text="Rédaction IA...")
        self.brain.generate_report(self.show)

    def show(self, txt):
        self.btn_gen.configure(state="normal", text="⚡ Générer Rapport")
        self.report_area.delete("0.0", "end")
        self.report_area.insert("0.0", txt)
        self.log("📄 Nouveau rapport disponible.")

if __name__ == "__main__":
    app = DashboardApp()
    app.mainloop()