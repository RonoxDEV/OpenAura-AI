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



import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import time
from PIL import Image
import os
import psutil
import platform
import keyring
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import subprocess
import shutil
import sys

# Gestion de WMI uniquement pour Windows
try:
    import wmi
    import pythoncom
except ImportError:
    wmi = None
    pythoncom = None

# --- CONFIGURATION DU LOOK ---
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class WizardApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- 1. CONFIGURATION FENÊTRE ---
        self.title("Assistant OpenAura")
        self.geometry("1000x750") # Un peu plus large pour afficher les 3 cartes
        self.resizable(True, True)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- 2. DATA ---
        # Gestion des chemins pour dev et production (PyInstaller)
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Si bundlé avec PyInstaller
        if getattr(sys, 'frozen', False):
            # Mode production (exécutable)
            base_dir = sys._MEIPASS
            self.assets_path = os.path.join(base_dir, "ui", "assets")
        else:
            # Mode développement
            self.assets_path = os.path.join(current_dir, "assets")

        self.config = {
            "install_type": None,
            "company_name": "",
            "website_url": "",
            "ai_engine": "local", 
            "api_provider": "",
            "api_key": "",
            "hardware_specs": {},
            "selected_model": "" # Stockera le modèle final choisi
        }

        # --- 3. FRAME PRINCIPALE ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure((0, 1), weight=1)

        # Lancement
        self.show_step_1()

    # --- UTILITAIRES ---
    def clear_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def create_nav_buttons(self, back_cmd, next_cmd, next_text="Suivant"):
        nav_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        nav_frame.pack(side="bottom", fill="x", pady=20)
        if back_cmd:
            ctk.CTkButton(nav_frame, text="Retour", fg_color="transparent", border_width=1, border_color="#D1D5DB", text_color="gray", hover_color="#F3F4F6", width=100, height=40, command=back_cmd).pack(side="left", padx=20)
        if next_cmd:
            self.btn_next_global = ctk.CTkButton(nav_frame, text=next_text, fg_color="#0066FF", hover_color="#0052CC", width=120, height=40, font=("Arial", 14, "bold"), command=next_cmd)
            self.btn_next_global.pack(side="right", padx=20)

    def create_header(self, step_num, title, subtitle):
        ctk.CTkLabel(self.main_frame, text=f"ÉTAPE {step_num} sur 7", fg_color="#E0F2FE", text_color="#0066FF", corner_radius=10, font=("Arial", 12, "bold"), width=120, height=30).pack(pady=(30, 15))
        ctk.CTkLabel(self.main_frame, text=title, font=("Arial", 32, "bold"), text_color="#111827").pack(pady=5)
        ctk.CTkLabel(self.main_frame, text=subtitle, font=("Arial", 16), text_color="#6B7280").pack(pady=(0, 40))

    # =========================================================================
    # ÉTAPES 1 & 2 (Identiques)
    # =========================================================================
    def show_step_1(self):
        self.clear_frame()
        self.create_header(1, "Bienvenue sur OpenAura", "Comment souhaitez-vous démarrer ?")
        cards_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        cards_frame.pack(expand=True)
        self.create_image_card(cards_frame, "stars.png", "Nouvelle Installation", "Configurer OpenAura depuis zéro.", self.action_go_to_step_2, 0)
        self.create_image_card(cards_frame, "folder.png", "Restaurer une sauvegarde", "Charger un fichier .OpenAuraConfig.json", self.action_restore, 1)
        ctk.CTkLabel(self.main_frame, text="OpenAura v1.0 - Private & Local AI", text_color="#9CA3AF", font=("Arial", 10)).pack(side="bottom", pady=10)

    def create_image_card(self, parent, img_filename, title, desc, command, col):
        full_path = os.path.join(self.assets_path, img_filename)
        try:
            pil_image = Image.open(full_path)
            ctk_icon = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(80, 80))
        except: ctk_icon = None
        card = ctk.CTkFrame(parent, width=320, height=280, corner_radius=20, fg_color="white", border_width=2, border_color="#E5E7EB", cursor="hand2")
        card.grid(row=0, column=col, padx=25, pady=20)
        card.grid_propagate(False)
        if ctk_icon: ctk.CTkLabel(card, text="", image=ctk_icon).place(relx=0.5, rely=0.35, anchor="center")
        else: ctk.CTkLabel(card, text="?", font=("Arial", 40)).place(relx=0.5, rely=0.35, anchor="center")
        ctk.CTkLabel(card, text=title, font=("Arial", 18, "bold"), text_color="#1F2937").place(relx=0.5, rely=0.65, anchor="center")
        ctk.CTkLabel(card, text=desc, font=("Arial", 13), text_color="#6B7280", wraplength=280).place(relx=0.5, rely=0.80, anchor="center")
        def on_enter(e): card.configure(border_color="#0066FF", fg_color="#F0F9FF")
        def on_leave(e): card.configure(border_color="#E5E7EB", fg_color="white")
        def on_click(e): command()
        for w in card.winfo_children() + [card]:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)

    def action_go_to_step_2(self):
        self.config["install_type"] = "new"
        self.show_step_2()

    def action_restore(self):
        file_path = filedialog.askopenfilename(filetypes=[("Configuration OpenAura", "*.json")])
        if file_path and file_path.endswith(".OpenAuraConfig.json"):
            messagebox.showinfo("Succès", f"Sauvegarde chargée.")

    def show_step_2(self):
        self.clear_frame()
        self.create_header(2, "Identité de l'entreprise", "Ces informations aident l'IA à comprendre le contexte.")
        form_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        form_frame.pack(pady=20)
        ctk.CTkLabel(form_frame, text="Nom de l'organisation *", font=("Arial", 14, "bold"), text_color="#374151").pack(anchor="w", pady=(10, 5))
        self.entry_name = ctk.CTkEntry(form_frame, width=400, height=45, corner_radius=10, border_color="#D1D5DB", font=("Arial", 14))
        self.entry_name.pack(pady=(0, 20))
        self.entry_name.insert(0, self.config["company_name"])
        ctk.CTkLabel(form_frame, text="Site Web (Optionnel)", font=("Arial", 14, "bold"), text_color="#374151").pack(anchor="w", pady=(10, 5))
        self.entry_web = ctk.CTkEntry(form_frame, width=400, height=45, corner_radius=10, border_color="#D1D5DB", font=("Arial", 14), placeholder_text="https://...")
        self.entry_web.pack(pady=(0, 10))
        self.entry_web.insert(0, self.config["website_url"])
        self.create_nav_buttons(back_cmd=self.show_step_1, next_cmd=self.validate_step_2)

    def validate_step_2(self):
        name = self.entry_name.get().strip()
        if not name:
            self.entry_name.configure(border_color="red")
            return
        self.config["company_name"] = name
        self.config["website_url"] = self.entry_web.get().strip()
        self.show_step_3_menu()

    # =========================================================================
    # ÉTAPE 3 - A : LE MENU (CHOIX DU MOTEUR)
    # =========================================================================
    def show_step_3_menu(self):
        self.clear_frame()
        self.create_header(3, "Moteur d'Intelligence", "Choisissez votre architecture IA.")
        
        selection_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        selection_frame.pack(pady=20)
        if not hasattr(self, "engine_var"): self.engine_var = ctk.StringVar(value="local")

        # LOCAL
        card_local = ctk.CTkFrame(selection_frame, fg_color="white", corner_radius=15, border_width=2, border_color="#E5E7EB")
        card_local.pack(pady=10, fill="x", padx=50)
        rb_local = ctk.CTkRadioButton(card_local, text="Mode Local (Ollama)", variable=self.engine_var, value="local", font=("Arial", 16, "bold"), text_color="#1F2937", border_color="#0066FF", fg_color="#0066FF")
        rb_local.pack(anchor="w", padx=20, pady=(15, 5))
        ctk.CTkLabel(card_local, text="L'IA tourne sur votre PC. 100% Privé. Gratuit.", font=("Arial", 13), text_color="gray").pack(anchor="w", padx=50, pady=(0, 15))

        # CLOUD
        card_cloud = ctk.CTkFrame(selection_frame, fg_color="white", corner_radius=15, border_width=2, border_color="#E5E7EB")
        card_cloud.pack(pady=10, fill="x", padx=50)
        rb_cloud = ctk.CTkRadioButton(card_cloud, text="Mode Cloud (API)", variable=self.engine_var, value="cloud", font=("Arial", 16, "bold"), text_color="#1F2937", border_color="#0066FF", fg_color="#0066FF")
        rb_cloud.pack(anchor="w", padx=20, pady=(15, 5))
        ctk.CTkLabel(card_cloud, text="Utilise des modèles distants (Claude, GPT). Payant.", font=("Arial", 13), text_color="gray").pack(anchor="w", padx=50, pady=(0, 15))

        def go_next():
            choice = self.engine_var.get()
            self.config["ai_engine"] = choice
            if choice == "local": self.show_step_3_local_benchmark()
            else: self.show_step_3_cloud_config()

        self.create_nav_buttons(back_cmd=self.show_step_2, next_cmd=go_next)

    # =========================================================================
    # ÉTAPE 3 - B : SOUS-PAGE LOCAL (BENCHMARK RÉEL)
    # =========================================================================
    def show_step_3_local_benchmark(self):
        self.clear_frame()
        self.create_header(3, "Analyse Matérielle", "Vérification de la compatibilité de votre PC.")

        bench_frame = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=15, border_width=1, border_color="#E5E7EB")
        bench_frame.pack(pady=30, padx=50, fill="x")

        self.lbl_bench_status = ctk.CTkLabel(bench_frame, text="Le scan analysera votre RAM et VRAM.", font=("Arial", 14), text_color="#374151")
        self.lbl_bench_status.pack(pady=(20, 10))

        self.progress_bar = ctk.CTkProgressBar(bench_frame, width=500, height=15, progress_color="#0066FF")
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        self.lbl_detected_specs = ctk.CTkLabel(bench_frame, text="", font=("Arial", 12), text_color="gray")
        self.lbl_detected_specs.pack(pady=(5, 0))

        self.lbl_recommendation = ctk.CTkLabel(bench_frame, text="", font=("Arial", 13, "bold"), text_color="#0066FF")
        self.lbl_recommendation.pack(pady=(0, 10))

        self.btn_scan = ctk.CTkButton(
            bench_frame, text="Lancer l'analyse système", 
            fg_color="#10B981", hover_color="#059669", font=("Arial", 14, "bold"),
            command=self.run_real_benchmark
        )
        self.btn_scan.pack(pady=(0, 20))

        # On pointe vers la page de choix de modèle, mais le bouton est désactivé au début
        self.create_nav_buttons(back_cmd=self.show_step_3_menu, next_cmd=self.show_step_3_local_model_choice)
        self.btn_next_global.configure(state="disabled")

    # =========================================================================
    # LE CŒUR DU SCANNER (AMÉLIORÉ CPU + GPU + VRAM)
    # =========================================================================
    def run_real_benchmark(self):
        self.btn_scan.configure(state="disabled", text="Analyse approfondie...")
        self.lbl_recommendation.configure(text="")
        
        def process_scan():
            if pythoncom:
                pythoncom.CoInitialize()
            
            try:
                steps = [
                    "Recensement des coeurs CPU...", 
                    "Test de la bande passante RAM...", 
                    "Interrogation WMI du GPU...", 
                    "Calcul du score d'IA Multimodale..."
                ]
                
                for i, step in enumerate(steps):
                    time.sleep(0.6) # Un peu de temps pour l'effet "pro"
                    self.progress_bar.set((i + 1) / len(steps))
                    self.lbl_bench_status.configure(text=step)

                # --- A. SCAN CPU & RAM ---
                # Coeurs physiques (plus importants que logiques pour l'IA)
                cpu_cores = psutil.cpu_count(logical=False) or 4
                cpu_freq = psutil.cpu_freq().max if psutil.cpu_freq() else 2500
                ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
                
                # --- B. SCAN GPU (ROBUSTE & FALLBACK) ---
                vram_gb = 0
                gpu_name = "Chipset Intégré (CPU)"
                
                # Petite DB de secours si WMI échoue
                GPU_FALLBACK_DB = {
                    "RTX 3060": 12, "RTX 3070": 8, "RTX 3080": 10, "RTX 3090": 24,
                    "RTX 4060": 8,  "RTX 4070": 12, "RTX 4080": 16, "RTX 4090": 24,
                    "RX 6600": 8,   "RX 6700": 12,  "RX 6800": 16,  "RX 7600": 8, 
                    "RX 7800": 16,  "RX 7900": 20
                }

                if wmi and platform.system() == "Windows":
                    try:
                        w = wmi.WMI()
                        for gpu in w.Win32_VideoController():
                            name = gpu.Name or ""
                            # On cherche une vraie carte graphique
                            if any(x in name.upper() for x in ["NVIDIA", "AMD", "RADEON", "RTX", "GTX"]):
                                gpu_name = name
                                
                                # Tentative 1 : WMI direct
                                try:
                                    raw_vram = abs(int(gpu.AdapterRAM))
                                    detected_vram = raw_vram / (1024**3)
                                except: detected_vram = 0

                                # Tentative 2 : Fallback DB si WMI buggé (<1GB sur une carte gamer)
                                if detected_vram < 1.0:
                                    name_upper = name.upper()
                                    for key, val in GPU_FALLBACK_DB.items():
                                        if key in name_upper:
                                            detected_vram = val
                                            # Correctif spécifique XT/Ti
                                            if ("XT" in name_upper or "TI" in name_upper) and detected_vram < 12:
                                                 detected_vram += 4 # Bonus estimation
                                            break
                                
                                if detected_vram > vram_gb:
                                    vram_gb = round(detected_vram, 1)
                    except Exception as e:
                        print(f"WMI Error: {e}")

                # --- C. CALCUL DU SCORE DE PUISSANCE (ALGORITHME PONDÉRÉ) ---
                # Formule : (VRAM * 3) + (RAM * 0.5) + (Cores * 0.5)
                # La VRAM compte triple car c'est critique pour charger les modèles Vision.
                
                power_score = (vram_gb * 3) + (ram_gb * 0.5) + (cpu_cores * 0.5)
                
                # Détermination du profil
                if power_score >= 35: # Ex: 10Go VRAM (30) + 16Go RAM (8) + 6 Cores (3) = 41
                    rec_id = "big"
                    rec_reason = "🚀 Workstation Détectée (VRAM Élevée)"
                elif power_score >= 18: # Ex: 4Go VRAM (12) + 16Go RAM (8) + 4 Cores (2) = 22
                    rec_id = "medium"
                    rec_reason = "✅ PC Performant (Capacité OCR Standard)"
                else:
                    rec_id = "tiny"
                    rec_reason = "💻 Configuration Légère (Modèle Optimisé)"

                # --- D. FINALISATION ---
                self.progress_bar.set(1.0)
                self.lbl_bench_status.configure(text="✅ Analyse complète.", text_color="green")
                
                specs_text = f"Système : {cpu_cores} Cœurs | {ram_gb} Go RAM\nGraphique : {gpu_name} ({vram_gb} Go VRAM)"
                self.lbl_detected_specs.configure(text=specs_text)
                self.lbl_recommendation.configure(text=f"Score Puissance : {int(power_score)} | {rec_reason}")

                # Sauvegarde
                self.config["hardware_specs"] = {
                    "ram_gb": ram_gb,
                    "vram_gb": vram_gb,
                    "cpu_cores": cpu_cores,
                    "gpu_name": gpu_name,
                    "rec_id": rec_id
                }
                
                self.after(0, lambda: self.btn_next_global.configure(state="normal"))

            except Exception as e:
                print(f"Fatal Error: {e}")
                self.lbl_bench_status.configure(text="Erreur critique scan", text_color="red")
            finally:
                if pythoncom:
                    pythoncom.CoUninitialize()

        threading.Thread(target=process_scan).start()

    # =========================================================================
    # ÉTAPE 3-C : NOUVELLE PAGE - CHOIX DU MODEL (VISION / OCR)
    # =========================================================================
    def show_step_3_local_model_choice(self):
        self.clear_frame()
        
        specs = self.config.get("hardware_specs", {})
        rec_id = specs.get("rec_id", "tiny")

        self.create_header(3, "Choix du Cerveau IA", "Sélectionnez un modèle capable de lire vos documents.")
        
        cards_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        cards_container.pack(fill="both", expand=True, padx=20)

        # --- NOUVELLE LISTE DES MODÈLES VISION ---
        models_data = [
            {
                "id": "tiny",
                "name": "Moondream2 (1.8B)",
                "tag": "moondream2",
                "desc": "⚡ Ultra-Rapide & Léger.\nIdéal pour décrire des images simplement.\nPeu précis sur les longs textes.",
                "req": "VRAM: < 3 GB (OK CPU)"
            },
            {
                "id": "medium",
                "name": "Qwen2-VL (7B)",
                "tag": "qwen2-vl",
                "desc": "👑 Le Roi de l'OCR.\nMeilleur que Llama pour lire tableaux et factures.\nExcellent équilibre.",
                "req": "VRAM: 6 GB - 8 GB"
            },
            {
                "id": "big",
                "name": "Llama-3.2-Vision (11B)",
                "tag": "llama3.2-vision",
                "desc": "🧠 Intelligence Maximale.\nCompréhension profonde des schémas et plans.\nDemande une grosse carte graphique.",
                "req": "VRAM: > 10 GB"
            }
        ]

        for model in models_data:
            is_recommended = (model["id"] == rec_id)
            
            border_color = "#10B981" if is_recommended else "#E5E7EB"
            border_width = 3 if is_recommended else 2
            bg_color = "#ECFDF5" if is_recommended else "white"

            card = ctk.CTkFrame(cards_container, width=250, height=380, fg_color=bg_color, 
                                border_color=border_color, border_width=border_width, corner_radius=15)
            card.pack(side="left", padx=15, pady=10, expand=True)
            card.pack_propagate(False)

            if is_recommended:
                ctk.CTkLabel(card, text="★ RECOMMANDÉ", text_color="#059669", font=("Arial", 12, "bold")).pack(pady=(15, 0))
            else:
                ctk.CTkLabel(card, text=" ", font=("Arial", 12)).pack(pady=(15, 0))

            ctk.CTkLabel(card, text=model["name"], font=("Arial", 18, "bold"), text_color="#111827", wraplength=220).pack(pady=(10, 5))
            ctk.CTkLabel(card, text=model["req"], font=("Arial", 12, "bold"), text_color="#DC2626").pack(pady=(0, 15))

            ctk.CTkLabel(card, text=model["desc"], font=("Arial", 13), text_color="#374151", wraplength=220, justify="center").pack(pady=10)

            btn_text = "Choisir ce modèle" if is_recommended else "Choisir"
            btn_col = "#10B981" if is_recommended else "#0066FF"
            
            # On passe le 'tag' technique (ex: qwen2-vl) au lieu du nom d'affichage
            ctk.CTkButton(card, text=btn_text, fg_color=btn_col, font=("Arial", 14, "bold"),
                          command=lambda m=model["tag"]: self.select_model_and_continue(m)).pack(side="bottom", pady=25)

        self.create_nav_buttons(back_cmd=self.show_step_3_local_benchmark, next_cmd=None)

    def select_model_and_continue(self, model_tag):
        self.config["selected_model_tag"] = model_tag # <--- IMPORTANT
        print(f"✅ Modèle choisi : {model_tag}")
        self.show_step_4_targets()


    # =========================================================================
    # ÉTAPE 3 - D : CLOUD (API) - Inchangé
    # =========================================================================
    def show_step_3_cloud_config(self):
        self.clear_frame()
        self.create_header(3, "Configuration API", "Connectez votre fournisseur d'IA.")
        form_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        form_frame.pack(pady=20)
        ctk.CTkLabel(form_frame, text="Fournisseur d'IA", font=("Arial", 14, "bold")).pack(anchor="w", pady=(10, 5))
        self.combo_provider = ctk.CTkComboBox(form_frame, values=["Claude (Anthropic)"], width=400, height=40, state="readonly", font=("Arial", 14))
        self.combo_provider.set("Claude (Anthropic)")
        self.combo_provider.pack(pady=(0, 20))
        ctk.CTkLabel(form_frame, text="Clé API (sk-ant...)", font=("Arial", 14, "bold")).pack(anchor="w", pady=(10, 5))
        self.entry_api_key = ctk.CTkEntry(form_frame, width=400, height=40, font=("Arial", 14), show="*", placeholder_text="sk-...")
        self.entry_api_key.pack(pady=(0, 10))
        self.entry_api_key.insert(0, self.config["api_key"])
        ctk.CTkLabel(form_frame, text="🔒 Votre clé est stockée localement et chiffrée.", text_color="gray", font=("Arial", 12)).pack()
        self.create_nav_buttons(back_cmd=self.show_step_3_menu, next_cmd=self.validate_step_3_cloud)

    def validate_step_3_cloud(self):
        key = self.entry_api_key.get().strip()
        if not key.startswith("sk-"):
            self.entry_api_key.configure(border_color="red")
            messagebox.showwarning("Erreur", "Format de clé API invalide.")
            return
        self.config["api_provider"] = "claude"
        self.config["api_key"] = key
        self.show_step_4_targets()

    # =========================================================================
    # ÉTAPE 4 : CONFIGURATION DES CIBLES (DOSSIERS)
    # =========================================================================
    def show_step_4_targets(self):
        self.clear_frame()
        self.create_header(4, "Configuration des cibles", "Quels dossiers ou serveurs NAS l'IA doit-elle surveiller ?")
        
        # Initialisation de la liste des cibles si vide
        if "targets" not in self.config:
            self.config["targets"] = []

        # Conteneur principal
        content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=50, pady=10)

        # Barre d'actions (Boutons Ajouter)
        action_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        action_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkButton(action_frame, text="Ajouter dossier local", fg_color="#374151", width=200, 
                      command=self.add_local_target).pack(side="left", padx=(0, 20))
        
        ctk.CTkButton(action_frame, text="Ajouter un NAS / Réseau", fg_color="#374151", width=200, 
                      command=self.open_nas_popup).pack(side="left")

        # Liste des dossiers (Scrollable)
        self.targets_list_frame = ctk.CTkScrollableFrame(content_frame, width=600, height=300, 
                                                         fg_color="white", corner_radius=10, 
                                                         border_width=1, border_color="#E5E7EB")
        self.targets_list_frame.pack(fill="both", expand=True)

        self.refresh_targets_list()

        # Navigation
        # Le retour dépend du moteur choisi (Local ou Cloud)
        back_func = self.show_step_3_local_model_choice if self.config["ai_engine"] == "local" else self.show_step_3_cloud_config
        self.create_nav_buttons(back_cmd=back_func, next_cmd=self.validate_step_4)

    def refresh_targets_list(self):
        # Nettoyer la liste visuelle
        for widget in self.targets_list_frame.winfo_children():
            widget.destroy()

        targets = self.config.get("targets", [])
        
        if not targets:
            ctk.CTkLabel(self.targets_list_frame, text="Aucune cible configurée. Ajoutez un dossier pour continuer.", text_color="gray", font=("Arial", 12, "italic")).pack(pady=20)
            return

        for idx, target in enumerate(targets):
            row = ctk.CTkFrame(self.targets_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=5, padx=5)

            # Icône selon le type
            icon = "📁" if target["type"] == "local" else "🌐"
            display_text = f"{icon} {target['path']}"
            if target["type"] == "nas":
                display_text += f" ({target.get('user', 'Anonyme')})"

            ctk.CTkLabel(row, text=display_text, font=("Arial", 12), text_color="#1F2937", anchor="w").pack(side="left", fill="x", expand=True)
            
            # Bouton Supprimer
            ctk.CTkButton(row, text="✖", width=30, height=30, fg_color="#EF4444", hover_color="#DC2626",
                          command=lambda i=idx: self.remove_target(i)).pack(side="right")

    def add_local_target(self):
        path = filedialog.askdirectory()
        if path:
            # Vérifier doublons
            for t in self.config["targets"]:
                if t["path"] == path: return
            
            self.config["targets"].append({"type": "local", "path": path})
            self.refresh_targets_list()

    def remove_target(self, index):
        del self.config["targets"][index]
        self.refresh_targets_list()

    # --- GESTION NAS / RÉSEAU ---
    def open_nas_popup(self):
        win = ctk.CTkToplevel(self)
        win.title("Connexion au serveur NAS")
        win.geometry("400x350")
        win.grab_set() # Focus sur la fenêtre

        ctk.CTkLabel(win, text="Connexion au serveur NAS", font=("Arial", 16, "bold")).pack(pady=20)

        ctk.CTkLabel(win, text="Adresse réseau (UNC)", anchor="w").pack(fill="x", padx=20, pady=(5, 0))
        entry_path = ctk.CTkEntry(win, placeholder_text="\\\\192.168.1.X\\Dossier")
        entry_path.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(win, text="Utilisateur", anchor="w").pack(fill="x", padx=20, pady=(5, 0))
        entry_user = ctk.CTkEntry(win)
        entry_user.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(win, text="Mot de passe", anchor="w").pack(fill="x", padx=20, pady=(5, 0))
        entry_pass = ctk.CTkEntry(win, show="*")
        entry_pass.pack(fill="x", padx=20, pady=5)

        def attempt_add():
            p = entry_path.get().strip()
            u = entry_user.get().strip()
            pw = entry_pass.get().strip()

            if not p: return

            # Test de connexion (Simulation Ping/ListDir)
            try:
                if os.path.exists(p):
                    pass
                else:
                    pass 
                
                # --- SÉCURITÉ : STOCKAGE DANS KEYRING ---
                if u and pw:
                    key_id = f"{u}@{p}"
                    keyring.set_password("OpenAura_NAS", key_id, pw)
                    print(f"🔐 Credentials NAS stockés sécurisés pour {key_id}")

                self.config["targets"].append({
                    "type": "nas",
                    "path": p,
                    "user": u,
                })
                self.refresh_targets_list()
                win.destroy()
                messagebox.showinfo("Succès", "Connexion réussie !")

            except Exception as e:
                messagebox.showerror("Erreur", str(e))

        ctk.CTkButton(win, text="Tester et ajouter", command=attempt_add, fg_color="#10B981", hover_color="#059669").pack(pady=20)

    def validate_step_4(self):
        if not self.config.get("targets"):
            messagebox.showwarning("Erreur", "Veuillez ajouter au moins un dossier à surveiller.")
            return
        
        print(f"✅ TARGETS: {self.config['targets']}")
        self.show_step_5_personality()

    # =========================================================================
    # ÉTAPE 5 : PERSONNALITÉ (SLIDER)
    # =========================================================================
    def show_step_5_personality(self):
        self.clear_frame()
        self.create_header(5, "Personnalité de l'IA", "Définissez le ton de communication de votre assistant.")

        # Valeur par défaut (0.5 = Équilibré)
        if "ai_personality" not in self.config:
            self.config["ai_personality"] = 0.5

        content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=50, pady=20)

        # --- Zone du Slider ---
        slider_frame = ctk.CTkFrame(content_frame, fg_color="white", corner_radius=15, border_width=1, border_color="#E5E7EB")
        slider_frame.pack(fill="x", pady=20, ipady=20)

        # Labels au-dessus
        labels_frame = ctk.CTkFrame(slider_frame, fg_color="transparent")
        labels_frame.pack(fill="x", padx=40, pady=(10, 5))
        
        ctk.CTkLabel(labels_frame, text="🤖 Professionnel & Concis", text_color="#374151", font=("Arial", 12, "bold")).pack(side="left")
        ctk.CTkLabel(labels_frame, text="☕ Chaleureux & Volubile", text_color="#374151", font=("Arial", 12, "bold")).pack(side="right")

        # Le Slider
        self.slider = ctk.CTkSlider(slider_frame, from_=0, to=1, number_of_steps=2, width=400, 
                                    command=self.update_personality_preview)
        self.slider.set(self.config["ai_personality"])
        self.slider.pack(pady=10)

        # --- Zone d'Aperçu (Chat Bubble) ---
        ctk.CTkLabel(content_frame, text="Aperçu de la réponse :", font=("Arial", 14, "bold"), text_color="#374151").pack(anchor="w", pady=(20, 5))

        self.preview_bubble = ctk.CTkFrame(content_frame, fg_color="#EFF6FF", corner_radius=20, border_width=1, border_color="#BFDBFE")
        self.preview_bubble.pack(fill="x", ipady=10)
        
        self.lbl_preview_text = ctk.CTkLabel(self.preview_bubble, text="", font=("Arial", 14, "italic"), text_color="#1E40AF", wraplength=700)
        self.lbl_preview_text.pack(padx=20, pady=10)

        # Initialiser le texte
        self.update_personality_preview(self.config["ai_personality"])

        self.create_nav_buttons(back_cmd=self.show_step_4_targets, next_cmd=self.validate_step_5)

    def update_personality_preview(self, value):
        val = float(value)
        if val == 0.0:
            text = "Analyse des documents terminée. Prêt pour les instructions suivantes."
            color = "#F3F4F6" # Gris
            text_col = "#374151"
            border = "#D1D5DB"
        elif val == 0.5:
            text = "Je peux vous aider à analyser ces documents. Souhaitez-vous commencer ?"
            color = "#EFF6FF" # Bleu
            text_col = "#1E40AF"
            border = "#BFDBFE"
        else:
            text = "Salut ! Je suis ravi de vous aider. On regarde ces fichiers ensemble ?"
            color = "#ECFDF5" # Vert
            text_col = "#065F46"
            border = "#6EE7B7"
        
        self.lbl_preview_text.configure(text=f"❝ {text} ❞", text_color=text_col)
        self.preview_bubble.configure(fg_color=color, border_color=border)

    def validate_step_5(self):
        val = self.slider.get()
        self.config["ai_personality"] = val
        
        # Définition du System Prompt interne selon le slider
        if val == 0.0:
            self.config["system_prompt_style"] = "formal_concise"
        elif val == 0.5:
            self.config["system_prompt_style"] = "balanced_professional"
        else:
            self.config["system_prompt_style"] = "casual_engaging"

        print(f"✅ PERSONALITY: {self.config['system_prompt_style']} ({val})")
        self.show_step_6_output()

    # =========================================================================
    # ÉTAPE 6 : OUTPUT & VALIDATION (Version Web / Universelle)
    # =========================================================================
    def show_step_6_output(self):
        self.clear_frame()
        self.create_header(6, "Flux de Validation", "Diffusion et contrôle humain via Page Web.")

        # Init Config
        if "output_channels" not in self.config:
            self.config["output_channels"] = {} 
        if "supervisor" not in self.config:
            self.config["supervisor"] = {"email": "", "smtp_config": {}}

        # --- GAUCHE : LES CANAUX FINAUX ---
        channels_frame = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=10, border_width=1, border_color="#E5E7EB")
        channels_frame.pack(fill="x", padx=50, pady=(10, 10))

        ctk.CTkLabel(channels_frame, text="1. Destination Finale (Après validation)", font=("Arial", 14, "bold"), text_color="#374151").pack(anchor="w", padx=20, pady=(15, 5))

        # Checkbox Discord
        self.var_discord = ctk.IntVar()
        self.chk_discord = ctk.CTkCheckBox(channels_frame, text="Discord (Webhook)", variable=self.var_discord, 
                                           command=self.toggle_discord_input, font=("Arial", 13))
        self.chk_discord.pack(anchor="w", padx=40, pady=5)

        # Input Discord
        self.discord_input_frame = ctk.CTkFrame(channels_frame, fg_color="transparent")
        self.entry_discord_url = ctk.CTkEntry(self.discord_input_frame, width=400, placeholder_text="https://discord.com/api/webhooks/...")
        self.entry_discord_url.pack(anchor="w", padx=40)
        
        if "discord_webhook" in self.config.get("output_channels", {}):
            self.chk_discord.select()
            self.toggle_discord_input()
            self.entry_discord_url.insert(0, self.config["output_channels"]["discord_webhook"])

        ctk.CTkLabel(channels_frame, text="").pack(pady=5)

        # --- DROITE : LE SUPERVISEUR ---
        supervisor_frame = ctk.CTkFrame(self.main_frame, fg_color="#F0F9FF", corner_radius=10, border_width=1, border_color="#BAE6FD")
        supervisor_frame.pack(fill="x", padx=50, pady=10)

        ctk.CTkLabel(supervisor_frame, text="2. Le Superviseur (Validation)", font=("Arial", 14, "bold"), text_color="#0369A1").pack(anchor="w", padx=20, pady=(15, 5))
        
        ctk.CTkLabel(supervisor_frame, text="Email du Superviseur :", font=("Arial", 12, "bold"), text_color="#0369A1").pack(anchor="w", padx=20)
        
        # Frame pour l'input + Bouton test
        email_action_frame = ctk.CTkFrame(supervisor_frame, fg_color="transparent")
        email_action_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.entry_supervisor_email = ctk.CTkEntry(email_action_frame, width=300, placeholder_text="eric.berthelin@atman.com")
        self.entry_supervisor_email.pack(side="left", padx=(0, 10))
        self.entry_supervisor_email.insert(0, self.config["supervisor"].get("email", ""))

        # BOUTON DE TEST D'ENVOI
        self.btn_test_email = ctk.CTkButton(email_action_frame, text="📧 Envoyer un rapport factice", 
                                            fg_color="#0369A1", width=180,
                                            command=self.send_validation_test)
        self.btn_test_email.pack(side="left")

        # Configuration SMTP
        btn_smtp = ctk.CTkButton(supervisor_frame, text="⚙️ Configurer le Serveur SMTP (Robot)", 
                                 fg_color="transparent", border_width=1, border_color="#0284C7", text_color="#0284C7",
                                 command=self.open_smtp_popup)
        btn_smtp.pack(anchor="w", padx=20, pady=(0, 20))

        # --- SÉCURITÉ ---
        security_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        security_frame.pack(fill="x", padx=50, pady=5)
        self.chk_security = ctk.CTkCheckBox(security_frame, text="Sécurité : Détruire le rapport si non validé sous 24h.",
                                            text_color="#991B1B", onvalue="accepted", offvalue="refused")
        self.chk_security.pack(anchor="w", padx=20)
        self.chk_security.select()

        self.create_nav_buttons(back_cmd=self.show_step_5_personality, next_cmd=self.validate_step_6)

    def toggle_discord_input(self):
        if self.chk_discord.get() == 1:
            self.discord_input_frame.pack(fill="x", pady=5)
        else:
            self.discord_input_frame.pack_forget()

    # --- POPUP CONFIGURATION SMTP ---
    def open_smtp_popup(self):
        win = ctk.CTkToplevel(self)
        win.title("Configuration Email (Robot)")
        win.geometry("500x450")
        win.grab_set()

        ctk.CTkLabel(win, text="Configuration du Robot Expéditeur", font=("Arial", 16, "bold")).pack(pady=(20, 10))
        ctk.CTkLabel(win, text="Ces identifiants servent uniquement à envoyer le mail de validation.", font=("Arial", 11), text_color="gray").pack()

        # Formulaire
        form = ctk.CTkFrame(win, fg_color="transparent")
        form.pack(pady=20)

        # Serveur
        ctk.CTkLabel(form, text="Serveur SMTP").grid(row=0, column=0, sticky="w", pady=5, padx=5)
        e_server = ctk.CTkEntry(form, width=250, placeholder_text="smtp.gmail.com")
        e_server.grid(row=0, column=1, pady=5)
        e_server.insert(0, "smtp.gmail.com") # Valeur par défaut courante

        # Port
        ctk.CTkLabel(form, text="Port").grid(row=1, column=0, sticky="w", pady=5, padx=5)
        e_port = ctk.CTkEntry(form, width=250, placeholder_text="587")
        e_port.grid(row=1, column=1, pady=5)
        e_port.insert(0, "587")

        # User
        ctk.CTkLabel(form, text="Email du Robot").grid(row=2, column=0, sticky="w", pady=5, padx=5)
        e_user = ctk.CTkEntry(form, width=250, placeholder_text="robot@atman.com")
        e_user.grid(row=2, column=1, pady=5)

        # Pass
        ctk.CTkLabel(form, text="Mot de passe (App)").grid(row=3, column=0, sticky="w", pady=5, padx=5)
        e_pass = ctk.CTkEntry(form, width=250, show="*")
        e_pass.grid(row=3, column=1, pady=5)

        # Restaurer valeurs existantes si présentes
        saved_smtp = self.config["supervisor"].get("smtp_config", {})
        if saved_smtp:
            e_server.delete(0, "end"); e_server.insert(0, saved_smtp.get("server", ""))
            e_port.delete(0, "end"); e_port.insert(0, saved_smtp.get("port", "587"))
            e_user.delete(0, "end"); e_user.insert(0, saved_smtp.get("user", ""))
            # Le mot de passe n'est pas affiché (il est dans le keyring), on laisse vide ou placeholder

        # Boutons Action
        def save_smtp():
            s, p = e_server.get(), e_port.get()
            u, pw = e_user.get(), e_pass.get()
            
            if not s or not u or not pw:
                messagebox.showerror("Erreur", "Tous les champs sont requis.")
                return

            # Test de connexion réel
            try:
                server = smtplib.SMTP(s, int(p))
                server.starttls()
                server.login(u, pw)
                server.quit()
                
                # Sauvegarde Sécurisée
                keyring.set_password("OpenAura_SMTP", u, pw)
                
                self.config["supervisor"]["smtp_config"] = {
                    "server": s,
                    "port": p,
                    "user": u
                }
                messagebox.showinfo("Succès", "Connexion SMTP réussie ! Configuration sauvegardée.")
                win.destroy()
            except Exception as e:
                messagebox.showerror("Échec Connexion", f"Impossible de se connecter au serveur mail :\n{e}")

        ctk.CTkButton(win, text="Tester & Sauvegarder", fg_color="#10B981", command=save_smtp).pack(pady=10)

    def validate_step_6(self):
        # 1. Discord
        discord_url = self.entry_discord_url.get().strip()
        if self.chk_discord.get() == 1:
            if "discord" not in discord_url:
                messagebox.showwarning("Erreur", "URL Discord invalide.")
                return
            self.config["output_channels"]["discord_webhook"] = discord_url
        
        # 2. Superviseur
        sup_email = self.entry_supervisor_email.get().strip()
        if not sup_email or "@" not in sup_email:
            messagebox.showwarning("Erreur", "Email du superviseur invalide.")
            return
        
        # Vérif si SMTP configuré
        if not self.config["supervisor"].get("smtp_config"):
             messagebox.showwarning("Attention", "Vous n'avez pas configuré le serveur d'envoi d'email (SMTP).\nL'IA ne pourra pas envoyer le lien de validation.")
             return

        self.config["supervisor"]["email"] = sup_email
        self.config["security_autodelete"] = (self.chk_security.get() == "accepted")

        print(f"✅ VALIDATION FLOW: Email -> WebPage -> {list(self.config['output_channels'].keys())}")
        self.show_step_7_planning()

    def send_validation_test(self):
        # 1. Récupération des infos
        target_email = self.entry_supervisor_email.get().strip()
        smtp_conf = self.config["supervisor"].get("smtp_config")
        
        # --- AJOUT : SAUVEGARDE DE LA CONFIG POUR LE SERVEUR ---
        discord_url = self.entry_discord_url.get().strip()
        try:
            with open("temp_config.json", "w") as f:
                json.dump({"discord_webhook": discord_url}, f)
        except Exception as e:
            print(f"Erreur sauvegarde temp: {e}")
        # -------------------------------------------------------

        if not target_email or "@" not in target_email:
            messagebox.showwarning("Erreur", "Veuillez entrer une adresse email valide pour le superviseur.")
            return

        if not smtp_conf:
            messagebox.showwarning("Erreur", "Veuillez d'abord configurer le serveur SMTP (Bouton engrenage).")
            return

        self.btn_test_email.configure(state="disabled", text="Envoi en cours...")

        # 2. Récupération du mot de passe sécurisé (Keyring)
        try:
            smtp_pass = keyring.get_password("OpenAura_SMTP", smtp_conf["user"])
            if not smtp_pass:
                raise Exception("Mot de passe SMTP introuvable dans le coffre-fort.")
        except Exception as e:
            messagebox.showerror("Erreur Keyring", str(e))
            self.btn_test_email.configure(state="normal", text="📧 Envoyer un rapport factice")
            return

        # 3. Création du contenu du mail (Exemple réaliste Atman)
        subject = "🔔 [AURA] Validation Requise : Rapport Hebdomadaire #42"
        
        # HTML Body - C'est ici qu'on simule ce que l'IA dirait
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: auto; border: 1px solid #ddd; border-radius: 10px; overflow: hidden;">
                <div style="background-color: #0066FF; padding: 20px; color: white;">
                    <h2 style="margin: 0;">OpenAura Analyst</h2>
                </div>
                <div style="padding: 20px;">
                    <p>Bonjour,</p>
                    <p>Voici le brouillon du rapport de surveillance pour la période du <b>12/02 au 19/02</b>.</p>
                    
                    <div style="background-color: #F3F4F6; padding: 15px; border-left: 4px solid #0066FF; margin: 20px 0;">
                        <p style="margin-top: 0;"><b>📊 Résumé de l'activité détectée :</b></p>
                        <p>Cette semaine a été marquée par une forte activité sur le dossier <b>/PROJETS/NATIV</b>. J'ai détecté l'ajout de 3 nouveaux plans PDF pour le prototype "Sèche-serviette V2".</p>
                        <p>⚠️ <b>Attention :</b> Un fichier <i>"facture_douteuse.exe"</i> a été déposé dans le dossier Public mardi à 14h02. Je recommande une vérification manuelle.</p>
                    </div>

                    <p>Avant que je ne diffuse ce message à toute l'équipe sur Discord, merci de valider ou corriger le contenu.</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="http://localhost:5000/validate/simulation_token" 
                           style="background-color: #10B981; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                           ✅ Valider et Envoyer
                        </a>
                        &nbsp;&nbsp;
                        <a href="http://localhost:5000/edit/simulation_token" 
                           style="background-color: #6B7280; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                           ✏️ Modifier
                        </a>
                    </div>
                </div>
                <div style="background-color: #F9FAFB; padding: 15px; text-align: center; font-size: 12px; color: #6B7280;">
                    Généré localement par OpenAura @ Atman Manufacture<br>
                    Ceci est un test de configuration.
                </div>
            </div>
        </body>
        </html>
        """

        # 4. Envoi réel
        threading.Thread(target=self._run_send_thread, args=(smtp_conf, smtp_pass, target_email, subject, html_content)).start()

    def _run_send_thread(self, conf, password, to_email, subject, html):
        try:
            msg = MIMEMultipart()
            msg['From'] = conf["user"]
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(html, 'html'))

            server = smtplib.SMTP(conf["server"], int(conf["port"]))
            server.starttls()
            server.login(conf["user"], password)
            server.send_message(msg)
            server.quit()

            self.after(0, lambda: messagebox.showinfo("Succès", f"Email envoyé à {to_email} !\nVérifiez votre boîte de réception."))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erreur SMTP", f"Échec de l'envoi :\n{e}"))
        finally:
            self.after(0, lambda: self.btn_test_email.configure(state="normal", text="📧 Envoyer un rapport factice"))

    # =========================================================================
    # ÉTAPE 7 : LE PLANNING (SCHEDULER)
    # =========================================================================
    def show_step_7_planning(self):
        self.clear_frame()
        self.create_header(7, "Planning d'Activité", "Définissez les périodes de surveillance et de rapport.")

        # Initialisation de la config si vide
        if "schedule" not in self.config:
            self.config["schedule"] = {} # Stockera { "Lundi_Matin": "passif", ... }

        # --- Légende ---
        legend_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        legend_frame.pack(pady=(0, 20))
        
        # Élément passif
        l1 = ctk.CTkFrame(legend_frame, width=20, height=20, fg_color="#3B82F6", corner_radius=5) # Bleu
        l1.pack(side="left", padx=(0, 5))
        ctk.CTkLabel(legend_frame, text="Surveillance (Passif)", font=("Arial", 12)).pack(side="left", padx=(0, 20))

        # Élément actif
        l2 = ctk.CTkFrame(legend_frame, width=20, height=20, fg_color="#EF4444", corner_radius=5) # Rouge
        l2.pack(side="left", padx=(0, 5))
        ctk.CTkLabel(legend_frame, text="Rapport & Validation (Actif)", font=("Arial", 12)).pack(side="left")

        # --- La Grille (Semainier) ---
        scheduler_frame = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=10)
        scheduler_frame.pack(fill="both", expand=True, padx=40, pady=10)

        days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        periods = ["Matin (8h-12h)", "Après-Midi (13h-17h)", "Soir (18h-22h)"]

        # Configuration de la grille
        scheduler_frame.grid_columnconfigure(0, weight=1) # Colonne titres lignes
        for i in range(len(days)):
            scheduler_frame.grid_columnconfigure(i+1, weight=1)

        # En-têtes (Jours)
        for col, day in enumerate(days):
            ctk.CTkLabel(scheduler_frame, text=day, font=("Arial", 12, "bold"), text_color="#374151").grid(row=0, column=col+1, pady=10)

        # Création des boutons (Cellules)
        self.schedule_buttons = {}

        for row, period in enumerate(periods):
            # Titre de la ligne (Période)
            ctk.CTkLabel(scheduler_frame, text=period, font=("Arial", 12, "bold"), text_color="#6B7280").grid(row=row+1, column=0, padx=10, pady=10, sticky="e")
            
            for col, day in enumerate(days):
                key = f"{day}_{row}" # ex: Lundi_0 (Matin)
                
                # Récupérer état sauvegardé ou défaut
                current_state = self.config["schedule"].get(key, "off")
                color = self.get_color_from_state(current_state)

                btn = ctk.CTkButton(scheduler_frame, text="", width=40, height=40, corner_radius=5,
                                    fg_color=color, hover_color=color,
                                    command=lambda k=key: self.toggle_schedule_cell(k))
                btn.grid(row=row+1, column=col+1, padx=5, pady=5, sticky="nsew")
                
                self.schedule_buttons[key] = btn

        # Navigation
        self.create_nav_buttons(back_cmd=self.show_step_6_output, next_cmd=self.validate_step_7, next_text="TERMINER")

    def get_color_from_state(self, state):
        if state == "passif": return "#3B82F6" # Bleu
        if state == "actif": return "#EF4444"  # Rouge
        return "#E5E7EB" # Gris (Off)

    def toggle_schedule_cell(self, key):
        # Cycle : Off -> Passif -> Actif -> Off
        current = self.config["schedule"].get(key, "off")
        
        if current == "off":
            new_state = "passif"
        elif current == "passif":
            new_state = "actif"
        else:
            new_state = "off"
        
        # Mise à jour data
        self.config["schedule"][key] = new_state
        
        # Mise à jour visuelle
        btn = self.schedule_buttons[key]
        new_color = self.get_color_from_state(new_state)
        btn.configure(fg_color=new_color, hover_color=new_color)

    def validate_step_7(self):
        # Vérification minimale : est-ce qu'il y a au moins une case active/passive ?
        has_activity = any(v != "off" for v in self.config["schedule"].values())
        
        if not has_activity:
            messagebox.showwarning("Planning vide", "Veuillez sélectionner au moins une plage horaire.")
            return

        print(f"✅ SCHEDULE: {len(self.config['schedule'])} slots configurés.")
        self.show_final_step_installation()

    # =========================================================================
    # ÉTAPE FINALE : INSTALLATION RÉELLE (Ollama + Modèle)
    # =========================================================================
    def show_final_step_installation(self):
        self.clear_frame()
        self.create_header("INSTALLATION", "Initialisation du Système", "Veuillez patienter pendant la configuration...")

        # Console de log (Style Terminal)
        self.console = ctk.CTkTextbox(self.main_frame, width=700, height=400, font=("Consolas", 12), 
                                      text_color="#10B981", fg_color="#000000")
        self.console.pack(pady=20)
        
        self.console.insert("0.0", "> Démarrage du processus d'installation OpenAura...\n")

        # Barre de progression
        self.progress_inst = ctk.CTkProgressBar(self.main_frame, width=600, height=20, progress_color="#0066FF")
        self.progress_inst.set(0)
        self.progress_inst.pack(pady=20)

        # Bouton (Caché au début)
        self.btn_finish = ctk.CTkButton(self.main_frame, text="Ouvrir le Tableau de Bord", 
                                        fg_color="#10B981", height=50, font=("Arial", 16, "bold"),
                                        command=self.destroy)

        # Lancement du Thread principal
        threading.Thread(target=self.run_real_installation).start()

    def log(self, message):
        """Ajoute une ligne dans la console et scroll en bas (thread-safe)"""
        def _do_log():
            self.console.insert("end", f"> {message}\n")
            self.console.see("end")
        self.after(0, _do_log)

    def run_real_installation(self):
        try:
            # --- 1. SAUVEGARDE DE LA CONFIG JSON ---
            self.log("Sauvegarde de la configuration locale...")
            self.progress_inst.set(0.1)

            # Créer le dossier .OpenAura à la racine du PC (home directory)
            home_dir = os.path.expanduser("~")
            config_dir = os.path.join(home_dir, ".OpenAura")

            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
                self.log(f"Dossier créé : {config_dir}")

            # Récupérer le nom de l'entreprise pour nommer le fichier config
            company_name = self.config.get("company_name", "OpenAura")
            config_filename = f"{company_name}.OpenAuraConfig.json"
            config_path = os.path.join(config_dir, config_filename)

            # On nettoie les objets non sérialisables avant de sauvegarder
            clean_config = self.config.copy()

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(clean_config, f, indent=4, ensure_ascii=False)

            self.log(f"Fichier {config_filename} généré avec succès.")
            self.log(f"Chemin : {config_path}")
            time.sleep(1)

            # --- 2. VÉRIFICATION OLLAMA ---
            self.log("Vérification du moteur IA (Ollama)...")
            self.progress_inst.set(0.2)
            
            ollama_path = shutil.which("ollama")
            
            if ollama_path:
                self.log(f"✅ Ollama détecté : {ollama_path}")
            else:
                self.log("⚠️ Ollama n'est pas installé.")
                self.install_ollama() # Lance l'installation

            # --- 3. TÉLÉCHARGEMENT DU MODÈLE CHOISI ---
            # Récupération du tag technique (ex: moondream, llama3.2-vision, qwen2-vl)
            # On regarde ce qui a été choisi à l'étape 3, sinon on prend le recommandé
            
            selected_model_tag = self.config.get("selected_model_tag")
            if not selected_model_tag:
                # Fallback si l'utilisateur n'a pas cliqué explicitement (ex: mode auto)
                specs = self.config.get("hardware_specs", {})
                rec_id = specs.get("rec_id", "tiny")

                mapping = {
                    "tiny": "moondream2",
                    "medium": "qwen2-vl",
                    "big": "llama3.2-vision"
                }
                selected_model_tag = mapping.get(rec_id, "moondream2")

            
            
            self.pull_ollama_model(selected_model_tag)

            # --- 4. FINALISATION ---
            self.progress_inst.set(1.0)
            self.log("✨ INSTALLATION TERMINÉE AVEC SUCCÈS !")
            self.log("Le service sentinelle est prêt à être lancé.")
            
            # Afficher le bouton final
            self.after(0, lambda: self.btn_finish.pack(pady=20))

        except Exception as e:
            self.log(f"❌ ERREUR CRITIQUE : {str(e)}")
            messagebox.showerror("Erreur Installation", str(e))

    def install_ollama(self):
        """Télécharge et installe Ollama avec barre de progression"""
        self.log("📥 Téléchargement de OllamaSetup.exe...")
        url = "https://ollama.com/download/OllamaSetup.exe"

        try:
            self.log("⚠️ Veuillez patienter pendant le téléchargement et l'installation de Ollama.")

            # Télécharger dans le répertoire temp
            import tempfile
            temp_dir = tempfile.gettempdir()
            installer_path = os.path.join(temp_dir, "OllamaSetup.exe")

            # Télécharger avec barre de progression
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))

            if total_size == 0:
                self.log("⚠️ Impossible de déterminer la taille du fichier.")
                total_size = 150 * 1024 * 1024  # Estimation 150MB

            downloaded = 0
            chunk_size = 8192
            start_time = time.time()

            with open(installer_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Calcul de la barre de progression
                        progress = downloaded / total_size
                        bars = int(progress * 40)
                        percentage = int(progress * 100)

                        # Temps écoulé et vitesse
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            speed = downloaded / elapsed / 1024 / 1024  # MB/s
                            remaining = (total_size - downloaded) / (downloaded / elapsed) if elapsed > 0 else 0
                            remaining_str = self._format_time(remaining)
                        else:
                            speed = 0
                            remaining_str = "Calcul..."

                        # Afficher la barre
                        bar = "█" * bars + "░" * (40 - bars)
                        size_mb = total_size / 1024 / 1024
                        downloaded_mb = downloaded / 1024 / 1024

                        msg = f"[{bar}] {percentage}% | {downloaded_mb:.1f}/{size_mb:.1f} MB | {speed:.1f} MB/s | ETA: {remaining_str}"

                        # Mettre à jour la console (remplacer la dernière ligne)
                        self.after(0, lambda msg=msg: self._update_last_log(msg))

            self.log("✅ Téléchargement terminé !")
            self.log("Lancement de l'installeur...")

            # Lancer l'installeur en arrière-plan
            subprocess.Popen([installer_path])

            self.log("⚠️ Veuillez suivre les instructions d'installation.")
            self.log("En attente de l'installation (cela peut prendre plusieurs minutes)...")

            # Vérifier pendant 15 minutes si Ollama s'installe
            for i in range(180):  # 180 tentatives x 5 secondes = 15 minutes
                time.sleep(5)

                # Vérifier dans le PATH
                if shutil.which("ollama"):
                    self.log("✅ Ollama détecté ! Installation réussie.")
                    return

                # Vérifier dans le chemin d'installation par défaut de Windows
                default_path = os.path.expanduser("~\\AppData\\Local\\Programs\\Ollama\\ollama.exe")
                if os.path.exists(default_path):
                    self.log("✅ Ollama installé avec succès !")
                    # Ajouter au PATH
                    ollama_bin_path = os.path.dirname(default_path)
                    os.environ['PATH'] = ollama_bin_path + os.pathsep + os.environ.get('PATH', '')
                    return

            self.log("⏱️ Timeout - Ollama n'a pas pu être détecté.")
            self.log("⚠️ Veuillez installer Ollama manuellement depuis https://ollama.com/download")

        except Exception as e:
            self.log(f"⚠️ Erreur : {e}")
            self.log("Tentative d'utilisation de Ollama existant...")

    def _format_time(self, seconds):
        """Formate le temps en format lisible"""
        if seconds < 0 or seconds > 3600:
            return "Calcul..."
        if seconds < 60:
            return f"{int(seconds)}s"
        else:
            mins = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{mins}m{secs}s"

    def _update_last_log(self, msg):
        """Remplace la dernière ligne de la console"""
        try:
            # Supprimer la dernière ligne
            content = self.console.get("1.0", "end-1c")
            last_newline = content.rfind('\n')
            if last_newline != -1:
                self.console.delete(f"1.0 + {last_newline} chars", "end-1c")
            else:
                self.console.delete("1.0", "end-1c")

            # Ajouter la nouvelle ligne
            self.console.insert("end", f"\n> {msg}")
            self.console.see("end")
        except:
            self.log(msg)  # Fallback

    def pull_ollama_model(self, model_tag):
        """Exécute 'ollama pull' et lit la sortie pour animer la console"""
        try:
            # Sous Windows, il faut cacher la fenêtre console noire qui pourrait apparaître
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            process = subprocess.Popen(
                ["ollama", "pull", model_tag],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, # Ollama écrit souvent la progress bar dans stderr
                text=True,
                startupinfo=startupinfo,
                encoding="utf-8" # Important pour les caractères spéciaux
            )
            
            self.log(f"Commande envoyée : ollama pull {model_tag}")
            
            # Lecture en temps réel
            while True:
                output = process.stderr.readline() # Ollama utilise stderr pour les barres de progression
                if output == '' and process.poll() is not None:
                    break
                if output:
                    clean_line = output.strip()
                    if clean_line:
                        # On affiche pas tout pour pas spammer, juste les pourcentages ou infos
                        if "downloading" in clean_line or "%" in clean_line or "verifying" in clean_line:
                            # On met à jour la dernière ligne de la console au lieu d'ajouter
                            # Astuce : supprimer la dernière ligne et réécrire pour effet animation
                            # Mais pour faire simple ici, on log juste
                            self.console.insert("end", f"{clean_line}\n")
                            self.console.see("end")
            
            if process.returncode == 0:
                self.log(f"✅ Modèle {model_tag} téléchargé et prêt.")
            else:
                raise Exception(f"Erreur lors du pull (Code {process.returncode})")

        except FileNotFoundError:
             # Si ollama n'est pas trouvé malgré l'install
             raise Exception("Commande 'ollama' introuvable. Redémarrez le logiciel.")

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
    app = WizardApp()
    app.mainloop()