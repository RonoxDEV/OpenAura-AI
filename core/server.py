from flask import Flask, request, render_template_string, redirect, url_for
import requests
import json
import os

app = Flask(__name__)

# --- TEMPLATES HTML (Le Design) ---
HTML_LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>OpenAura - Validation</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #F3F4F6; display: flex; justify-content: center; padding-top: 50px; }
        .card { background: white; width: 600px; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { color: #111827; font-size: 24px; margin-bottom: 10px; }
        .status { font-weight: bold; padding: 5px 10px; border-radius: 5px; font-size: 14px; display: inline-block; margin-bottom: 20px;}
        .waiting { background: #FEF3C7; color: #D97706; }
        .success { background: #D1FAE5; color: #059669; }
        .error { background: #FEE2E2; color: #991B1B; }
        textarea { width: 100%; height: 150px; padding: 10px; border: 1px solid #D1D5DB; border-radius: 8px; font-family: sans-serif; margin-bottom: 20px;}
        .btn { padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: bold; border: none; cursor: pointer; font-size: 16px; }
        .btn-green { background: #10B981; color: white; }
        .btn-green:hover { background: #059669; }
        .btn-gray { background: #6B7280; color: white; }
    </style>
</head>
<body>
    <div class="card">
        {{ content | safe }}
    </div>
</body>
</html>
"""

current_report = {
    "status": "waiting",
    "content": """📊 Résumé de l'activité détectée :
Cette semaine a été marquée par une forte activité sur le dossier /PROJETS/NATIV. 
J'ai détecté l'ajout de 3 nouveaux plans PDF pour le prototype "Sèche-serviette V2".

⚠️ Attention : Un fichier "facture_douteuse.exe" a été déposé dans le dossier Public mardi à 14h02."""
}

@app.route('/validate/<token>')
def validate_page(token):
    if current_report["status"] == "validated":
        state_html = '<span class="status success">✅ DÉJÀ VALIDÉ</span>'
        action_html = "<p>Ce rapport a déjà été envoyé aux équipes.</p>"
    else:
        state_html = '<span class="status waiting">⏳ EN ATTENTE DE VALIDATION</span>'
        action_html = f"""
        <p>Voici le brouillon actuel. Vous pouvez le modifier si besoin.</p>
        <form action="/confirm/{token}" method="POST">
            <textarea name="report_text">{current_report['content']}</textarea>
            <br>
            <button type="submit" class="btn btn-green">✅ Valider et Diffuser</button>
        </form>
        """

    body = f"<h1>Superviseur OpenAura</h1>{state_html}{action_html}"
    return render_template_string(HTML_LAYOUT, content=body)

@app.route('/confirm/<token>', methods=['POST'])
def confirm_action(token):
    new_text = request.form.get('report_text')
    current_report["content"] = new_text
    current_report["status"] = "validated"
    
    # --- LOGIQUE D'ENVOI SUR DISCORD ---
    status_msg = ""
    webhook_url = ""
    
    # 1. Lire le fichier config temporaire
    if os.path.exists("temp_config.json"):
        try:
            with open("temp_config.json", "r") as f:
                data = json.load(f)
                webhook_url = data.get("discord_webhook", "")
        except: pass

    # 2. Envoyer
    if webhook_url and "discord" in webhook_url:
        try:
            # Payload Discord simple
            payload = {
                "username": "OpenAura Analyst",
                "content": f"📢 **Rapport Validé par le Superviseur**\n\n{new_text}"
            }
            requests.post(webhook_url, json=payload)
            status_msg = "<p style='color:green'>✅ Diffusé sur Discord avec succès.</p>"
        except Exception as e:
            status_msg = f"<p style='color:red'>❌ Erreur d'envoi Discord : {e}</p>"
    else:
        status_msg = "<p style='color:orange'>⚠️ Aucun Webhook Discord trouvé (Mode Simulation).</p>"

    # 3. Page de confirmation
    body = f"""
        <div style="text-align: center;">
            <div style="font-size: 50px;">🚀</div>
            <h1>Rapport Envoyé !</h1>
            {status_msg}
            <br>
            <a href="#" class="btn btn-gray" onclick="window.close()">Fermer la fenêtre</a>
        </div>
    """
    return render_template_string(HTML_LAYOUT, content=body)

@app.route('/edit/<token>')
def edit_page(token):
    return redirect(url_for('validate_page', token=token))

if __name__ == '__main__':
    print("🌍 SERVEUR WEB OPENAURA DÉMARRÉ (Port 5000)")
    app.run(port=5000, debug=True)
