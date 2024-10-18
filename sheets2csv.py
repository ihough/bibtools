#!/usr/bin/env python
#
# requires the following installations : 
#
# pip install gspread google-auth
# pip install requests 

import gspread
from google.oauth2.service_account import Credentials
import requests
import csv

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


# Function to get first author, title and year from a DOI

def get_paper_details(doi):
    #print(doi)
    url = f"https://api.crossref.org/works/{doi}"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        title = data['message'].get('title', ["No title found"])[0]  # Get the first title
        year = data['message']['issued']['date-parts'][0][0]  # Get the year of publication
        authors = data['message'].get('author', [])
        
        # Get the first author's name, if available
        if authors:
            first_author = authors[0].get('given', '') + ' ' + authors[0].get('family', '')
        else:
            first_author = "No author found"
            
        return title, year, first_author
    else:
        #print('not found')
        return "DOI not found", "N/A", "N/A"  # In case of an invalid DOI or no data



# Open a CSV file to write the data
csv_file = "papers.csv"

with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    
    # Write the header row
    writer.writerow(["First Author","Year","DOI", "Title"])
    
    # Fetch title and year for each DOI and write to the CSV file
    for doi in extracted_dois:
        title, year, first_author = get_paper_details(doi)
        writer.writerow([first_author,year, doi, title])

print(f"CSV file '{csv_file}' created successfully!")

