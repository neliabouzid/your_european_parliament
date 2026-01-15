import os
from dotenv import load_dotenv
load_dotenv()

import json
import re
from datetime import datetime
from urllib.parse import unquote
from flask import Flask, render_template
import psycopg2
from psycopg2.extras import DictCursor
import ast
from dateutil import parser

app = Flask(__name__)

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': os.getenv('DB_PORT', 5432)
}

MAIN_SUBJECTS = {
    "1": "European citizenship",
    "2": "Internal market, single market",
    "3": "Community policies",
    "4": "Economic, social and territorial cohesion",
    "5": "Economic and monetary system",
    "6": "External relations of the Union",
    "7": "Area of freedom, security and justice",
    "8": "State and evolution of the Union",
    "9": "Other topics",
}

def get_db_connection():
    """
    Establishes a connection to the PostgreSQL database 
    using the global configuration dictionary.
    """
    return psycopg2.connect(**DB_CONFIG)

def clean_subjects(text):
    """
    Splits a string of subjects based on legislative codes (e.g., 1.10.01).
    Returns a list of clean subject strings.
    """
    if not text:
        return []

    # Regex pattern to identify and remove numerical subject codes
    pattern = r'(?:\s*,\s*)?\d+(?:\.\d+)+\s*'
    parts = re.split(pattern, text)
    
    # Filter out empty strings and strip whitespace
    return [p.strip() for p in parts if p.strip()]

def extract_main_subjects(text):
    """
    Identifies the primary legislative categories from a text 
    by extracting the leading digit of the subject codes.
    """
    if not text:
        return []
    
    # Finds the first digit of codes like '3.10.04'
    matches = re.findall(r'\b([1-9])(?:\.\d+)+', text)
    return sorted(set(matches))

def extract_dates(text):
    """
    Parses various date formats from a raw string.
    Supports ISO (YYYY-MM-DD), European (DD/MM/YYYY), and textual formats.
    """
    if not text:
        return []

    # Multi-format date pattern for flexible extraction
    date_pattern = r"""
        (\d{4}-\d{2}-\d{2}) |
        (\d{2}/\d{2}/\d{4}) |
        (\d{2}-\d{2}-\d{4}) |
        (\d{2}\.\d{2}\.\d{4}) |
        (\d{1,2}\s\w+\s\d{4}) |
        (\d{1,2}\s\w+\.\s\d{4}) |
        (\d{1,2}\s\w+\s?\d{4})
    """

    matches = re.findall(date_pattern, text, flags=re.VERBOSE)
    parsed = []

    for match in matches:
        # Retrieve the first non-empty group from the match
        raw = next((m for m in match if m), None)
        if not raw:
            continue
        try:
            # dayfirst=True ensures DD/MM is prioritized over MM/DD
            parsed.append(parser.parse(raw, dayfirst=True))
        except Exception:
            continue

    return parsed

def clean_data_recursively(data):
    """
    Traverses dictionaries and lists to find strings formatted as Python lists.
    Uses literal_eval to convert strings like "['Name']" into actual list objects.
    """
    if isinstance(data, dict):
        return {k: clean_data_recursively(v) for k, v in data.items()}
    if isinstance(data, list):
        return [clean_data_recursively(i) for i in data]
    
    # Check if the string is a literal representation of a Python list
    if isinstance(data, str) and data.startswith('[') and data.endswith(']'):
        try:
            return ast.literal_eval(data)
        except Exception:
            return data
    return data

def sort_events_chronologically(events_dict):
    """
    Sorts a dictionary of events by their internal 'Date' field.
    Events without a valid date are placed at the beginning of the list.
    """
    if not isinstance(events_dict, dict):
        return events_dict

    def parse_date(item):
        date_str = item[1].get('Date')
        if not date_str or date_str == "N/A":
            return datetime.min
        try:
            return datetime.strptime(date_str, '%d/%m/%Y')
        except ValueError:
            return datetime.min

    # Returns a new dictionary sorted by the parsed datetime object
    return dict(sorted(events_dict.items(), key=parse_date))

def clean_incomplete_summary(text):
    """
    Ensures that AI-generated summaries do not end with a broken sentence.
    Trims the text back to the last valid punctuation mark (. ! ?).
    """
    if not text or not isinstance(text, str):
        return text

    # Locate the position of the final full sentence termination
    last_punctuation = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
    
    if last_punctuation == -1:
        return "Summary currently being updated..."
        
    return text[:last_punctuation + 1].strip()

def parse_field(field):
    # Returns an empty dictionary if the field is null or empty
    if not field:
        return {}
    if isinstance(field, str):
        try:
            # First attempt: parse as a Python literal (e.g., if it uses single quotes)
            return ast.literal_eval(field)
        except Exception:
            try:
                # Second attempt: parse as standard JSON
                return json.loads(field)
            except Exception:
                # Return empty dict if both parsing attempts fail
                return {}
    return field


@app.route('/')
def index():
    try:
        # Establish database connection and create a cursor
        conn = get_db_connection()
        cur = conn.cursor()

        # Retrieve the main procedure details where a title is present
        cur.execute("""
            SELECT reference, title, key_events, stage_reached_in_procedure
            FROM procedures_2025
            WHERE title IS NOT NULL AND title != ''
        """)

        rows = cur.fetchall()
        cur.close()
        conn.close()

        positions = []

        for ref, title, key_events, stage in rows:
            parsed_dates = []

            # Logic to extract dates from the key_events data structure
            if isinstance(key_events, dict):
                for event in key_events.values():
                    if isinstance(event, dict) and 'Date' in event:
                        try:
                            # Convert string dates into datetime objects for sorting
                            parsed_dates.append(
                                parser.parse(event['Date'], dayfirst=True)
                            )
                        except Exception:
                            pass
            elif isinstance(key_events, str):
                # Use helper function to find dates within a string
                parsed_dates = extract_dates(key_events)

            # Identify the most recent event date for this procedure
            latest = max(parsed_dates) if parsed_dates else None

            positions.append({
                "reference": ref,
                "title": title or "Untitled",
                # Map technical stage names to simplified status
                "stage": "COMPLETED" if stage == "Procedure completed" else "ONGOING",
                "last_date": latest,
                "formatted_date": latest.strftime("%d %b. %Y") if latest else "Unknown date"
            })

        # Sort all procedures by date (descending) and take the top 4
        recent = sorted(
            [p for p in positions if p["last_date"]],
            key=lambda x: x["last_date"],
            reverse=True
        )[:4]

        return render_template("index.html", recent_positions=recent)

    except Exception as e:
        # Handle connection or query failures
        return f"Database error: {e}", 500


@app.route('/procedures.html')
def index_procedures():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Select data including the subjects column for filtering
        cur.execute("""           
            SELECT reference, title, key_events, stage_reached_in_procedure, subjects
            FROM procedures_2025
            WHERE title IS NOT NULL AND title != ''
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

            parsed_dates = []

            # Extract dates from events to find the most recent timeline point
            if isinstance(key_events, dict):
                for event_data in key_events.values():
                    if isinstance(event_data, dict) and 'Date' in event_data:
                        try:
                            dt = parser.parse(event_data['Date'], dayfirst=True)
                            parsed_dates.append(dt)
                        except Exception:
                            continue
            elif isinstance(key_events, str):
                parsed_dates = extract_dates(key_events)

            # Format the date for the frontend display
            if parsed_dates:
                latest_parsed_date = max(parsed_dates)
                formatted_date = latest_parsed_date.strftime("%d %b. %Y")
            else:
                latest_parsed_date = None
                formatted_date = "Unknown date"

            # Extract year for specific filtering requirements
            year = latest_parsed_date.year if latest_parsed_date else ""

            # Standardize the procedure status string
            formatted_stage = (
                "COMPLETED" if stage == "Procedure completed" else "ONGOING"
            )

            # Format subject IDs into a single string for JavaScript filtering
            main_subjects = extract_main_subjects(row[4])
            subjects_string = "|".join(main_subjects)

            positions.append({
                'reference': ref,
                'title': title,
                'stage': formatted_stage,
                'date': formatted_date,
                'sort_date': latest_parsed_date,
                'year': year,
                'subjects': subjects_string
            })

        return render_template('index_procedures.html', rows=positions)

    except Exception as e:
        import traceback
        # Print full stack trace to the terminal for debugging
        traceback.print_exc()
        return f"Erreur base de données: {str(e)}", 500

@app.route('/procedure/<path:reference>.html')
def show_procedure(reference):
    # Decode the URL-encoded reference string to match database records
    reference = unquote(reference)
    
    # Establish a connection and use DictCursor to access columns by name
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor) 

    # Retrieve comprehensive procedure details from the 2025 database table
    cur.execute("""
        SELECT reference, title, stage_reached_in_procedure AS stage, 
               subjects, proposal_summary, final_act_summary, key_players, key_events
        FROM procedures_2025
        WHERE reference = %s 
        AND title IS NOT NULL 
        AND title != ''
    """, (reference,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    # Handle cases where the requested legislative procedure does not exist
    if not row:
        return "Procédure non trouvée", 404

    # Process the raw subjects string into a structured list
    subjects_list = clean_subjects(row['subjects'])

    # Standardize the key players data structure for the template
    key_players = clean_data_recursively(parse_field(row['key_players']))
    
    # First, sanitize the event strings, then order them by date for the timeline
    raw_events = clean_data_recursively(parse_field(row['key_events']))
    key_events_data = sort_events_chronologically(raw_events)

    # Remove trailing fragments from AI summaries to ensure they end with punctuation
    p_summary = clean_incomplete_summary(row['proposal_summary'])
    f_summary = clean_incomplete_summary(row['final_act_summary'])

    # Consolidate procedure metadata into a single dictionary for the view
    position = {
        'reference': row['reference'],
        'title': row['title'] or "Sans titre",
        'stage': row['stage'] or "Non spécifié",
        'subjects': subjects_list,
        'proposal_summary': p_summary or "The proposal hasn't been posted yet.",
        'final_act_summary': f_summary or "The final act hasn't been posted yet.",
    }
    
    # Render the detailed view with the sanitized and sorted legislative data
    return render_template(
        'procedure_detail.html',
        position=position,
        key_players_data=key_players, 
        key_events_data=key_events_data,
    )


@app.route('/in-the-making.html')
def in_the_making():
    # Placeholder route for features currently under development
    return render_template('in_the_making.html')

@app.route('/about.html')
def about():
    # Route to the About section
    return render_template('about.html')

@app.route('/whats-the-eu.html')
def whats_the_eu():
    # Route to the What's the EU? section
    return render_template('whats-the-eu.html')

@app.route('/whats-a-procedure.html')
def whats_a_procedure():
    # Route to the What's a procedure? section
    return render_template('whats-a-procedure.html')

if __name__ == '__main__':
    # Start the Flask development server on the default port 5000
    # Note: debug=True is helpful for development but should be disabled in production
    app.run(debug=True, port=5000)
