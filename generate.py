#!/usr/bin/env python3
# generate.py
"""
Generates one HTML page per row in the CSV file.
Usage:
  python generate.py 
"""

import csv
import os
import re
import html
from collections import defaultdict, OrderedDict
import json
import ast
from datetime import datetime
from bs4 import BeautifulSoup

# Increase CSV field size limit to handle very long cells (here legislative texts)
csv.field_size_limit(10_000_000)

# HTML template for each generated procedure page
TEMPLATE = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>YEP</title>
    <link rel="icon" type="image/svg+xml" href="../../../logo_yep.svg" />
    <link rel="stylesheet" href="../../../yep_procedures.css" />
  </head>
  <body>
    <!-- Navigation bar -->
    <div class="navbar">
      <!-- Logo linking back to homepage -->
      <a href="../../../yep_homepage.html" id="logo-link">
        <img src="../../../logo_yep.svg" alt="YEP logo" class="nav-logo" />
      </a>
      <div class="nav-links">
        <a href="#" class="nav-link" data-page="eu">What's the EU?</a>
        <a href="#" class="nav-link" data-page="procedure">What is a procedure?</a>
        <div class="subnav">
          <a href="javascript:void(0)" class="subnavbtn">Procedures</a>
          <div class="subnav-content">
            <!-- Updated links -->
            <a href="../../index_position.html" class="nav-link" data-page="completed">Completed procedures</a>
            <a href="../../index_proposal.html" class="nav-link" data-page="ongoing">Ongoing procedures</a>
          </div>
        </div>
      </div>
    </div>

    <!-- Title and metadata section -->
    <div class="title">{title}</div>
    <div class="subjects"><strong>Subject(s):</strong> {subjects}</div>
    <div class="stage"><strong>Stage reached:</strong> {stage}</div>
    <div class="reference"><strong>Reference:</strong><a href="#"> {reference_display}</a></div>
    
    <!-- Main content area -->
    <div class="main">
      <div class="content">
        <div class="explanation-title">
          {explanation_title}
        </div>
        <div class="proposal-text">
          {proposal_summary}
        </div>
      </div>

      <!-- Sidebar: key players and main dates -->
      <div class="sidebar">
        <div class="box key-players">
          {key_players}
        </div>
        <div class="box main-dates">
          <h3>Main Dates</h3>
          {main_dates}
        </div>
      </div>
    </div>
  </body>
</html>
"""

# Map of expected CSV column names (for flexibility in column headers)
SAFE_COL_HEADERS = {
    "reference": ["reference"],
    "title": ["title"],
    "proposal_summary": ["proposal_summary"],
    "stage": ["stage reached in procedure"],
    "subjects": ["subjects"],
    # Optional columns that may or may not exist
    "key_players": ["key_players"],
    "key_events": ["key_events"],
}


def find_column_name(fieldnames, possible_names):
    """Return the first matching column name from the CSV (case-insensitive)."""
    # Create a mapping of lowercase field names to their original case
    fn_lower = {fn.lower(): fn for fn in fieldnames}
    # Loop through possible column names and return the first match
    for p in possible_names:
        if p.lower() in fn_lower:
            return fn_lower[p.lower()]
    # Return None if no matching name is found
    return None


def slugify_ref(ref: str) -> str:
    """Create a filesystem-safe slug from a procedure reference string."""
    # Convert the reference to string and remove leading/trailing spaces
    ref = str(ref).strip()
    # Replace spaces with dashes
    ref = ref.replace(" ", "-")
    # Remove all characters except letters, digits, hyphens, and underscores
    ref = re.sub(r"[^A-Za-z0-9\-_]", "", ref)
    # If nothing is left, raise an error
    if not ref:
        raise ValueError("Reference is empty after cleaning.")
    return ref


def ensure_dir(path):
    """Create directory if it doesn’t exist."""
    # Make sure the directory path exists, create it if necessary
    os.makedirs(path, exist_ok=True)


def safe_or_raw(text: str, allow_html: bool):
    """Return text as-is (if HTML allowed) or safely escaped for HTML."""
    # Handle None values
    if text is None:
        return ""
    # If HTML is allowed, return the text unchanged
    if allow_html:
        return text
    # Otherwise, escape HTML characters and replace line breaks with <br> tags
    escaped = html.escape(text)
    return escaped.replace("\n", "<br />\n")


def render_key_players(data_str):
    """Render 'key_players' JSON into HTML tables per institution."""
    # Return empty string if no data provided
    if not data_str:
        return ""
    try:
        # Try to parse JSON string into a Python dictionary
        data = json.loads(data_str)
    except json.JSONDecodeError:
        # If JSON is invalid, return raw text wrapped in <pre> for readability
        return f"<pre>{html.escape(data_str)}</pre>"

    html_parts = []
    html_parts.append('Key Players') # Add title for the table

    # Iterate over institutions (keys in the JSON)
    for institution, entries in data.items():
        html_parts.append(f'<div class="institution-block"><h3>{html.escape(institution)}</h3>')

        # Case 1: entries is a list of dictionaries
        if isinstance(entries, list) and entries:
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                # Create an HTML table with header and rows
                html_parts.append('<table class="key-players-table"><thead><tr>')
                for k in entry.keys():
                    html_parts.append(f"<th>{html.escape(k)}</th>")
                html_parts.append("</tr></thead><tbody><tr>")
                for v in entry.values():
                    html_parts.append(f"<td>{html.escape(str(v))}</td>")
                html_parts.append("</tr></tbody></table>")

        # Case 2: entries is a single dictionary
        elif isinstance(entries, dict) and entries:
            html_parts.append('<table class="key-players-table"><thead><tr>')
            for k in entries.keys():
                html_parts.append(f"<th>{html.escape(k)}</th>")
            html_parts.append("</tr></thead><tbody><tr>")
            for v in entries.values():
                html_parts.append(f"<td>{html.escape(str(v))}</td>")
            html_parts.append("</tr></tbody></table>")

        # Case 3: no available data
        else:
            html_parts.append("<p><em>No details available</em></p>")

        # Close the institution section
        html_parts.append("</div>")

    # Join all HTML sections into one string
    return "\n".join(html_parts)


def render_key_events(value):
    """Convert 'key_events' column (stringified dict) into an HTML table."""
    # Return placeholder if no events are available
    if not value:
        return "<p>No key events available.</p>"

    try:
        # Safely evaluate the string into a Python dictionary
        data = ast.literal_eval(value)
    except Exception as e:
        # If parsing fails, show an error message with the exception
        return f"<p>Error parsing key_events: {html.escape(str(e))}</p>"

    rows_html = []
    # Iterate through all events and build table rows
    for event, details in data.items():
        date = details.get("Date", "")
        refs = details.get("Reference", [])
        href = ""
        # Get the first link if references are available
        if isinstance(refs, list) and len(refs) > 0 and isinstance(refs[0], dict):
            href = refs[0].get("href", "")
        # Create a hyperlink if a URL exists
        if href:
            event_html = f'<a href="{html.escape(href)}" target="_blank">{html.escape(event)}</a>'
        else:
            event_html = html.escape(event)

        # Add a table row for the event
        rows_html.append(f"<tr><td>{html.escape(date)}</td><td>{event_html}</td></tr>")

    # Return the complete HTML table
    return f"""
    <table class="key-events-table">
      <thead><tr><th>Date</th><th>Event</th></tr></thead>
      <tbody>
        {''.join(rows_html)}
      </tbody>
    </table>
    """


def parse_ordered_dict_string(s):
    """Parse text formatted as OrderedDict(...) into a Python dictionary."""
    # Return None if input is empty or not a string
    if not s or not isinstance(s, str):
        return None
    # Remove leading/trailing spaces
    s = s.strip()
    # Detect OrderedDict pattern
    if s.startswith('OrderedDict(') and s.endswith(')'):
        inner_content = s[12:-1]  # Extract content inside parentheses
        try:
            # Safely evaluate the inner content as a Python object
            return ast.literal_eval(inner_content)
        except:
            # If parsing fails, try a more advanced parser
            return parse_complex_ordered_dict(s)
    return None

def parse_complex_ordered_dict(s):
    """Handle complex OrderedDict cases."""
    try:
        # Allow only OrderedDict objects to be evaluated safely
        allowed_objects = {'OrderedDict': OrderedDict}
        # Use eval in a restricted environment to convert the string into a Python object
        return eval(s, {"__builtins__": {}}, allowed_objects)
    except Exception as e:
        # Print debug message if parsing fails
        print(f"DEBUG: Complex parsing failed: {e}")
        return None


def render_events_data(data):
    """Render parsed 'events' data into readable HTML tables."""
    # If there's no data, return a placeholder message
    if not data:
        return "<p><em>No details available</em></p>"

    html_parts = []
    # If the data is a dictionary, iterate through each event
    if isinstance(data, dict):
        for event_name, details in data.items():
            # Add the event name as a section title
            html_parts.append(f'<div class="event-block"><h3>{html.escape(str(event_name))}</h3>')
            # If the event details are a dictionary, render them as a table
            if isinstance(details, dict):
                html_parts.append('<table class="main-dates-table"><tbody>')
                for key, value in details.items():
                    # Format each cell (may include links)
                    cell_content = format_cell_content(key, value)
                    html_parts.append(f'<tr><th>{html.escape(str(key))}</th><td>{cell_content}</td></tr>')
                html_parts.append('</tbody></table>')
            else:
                # If details are not a dictionary, show them as plain text
                html_parts.append(f'<p>{html.escape(str(details))}</p>')
            html_parts.append('</div>')
    else:
        # If the data is not a dictionary, show the raw content
        html_parts.append(f'<pre>{html.escape(str(data))}</pre>')

    # Return the assembled HTML or a default message if nothing was rendered
    return "\n".join(html_parts) if html_parts else "<p><em>No details available</em></p>"


def format_cell_content(key, value):
    """Format individual table cells, adding links where appropriate."""
    # If the value is a list and the key is 'reference', create clickable links
    if isinstance(value, list) and key.lower() == "reference":
        links = []
        for item in value:
            if isinstance(item, dict):
                # Extract display text and link URL
                text = html.escape(str(item.get("text") or item.get("Text", "")))
                href = html.escape(str(item.get("href") or item.get("Href", "#")))
                # Use text if available, otherwise use URL as display text
                display_text = text if text.strip() else href
                links.append(f'<a href="{href}" target="_blank" rel="noopener noreferrer">{display_text}</a>')
            else:
                # Handle non-dictionary list items
                links.append(html.escape(str(item)))
        return "<br/>".join(links)
    # If the value is a dict or list, escape it for safe display
    elif isinstance(value, (dict, list)):
        return html.escape(str(value))
    # Otherwise, just escape the value as text
    else:
        return html.escape(str(value))


def get_last_event_date(key_events_str: str) -> str:
    """Extract the most recent date from key_events and format it nicely."""
    # Return placeholder if no key_events provided
    if not key_events_str:
        return "—"
    try:
        # Safely parse the string representation into a Python dict
        key_events = ast.literal_eval(key_events_str)
        if not isinstance(key_events, dict):
            return "—"
        dates = []
        # Iterate through all events to extract 'Date' fields
        for event, details in key_events.items():
            if isinstance(details, dict) and "Date" in details:
                date_str = details["Date"]
                try:
                    # Convert date string (format: DD/MM/YYYY) into a datetime object
                    date = datetime.strptime(date_str, "%d/%m/%Y").date()
                    dates.append(date)
                except ValueError:
                    # Skip malformed dates
                    pass
        # If there are valid dates, return the most recent one formatted nicely
        if dates:
            last_date = max(dates)
            return last_date.strftime("%b. %dth, %Y") 
    except Exception:
        # In case of any parsing error, return placeholder
        pass
    return "—"

def generate_pages(input_csv: str, output_dir: str, allow_html: bool, mode: str = "proposal"):
    """
    Generate HTML pages for proposals or positions.
    mode = "proposal" (Commission proposals) or "position" (Parliament positions).
    """
    # Ensure base output directories exist
    ensure_dir(output_dir)
    base_folder = os.path.join(output_dir, f"legislative-{mode}")
    ensure_dir(base_folder)

    used_refs = defaultdict(int)  # Track duplicate references
    index_entries = []  # Store entries for the index page
    rows_data = []  # Store raw rows to use later (for event dates, etc.)

    # Open and read the CSV file
    with open(input_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise SystemExit("CSV seems empty or malformed (no headers).")

        # Detect correct column names using SAFE_COL_HEADERS mapping
        col_map = {}
        for key, possibles in SAFE_COL_HEADERS.items():
            found = find_column_name(reader.fieldnames, possibles)
            col_map[key] = found

        # Fallback: detect “position_summary” if “proposal_summary” not found
        if not col_map["proposal_summary"]:
            for fn in reader.fieldnames:
                if fn.lower() == "position_summary":
                    col_map["proposal_summary"] = fn
                    break

        # Validate required columns
        if not col_map["reference"]:
            raise SystemExit("Error: missing 'reference' column in CSV.")
        if not col_map["proposal_summary"]:
            raise SystemExit("Error: missing 'proposal_summary' or 'position_summary' column.")
        if not col_map["title"]:
            print("[WARN] 'title' column not found; pages will have an empty title.")

        # Iterate through CSV rows
        for rownum, row in enumerate(reader, start=1):
            raw_ref = row.get(col_map["reference"], "").strip()
            if not raw_ref:
                print(f"[WARN] Row {rownum}: empty reference -> skipped")
                continue
            try:
                slug = slugify_ref(raw_ref)  # Create a clean reference slug
            except ValueError:
                print(f"[WARN] Row {rownum}: invalid reference '{raw_ref}' -> skipped")
                continue

            # Handle duplicate reference cases by appending a counter
            used_refs[slug] += 1
            final_slug = slug if used_refs[slug] == 1 else f"{slug}-{used_refs[slug]-1}"

            # Extract and map fields safely
            title = row.get(col_map["title"], "") if col_map["title"] else ""
            summary = row.get(col_map["proposal_summary"], "")
            stage = row.get(col_map["stage"], "") if col_map["stage"] else ""
            subjects = row.get(col_map["subjects"], "") if col_map["subjects"] else ""
            key_players = row.get(col_map["key_players"], "") if col_map.get("key_players") else ""
            key_events = row.get(col_map["key_events"], "") if col_map.get("key_events") else ""

            # Escape or preserve HTML based on configuration
            title_html = safe_or_raw(title, allow_html)
            summary_html = safe_or_raw(summary, allow_html)
            stage_html = safe_or_raw(stage, allow_html)
            subjects_html = safe_or_raw(subjects, allow_html)
            key_players_html = render_key_players(key_players)
            key_events_html = render_key_events(key_events)

            # Create output directory and file path for this procedure
            out_dir = os.path.join(base_folder, final_slug)
            ensure_dir(out_dir)
            out_file = os.path.join(out_dir, "index.html")

            # Section title differs depending on the mode (proposal/position)
            if mode == "position":
                explanation_title = "What is the position of the European Parliament on the procedure?"
            else:
                explanation_title = "What does the European Commission's proposal consist in?"

            # Fill the HTML template with data
            rendered = TEMPLATE.format(
                title=title_html,
                subjects=subjects_html,
                stage=stage_html,
                reference_display=html.escape(raw_ref),
                proposal_summary=summary_html,
                key_players=key_players_html,
                main_dates=key_events_html,
                explanation_title=explanation_title,
            )

            # Write rendered HTML to file
            with open(out_file, "w", encoding="utf-8") as fo:
                fo.write(rendered)

            # Store entry for index generation
            url = f"/output/legislative-{mode}/{final_slug}/index.html"
            # compute last date from key_events field (string) using existing helper
            last_date_str = get_last_event_date(key_events)  # returns "—" or e.g. "Oct. 24th, 2025"
            index_entries.append((raw_ref, final_slug, url, title, stage, subjects, last_date_str))
            rows_data.append(row)

            # --- NEW: write latest_procedures.json ---
            latest_json_path = os.path.join(output_dir, "latest_procedures.json")
            with open(latest_json_path, "w", encoding="utf-8") as f:
                json.dump([
                    {
                        "slug": slug,
                        "title": title,
                        "date": last_date_str,
                        "url": url
                    }
                    for raw_ref, slug, url, title, stage, subjects, last_date_str in index_entries
                ], f, indent=2)
            print(f"latest_procedures.json written: {latest_json_path}")

            print(f"[OK] Generated: {out_file}")

    # After generating all pages, create the index page
    index_path = os.path.join(output_dir, f"index_{mode}.html")
    title_index = 'Completed procedures' if mode == 'position' else 'Ongoing procedures'

    # Write the index page HTML
    with open(index_path, "w", encoding="utf-8") as ix:
        ix.write(f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>{title_index} – YEP</title>
            <link rel="icon" type="image/svg+xml" href="../../logo_yep.svg" />
            <link rel="stylesheet" href="../../yep_procedures.css" />
            <link rel="stylesheet" href="../../homepage.css" />
        </head>
        <body>
            <!-- Navigation bar -->
            <div class="navbar">
            <a href="../yep_homepage.html" id="logo-link">
                <img src="../../logo_yep.svg" alt="YEP logo" class="nav-logo" />
            </a>
            <div class="nav-links">
                <a href="#" class="nav-link" data-page="eu">What's the EU?</a>
                <a href="#" class="nav-link" data-page="procedure">What is a procedure?</a>
                <div class="subnav">
                <a href="javascript:void(0)" class="subnavbtn">Procedures</a>
                <div class="subnav-content">
                    <a href="index_position.html" class="nav-link">Completed procedures</a>
                    <a href="index_proposal.html" class="nav-link">Ongoing procedures</a>
                </div>
                </div>
            </div>
            </div>
            <div class="title">{title_index}</div>
            <div class="cards-wrapper">
                    """)

        # Create a card for each procedure
        for raw_ref, slug, url, title, stage, subjects, last_date_str in index_entries:
            last_date = last_date_str
            title_display = html.escape(title) if title else html.escape(raw_ref)
            stage_display = "ONGOING" if mode == "proposal" else "COMPLETED"
            blue_corner_class = "blue-corner-small" if mode == "position" else "blue-corner"

            # Write each card block into the index
            ix.write(f"""
                <a href="{url}" class="card-link" data-page="{slug}">
                <div class="card">
                    <div class="card-content">
                        <div class="{blue_corner_class}"><p>{stage_display}</p></div>
                        <div class="date">{last_date}</div>
                        <p>{title_display}</p>
                    </div>
                </div>
                </a>
                    """)

        # Close HTML document
        ix.write("""
            </div>
        </body>
        </html>
        """)

    print(f"\nStyled index has been generated ({mode}): {index_path}")
    return index_entries

def update_homepage_latest_4(output_dir: str, all_entries: list):
    """
    Replace the 4 cards in homepage <div class="cards-wrapper">
    with the latest 4 procedures, removing the old cards completely.
    """
    homepage_path = os.path.join(output_dir, "../yep_homepage.html")
    if not os.path.exists(homepage_path):
        print("Homepage not found:", homepage_path)
        return

    # Sort entries by last date descending
    enriched = []
    for item in all_entries:
        raw_ref, slug, url, title, stage, subjects, last_date_str = item
        dt = datetime.min
        if last_date_str and last_date_str != "—":
            clean = re.sub(r'(st|nd|rd|th)', '', last_date_str)
            try:
                dt = datetime.strptime(clean, "%b. %d, %Y")
            except:
                pass
        enriched.append((dt, raw_ref, slug, url, title, stage, subjects, last_date_str))

    enriched.sort(key=lambda x: x[0], reverse=True)
    latest = enriched[:4]

    # Load homepage
    with open(homepage_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    cards_wrapper = soup.find("div", class_="cards-wrapper")
    if not cards_wrapper:
        print("No <div class='cards-wrapper'> found")
        return

    # Remove all existing card links (only direct children)
    for child in list(cards_wrapper.find_all("a", class_="card-link", recursive=False)):
        child.decompose()

    # Add the latest 4 cards
    for dt, raw_ref, slug, url, title, stage, subjects, last_date_str in latest:
        # Decide stage and corner class
        mode = "proposal" if "proposal" in url else "position"
        stage_text = "ONGOING" if mode == "proposal" else "COMPLETED"
        blue_corner_class = "blue-corner" if mode == "proposal" else "blue-corner-small"

        # Let JS build the href dynamically; Python just sets data-page and mode
        a_tag = soup.new_tag("a", href="#", **{"class": "card-link", "data-page": slug, "data-mode": mode})        
        card_div = soup.new_tag("div", **{"class": "card"})
        content_div = soup.new_tag("div", **{"class": "card-content"})

        corner_div = soup.new_tag("div", **{"class": blue_corner_class})
        p_stage = soup.new_tag("p")
        p_stage.string = stage_text
        corner_div.append(p_stage)

        date_div = soup.new_tag("div", **{"class": "date"})
        date_div.string = last_date_str if last_date_str != "—" else ""

        p_title = soup.new_tag("p")
        p_title.string = title or raw_ref

        content_div.append(corner_div)
        content_div.append(date_div)
        content_div.append(p_title)
        card_div.append(content_div)
        a_tag.append(card_div)
        cards_wrapper.append(a_tag)

    # Write back
    with open(homepage_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print("Homepage updated with the 4 latest procedures.")

def main():
    """Main entry point for generating legislative pages."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    output_dir = os.path.join(base_dir, "output")

    # Define paths for both proposal and position CSVs
    proposal_csv = os.path.join(data_dir, "for_mvp_proposal.csv")
    position_csv = os.path.join(data_dir, "for_mvp_position.csv")

    all_entries = []

    # Generate Commission's proposal pages
    if os.path.exists(proposal_csv):
        print("Generation of the pages for the PROPOSALS")
        entries_proposal = generate_pages(proposal_csv, output_dir, allow_html=True, mode="proposal")
        all_entries.extend(entries_proposal)
    else:
        print("Proposal file not found:", proposal_csv)

    # Generate Parliament's position pages
    if os.path.exists(position_csv):
        print("Generation of the pages for the POSITIONS")
        entries_position = generate_pages(position_csv, output_dir, allow_html=True, mode="position")
        all_entries.extend(entries_position)
    else:
        print("Position file not found:", position_csv)

    # Update homepage cards with the 4 latest procedures
    if all_entries:
        update_homepage_latest_4(output_dir, all_entries)

# Execute the script only if run directly
if __name__ == "__main__":
    main()