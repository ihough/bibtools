#!/usr/bin/env python3

"""Read papers from Google Sheet, lookup bibliographic details, and write to CSV"""

import argparse
import csv
import logging
from pathlib import Path

from utils import get_sheet_papers, PAPER_TO_SHEET


logger = logging.getLogger(__name__)


def sheets2csv(force: bool = False, no_lookup: bool = False) -> None:
    """Read papers from Google Sheet, lookup bibliographic details, and write to CSV"""

    csv_path = Path("papers.csv")
    if csv_path.exists() and not force:
        raise ValueError(f"File exists: {csv_path}. Use --force to overwrite.")

    # Read deduplicated papers from the Google Sheet
    papers = get_sheet_papers()

    # Possibly crossref or hal.science for paper details and write to CSV
    if no_lookup:
        logger.info("Skipping lookup of missing details")
    else:
        logger.info("Looking up bibliographic details for %s papers", len(papers))
    with csv_path.open(mode="w", newline="", encoding="utf-8") as file:
        # Write header row
        writer = csv.writer(file, dialect="unix")
        writer.writerow(PAPER_TO_SHEET.keys())

        # Look up paper details and write to CSV, merging duplicates. Duplicates may
        # remain if a paper was listed once with only DOI and again with only HAL ID
        dois = {}
        hal_ids = {}
        n_duplicates = 0
        for i, paper in enumerate(papers):
            if not no_lookup and (i + 1) % 10 == 0:
                logger.info("[%s of %s]", i + 1, len(papers))

            # Merge duplicates
            if paper.doi in dois or paper.hal_id in hal_ids:
                # Find the previous occurence of the paper and update the lister
                original = dois[paper.doi] if paper.doi in dois else hal_ids[paper.hal_id]
                logger.info("Skipping %s (already added by %s)", paper, original.lister)
                original.lister += f" + {paper.lister}"
                n_duplicates += 1
                continue

            # Possibly lookup bibliogrpahic details
            if not no_lookup:
                paper.lookup_details()

            # Write details to CSV
            writer.writerow([getattr(paper, attr) for attr in PAPER_TO_SHEET])

            # Remember DOI and HAL ID for deduplication
            if paper.has_doi():
                dois[paper.doi] = paper
            if paper.has_hal_id():
                hal_ids[paper.hal_id] = paper

    # Report number of duplicates removed
    if n_duplicates > 0:
        logger.info("Merged %s duplicates", n_duplicates)

    logger.info("Paper details written to %s", csv_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Read papers from the Google Sheet, look up bibliographic details and"
        + " abstracts from Crossref, HAL, Semantic Scholar, and SCOPUS, and write to"
        + " papers.csv"
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="overwrite existing papers.csv file"
    )
    parser.add_argument(
        "--no-lookup", action="store_true", help="do not look up missing details"
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

    sheets2csv(force=args.force, no_lookup=args.no_lookup)
