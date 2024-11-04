# bibtools

Tools for visualizing research publications.

* Read or update a Google Sheet listing papers
* Deduplicate papers based on DOI and HAL ID
* Look up bibliographic details and abstracts from [Crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/), [HAL](https://api.archives-ouvertes.fr/docs/search), [Semantic Scholar](https://api.semanticscholar.org/api-docs/), and [Scopus](https://dev.elsevier.com/documentation/AbstractRetrievalAPI.wadl)
* Create wordclouds from titles and abstracts


## Tools

* `sheets2csv`: read papers from a Google Sheet, look up bibliographic details and abstracts, and write to `papers.csv`

* `csv2sheets`: update a Google Sheet with bibliographic details and abstracts from `papers.csv`

* `sheets2wordcloud`: read paper titles and abstracts from a Google Sheet and generate wordclouds

* `csv2wordcloud`: read paper titles and abstracts from `papers.csv` and generate wordclouds

* `sheets2bib`: read papers from a Google Sheet, look up bibtex records, and write to `references.bib`


## Setup

#### Create a Google Cloud project

* Open the [Google Cloud Resource Manager](https://console.cloud.google.com/cloud-resource-manager)
* Click 'CREATE PROJECT' and follow the instructions
* Open the [Google Cloud Console](https://console.cloud.google.com/) and ensure your project is selected

#### Enable the Google Sheets API

* Open the [Google Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com) in the API library
* Click 'ENABLE'

#### Add a service account

* Open the [service accounts dashboard](https://console.cloud.google.com/iam-admin/serviceaccounts)
* Click 'CREATE SERVICE ACCOUNT' and follow the instructions. You don't need to grant the service account access to your project or grant users access to the service account.

#### Add a key to the service account

* On the [service accounts dashboard](https://console.cloud.google.com/iam-admin/serviceaccounts), click on the service account's email
* Click the 'KEYS' tab
* Click 'ADD KEY' > 'Create new key' and create a JSON key
* Move the json key file that is automatically downloaded to the `keys/` directory of this repository

#### Optional: configure a Scopus API key

Configuring a Scopus API key gives access to some abstracts that are not available from crossref, hal.science, and semantic scholar.

* Go to https://dev.elsevier.com/apikey/manage (you will need to sign in or create an account)
* Click 'Create API Key'
* Choose a label and agree to the API service agreement. Note that the agreement stipulates that "all right, title and interest in and to any derivative works based upon the Elsevier content remain with Elsevier and its suppliers". You do not need to agree to the provisions for text and datamining.
* Click 'Submit >'
* Copy the key and paste it into the file `keys/scopus_api_key`

#### Update `configuration.yml`

* Set the URL of the Google Sheet listing the publications. You must give the service account's email 'Viewer' access to this sheet or share it publicly ('Anyone with the link can view'). If you want to use the `csv2sheets` tool to update the sheet, you need to give the service account 'Editor' access or set 'Anyone with the link can edit' permissions for the public link.

* Optionally set the email to use for [polite Crossref queries](https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/#pick-the-right-service-level). This allows Crossref to contact you in the unlikely event that bibtools starts causing problems on their servers. If you don't configure an email, bibtools will try to use your git email (from `git config user.email`). If that fails, bibtools will use public crossref queries.


## Use cases

To look up bibliographic details for papers in the Google Sheet, use `sheets2csv.py`. This will save the details to `papers.csv`.

To update the Google Sheet with the bibliographic details in `papers.csv`, use `csv2sheets.py`.

To copy bibliographic details from the Google Sheet to `papers.csv` without looking up missing details, use `sheets2csv.py --no-lookup`

To generate wordclouds by research theme using only papers with a HAL ID, use `csv2wordcloud --by-theme --hal-only` or `sheets2wordcloud --by-theme --hal-only`.
