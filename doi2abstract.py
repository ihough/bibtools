#!/usr/bin/env python
#

import requests

# Function to get the abstract of a paper from its DOI using the Semantic Scholar API
def get_paper_abstract(doi, api_key):
    # Semantic Scholar API endpoint
    api_url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=title,abstract"
    
    headers = {
#        "x-api-key": api_key  # Your API key from Semantic Scholar
    }
    
    # Send the request to the Semantic Scholar API
    response = requests.get(api_url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        title = data.get('title', 'No title available')
        abstract = data.get('abstract', 'No abstract available')
        return title, abstract
    else:
        return None, f"Error: DOI {doi} not found or request failed with status {response.status_code}"

# Main function to take DOI as input and fetch the abstract
def main():
    api_key = "your_semantic_scholar_api_key"  # Replace with your Semantic Scholar API key
    doi = input("Enter the DOI of the paper: ")
    
    title, abstract = get_paper_abstract(doi, api_key)
    
    if title:
        print(f"\nTitle: {title}")
        print(f"\nAbstract: {abstract}")
    else:
        print(abstract)

if __name__ == "__main__":
    main()

