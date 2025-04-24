#!/usr/bin/env python3

"""Read paper titles and abstracts from a Google Sheet and generate wordclouds"""

import argparse
import logging

from utils import get_sheet_papers, papers_to_wordclouds, wordcloud_argparser


logger = logging.getLogger(__name__)


def sheets2wordcloud(args: argparse.Namespace) -> None:
    """Read paper titles and abstracts from a Google Sheet and generate wordclouds"""

    # Read papers from Google Sheet
    papers = get_sheet_papers()

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
        description="Generate wordclouds from the titles and abstracts in a Google Sheet"
    )
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )

    sheets2wordcloud(args)
