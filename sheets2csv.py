#!/usr/bin/env python3

"""Read papers from a Google Sheet, look up DOI and details, and write to a CSV"""

import argparse
import csv
import logging
from pathlib import Path

from utils import get_sheet_papers, PAPER_TO_SHEET


logger = logging.getLogger(__name__)


def sheets2csv(
    csv_path: Path,
    force: bool = False,
    lookup: bool = True,
    get_abstract: bool = True,
    get_hal_id=True,
) -> None:
    """Read papers from a Google Sheet, look up DOI and details, and write to a CSV

    Details are from Crossref and HAL. Abstracts are from Semantic Scholar and Scopus.

    Args:
        csv_path: Path to output CSV file
        force: Whether to overwrite existing `csv_path` (default: False)
        lookup: Whether to look up missing details (default: True)
        get_abstract: Whether to look up missing abstracts (default: True)
        get_hal_id: Whether to look up missing HAL ID (default: True)
    """

    if csv_path.exists() and not force:
        raise ValueError(f"File exists: {csv_path}. Use --force to overwrite.")

    papers = get_sheet_papers()
    if not any(papers):
        logger.info("No papers found in Google Sheet")
        return None

    if not lookup:
        logger.info("Skipping lookup of missing details")
    else:
        logger.info("Looking up bibliographic details for %s papers", len(papers))
    with csv_path.open(mode="w", newline="", encoding="utf-8") as file:
        # Write header row
        writer = csv.writer(file, dialect="unix")
        writer.writerow(PAPER_TO_SHEET.keys())

        # Look up paper details and write to CSV, merging duplicates. Duplicates may
        # remain if a paper was listed once with only DOI and again with only HAL ID.
        dois = {}
        hal_ids = {}
        n_duplicates = 0
        for i, paper in enumerate(papers):
            if lookup and (i + 1) % 10 == 0:
                logger.info("[%s of %s]", i + 1, len(papers))

            # Merge duplicates
            if paper.doi in dois or paper.hal_id in hal_ids:
                # Find the previous occurence of the paper and update the lister
                original = dois[paper.doi] if paper.doi in dois else hal_ids[paper.hal_id]
                logger.info("Skipping %s (already added by %s)", paper, original.lister)
                original.lister += f" + {paper.lister}"
                n_duplicates += 1
                continue

            # Get and write details
            if lookup:
                paper.lookup_details(get_hal_id=get_hal_id, get_abstract=get_abstract)
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
        description="Read papers from a Google Sheet, look up DOI and details, and write"
        + " to a CSV file",
        epilog="Bibliographic details from Crossref and HAL. Abstracts from Semantic"
        + " Scholar and SCOPUS.",
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="overwrite existing output CSV file"
    )
    parser.add_argument(
        "--no-abstract",
        action="store_false",
        help="do not look up abstracts",
        dest="get_abstract",
    )
    parser.add_argument(
        "--no-hal", action="store_false", help="do not look up HAL ID", dest="get_hal_id"
    )
    parser.add_argument(
        "--no-lookup",
        action="store_false",
        dest="lookup",
        help="Do not look up missing details",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="display DEBUG level messages"
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        default="papers.csv",
        type=Path,
        help="Path to output CSV file (default: papers.csv)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    sheets2csv(
        csv_path=args.csv_path,
        force=args.force,
        lookup=args.lookup,
        get_abstract=args.get_abstract,
        get_hal_id=args.get_hal_id,
    )
