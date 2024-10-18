#!/usr/bin/env python

import gspread
from google.oauth2.service_account import Credentials

# 1. Path to your downloaded service account key file (the JSON file)
SERVICE_ACCOUNT_FILE = 'REDACTED'

# 2. Define the scope required for Google Sheets (read-only in this case)
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# 3. Authenticate with the service account file
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# 4. Open the Google Sheet by its URL
SHEET_URL = 'REDACTED'
sheet = client.open_by_url(SHEET_URL).sheet1  # Accesses the first sheet in the document


# 5. Fetch all the data from the sheet
data = sheet.get_all_records()

# 6. Print the data (you can process it as needed)
for row in data:
    print(row)

