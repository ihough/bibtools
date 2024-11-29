#!/usr/bin/env python3

"""Read paper titles and abstracts from a CSV and generate wordclouds"""

import logging

from utils import get_csv_papers, papers_to_wordclouds, parse_wordcloud_args


logger = logging.getLogger(__name__)


def csv2wordcloud(args: dict) -> None:
    """Read paper titles and abstracts from a CSV and generate wordclouds"""

    # Read papers from CSV
    papers = get_csv_papers()

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
    args = parse_wordcloud_args(
        description="Generate wordclouds from the titles and abstracts in papers.csv"
    )

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )

    csv2wordcloud(args)
