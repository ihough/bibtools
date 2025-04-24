#!/usr/bin/env python3

"""Read references from a text file, look up DOI and details, and write to a CSV file"""

import argparse
import csv
import logging
from pathlib import Path

from utils import get_txt_references


logger = logging.getLogger(__name__)


def txt2csv(txt_path: Path, csv_path: Path, force: bool = False) -> None:
    """Read references from a text file, lookup DOI and details, and write to a CSV

    Details are from crossref.org

    Args:
        txt_path: Path to text file listing papers (one per row)
        csv_path: Path to output CSV file
        force: Whether to overwrite existing `csv_path` (default: False)
    """

    # Check output path
    if csv_path.exists() and not force:
        raise ValueError(f"File exists: {csv_path}. Use --force to overwrite.")

    # Read the list of references
    references = get_txt_references(txt_path)

    if not any(references):
        logger.info("No references found in %s", txt_path)
        return None

    # Query crossref.org for paper details and write to CSV
    logger.info("Looking up bibliographic details for %s references", len(references))
    with csv_path.open(mode="w", newline="", encoding="utf-8") as file:
        # Write header row
        csv_headers = [
            "doi",
            "author",
            "year",
            "title",
            "journal",
            "volume",
            "issue",
            "page",
            "query",
            "score",
        ]
        writer = csv.writer(file, dialect="unix")
        writer.writerow(csv_headers)

        # Look up paper details and write to CSV
        # Don't merge duplicates b/c there may be mismatches
        for i, ref in enumerate(references):
            if (i + 1) % 10 == 0:
                logger.info("[%s of %s]", i + 1, len(references))

            ref.lookup_details()

            # Write details to CSV
            csv_attrs = ["text" if x == "query" else x for x in csv_headers]
            writer.writerow([getattr(ref, attr) for attr in csv_attrs])

    logger.info("Matched papers written to %s", csv_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Read references from a text file, look up DOI and details from"
        + " crossref.org, and write to a CSV file"
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="overwrite existing output CSV file"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="display DEBUG level messages"
    )
    parser.add_argument(
        "txt_path", type=Path, help="Path to text file listing references"
    )
    parser.add_argument(
        "csv_path",
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

    txt2csv(txt_path=args.txt_path, csv_path=args.csv_path, force=args.force)
