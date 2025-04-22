#!/usr/bin/env python3

"""Read papers from a CSV, look up DOI and details, and write to a new CSV"""

import argparse
import csv
import logging
from pathlib import Path

from utils import get_csv_papers


logger = logging.getLogger(__name__)


def csv2csv(
    in_path: Path,
    out_path: Path,
    force: bool = False,
    get_abstract=True,
    get_hal_id=True,
) -> None:
    """Read papers from a CSV, look up DOI and details, and write to a new CSV

    Details are from Crossref and HAL. Abstracts are from Semantic Scholar and Scopus.

    Args:
        in_path: Path to CSV file listing papers (one per row). Must have a 'doi' or
            'hal_id' column listing each paper's DOI or HAL ID.
        out_path: Path to output CSV file
        force: Whether to overwrite existing `out_path` (default: False)
        get_abstract: Whether to look up missing abstracts (default: True)
        get_hal_id: Whether to look up missing HAL ID (default: True)
    """

    if out_path.exists() and not force:
        raise ValueError(f"File exists: {out_path}. Use --force to overwrite.")

    papers = get_csv_papers(in_path)
    if not any(papers):
        logger.info("No papers found in %s", in_path)
        return None

    logger.info("Looking up bibliographic details for %s papers", len(papers))
    with out_path.open(mode="w", newline="", encoding="utf-8") as file:
        # Write header row
        csv_headers = ["doi", "author", "year", "title", "journal"]
        if get_abstract:
            csv_headers.append("abstract")
        if get_hal_id:
            csv_headers.insert(1, "hal_id")
        writer = csv.writer(file, dialect="unix")
        writer.writerow(csv_headers)

        # Look up paper details and write to new CSV, merging duplicates. Duplicates may
        # remain if a paper was listed once with only DOI and again with only HAL ID.
        dois = set()
        hal_ids = set()
        n_duplicates = 0
        for i, paper in enumerate(papers):
            if (i + 1) % 10 == 0:
                logger.info("[%s of %s]", i + 1, len(papers))

            # Merge duplicates
            if paper.doi in dois or paper.hal_id in hal_ids:
                logger.info("Skipping duplicate %s", paper)
                n_duplicates += 1
                continue

            # Get and write details
            paper.lookup_details(get_hal_id=get_hal_id, get_abstract=get_abstract)
            writer.writerow([getattr(paper, attr) for attr in csv_headers])

            # Remember DOI and HAL ID for deduplication
            if paper.has_doi():
                dois.add(paper.doi)
            if paper.has_hal_id():
                hal_ids.add(paper.hal_id)

    # Report number of duplicates removed
    if n_duplicates > 0:
        logger.info("Merged %s duplicates", n_duplicates)

    logger.info("Paper details written to %s", out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Read papers from a CSV, look up details, and write to a new CSV",
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
        "-v", "--verbose", action="store_true", help="display DEBUG level messages"
    )
    parser.add_argument(
        "in_path",
        help="path to CSV file listing papers. Each paper must have a DOI or HAL ID. Use"
        + "txt2csv.py if you need to look up DOIs for a list of references.",
    )
    parser.add_argument(
        "out_path",
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

    csv2csv(
        in_path=args.in_path,
        out_path=args.out_path,
        force=args.force,
        get_abstract=args.get_abstract,
        get_hal_id=args.get_hal_id,
    )
