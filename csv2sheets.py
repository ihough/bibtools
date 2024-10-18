#!/usr/bin/env python
#
# requires the following installations :
#
# pip install gspread google-auth


import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# 1. Path to your downloaded service account key file (the JSON file)
SERVICE_ACCOUNT_FILE = 'REDACTED'

# 2. Define the scope required for Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# 3. Authenticate with the service account
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# 4. Open the Google Sheet by its URL or spreadsheet ID
SHEET_URL = 'REDACTED'
sheet = client.open_by_url(SHEET_URL).sheet1  # Access the first sheet

# 5. Read the CSV file using pandas
csv_file = './papers.csv'
df = pd.read_csv(csv_file)

# 6. Clear existing content in the sheet (optional)
sheet.clear()

# 7. Update the Google Sheet with the data from the CSV
# Convert the dataframe to a list of lists (values) to be inserted into the sheet
sheet_data = [df.columns.values.tolist()] + df.values.tolist()  # Include headers
sheet.update(sheet_data)

print("Google Sheet updated successfully!")

