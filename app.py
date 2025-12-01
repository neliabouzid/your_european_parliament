import json
import re
from datetime import datetime
from urllib.parse import unquote
# Importations de Flask et Psycopg2
from flask import Flask, render_template, g
import psycopg2
from psycopg2.extras import NamedTupleCursor, DictCursor
import html
from ast import literal_eval
from dateutil import parser
from dotenv import load_dotenv
import os

app = Flask(__name__)

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': os.getenv('DB_PORT', 5432)  # Default to 5432 if not set
}

# --- Fonctions de Base de Données ---

def get_db_connection():
    """Établit et retourne une connexion à la base de données PostgreSQL."""
    conn = psycopg2.connect(**DB_CONFIG)
    # Utiliser NamedTupleCursor pour pouvoir accéder aux colonnes par leur nom (ex: row.title)
    # J'utilise DictCursor ici car il est plus facile à manipuler pour les résultats
    # C'est plus simple que d'utiliser une fonction générique 'query_db' dans ce cas.
    return conn

def clean_subjects(text):
    if not text:
        return []

    # Matches ANY sequence like: 1.2, 3.10.04.02, 12.3.4.5.6, etc.
    # Explanation:
    #   \d+         → at least one digit
    #   (?:\.\d+)+  → one or more occurrences of ".digits"
    #
    pattern = r"\d+(?:\.\d+)+"

    # Split on the pattern. Since we used a NON-capturing group (?: ),
    # re.split will NOT include separators in the output.
    parts = re.split(pattern, text)

    # Clean whitespace and remove empty results.
    subjects = [p.strip() for p in parts if p.strip()]

    return subjects

def extract_dates(text):
    if not text:
        return []

    # Normaliser les slashes
    text = (
        text.replace("⁄", "/")
            .replace("／", "/")
            .replace("∕", "/")
    )

    # Regex multi-formats
    date_pattern = r"""
        (\d{4}-\d{2}-\d{2}) |        # 2025-06-24
        (\d{2}/\d{2}/\d{4}) |        # 24/06/2025
        (\d{2}-\d{2}-\d{4}) |        # 24-06-2025
        (\d{2}\.\d{2}\.\d{4}) |      # 24.06.2025
        (\d{1,2}\s\w+\s\d{4}) |      # 24 June 2025
        (\d{1,2}\s\w+\.\s\d{4}) |    # 24 Jun. 2025
        (\d{1,2}\s\w+\s?\d{4})       # 24 Jun 2025
    """

    matches = re.findall(date_pattern, text, flags=re.VERBOSE)

    parsed = []

    for match in matches:
        # Chaque match est un tuple → on prend le groupe non vide
        raw = next((m for m in match if m), None)

        if not raw:
            continue

        try:
            dt = parser.parse(raw, dayfirst=True)
            parsed.append(dt)
        except Exception as e:
            print("Impossible de parser :", raw, e)

    return parsed

# --- Routes Flask ---

@app.route('/')
def index():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT reference, title, key_events, "Stage reached in procedure"
            FROM for_mvp_position
        """)
        rows = cur.fetchall()

        cur.close()
        conn.close()

        positions = []
        for row in rows:
            ref = row[0]
            title = row[1] or "Sans titre"
            key_events = row[2]
            stage = row[3]

            parsed_dates = extract_dates(key_events)

            if parsed_dates:
                latest_parsed_date = max(parsed_dates)
                formatted_date = latest_parsed_date.strftime("%d %b. %Y")
            else:
                formatted_date = "Unknown date"
                latest_parsed_date = ""

            if stage == "Procedure completed":
                formatted_stage = "COMPLETED"
            else:
                formatted_stage = "ONGOING"

            positions.append({
                "reference": ref,
                "title": title,
                "stage": formatted_stage,
                "last_date": latest_parsed_date,
                "formatted_date": formatted_date
            })

        # Trier par la dernière date DESC, garder les 4 premiers
        recent = sorted(
            [p for p in positions if p["last_date"] is not None],
            key=lambda x: x["last_date"],
            reverse=True
        )[:4]

        return render_template("index.html", recent_positions=recent)

    except Exception as e:
        print(f"Erreur : {e}")
        return f"Erreur DB : {e}", 500

@app.route('/positions')
def index_positions():
    # Cette fonction liste toutes les positions, je la laisse telle quelle
    # (sauf pour l'utilisation de get_db_connection)
    print("Accès à /positions")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # NOTE: J'ai retiré 'key_events' de la sélection car il n'est pas utilisé pour la liste
        cur.execute("""
            SELECT reference, title, "Stage reached in procedure", key_events
            FROM for_mvp_position
            ORDER BY reference
        """)
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        positions_list = []
        
        for row in rows:
            # Assurez-vous que row est accessible par index (car fetchall() retourne des tuples par défaut)
            key_events = row[3] or ""
                    
            # Utilisation de la conversion en datetime et max pour trouver la date la plus récente
            parsed_dates = extract_dates(key_events)

            if parsed_dates:
                last_date = max(parsed_dates).strftime("%d %b. %Y")
            else:
                last_date = "Unknown date"

            positions_list.append({
                'reference': row[0],
                'title': row[1],
                'stage': row[2],
                'date': last_date,
            })
            
        return render_template('index_positions.html', rows=positions_list) # Assurez-vous d'avoir ce template
    
    except Exception as e:
        print(f"Erreur base de données (index_positions): {e}")
        return f"Erreur base de données: {str(e)}", 500


@app.route('/position/<path:reference>')
def show_position(reference):
    from urllib.parse import unquote
    from psycopg2.extras import DictCursor

    reference = unquote(reference)

    conn = get_db_connection()
    # Utiliser DictCursor est une bonne idée ici
    cur = conn.cursor(cursor_factory=DictCursor) 

    cur.execute("""
        SELECT reference, title, "Stage reached in procedure" AS stage, 
                subjects, position_summary, key_players, key_events
        FROM for_mvp_position
        WHERE reference = %s
    """, (reference,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        print(f"Aucune position trouvée pour la référence: {reference}")
        return "Position non trouvée", 404
    
    subjects_list = clean_subjects(row[3])

    # ----------- Position "normale" -----------
    position = {
        'reference': row['reference'],
        'title': row['title'] or "Sans titre",
        'stage': row['stage'] or "Non spécifié",
        'subjects': subjects_list,
        'position_summary': row['position_summary'] or "Aucun résumé disponible",
    }
    
    # ----------- KEY PLAYERS (Chaîne de la DB -> Dictionnaire Python) -----------
    key_players_str = row.get("key_players") # Utiliser .get pour plus de sécurité
    key_players = {}
    
    if key_players_str:
        try:
            # Tente de décoder la chaîne JSON
            key_players = json.loads(key_players_str)
        except json.JSONDecodeError as e:
            # Gestion d'erreur au cas où la structure n'est pas parfaite (comme avant)
            print(f"Erreur de décodage JSON pour key_players de {reference}: {e}")
            key_players = {"Erreur de Données": "Impossible d'analyser la structure des acteurs principaux."}

    key_events_str = row.get('key_events') 
    key_events_data = {}

    if key_events_str:
        try:
            # 1. Tenter l'évaluation littérale (pour les chaînes avec guillemets simples)
            key_events_data = literal_eval(key_events_str)
            # S'assurer que le résultat est bien un dictionnaire
            if not isinstance(key_events_data, dict):
                raise ValueError("Literal evaluation did not result in a dictionary.")
                
        except (ValueError, SyntaxError) as e_literal:
            # 2. Si l'évaluation littérale échoue, tenter le décodage JSON standard
            try:
                key_events_data = json.loads(key_events_str)
            except json.JSONDecodeError as e_json:
                # 3. Échec final
                print(f"Erreur de décodage JSON (Standard) pour key_events de {reference}: {e_json}")
                print(f"Erreur d'évaluation littérale pour key_events de {reference}: {e_literal}")
                
                # Afficher l'erreur que vous avez vue
                key_events_data = {"Erreur de Données": {"Date": "Impossible d'analyser la structure des événements clés."}}

    # ----------- Rendu du template -----------
    return render_template(
        'position_detail.html',
        position=position,
        # IMPORTANT: Passer l'objet Dictionnaire Python (key_players), PAS la chaîne brute.
        key_players_data=key_players, 
        key_events_data=key_events_data,
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)