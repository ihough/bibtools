#!/usr/bin/env python

"""Read papers from Google Sheet, lookup details, and write to BibTeX file"""

import argparse
import logging
from pathlib import Path

from utils import get_sheet_papers


logger = logging.getLogger(__name__)


def sheets2bib(force: bool = False) -> None:
    """Read papers from Google Sheet, lookup details, and write to BibTeX file"""

    bib_path = Path("references.bib")
    if bib_path.exists() and not force:
        raise ValueError(f"File exists: {bib_path}. Use --force to overwrite.")

    # Read deduplicated papers from the Google Sheet
    papers = get_sheet_papers()
    if not any(papers):
        raise ValueError("No papers found in Google Sheet")

    # Query crossref or hal.science for paper BibTeX and write to .bib file
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

            # Write BibTeX entry
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="overwrite existing references.bib file",
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

    sheets2bib(force=args.force)
