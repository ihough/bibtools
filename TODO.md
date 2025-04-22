TODO
====

## Updates

* Implement requests backoff using `backoff` per https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/#optimize-your-requests-and-pay-attention-to-errors
* Make *2wordcloud.py fail fast by checking if output files exist before loading papers
* Use `html.unescape` to unescape response text e.g. "Environmental Science &amp; Technology" -> "Environmental Science & Technology"
* Allow specifying path to sheets key in `configuration.yml`
* Consider moving Google Sheets URL from `configuration.yml` to `keys/`


## New tools

* Tool to read BibTeX file and write to CSV


## New visualisations

* Author coauthorship network
  - colour / group authors by institute
  - filter by any team member

* Calendar / timeline of publications
  - Filter or color by researcher / theme

* Frequency chart of journals
  - Filter by researchers / theme
  - Annotate by open access / not

* Timeline showing evolution of titles / keywords

* Include other scientific output
  - datasets
  - code / software
  - peer reviews?

* Map of collaborations

* Impact (number of citations? over time?)

* Dash dashboard with plotly
