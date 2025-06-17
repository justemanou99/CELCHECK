from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import unicodedata
import os
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static')
app.secret_key = 'celcheck2025'  # Clé secrète pour gérer les sessions

# Identifiants d’accès admin
USERNAME = 'admin'
PASSWORD = 'celcheck2025'

# Configuration upload
UPLOAD_FOLDER = os.path.abspath('.')  # dossier actuel
ALLOWED_EXTENSIONS = {'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# === ROUTE POUR LA CONNEXION ADMIN ===
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USERNAME and password == PASSWORD:
            session['admin'] = True
            return redirect(url_for('upload_file'))  # Redirige vers la page d'upload après connexion
        else:
            error = 'Nom d’utilisateur ou mot de passe incorrect'
    return render_template('admin_login.html', error=error)

# === ROUTE POUR L’UPLOAD DU FICHIER EXCEL ===
@app.route('/admin/upload', methods=['GET', 'POST'])
def upload_file():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    message = ''
    global data  # On modifie la variable globale data

    if request.method == 'POST':
        if 'file' not in request.files:
            message = 'Aucun fichier sélectionné.'
            return render_template('upload.html', message=message)

        file = request.files['file']

        if file.filename == '':
            message = 'Aucun fichier sélectionné.'
            return render_template('upload.html', message=message)

        if file and allowed_file(file.filename):
            filename = secure_filename('clients_non_conformes.xlsx')  # nom fixe
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Recharger les données
            try:
                data = pd.read_excel(filepath, header=1)
                data.columns = [unicodedata.normalize("NFKD", col).encode("ASCII", "ignore").decode("utf-8").strip().replace('\u00a0', '') for col in data.columns]
                data = data.rename(columns={"Prenom": "Prénom"})
                message = 'Fichier mis à jour avec succès !'
            except Exception as e:
                message = f"Erreur lors du chargement du fichier : {e}"

        else:
            message = 'Format de fichier non autorisé. Veuillez uploader un fichier .xlsx'

    return render_template('upload.html', message=message)

# === CHARGEMENT INITIAL DE LA BASE
try:
    data = pd.read_excel("clients_non_conformes.xlsx", header=1)
    data.columns = [unicodedata.normalize("NFKD", col).encode("ASCII", "ignore").decode("utf-8").strip().replace('\u00a0', '') for col in data.columns]
    data = data.rename(columns={"Prenom": "Prénom"})
except Exception as e:
    data = pd.DataFrame()
    print("Erreur lors du chargement du fichier Excel :", e)

# === PAGE PRINCIPALE ===
@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    clients = []

    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        prenom = request.form.get("prenom", "").strip()

        # Nettoyage des entrées
        nom_clean = unicodedata.normalize("NFKD", nom).encode("ASCII", "ignore").decode("utf-8").upper()
        prenom_clean = unicodedata.normalize("NFKD", prenom).encode("ASCII", "ignore").decode("utf-8").upper()

        if not data.empty and "Nom" in data.columns and "Prénom" in data.columns:
            data["Nom"] = data["Nom"].astype(str).str.strip().str.upper()
            data["Prénom"] = data["Prénom"].astype(str).str.strip().str.upper()

            # === RECHERCHE EXACTE NOM + PRENOM
            exact_match = data[(data["Nom"] == nom_clean) & (data["Prénom"] == prenom_clean)]
            if not exact_match.empty:
                clients = exact_match.to_dict(orient="records")
                message = "⚠️ Ce client est non conforme ,merci de pas proceder à l'ouverture de son compte.Pour plus d'infomation contacter le service conformité."
            else:
                # === RECHERCHE PARTIELLE SI PRÉNOM INCOMPLET
                prenom_parts = prenom_clean.split()

                def match_prenoms(prenom_base):
                    return all(part in prenom_base for part in prenom_parts)

                partial_match = data[data["Nom"] == nom_clean]
                partial_match = partial_match[partial_match["Prénom"].apply(match_prenoms)]

                if not partial_match.empty:
                    clients = partial_match.to_dict(orient="records")
                    message = f"⚠️ {len(clients)} client(s) trouvé(s) avec nom exact et prénoms partiels."
                else:
                    message = "✅ Ce client n’est pas signalé. Vous pouvez procéder à la création du compte."
        else:
            message = "❌ Fichier invalide : colonnes 'Nom' ou 'Prénom' manquantes."

    return render_template("index.html", message=message, clients=clients)

if __name__ == "__main__":
    app.run(debug=True)
