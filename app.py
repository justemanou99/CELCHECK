from flask import Flask, render_template, request
import pandas as pd
import unicodedata

app = Flask(__name__, static_folder='static')


# Charger et nettoyer les colonnes du fichier Excel
data = pd.read_excel("Clients_non_conformes.csv.xlsx", header=1)

# Nettoyage et renommage des colonnes clés
data.columns = [unicodedata.normalize("NFKD", col).encode("ASCII", "ignore").decode("utf-8").strip().replace('\u00a0', '') for col in data.columns]

# Renommer la colonne 'Prenom' avec accent bizarre en 'Prénom'
data = data.rename(columns={"Prenom": "Prénom"})

@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    client_info = None

    if request.method == "POST":
        # Nettoyer les saisies utilisateur
        nom = unicodedata.normalize("NFKD", request.form["nom"]).encode("ASCII", "ignore").decode("utf-8").strip().upper()
        prenom = unicodedata.normalize("NFKD", request.form["prenom"]).encode("ASCII", "ignore").decode("utf-8").strip().upper()

        # Vérifie que les colonnes existent avant de rechercher
        if "Nom" in data.columns and "Prénom" in data.columns:
            # Nettoyer les colonnes 'Nom' et 'Prénom' de la base
            data["Nom"] = data["Nom"].astype(str).str.strip().str.upper()
            data["Prénom"] = data["Prénom"].astype(str).str.strip().str.upper()

            # Comparaison
            result = data[
                (data["Nom"] == nom) & (data["Prénom"] == prenom)
            ]

            if not result.empty:
                client_info = result.iloc[0].to_dict()
                message = "⚠️ Ce client est non conforme. Merci de ne pas créer de compte et de contacter le service conformité."
            else:
                message = "✅ Ce client n’est pas signalé. Vous pouvez procéder à la création du compte."
        else:
            message = "❌ Les colonnes 'Nom' ou 'Prénom' sont introuvables dans le fichier."

    return render_template("index.html", message=message, client=client_info)

if __name__ == "__main__":
    app.run(debug=True)
