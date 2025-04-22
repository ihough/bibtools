#!/usr/bin/env python3

"""Read papers from a Google Sheet, lookup details, and write to a BibTeX file"""

import argparse
import logging
from pathlib import Path

from utils import get_sheet_papers


logger = logging.getLogger(__name__)


def sheets2bib(bib_path: Path, force: bool = False) -> None:
    """Read papers from a Google Sheet, lookup details, and write to a BibTeX file

    BibTeX lookup uses crossref.org and hal.science

    Args:
        bib_path: Path to output BibTeX file
        force: Whether to overwrite existing `bib_path` (default: False)
    """

    if bib_path.exists() and not force:
        raise ValueError(f"File exists: {bib_path}. Use --force to overwrite.")

    # Read deduplicated papers from the Google Sheet
    papers = get_sheet_papers()

    if not any(papers):
        logger.info("No papers found in Google Sheet")
        return None

    # Query crossref or hal.science for paper BibTeX and write to output file
    # Duplicates may remain if paper was listed with only DOI and again with only HAL ID
    logger.info("Getting BibTeX for %s papers", len(papers))
    with bib_path.open(mode="w", encoding="utf-8") as file:
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

            # Get and write BibTeX entry
            file.write(paper.get_bibtex())
            file.write("\n\n")  # Add spacing between entries

            # Remember DOI and HAL ID for deduplication
            if paper.has_doi():
                dois.add(paper.doi)
            if paper.has_hal_id():
                hal_ids.add(paper.hal_id)

    # Report number of duplicates removed
    if n_duplicates > 0:
        logger.info("Skipped %s duplicates", n_duplicates)

    logger.info("BibTeX written to %s", bib_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Read paper DOIs / HAL IDs from a Google Sheet, look up details, and"
        + " write to a BibTeX file",
        epilog="Details are from Crossref and HAL",
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="overwrite existing output BibTeX file"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="display DEBUG level messages"
    )
    parser.add_argument(
        "bib_path",
        nargs="?",
        default="references.bib",
        type=Path,
        help="path to output BibTeX file (default: references.bib)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    sheets2bib(bib_path=args.bib_path, force=args.force)
