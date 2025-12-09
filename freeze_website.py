from flask_frozen import Freezer
from app import app  # Importe l'objet 'app' depuis le fichier 'app.py'

# Configure Frozen-Flask pour générer les URLs relatives
# (indispensable pour que le CSS marche sur GitHub Pages sans domaine perso)
app.config['FREEZER_RELATIVE_URLS'] = True
app.config['FREEZER_DESTINATION'] = 'docs'  # <--- AJOUTE CETTE LIGNE

freezer = Freezer(app)

if __name__ == '__main__':
    freezer.freeze()