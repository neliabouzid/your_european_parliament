# html_renderers.py
import html
import json
import ast
import re
from datetime import datetime
from collections import OrderedDict

# ─────────────────────────────────────────────────────────
# Helper: safely escape or allow HTML
# ─────────────────────────────────────────────────────────
def safe_or_raw(text: str, allow_html: bool = True):
    if text is None:
        return ""
    if allow_html:
        return text
    escaped = html.escape(text)
    return escaped.replace("\n", "<br />\n")


# ─────────────────────────────────────────────────────────
# KEY PLAYERS (Acteurs clés)
# ─────────────────────────────────────────────────────────
def render_key_players(data_str: str) -> str:
    """
    Reproduit fidèlement le rendu précédent :
    - Sections par institution
    - Tables HTML dynamiques
    - Titre "Key Players"
    """

    if not data_str:
        return "<p><em>No key players available.</em></p>"

    try:
        data = json.loads(data_str)
    except json.JSONDecodeError:
        return f"<pre>{html.escape(data_str)}</pre>"

    html_parts = []
    html_parts.append("<h3>Key Players</h3>")

    for institution, entries in data.items():

        html_parts.append(
            f'<div class="institution-block"><h3>{html.escape(institution)}</h3>'
        )

        # Case 1 — list of dicts
        if isinstance(entries, list) and entries:
            for entry in entries:
                if isinstance(entry, dict):
                    html_parts.append(
                        '<table class="key-players-table"><thead><tr>'
                    )
                    for k in entry.keys():
                        html_parts.append(f"<th>{html.escape(k)}</th>")
                    html_parts.append("</tr></thead><tbody><tr>")
                    for v in entry.values():
                        html_parts.append(
                            f"<td>{html.escape(str(v))}</td>"
                        )
                    html_parts.append("</tr></tbody></table>")

        # Case 2 — single dict
        elif isinstance(entries, dict) and entries:
            html_parts.append(
                '<table class="key-players-table"><thead><tr>'
            )
            for k in entries.keys():
                html_parts.append(f"<th>{html.escape(k)}</th>")
            html_parts.append("</tr></thead><tbody><tr>")
            for v in entries.values():
                html_parts.append(f"<td>{html.escape(str(v))}</td>")
            html_parts.append("</tr></tbody></table>")

        else:
            html_parts.append("<p><em>No details available</em></p>")

        html_parts.append("</div>")

    return "\n".join(html_parts)


# ─────────────────────────────────────────────────────────
# KEY EVENTS (Événements clés)
# ─────────────────────────────────────────────────────────
def render_key_events(value: str) -> str:
    """
    Reproduction fidèle du rendu HTML précédent des « key events ».
    """
    if not value:
        return "<p>No key events available.</p>"

    try:
        data = ast.literal_eval(value)
    except Exception as e:
        return f"<p>Error parsing key_events: {html.escape(str(e))}</p>"

    rows = []

    for event, details in data.items():
        date = details.get("Date", "")
        refs = details.get("Reference", [])

        href = ""
        if isinstance(refs, list) and refs and isinstance(refs[0], dict):
            href = refs[0].get("href", "")

        if href:
            event_html = f'<a href="{html.escape(href)}" target="_blank">{html.escape(event)}</a>'
        else:
            event_html = html.escape(event)

        rows.append(f"<tr><td>{html.escape(date)}</td><td>{event_html}</td></tr>")

    return f"""
    <table class="key-events-table">
      <thead><tr><th>Date</th><th>Event</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    """


# ─────────────────────────────────────────────────────────
# OTHER EVENTS BLOCKS (pour "Main Dates" si utilisé ailleurs)
# ─────────────────────────────────────────────────────────
def render_events_data(data):
    if not data:
        return "<p><em>No details available</em></p>"

    html_parts = []

    if isinstance(data, dict):
        for event_name, details in data.items():
            html_parts.append(
                f'<div class="event-block"><h3>{html.escape(str(event_name))}</h3>'
            )
            if isinstance(details, dict):
                html_parts.append('<table class="main-dates-table"><tbody>')
                for key, value in details.items():
                    cell = format_cell_content(key, value)
                    html_parts.append(
                        f"<tr><th>{html.escape(str(key))}</th><td>{cell}</td></tr>"
                    )
                html_parts.append("</tbody></table>")
            else:
                html_parts.append(f"<p>{html.escape(str(details))}</p>")
            html_parts.append("</div>")
    else:
        return f"<pre>{html.escape(str(data))}</pre>"

    return "\n".join(html_parts)


def format_cell_content(key, value):
    if isinstance(value, list) and key.lower() == "reference":
        links = []
        for item in value:
            if isinstance(item, dict):
                text = html.escape(item.get("text") or item.get("Text", ""))
                href = html.escape(item.get("href") or item.get("Href", "#"))
                display = text or href
                links.append(f'<a href="{href}" target="_blank">{display}</a>')
            else:
                links.append(html.escape(str(item)))
        return "<br/>".join(links)

    if isinstance(value, (dict, list)):
        return html.escape(str(value))

    return html.escape(str(value))


# ─────────────────────────────────────────────────────────
# LAST EVENT DATE (pour tri + affichage)
# ─────────────────────────────────────────────────────────
def get_last_event_date(key_events_str: str) -> str:
    if not key_events_str:
        return "—"

    try:
        data = ast.literal_eval(key_events_str)
        if not isinstance(data, dict):
            return "—"

        dates = []
        for details in data.values():
            if isinstance(details, dict) and "Date" in details:
                try:
                    dt = datetime.strptime(details["Date"], "%d/%m/%Y").date()
                    dates.append(dt)
                except ValueError:
                    pass

        if dates:
            last = max(dates)
            return last.strftime("%b. %dth, %Y")

    except Exception:
        pass

    return "—"
