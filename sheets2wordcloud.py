#!/usr/bin/env python3

"""Read paper titles and abstracts from Google Sheet and generate wordclouds"""

import logging

from utils import get_sheet_papers, papers_to_wordclouds, parse_wordcloud_args


logger = logging.getLogger(__name__)


def sheets2wordcloud(args: dict) -> None:
    """Read paper titles and abstracts from Google Sheet and generate wordclouds"""

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
    )


if __name__ == "__main__":
    args = parse_wordcloud_args(
        description="Generate wordclouds from the titles and abstracts in the Google Sheet"
    )

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )

    sheets2wordcloud(args)
