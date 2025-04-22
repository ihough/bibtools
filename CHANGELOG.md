# Changelog

This file is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.0.3]

### Added

- `csv2bib.py`: read paper DOI / HAL IDs from CSV file and lookup BibTeX
- `csv2csv.py`: read paper DOI / HAL IDs from CSV file and lookup details (author, abstract, etc.)

## [0.0.2]

### Added

- `txt2csv.py`: matches references in a text file to Crossref records
- Cache API requests
- Use URL-encoded DOIs in API requests

### Changed

- Specify path to input and output files on command line
- Reorganize README
- Modify Google Sheet header columns

## [0.0.1]

### Added

- `csv2sheets.py`: reads bibliographic details from `papers.csv` and updates a Google Sheet
- `csv2wordcloud.py`: reads abstracts and titles from `papers.csv` and generates wordclouds
- `sheets2bib.py`: reads papers from a Google Sheet, looks up bibtex records, and writes to `references.bib`
- `sheets2csv.py`: reads papers from a Google Sheet, looks up bibliographic details, and writes to `papers.csv`
- `sheets2wordcloud.py`: reads abstracts and titles from a Google Sheet and generates wordclouds
