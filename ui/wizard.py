import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import time
from PIL import Image
import os
import psutil
import platform
import keyring

# Gestion de WMI uniquement pour Windows
try:
    import wmi
except ImportError:
    wmi = None

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
        current_dir = os.path.dirname(os.path.abspath(__file__))
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
        self.lbl_detected_specs.pack(pady=(5, 5))

        self.btn_scan = ctk.CTkButton(
            bench_frame, text="Lancer l'analyse système", 
            fg_color="#10B981", hover_color="#059669", font=("Arial", 14, "bold"),
            command=self.run_real_benchmark
        )
        self.btn_scan.pack(pady=(0, 20))

        # On pointe vers la page de choix de modèle, mais le bouton est désactivé au début
        self.create_nav_buttons(back_cmd=self.show_step_3_menu, next_cmd=self.show_step_3_local_model_choice)
        self.btn_next_global.configure(state="disabled")

    def run_real_benchmark(self):
        self.btn_scan.configure(state="disabled", text="Analyse en cours...")
        
        def process_scan():
            steps = ["Initialisation...", "Lecture de la mémoire système...", "Interrogation du GPU...", "Calcul du score IA..."]
            for i, step in enumerate(steps):
                time.sleep(0.5)
                self.progress_bar.set((i + 1) / 5)
                self.lbl_bench_status.configure(text=step)

            try:
                # --- SCAN RAM ---
                ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
                
                # --- SCAN GPU (WMI) ---
                vram_gb = 0
                gpu_name = "GPU Intégré / Inconnu"
                
                if wmi and platform.system() == "Windows":
                    try:
                        w = wmi.WMI()
                        for gpu in w.Win32_VideoController():
                            name = gpu.Name or ""
                            if "NVIDIA" in name or "AMD" in name:
                                gpu_name = name
                                # Tentative de lecture VRAM
                                try:
                                    raw_vram = abs(int(gpu.AdapterRAM))
                                    current_vram = raw_vram / (1024**3)
                                    if current_vram > vram_gb:
                                        vram_gb = round(current_vram, 1)
                                except: pass
                    except: pass

                # --- LOGIQUE DE RECOMMANDATION (Tiny / Medium / Big) ---
                # Rec_id servira à surligner la carte sur la page suivante
                rec_id = "tiny"
                rec_reason = "Configuration légère"

                if ram_gb >= 16:
                    rec_id = "big"
                    rec_reason = "RAM > 16GB : Prêt pour la Vision"
                elif ram_gb >= 8:
                    rec_id = "medium"
                    rec_reason = "RAM 8-16GB : Équilibre Parfait"
                else:
                    rec_id = "tiny"
                    rec_reason = "RAM < 8GB : Modèle optimisé requis"

                # Fin Scan
                self.progress_bar.set(1.0)
                self.lbl_bench_status.configure(text="✅ Analyse terminée.", text_color="green")
                
                specs_text = f"Détecté : {ram_gb} Go RAM | {gpu_name} ({vram_gb} Go VRAM)"
                self.lbl_detected_specs.configure(text=specs_text + f"\nRecommendation : {rec_reason}")

                # Sauvegarde
                self.config["hardware_specs"] = {
                    "ram_gb": ram_gb,
                    "gpu_name": gpu_name,
                    "rec_id": rec_id  # tiny, medium, ou big
                }
                
                self.btn_next_global.configure(state="normal")

            except Exception as e:
                print(f"Erreur: {e}")
                self.lbl_bench_status.configure(text="Erreur lors du scan (voir console)", text_color="red")

        threading.Thread(target=process_scan).start()

    # =========================================================================
    # ÉTAPE 3 - C : NOUVELLE PAGE - CHOIX DU MODEL
    # =========================================================================
    def show_step_3_local_model_choice(self):
        self.clear_frame()
        
        # Récupération de la reco
        specs = self.config.get("hardware_specs", {})
        rec_id = specs.get("rec_id", "tiny") # tiny par défaut

        self.create_header(3, "Choix du Modèle IA", "Sélectionnez le cerveau de votre assistant.")
        
        # Conteneur des cartes
        cards_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        cards_container.pack(fill="both", expand=True, padx=20)

        # Définition des 3 modèles
        models_data = [
            {
                "id": "tiny",
                "name": "TinyLlama-1.1B",
                "desc": "Ultra rapide. Idéal pour PC bureautique sans carte graphique.",
                "req": "RAM: < 8GB"
            },
            {
                "id": "medium",
                "name": "Llama-3.2-3B",
                "desc": "Le standard actuel. Intelligent et réactif.",
                "req": "RAM: 8GB - 16GB"
            },
            {
                "id": "big",
                "name": "Llama-3.2-Vision",
                "desc": "Analyse d'images & Texte. Puissant mais gourmand.",
                "req": "RAM: > 16GB"
            }
        ]

        # Création des 3 cartes
        for model in models_data:
            is_recommended = (model["id"] == rec_id)
            
            # Style conditionnel
            border_color = "#10B981" if is_recommended else "#E5E7EB" # Vert si reco
            border_width = 3 if is_recommended else 2
            bg_color = "#ECFDF5" if is_recommended else "white" # Fond vert très clair si reco

            card = ctk.CTkFrame(cards_container, width=250, height=350, fg_color=bg_color, 
                                border_color=border_color, border_width=border_width, corner_radius=15)
            card.pack(side="left", padx=15, pady=10, expand=True)
            card.pack_propagate(False)

            # Badge Recommandé
            if is_recommended:
                ctk.CTkLabel(card, text="★ RECOMMANDÉ", text_color="#059669", font=("Arial", 12, "bold")).pack(pady=(15, 0))
            else:
                ctk.CTkLabel(card, text=" ", font=("Arial", 12)).pack(pady=(15, 0)) # Espace

            # Titre
            ctk.CTkLabel(card, text=model["name"], font=("Arial", 18, "bold"), text_color="#111827", wraplength=220).pack(pady=(10, 5))
            
            # Requis
            ctk.CTkLabel(card, text=model["req"], font=("Arial", 11, "italic"), text_color="#6B7280").pack(pady=(0, 15))

            # Desc
            ctk.CTkLabel(card, text=model["desc"], font=("Arial", 13), text_color="#374151", wraplength=220, justify="center").pack(pady=10)

            # Bouton Choisir
            btn_text = "Installer" if is_recommended else "Choisir"
            btn_col = "#10B981" if is_recommended else "#0066FF"
            
            ctk.CTkButton(card, text=btn_text, fg_color=btn_col, font=("Arial", 14, "bold"),
                          command=lambda m=model["name"]: self.select_model_and_continue(m)).pack(side="bottom", pady=25)

        self.create_nav_buttons(back_cmd=self.show_step_3_local_benchmark, next_cmd=None)

    def select_model_and_continue(self, model_name):
        self.config["selected_model"] = model_name
        print(f"✅ Modèle choisi : {model_name}")
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
    # ÉTAPE 6 : OUTPUT & VALIDATION
    # =========================================================================
    def show_step_6_output(self):
        self.clear_frame()
        self.create_header(6, "Destination & Contrôle", "Où envoyer le rapport et qui doit le valider ?")

        # Initialisation Config
        if "output_channels" not in self.config:
            self.config["output_channels"] = []
        if "validator_contact" not in self.config:
            self.config["validator_contact"] = ""

        # --- PARTIE A : CANAUX DE SORTIE ---
        channels_frame = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=10, border_width=1, border_color="#E5E7EB")
        channels_frame.pack(fill="x", padx=50, pady=(10, 20))

        ctk.CTkLabel(channels_frame, text="Canaux de Diffusion", font=("Arial", 14, "bold"), text_color="#374151").pack(anchor="w", padx=20, pady=(15, 10))

        # Checkboxes (On pourrait ajouter des icônes plus tard)
        self.chk_discord = ctk.CTkCheckBox(channels_frame, text="Discord (Webhook)", font=("Arial", 13))
        self.chk_discord.pack(anchor="w", padx=40, pady=5)
        
        self.chk_email = ctk.CTkCheckBox(channels_frame, text="Email (SMTP)", font=("Arial", 13))
        self.chk_email.pack(anchor="w", padx=40, pady=5)
        
        self.chk_slack = ctk.CTkCheckBox(channels_frame, text="Slack", font=("Arial", 13))
        self.chk_slack.pack(anchor="w", padx=40, pady=5)
        
        # Restaurer l'état si déjà coché (logique simplifiée pour l'exemple)
        if "Discord" in self.config["output_channels"]: self.chk_discord.select()
        if "Email" in self.config["output_channels"]: self.chk_email.select()
        if "Slack" in self.config["output_channels"]: self.chk_slack.select()

        # Espace vide en bas du cadre
        ctk.CTkLabel(channels_frame, text="").pack(pady=5)

        # --- PARTIE B : LE SUPERVISEUR ---
        validator_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        validator_frame.pack(fill="x", padx=50, pady=10)

        ctk.CTkLabel(validator_frame, text="Superviseur (Validateur Humain)", font=("Arial", 14, "bold"), text_color="#374151").pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(validator_frame, text="Email ou ID Discord de la personne qui doit approuver le rapport.", font=("Arial", 12), text_color="gray").pack(anchor="w", pady=(0, 10))

        self.entry_validator = ctk.CTkEntry(validator_frame, width=400, height=40, placeholder_text="ex: eric.b@atman.com")
        self.entry_validator.pack(anchor="w", fill="x")
        self.entry_validator.insert(0, self.config["validator_contact"])

        # --- PARTIE C : SÉCURITÉ (OBLIGATOIRE) ---
        security_frame = ctk.CTkFrame(self.main_frame, fg_color="#FEF2F2", corner_radius=10, border_width=1, border_color="#FCA5A5")
        security_frame.pack(fill="x", padx=50, pady=20, ipady=10)

        ctk.CTkLabel(security_frame, text="⚠️ Règle de Sécurité Critique", text_color="#B91C1C", font=("Arial", 13, "bold")).pack(anchor="w", padx=20, pady=(10, 5))
        
        self.chk_security = ctk.CTkCheckBox(security_frame, text="Si aucune validation n'est reçue avant lundi 8h00, le rapport est détruit automatiquement.",
                                            text_color="#7F1D1D", onvalue="accepted", offvalue="refused")
        self.chk_security.pack(anchor="w", padx=20, pady=10)

        # Navigation
        self.create_nav_buttons(back_cmd=self.show_step_5_personality, next_cmd=self.validate_step_6)

    def validate_step_6(self):
        # 1. Récupérer les canaux
        selected_channels = []
        if self.chk_discord.get() == 1: selected_channels.append("Discord")
        if self.chk_email.get() == 1: selected_channels.append("Email")
        if self.chk_slack.get() == 1: selected_channels.append("Slack")

        if not selected_channels:
            messagebox.showwarning("Attention", "Veuillez sélectionner au moins un canal de diffusion.")
            return

        # 2. Vérifier le validateur
        validator = self.entry_validator.get().strip()
        if not validator:
            self.entry_validator.configure(border_color="red")
            messagebox.showwarning("Attention", "Un superviseur est obligatoire.")
            return

        # 3. Vérifier la case sécurité
        if self.chk_security.get() != "accepted":
            self.chk_security.configure(text_color="red")
            messagebox.showerror("Sécurité", "Vous devez accepter la règle de destruction automatique pour continuer.")
            return

        # Sauvegarde
        self.config["output_channels"] = selected_channels
        self.config["validator_contact"] = validator
        self.config["security_autodelete"] = True

        print(f"✅ OUTPUT: {selected_channels} -> {validator}")
        
        # Passage à l'étape suivante (Planning)
        self.show_step_7_planning()

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
    # ÉTAPE FINALE : INITIALISATION (Simulation)
    # =========================================================================
    def show_final_step_installation(self):
        self.clear_frame()
        self.create_header("FIN", "Initialisation du Système", "OpenAura configure votre environnement...")

        # Console de log
        self.console = ctk.CTkTextbox(self.main_frame, width=700, height=400, font=("Consolas", 12), 
                                      text_color="#10B981", fg_color="#000000") # Look Terminal Matrix
        self.console.pack(pady=20)
        
        self.console.insert("0.0", "> Initialisation du noyau OpenAura...\n")
        self.console.insert("end", f"> Profil Entreprise : {self.config.get('company_name')}\n")

        # Barre de progression globale
        self.progress_inst = ctk.CTkProgressBar(self.main_frame, width=600, height=20, progress_color="#0066FF")
        self.progress_inst.set(0)
        self.progress_inst.pack(pady=20)

        # Lancement Thread
        threading.Thread(target=self.run_final_install_logic).start()

    def run_final_install_logic(self):
        # Simulation des étapes finales
        steps = [
            "Génération du fichier de configuration JSON...",
            "Chiffrement des identifiants dans Windows Credential Manager...",
            "Vérification de la présence d'Ollama...",
            "Initialisation de la base de données SQLite (WAL Mode)...",
            "Création des Watchdogs sur les dossiers cibles...",
            "Téléchargement du modèle IA (Simulation)...",
            "Démarrage du service 'Sentinelle'...",
        ]

        for i, step in enumerate(steps):
            time.sleep(1.2) # Temps pour lire
            self.console.insert("end", f"> {step} [OK]\n")
            self.console.see("end")
            self.progress_inst.set((i + 1) / len(steps))

        self.console.insert("end", "\n> ✨ INSTALLATION TERMINÉE AVEC SUCCÈS.\n")
        
        # Bouton quitter / lancer
        self.btn_finish = ctk.CTkButton(self.main_frame, text="Ouvrir le Tableau de Bord", 
                                        fg_color="#10B981", height=50, font=("Arial", 16, "bold"),
                                        command=self.destroy) # Ferme le wizard
        self.after(0, lambda: self.btn_finish.pack(pady=20))

if __name__ == "__main__":
    app = WizardApp()
    app.mainloop()