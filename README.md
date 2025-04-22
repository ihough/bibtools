# bibtools

Tools for managing and visualizing a bibliography


## Usage

Run any tool with `-h` or `--help` to display help.

### Base tools

Generate wordclouds from the titles and abstracts in a CSV file:

```bash
python csv2wordcloud.py papers.csv
```

Read references (citations) from a text file, look up DOI and details from [Crossref](https://www.crossref.org/) and write to a CSV file (default: `references.csv`):

```bash
python txt2csv.py references.txt
```

> [!WARNING]
> The `txt2csv.py` script will likely output warnings about matches that may be less accurate. You **must** verify the correcteness of these matches in the output CSV.

Matching references to Crossref items is an inherently perfect process. We **highly recommend** inspecting the output CSV file to ensure **all** matches are correct. You can do this by comparing the `author`, `title`, `year`, and `journal` columns to the `query` column, which contains the original references from the input text file. The `score` column contains the match score.

For more on matching, see [Crossref's metadata matching blog series](https://www.crossref.org/categories/metadata-matching/).

### Google Sheets tools

> [!NOTE]
> Scripts with `sheets` in their name interact with Google Sheets. You must complete the [setup steps](#setup) below to configure API access to a Google Sheet before using these tools.

Update the configured Google Sheet with bibliographic details from a CSV file:

```bash
python csv2sheets.py papers.csv
```

Read papers from the configured Google Sheet, look up BibTeX from [Crossref](https://www.crossref.org/) and [HAL](https://hal.science), and write to a BibTeX file (default: `references.bib`):

```bash
python sheets2bib.py
```

Read papers from the configured Google Sheet, look up bibliographic details and abstracts from [Crossref](https://www.crossref.org/), [HAL](https://hal.science), [DataCite](https://datacite.org/), [Semantic Scholar](https://www.semanticscholar.org/), and [SCOPUS](https://www.elsevier.com/products/scopus), and write to a CSV file (default: `papers.csv`):

```bash
python sheets2csv.py
```

Copy bibliographic details from the configured Google Sheet to a CSV file (default: `papers.csv`) without looking up missing details:

```bash
python sheets2csv.py --no-lookup
```

Generate wordclouds from the titles and abstracts in the configured Google Sheet:

```bash
python sheets2wordcloud.py
```

### Further wordcloud examples

All wordcloud options are available for both CSV (`csv2wordcloud.py`) and Google Sheets (`sheets2wordcloud.py`) input.

Generate wordclouds from a CSV file, considering only unigrams (not common collocations):

```bash
python csv2wordcloud.py --unigrams papers.csv
```

Generate wordclouds from a CSV file, skipping any papers that do not have a HAL ID and making a separate wordcloud for each research theme (indicated by a CSV column):

```bash
python csv2wordcloud.py --hal-only --by-theme papers.csv
```

Generate wordclouds from the titles and abstracts in a CSV file, giving 3x weight to papers where a team member is first, corresponding, or last author (indicated by a CSV column), and setting the output size to 250 x 500 pixels:

```bash
python csv2wordcloud.py --weight 3 --height 250 --width 500 papers.csv
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

* Set the URL of the Google Sheet listing the publications. This step is only needed to use the scripts that interact with Google Sheets (all scripts with `sheets` in their name).

* Optionally set a contact email to include in the User-Agent header of API requests. This allows API providers to contact you if the bibtools scripts cause issues with their service. Currently, the header is only used for queries to [Crossref](https://www.crossref.org/), who routes queries with contact information to a less-congested ["polite" API pool](https://github.com/CrossRef/rest-api-doc#good-manners--more-reliable-service). If you don't configure an email, bibtools will try to use your git email (from `git config user.email`).

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

5. Move the JSON key file that was downloaded to the `keys/` directory of this repository and rename it so the filename starts with `google-sheets-key` e.g. `google-sheets-key_original-filename.json`

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
