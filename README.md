# bibtools

Tools for visualizing research publications.

## Usage

Run any tool with `-h` or `--help` to display help.

Read papers from the Google Sheet, look up bibliographic details and abstracts from [Crossref](https://www.crossref.org/), [HAL](https://hal.science), [DataCite](https://datacite.org/), [Semantic Scholar](https://www.semanticscholar.org/), and [SCOPUS](https://www.elsevier.com/products/scopus), and write to `papers.csv`:

```bash
python sheets2csv.py
```

Copy bibliographic details from the Google Sheet to `papers.csv` without looking up missing details:

```bash
python sheets2csv.py --no-lookup
```

Update the Google Sheet with bibliographic details from `papers.csv`:

```bash
python csv2sheets.py
```

Generate wordclouds from the titles and abstracts in `papers.csv`, skipping any papers that do not have a HAL ID, and making a separate wordcloud for each research theme:

```bash
python csv2wordcloud.py --hal-only --by-theme
```

Generate wordclouds from the titles and abstracts in the Google Sheet, giving 3x weight to papers where a team member is first or corresponding author:

```bash
python sheets2wordcloud.py --weight 3
```

Read papers from the Google Sheet, look up BibTeX from [Crossref](https://www.crossref.org/) and [HAL](https://hal.science), and write to `references.bib`:

```bash
python sheets2bib.py
```

## Setup

### Install dependencies

Using [micromamba](https://mamba.readthedocs.io/en/latest/user_guide/micromamba.html):

```bash
micromamba create --file environment.yml
micromamba activate bibtools
```

Using a virtual environment:

```bash
python3 -m venv venv/
. venv/bin/activate
pip install .
```

### Update `configuration.yml`

* Set the URL of the Google Sheet listing the publications

* Optionally set the email to use for the [Crossref API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/#pick-the-right-service-level). This will allow bibtools to use crossref's "polite" API pool. Crossref will only use the email to contact you in the unlikely event that bibtools causes a problem on their servers. If you don't configure an email, bibtools will try to use your git email (from `git config user.email`). If that fails, bibtools will use crossref's "public" API pool which may be less reliable.

### Configure the Google Sheets API

For these tools to access the Google Sheet listing publications, you must set up a Google Cloud service account with an authentication key and API access:

1. Create a Google Cloud project

    * Open the [Google Cloud Resource Manager](https://console.cloud.google.com/cloud-resource-manager)
    * Click 'CREATE PROJECT' and follow the instructions
    * Open the [Google Cloud Console](https://console.cloud.google.com/) and ensure your project is selected

2. Enable the Google Sheets API

    * Open the [Google Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com) in the API library
    * Click 'ENABLE'

3.  Add a service account

    * Open the [service accounts dashboard](https://console.cloud.google.com/iam-admin/serviceaccounts)
    * Click 'CREATE SERVICE ACCOUNT' and follow the instructions. You don't need to grant the service account access to your project or grant users access to the service account.

4. Add a key to the service account

    * On the [service accounts dashboard](https://console.cloud.google.com/iam-admin/serviceaccounts), click on the service account's email
    * Click the 'KEYS' tab
    * Click 'ADD KEY' > 'Create new key'
    * Choose 'JSON' key type and click 'CREATE'. This will download a JSON key file.

5. Move the JSON key file that was downloaded to the `keys/` directory of this repository

6. Share the Google Sheet listing the papers with the service account

    * Open the Google Sheet and click "Share"
    * Enter the service account's email, choose 'Editor' from the dropdown, and click 'Share'. Alternatively, you can share the sheet publicly ('Anyone with the link'). You must choose the 'Editor' role to allow bibtools to modify the Google Sheet.

### Configure a Scopus API key (optional)

Configuring a Scopus API key gives access to some abstracts that are not available from Crossref, HAL, or Semantic Scholar.

* Go to https://dev.elsevier.com/apikey/manage (you will need to sign in or create an account)
* Click 'Create API Key'
* Choose a label and agree to the API service agreement. Note that the agreement stipulates that "all right, title and interest in and to any derivative works based upon the Elsevier content remain with Elsevier and its suppliers". You do not need to agree to the provisions for text and datamining.
* Click 'Submit'
* Copy the key and paste it into the file `keys/scopus_api_key`
