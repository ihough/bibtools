#!/usr/bin/env python

"""Update Google Sheet with paper bibliographic details from a CSV"""

import argparse
import logging

from utils import read_csv, get_sheet


logger = logging.getLogger(__name__)


def csv2sheets():
    """Update Google Sheet with paper bibliographic details from a CSV"""

    # Read papers from the CSV
    papers = read_csv()
    if not any(papers):
        raise ValueError("No papers found in CSV")

    # Convert DOI and HAL ID to links
    papers["DOI link"] = papers["DOI"].apply(
        lambda doi: doi if doi == "no doi" else f"https://doi.org/{doi}"
    )
    papers["HAL link"] = papers["HAL ID"].apply(
        lambda id: id if id == "no hal id" else f"https://hal.science/{id}"
    )

    # Convert first/corresponding author from True/False to Yes/No
    papers["Is a team member the first or corresponding author?"] = papers[
        "Is a team member the first or corresponding author?"
    ].apply(lambda x: "Yes" if x else "No")

    # Clear the Google Sheet except the first two rows (titles + headers)
    sheet = get_sheet(write=True)
    titles = sheet.row_values(1)
    headers = sheet.row_values(2)
    sheet.clear()
    sheet.update(values=[titles, headers], range_name="A1")

    # Write paper details
    sheet.update(values=papers[headers].values.tolist(), range_name="A3")

    logger.info("Updated %s", sheet.url)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
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
