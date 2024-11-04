#!/usr/bin/env python

"""Read paper titles and abstracts from Google Sheet and generate wordclouds"""

import argparse
import logging

from utils import get_sheet_papers, papers_to_wordclouds


logger = logging.getLogger(__name__)


def parse_wordcloud_args() -> argparse.Namespace:
    """Parse command-line arguments for wordclouds"""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--by-theme",
        action="store_true",
        help="generate separate wordclouds for each research theme",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="overwrite existing wordcloud_*.png files",
    )
    parser.add_argument(
        "--hal-only",
        action="store_true",
        help="exclude papers that do not have a HAL ID",
    )
    parser.add_argument(
        "-w",
        "--weight",
        default=0,
        type=int,
        help="extra weight for papers where a team member is first or corresponding"
        + " author (default: 0 = no extra weight)",
    )

    return parser.parse_args()


def sheets2wordcloud(
    by_theme: bool = False, force: bool = False, hal_only: bool = False, weight: int = 0
) -> None:
    """Read paper titles and abstracts from Google Sheet and generate wordclouds"""

    # Read papers from Google Sheet
    papers = get_sheet_papers()
    if not any(papers):
        raise ValueError("No papers found in Google Sheet")

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
