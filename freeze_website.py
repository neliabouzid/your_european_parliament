"""
This script converts the dynamic Flask application into a static website.
It generates a set of HTML files and assets based on the app's routes, 
allowing the site to be hosted on static platforms like GitHub Pages.
"""

from flask_frozen import Freezer
from app import app  # Import the 'app' object from the 'app.py' file

# Configure Frozen-Flask to generate relative URLs
app.config['FREEZER_RELATIVE_URLS'] = True
# Set the output directory to 'docs' (common for GitHub Pages)
app.config['FREEZER_DESTINATION'] = 'docs'  

freezer = Freezer(app)

if __name__ == '__main__':
    freezer.freeze()