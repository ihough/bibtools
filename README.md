# bibtools

Tools for extracting information out of a list of papers.

## Usage

1. Create a [Google Cloud project](https://console.cloud.google.com/)
2. Enable the [Google Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com)
3. Add a [service account](https://console.cloud.google.com/apis/credentials)
4. Add a key to the service account
  - Go to the [service accounts dashboard](https://console.cloud.google.com/iam-admin/serviceaccounts/)
  - Click on the service account
  - Click on the 'KEYS' tab
  - Click on 'ADD KEY' - 'Create new key' and create a JSON key.
  - Move the json key file that is automatically downloaded to the `keys/` directory of this repository
5. Configure the tools
  - Edit `configuration.yml` and set the path to your key file and the Google Sheet with the list of papers. The sheet must be publicly shared ('Anyone with the link can access' permissions).
