from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import unicodedata
import os
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static')
app.secret_key = 'celcheck2025'

USERNAME = 'admin'
PASSWORD = 'celcheck2025'

# Configuration upload
base_dir = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = base_dir
ALLOWED_EXTENSIONS = {'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Normalisation robuste des noms de colonnes
def normalize_columns(df):
    def clean(col):
        return (
            unicodedata.normalize("NFKD", col)
            .encode("ASCII", "ignore")
            .decode("utf-8")
            .strip()
            .replace('\u00a0', '')  # espace insécable
            .replace('\xa0', '')    # autre type d’espace
        )

    df.columns = [clean(col) for col in df.columns]

    # Renommer pour uniformiser
    for col in df.columns:
        if col.lower() in ['prenom', 'prénom']:
            df.rename(columns={col: 'Prénom'}, inplace=True)
        elif col.lower() == 'nom':
            df.rename(columns={col: 'Nom'}, inplace=True)

    return df

def load_data():
    file_path = os.path.join(base_dir, "clients_non_conformes.xlsx")
    print(f"DEBUG: Chemin du fichier Excel : {file_path}")
    
    if not os.path.exists(file_path):
        print("ERREUR : fichier clients_non_conformes.xlsx introuvable !")
        return pd.DataFrame()
    
    try:
        df = pd.read_excel(file_path, header=1)
        df = normalize_columns(df)
        print("Colonnes chargées :", df.columns.tolist())
        return df
    except Exception as e:
        print(f"Erreur lors du chargement du fichier : {e}")
        return pd.DataFrame()

# Chargement initial des données
data = load_data()

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USERNAME and password == PASSWORD:
            session['admin'] = True
            return redirect(url_for('upload_file'))
        else:
            error = 'Nom d’utilisateur ou mot de passe incorrect'
    return render_template('admin_login.html', error=error)

@app.route('/admin/upload', methods=['GET', 'POST'])
def upload_file():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    message = ''
    if request.method == 'POST':
        if 'file' not in request.files:
            message = 'Aucun fichier sélectionné.'
            return render_template('upload.html', message=message)

        file = request.files['file']
        if file.filename == '':
            message = 'Aucun fichier sélectionné.'
            return render_template('upload.html', message=message)

        if file and allowed_file(file.filename):
            filename = secure_filename('clients_non_conformes.xlsx')
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                file.save(filepath)
                global data
                data = load_data()
                message = '✅ Fichier mis à jour avec succès.'
            except Exception as e:
                message = f"❌ Erreur lors de la sauvegarde ou du chargement : {e}"
        else:
            message = '❌ Format non autorisé. Veuillez envoyer un fichier .xlsx.'

    return render_template('upload.html', message=message)

@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    clients = []

    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        prenom = request.form.get("prenom", "").strip()

        nom_clean = unicodedata.normalize("NFKD", nom).encode("ASCII", "ignore").decode("utf-8").upper()
        prenom_clean = unicodedata.normalize("NFKD", prenom).encode("ASCII", "ignore").decode("utf-8").upper()

        if not data.empty and "Nom" in data.columns and "Prénom" in data.columns:
            data["Nom"] = data["Nom"].astype(str).str.strip().str.upper()
            data["Prénom"] = data["Prénom"].astype(str).str.strip().str.upper()

            exact_match = data[(data["Nom"] == nom_clean) & (data["Prénom"] == prenom_clean)]
            if not exact_match.empty:
                clients = exact_match.to_dict(orient="records")
                message = "⚠️ Ce client est non conforme, merci de ne pas procéder à l'ouverture de son compte."
            else:
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
