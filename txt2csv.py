#!/usr/bin/env python3

"""Read references from a text file, look up DOI and details, and write to CSV"""

import argparse
import csv
import logging
from pathlib import Path

from utils import get_txt_references


logger = logging.getLogger(__name__)


def txt2csv(refs_path: Path, out_path: Path, force: bool = False) -> None:
    """Read references from a text file, lookup DOI and details, and write to CSV"""

    # Check output path
    if out_path.exists() and not force:
        raise ValueError(f"File exists: {out_path}. Use --force to overwrite.")

    # Read the list of references
    references = get_txt_references(refs_path)

    if not any(references):
        logger.info("No references found in %s", refs_path)
        return None

    # Query crossref.org for paper details and write to CSV
    logger.info("Looking up bibliographic details for %s references", len(references))
    with out_path.open(mode="w", newline="", encoding="utf-8") as file:
        # Write header row
        csv_columns = ["doi", "author", "year", "title", "journal", "query_text"]
        writer = csv.writer(file, dialect="unix")
        writer.writerow(csv_columns)

        # Look up paper details and write to CSV, merging duplicates
        dois = {}
        n_duplicates = 0
        for i, ref in enumerate(references):
            if (i + 1) % 10 == 0:
                logger.info("[%s of %s]", i + 1, len(references))

            ref.lookup_details()

            # Merge duplicates
            if ref.doi in dois:
                continue

            # Write details to CSV
            csv_attrs = [x if x != "query_text" else "text" for x in csv_columns]
            writer.writerow([getattr(ref, attr) for attr in csv_attrs])

            # Remember DOI for deduplication
            dois[ref.doi] = 1

    # Report number of duplicates removed
    if n_duplicates > 0:
        logger.info("Merged %s duplicates", n_duplicates)

    logger.info("Paper details written to %s", out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Read references from a text file, look up DOI and details from "
        + "Crossref, and write to a CSV file.\n\nNote: the text file must contain one "
        + "reference per row."
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="overwrite existing output CSV file"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="display DEBUG level messages"
    )
    parser.add_argument(
        "refs_path", type=Path, help="Path to text file listing references"
    )
    parser.add_argument(
        "out_path",
        nargs="?",
        default="references.csv",
        type=Path,
        help="Path to output CSV file (default: references.csv)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    txt2csv(refs_path=args.refs_path, out_path=args.out_path, force=args.force)
