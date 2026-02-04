import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import time
from PIL import Image
import os
import psutil
import platform

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
        self.show_step_4_placeholder()


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
        self.show_step_4_placeholder()

    # =========================================================================
    # ÉTAPE 4 : Placeholder
    # =========================================================================
    def show_step_4_placeholder(self):
        self.clear_frame()
        self.create_header(4, "Installation", "Téléchargement des composants...")
        
        info = f"Moteur: {self.config.get('ai_engine')}\n"
        if self.config.get('ai_engine') == 'local':
            info += f"Modèle à installer: {self.config.get('selected_model')}\n"
            info += f"Specs: {self.config.get('hardware_specs')}"
        else:
            info += f"Provider: {self.config.get('api_provider')}"

        ctk.CTkLabel(self.main_frame, text=info, font=("Consolas", 12), justify="left", text_color="#374151").pack(pady=20)
        
        self.create_nav_buttons(back_cmd=self.show_step_3_menu, next_cmd=None)

if __name__ == "__main__":
    app = WizardApp()
    app.mainloop()