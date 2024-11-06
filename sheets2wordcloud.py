#!/usr/bin/env python3

"""Read paper titles and abstracts from Google Sheet and generate wordclouds"""

import logging

from utils import get_sheet_papers, papers_to_wordclouds, parse_wordcloud_args


logger = logging.getLogger(__name__)


def sheets2wordcloud(
    by_theme: bool = False, force: bool = False, hal_only: bool = False, weight: int = 0
) -> None:
    """Read paper titles and abstracts from Google Sheet and generate wordclouds"""

    # Read papers from Google Sheet
    papers = get_sheet_papers()

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

    sheets2wordcloud(
        by_theme=args.by_theme,
        force=args.force,
        hal_only=args.hal_only,
        weight=args.weight,
    )
