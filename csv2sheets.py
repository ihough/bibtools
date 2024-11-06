#!/usr/bin/env python3

"""Update Google Sheet with paper bibliographic details from a CSV"""

import argparse
import logging

from utils import read_csv, get_sheet, PAPER_TO_SHEET


logger = logging.getLogger(__name__)


def csv2sheets():
    """Update Google Sheet with paper bibliographic details from a CSV"""

    # Read papers from the CSV
    papers_df = read_csv()

    # Convert DOI and HAL ID to links
    papers_df["doi"] = papers_df["doi"].apply(
        lambda doi: doi if doi == "no doi" else f"https://doi.org/{doi}"
    )
    papers_df["hal_id"] = papers_df["hal_id"].apply(
        lambda hal: hal if hal == "no hal id" else f"https://hal.science/{hal}"
    )

    # Convert first/corresponding author is team member from True/False to Yes/No
    papers_df["is_main"] = papers_df["is_main"].apply(lambda x: "Yes" if x else "No")

    # Rename columns to match Google Sheet headers
    papers_df = papers_df.rename(columns=PAPER_TO_SHEET)

    # Clear the Google Sheet except the first two rows (titles + headers)
    sheet = get_sheet(write=True)
    titles = sheet.row_values(1)
    headers = sheet.row_values(2)
    sheet.clear()
    sheet.update(values=[titles, headers], range_name="A1")

    # Write paper details
    sheet.update(values=papers_df[headers].values.tolist(), range_name="A3")

    logger.info("Updated Google Sheet with paper details")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update the Google Sheet with bibliographic details from papers.csv"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="display DEBUG level messages"
    )
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    csv2sheets()
