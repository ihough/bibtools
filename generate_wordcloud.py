#!/usr/bin/env python
#
# pip install gspread oauth2client wordcloud matplotlib
# pip install --upgrade Pillow
# pip install --upgrade wordcloud
# pip install wordcloud==1.8.0 

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# Function to connect to Google Sheets

SERVICE_ACCOUNT_FILE = 'REDACTED'

def connect_to_google_sheet(sheet_url):
    # Define the scope for accessing Google Sheets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    
    # Use credentials.json to authenticate
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
    
    # Authorize the client
    client = gspread.authorize(creds)
    
    # Open the Google Sheet
    sheet = client.open_by_url(sheet_url).sheet1
    
    return sheet

# Function to get content from a specific column
def get_column_content(sheet, column_index):
    column_data = sheet.col_values(column_index)  # Get the entire column (index starts from 1)
    return " ".join(column_data)  # Join all the content into a single string

# Function to generate a word cloud from text
def generate_wordcloud(text):
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    
    # Display the generated word cloud using matplotlib
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    plt.show()

# Main function
def main():
    # Replace with the name of your Google Spreadsheet
    sheet_url = 'REDACTED'    
    # Connect to the Google Sheet
    sheet = connect_to_google_sheet(sheet_url)
 
   # Get the content of a specific column (e.g., column 1)
    column_index = 2  # Change to the appropriate column number
    text_data = get_column_content(sheet, column_index)
   
    #print(text_data) 
    # Generate a word cloud from the column data
    generate_wordcloud(text_data)

if __name__ == "__main__":
    main()

