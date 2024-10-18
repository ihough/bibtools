#!/usr/bin/env python

import csv
import re
import logging
from pathlib import Path
from warnings import warn

import gspread
import requests
from google.oauth2.service_account import Credentials

from configure import CONFIG


logger = logging.getLogger(__name__)


def validate_layout(sheet: gspread.Worksheet) -> None:
    """Confirm the sheet has the expected layout

    Row 2 must contain column headers. Column B must contain DOIs.
    """

    b2 = sheet.get_values("B2")[0][0]
    if b2.lower().strip() != "doi link":
        msg = (
            "Unrecognized sheet layout."
            + "\nRow 2 should contain column headers and column B should contain DOIs."
            + f"\nCell B2 should contain 'DOI link'; got '{b2}'."
        )
        raise ValueError(msg)


def parse_doi_links(doi_links: list[str]) -> list[str]:
    """Standardize a list of DOI URLs

    Standardized format: https://doi.org/[doi]

    Recognized formats:
    * http[s]://[dx.]doi.org/<doi>
    * http[s]://doi-org.<subdomain>.grenet.fr/<doi>
    * http[s]://<domain and path>/doi/[full/]/<doi>
    * <doi>

    Warns if any unrecognized values
    """

    def _parse(url, patterns, repl):
        for pattern in patterns:
            if re.match(pattern, url):
                return re.sub(pattern, repl, url)

    doi_pattern = r"(10\.\d{4}.+)"
    patterns = [
        # doi.org/<doi>, dx.doi.org/<doi>
        r"^\s*https?:\/\/(?:dx\.)?doi\.org\/" + doi_pattern,
        # doi-org.*.grenet.fr/<doi>
        r"^\s*https?:\/\/doi-org\.[\w-]+\.grenet\.fr\/" + doi_pattern,
        # */doi/[full/]/<doi>
        r"^\s*https?:\/\/[\w\.]+\/doi\/(?:full\/)" + doi_pattern,
        # <doi>
        r"^\s*" + doi_pattern,
    ]
    repl = r"https://doi.org/\1"

    standardized = []
    unrecognized = []
    for url in doi_links:
        result = _parse(url, patterns, repl)
        if result is not None:
            standardized += [result]
        else:
            unrecognized += [url]

    if any(unrecognized):
        warn(f"Unrecognized DOI links: ({len(unrecognized)}):\n{unrecognized}")

    return standardized


def get_paper_details(doi) -> list[str]:
    """Look up a paper DOI and return first author's name + ORCID, title, and year"""

    url = f"https://api.crossref.org/works/{doi}"
    try:
        response = requests.get(url, timeout=10)
    except requests.exceptions.ReadTimeout as err:
        raise requests.exceptions.Timeout(f"Timed out getting {url}") from err

    if response.status_code == 200:
        data = response.json()
        title = data["message"].get("title", ["No title found"])[0]
        year = data["message"]["issued"]["date-parts"][0][0]
        authors = data["message"].get("author", [])

        # Get the first author's name, if available
        if any(authors):
            first_author = (
                authors[0].get("given", "No author found")
                + " "
                + authors[0].get("family", "").upper()
            )
            orcid = authors[0].get("ORCID", "No ORCID found")
        else:
            first_author = "No author found"
            orcid = "No ORCID found"

        return title, year, first_author, orcid
    else:
        return "DOI not found", "N/A", "N/A", "N/A"  # In case of invalid DOI or no data


def csv2sheets() -> None:
    """Read a list of papers from a Google Sheet and write to a CSV

    The CSV will have columns:
    * First Author
    * Year
    * DOI
    * Title
    """

    # Authenticate with the service account file
    creds = Credentials.from_service_account_file(
        CONFIG["service_account_key"], scopes=[CONFIG["scope_sheets_read"]]
    )
    client = gspread.authorize(creds)

    logger.info("Reading papers from Google Sheet %s", CONFIG['sheet_url'])

    # Load and validate the sheet
    sheet = client.open_by_url(CONFIG["sheet_url"]).sheet1
    validate_layout(sheet)

    # Read DOIs from the column labelled 'DOI link'
    headers = sheet.row_values(2)  # Column headers are on second row
    doi_col_idx = headers.index("DOI link") + 1  # Google Sheets indexes from 1
    doi_links = sheet.col_values(doi_col_idx)[2:]  # First to rows are headers

    # Standardize the DOI links, warning about any that could not be standardized
    doi_links = parse_doi_links(doi_links)

    # Extract DOIs from the standardized links
    dois = [s.split("doi.org/", 1)[1] for s in doi_links]

    logger.info("Querying Crossref for %s papers", len(dois))

    # Open a CSV file to write the data
    out_path = Path("papers.csv")
    if out_path.exists():
        warn(f"{out_path} exists, overwriting.")
    with open(out_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        # Write the header row
        writer.writerow(["First Author", "First Author ORCID", "Year", "DOI", "Title"])

        # Fetch title and year for each DOI and write to the CSV file
        for doi in dois:
            title, year, first_author, orcid = get_paper_details(doi)
            writer.writerow([first_author, orcid, year, doi, title])

    print(f"Papers list written to {out_path}")


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )
    csv2sheets()
