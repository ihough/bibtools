#!/usr/bin/env python3

"""Read paper titles and abstracts from a CSV and generate wordclouds"""

import argparse
import logging

from utils import get_csv_papers, papers_to_wordclouds, wordcloud_argparser

logger = logging.getLogger(__name__)


def csv2wordcloud(csv_path: str, args: argparse.Namespace) -> None:
    """Read paper titles and abstracts from a CSV and generate wordclouds"""

    # Read papers from CSV
    papers = get_csv_papers(csv_path)

    # Generate wordclouds from titles and abstracts
    papers_to_wordclouds(
        papers,
        by_theme=args.by_theme,
        force=args.force,
        hal_only=args.hal_only,
        weight=args.weight,
        height=args.height,
        width=args.width,
        collocations=not args.unigrams,
    )


if __name__ == "__main__":
    parser = wordcloud_argparser(
        description="Generate wordclouds from a CSV listing paper titles and abstracts"
    )
    parser.add_argument("csv_path", help="Path to CSV file listing papers")
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )

    csv_path = args.csv_path
    del args.csv_path
    csv2wordcloud(csv_path, args)
