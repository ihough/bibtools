#!/usr/bin/env python

"""Read paper titles and abstracts from a CSV and generate wordclouds"""

import logging

from sheets2wordcloud import parse_wordcloud_args
from utils import get_csv_papers, papers_to_wordclouds


logger = logging.getLogger(__name__)


def csv2wordcloud(
    by_theme: bool = False, force: bool = False, hal_only: bool = False, weight: int = 0
) -> None:
    """Read paper titles and abstracts from a CSV and generate wordclouds"""

    # Read papers from CSV
    papers = get_csv_papers()
    if not any(papers):
        raise ValueError("No papers found in CSV")

    # Generate wordclouds from titles and abstracts
    papers_to_wordclouds(
        papers, by_theme=by_theme, force=force, hal_only=hal_only, weight=weight
    )


if __name__ == "__main__":
    args = parse_wordcloud_args()

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )

    csv2wordcloud(
        by_theme=args.by_theme,
        force=args.force,
        hal_only=args.hal_only,
        weight=args.weight,
    )
