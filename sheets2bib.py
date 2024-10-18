#!/usr/bin/env python
#
# requires the following installations : 
#
# pip install gspread google-auth
# pip install requests 

import gspread
from google.oauth2.service_account import Credentials
import requests


# Path to your downloaded service account key file (the JSON file)
SERVICE_ACCOUNT_FILE = 'REDACTED'

# Define the scope required for Google Sheets (read-only in this case)
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Authenticate with the service account file
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# Open the Google Sheet by its URL
SHEET_URL = 'REDACTED'
sheet = client.open_by_url(SHEET_URL).sheet1  # Accesses the first sheet in the document

# Fetch the third row (indexing starts at 1, so third row is 3)
third_col = sheet.col_values(3)

# Print the third row
urls = third_col

# Substrings to check for
substring1 = 'https://doi.org/'
substring2 = 'https://dx.doi.org/'

# Filter the list to include items that contain one of the sustrings'
filtered_dois = [item for item in urls if substring1 in item or substring2 in item]

# Predefined substring to split on
split_string = "doi.org/"

# Extracting the part of each string after the predefined substring
extracted_dois = [s.split(split_string, 1)[1] for s in filtered_dois if split_string in s]


# function to turn a doi in a bibtext entry 

def get_bibtex(doi):
    url = f"https://doi.org/{doi}"
    headers = {"Accept": "application/x-bibtex"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.text  # Return the BibTeX entry
    else:
        return f"% Error: Unable to fetch BibTeX for DOI {doi}\n"  # Return an error comment in BibTeX format


# Open a new .bib file to write the entries
with open("references.bib", "w") as bibfile:
    for doi in extracted_dois:
        bibtex_entry = get_bibtex(doi)
        bibfile.write(bibtex_entry)
        bibfile.write("\n\n")  # Add spacing between entries

print("BibTeX file created successfully: references.bib")

