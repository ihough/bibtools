"""Models and helper utilities"""

import logging
import re
import string
from dataclasses import dataclass, field
from pathlib import Path
from warnings import warn

import argparse
import gspread
import pandas as pd
import requests
from google.oauth2.service_account import Credentials
from wordcloud import STOPWORDS, WordCloud

from configure import Configure

logger = logging.getLogger(__name__)

CONFIG = Configure()

# Mapping of Paper attributes / CSV headers to Google Sheet headers
PAPER_TO_SHEET = {
    "lister": "Team member listing the paper / HDR / thesis / book / chapter / other",
    "doi": "DOI link",
    "hal_id": "HAL link",
    "is_main": "Is a team member the first or corresponding author?",
    "theme": "Theme",
    "note": "Note",
    "title": "Title",
    "author": "First Author",
    "year": "Year",
    "journal": "Journal",
    "orcid": "First Author ORCID",
    "abstract": "Abstract",
}


@dataclass(kw_only=True)
class Paper:
    """Class to represent a scientific publication

    Args:
        doi: The paper's DOI. A paper must have a DOI or HAL ID. May be a link e.g.
            https://doi.org/10.1000/182. Set to 'no doi' the paper has no DOI.
        hal_id: The paper's HAL ID. A paper must have a HAL ID or DOI. May be a link e.g.
            https://hal.science/hal-00000001v1. Set to 'no hal id' if paper has no HAL ID.
        author: The paper's first author (default: None)
        year: The paper's publication year (default: None)
        is_main: Whether a team member is first or corresponding author (default: False).
            Values 'true', 'yes', 'y', and 'oui' will be interpreted as True.
        theme: Can be used to group papers by research theme (default: None)
        lister: The team member that listed the paper (default: None)
        note: Additional information (default: None)
        title: The paper's title (default: None)
        journal: The paper's journal (default: None)
        orcid: The first author's ORCID (default: None)
        abstract: The paper's abstract (default: None)
    """

    doi: str | None = None
    hal_id: str | None = None
    author: str | None = None
    year: int | None = None
    is_main: bool | str = False
    theme: int | None = None
    lister: str | None = field(repr=False, default=None)
    note: str | None = field(repr=False, default=None)
    title: str | None = field(repr=False, default=None)
    journal: str | None = field(repr=False, default=None)
    orcid: str | None = field(repr=False, default=None)
    abstract: str | None = field(repr=False, default=None)
    _rate_limit: int = field(init=False, repr=False, default=50)

    def __post_init__(self) -> None:
        self.doi = self.parse_doi(self.doi)
        self.hal_id = self.parse_hal_id(self.hal_id)
        if not self.has_doi() and not self.has_hal_id():
            raise ValueError("Paper must have DOI or HAL ID; got neither.")

        self.is_main = str(self.is_main).strip().lower() in ["true", "yes", "y", "oui"]

    def _get(self, url: str, headers: str = None, timeout: int = 10) -> requests.Response:
        """GET a url and raise if request times out or status != 200"""

        try:
            return requests.get(url, headers=headers, timeout=timeout)
        except requests.exceptions.ReadTimeout as err:
            raise requests.exceptions.Timeout(f"Timed out querying {url}") from err

    def crossref_headers(self) -> dict | None:
        """Possibly return User-Agent header for polite crossref queries"""

        if CONFIG.crossref_email is not None:
            return {"User-Agent": f"bibtools/0.0.1 (mailto:{CONFIG.crossref_email})"}

        return None

    def doi_link(self) -> str | None:
        """Return the DOI link e.g. https://doi.org/10.1000/182"""

        if self.has_doi():
            return f"https://doi.org/{self.doi}"
        return None

    def get_abstract_scopus(self) -> str:
        """Query Scopus for paper abstract

        Only used if abstract not found on crossref, hal.science, or semantic scholar.
        Note that Elsevier retains "all right, title and interest in and to any derivative
        works based upon" scopus abstracts.
        """

        # Skip if no API key
        if CONFIG.scopus_key is None:
            return None

        url = (
            f"https://api.elsevier.com/content/article/doi/{self.doi}"
            + f"?apiKey={CONFIG.scopus_key}&field=dc:description"
        )
        headers = {"Accept": "application/json"}
        response = self._get(url, headers)

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            raise ValueError(f"Error: status {response.status_code} from {url}")

        data = response.json()["full-text-retrieval-response"]["coredata"]
        abstract = data["dc:description"]

        return re.sub(r"\s+", " ", abstract).strip()

    def get_abstract_semanticscholar(self) -> str | None:
        """Query Semantic Scholar for paper abstract

        Only used if abstract not found on crossref or hal.science
        """

        url = (
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{self.doi}"
            + "?fields=abstract"
        )
        response = self._get(url)

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            raise ValueError(f"Error: status {response.status_code} from {url}")

        abstract = response.json()["abstract"]
        if abstract is not None:
            return re.sub(r"\s+", " ", abstract).strip()

        return None

    def get_bibtex(self) -> str:
        """Return BibTeX entry for paper"""

        # If DOI is missing, try to get it from hal.science
        if self.doi is None:
            self.doi = self.get_details_hal()["doi"]

        # Prefer DOI-based BibTeX from crossref
        if self.has_doi():
            return self.get_bibtex_crossref()

        # Fall back on HAL ID-based BibTeX from hal.science
        return self.get_bibtex_hal()

    def get_bibtex_crossref(self) -> str:
        """Query crossref.org with the paper's DOI and return a BibTeX entry"""

        url = f"https://api.crossref.org/works/{self.doi}/transform"
        headers = {"Accept": "application/x-bibtex"}
        if self.crossref_headers() is not None:
            headers |= self.crossref_headers()
        response = self._get(url, headers=headers)

        # If not found, return an error comment in BibTeX format
        if response.status_code == 404:
            return f"% Error: No BibTeX found for doi:{self.doi}"

        if response.status_code != 200:
            raise ValueError(f"Error: status {response.status_code} from {url}")

        return response.text.strip()

    def get_bibtex_hal(self) -> str:
        """Query hal.science with the paper's HAL ID and return a BibTeX entry"""

        url = (
            f"https://api.archives-ouvertes.fr/search/?q=halId_id:{self.hal_id}&wt=bibtex"
        )
        response = self._get(url)

        if response.status_code != 200:
            raise ValueError(f"Error: status {response.status_code} from {url}")

        data = response.text.strip()

        # If not found, return an error comment in BibTeX format
        if data == "":
            return f"% Error: No BibTeX found for hal:{self.hal_id}"

        # Confirm that only 1 entry was returned
        n_entries = data.count(r"HAL_ID =")
        if n_entries != 1:
            raise ValueError(f"Found {n_entries} HAL records matching hal:{self.hal_id}")

        return data

    def get_details_crossref(self) -> dict:
        """Query crossref.org with the paper's DOI and return bibliographic details

        Note: could query doi.org using content negotiation (e.g. set "Accept" header to
        "application/vnd.citationstyles.csl+json") but this just redirects to crossref.
        See https://citation.crosscite.org/docs.html for details.
        """

        url = f"https://api.crossref.org/works/{self.doi}"
        response = self._get(url, headers=self.crossref_headers())

        # Return if DOI not found
        if response.status_code == 404:
            return {}

        if response.status_code != 200:
            raise ValueError(f"Error: status {response.status_code} from {url}")

        # Monitor the API rate limit
        rate_limit = int(
            int(response.headers["x-ratelimit-limit"])
            / int(response.headers["x-ratelimit-interval"][:-1])
        )
        if rate_limit != self._rate_limit:
            warn(
                f"Crossref API rate limit changed from {self._rate_limit}/sec to"
                + f" {rate_limit}/sec."
            )
            self._rate_limit = rate_limit

        data = response.json()["message"]
        details = {
            "doi": data["DOI"],
            "title": re.sub(r"\s+", " ", data["title"][0]).strip(),
            "year": data["issued"]["date-parts"][0][0],
        }
        if any(data.get("author", [])):
            author = data["author"][0]
            details["author"] = author["given"] + " " + author["family"].upper()
            if author.get("ORCID") is not None:
                details["orcid"] = author.get("ORCID")
        if any(data.get("container-title", [])):
            details["journal"] = data["container-title"][0]
        abstract = data.get("abstract")
        if abstract is not None:
            details["abstract"] = re.sub(r"\s+", " ", abstract).strip()

        return details

    def get_details_datacite(self) -> dict:
        """Query datacite.org with a DOI and return details"""

        url = f"https://api.datacite.org/dois/{self.doi}"
        response = self._get(url, headers=self.crossref_headers())

        # Return if DOI not found
        if response.status_code == 404:
            return {}

        if response.status_code != 200:
            raise ValueError(f"Error: status {response.status_code} from {url}")

        data = response.json()["data"]["attributes"]
        author = data["creators"][0]
        details = {
            "doi": data["doi"],
            "author": author["givenName"] + " " + author["familyName"].upper(),
            "title": re.sub(r"\s+", " ", data["titles"][0]["title"]).strip(),
            "year": data["publicationYear"],
        }
        abstract = None
        if any(data.get("descriptions")):
            for desc in data["descriptions"]:
                if desc["descriptionType"] == "Abstract":
                    abstract = desc["description"]
                    break
        if abstract is not None:
            details["abstract"] = re.sub(r"\s+", " ", abstract).strip()

        return details

    def get_details_hal(self) -> dict:
        """Query hal.science with paper HAL ID or DOI and return bibliographic details"""

        # Notes:
        # * When querying by HAL ID, use "q={self.hal_id}" b/c records can have multiple
        #   HAL IDs. For example, 'hal-04538966' and 'insu-04707980' identify the same
        #   record. Searching with "q=halId_id:{self.hal_id}" searches only the primary ID
        #   field, so a search for "q=halId_id:insu-04707980" will return no matches.
        # * Do not get author ORCID (authORCIDIdExt_s) because it does not include entries
        #   for authors whose ORCID is unknown. This means that the first ORCID may not
        #   belong to the first author.
        query = self.hal_id if self.has_hal_id() else f"doiId_id:{self.doi}"
        url = (
            f"https://api.archives-ouvertes.fr/search/?q={query}&fl=doiId_s,halId_s"
            + ",authFirstName_s,authLastName_s,producedDateY_i,title_s,journalTitle_s"
            + ",abstract_s"
        )
        response = self._get(url)

        if response.status_code != 200:
            raise ValueError(f"Error: status {response.status_code} from {url}")

        data = response.json()["response"]

        # Return empty dict if no record found
        if data["numFound"] == 0:
            return {}

        if data["numFound"] != 1:
            raise ValueError(f"Found {data["numFound"]} HAL records matching {query}")

        data = data["docs"][0]
        author = data["authFirstName_s"][0] + " " + data["authLastName_s"][0].upper()
        details = {
            "doi": data.get("doiId_s", "no doi"),
            "hal_id": data["halId_s"],
            "author": author,
            "title": data["title_s"][0],
            "year": data["producedDateY_i"],
        }
        if data.get("journalTitle_s") is not None:
            details["journal"] = data["journalTitle_s"]
        abstract = data.get("abstract_s", [None])[0]
        if abstract is not None:
            details["abstract"] = re.sub(r"\s+", " ", abstract)

        return details

    def hal_link(self) -> str | None:
        """Return the HAL link e.g. https://hal.science/hal-00000001"""

        if self.has_hal_id():
            return f"https://hal.science/{self.hal_id}"
        return None

    def has_doi(self) -> bool:
        """Returns True if paper has a DOI"""

        return self.doi is not None and self.doi.lower() != "no doi"

    def has_hal_id(self) -> bool:
        """Returns True if paper has a HAL ID"""

        return self.hal_id is not None and self.hal_id.lower() != "no hal id"

    def lookup_details(self) -> None:
        """Get and set bibliographic details"""

        # Look up details from hal.science (searches by DOI or HAL ID)
        info = self.get_details_hal()

        # Set HAL ID if HAL record was found. HAL records may have multiple IDs, so this
        # ensures that the 'main' ID is used. It also sets the HAL ID if it was missing
        # and the record was found by DOI.
        self.hal_id = info.get("hal_id", "no hal id")

        # Set DOI if it was missing or paper was marked as having no DOI
        if not self.has_doi() and "doi" in info:
            self.doi = info["doi"]

        # If paper has a DOI, look up details from crossref
        if self.has_doi():
            info |= self.get_details_crossref()  # prefer info from crossref

            # If no info, query datacite (in case the 'paper' is a dataset or software)
            if not any(info):
                info = self.get_details_datacite()

            # If abstract is missing, try to get it from semantic scholar
            if info.get("abstract") is None:
                info["abstract"] = self.get_abstract_semanticscholar()

            # If abstract still missing, try to get it from Scopus
            if info.get("abstract") is None:
                info["abstract"] = self.get_abstract_scopus()

        # Raise if could not find bibliographic details
        if not any(info):
            raise ValueError(f"No HAL, Crossref, or DataCite record for {self}")

        # Set bibliographic attributes
        self.author = info.get("author")
        self.orcid = info.get("orcid")
        self.title = info["title"]
        self.year = info["year"]
        self.journal = info.get("journal")
        self.abstract = info.get("abstract")

    def parse_doi(self, doi: str) -> str | None:
        """Parse a DOI or DOI link and return the standardized DOI

        Recognized formats:
            - <DOI>
            - http[s]://[dx.]doi.org/<DOI>
            - http[s]://doi-org.<subdomain>.grenet.fr/<DOI>
            - http[s]://<domain and path>/doi/[full/]/<DOI>
            - 'no doi'
        """

        if doi is None or doi.strip() == "":
            return None
        doi = doi.lower().strip()

        doi_pattern = r"(10\.\d{4}.+)"
        patterns = [
            # <DOI>
            r"^" + doi_pattern,
            # [dx.]doi.org/<DOI>
            r"^https?:\/\/(?:dx\.)?doi\.org\/" + doi_pattern,
            # doi-org.*.grenet.fr/<DOI>
            r"^https?:\/\/doi-org\.[\w-]+\.grenet\.fr\/" + doi_pattern,
            # */doi/[full/]/<DOI>
            r"^https?:\/\/[\w\.]+\/doi\/(?:full\/)" + doi_pattern,
            # Paper has no DOI
            r"^(no doi)$",
        ]
        for pattern in patterns:
            if re.match(pattern, doi):
                doi = re.sub(pattern, r"\1", doi)
                return doi

        raise ValueError(f"Unrecognized DOI: {doi}")

    def parse_hal_id(self, hal_id: str) -> str | None:
        """Parse a HAL ID or link and return the standardized HAL ID

        Recognized formats:
            - <HAL ID>v<version>
            - http[s]://[<institute>.]/<HAL ID>v<version>
            - 'no hal id'
        """

        if hal_id is None or hal_id.strip() == "":
            return None
        hal_id = hal_id.lower().strip()

        id_pattern = r"([\w-]+?-\d+).*"
        patterns = [
            # <HAL ID>
            r"^" + id_pattern,
            # [<institute>.]hal.science/<HAL ID>
            r"^https?:\/\/(?:\w+\.)?hal\.science\/" + id_pattern,
            # Paper has no HAL ID
            r"^(no hal id)$",
        ]
        for pattern in patterns:
            if re.match(pattern, hal_id):
                return re.sub(pattern, r"\1", hal_id)

        raise ValueError(f"Unrecognized HAL ID: {hal_id}")


def generate_wordcloud(
    text: str,
    width: int = 1000,
    height: int = 500,
    max_words: int = 200,
    min_font_size: int = 8,
    stopwords: set | None = None,
    random_state: int = 42,
    background_color: str = "white",
    regexp: str = r"\w[\w\.\-']+",
    min_word_length: int = 2,
    collocations: bool = True,
    collocation_threshold: int = 10,
) -> WordCloud:
    """Generate a wordcloud from text"""

    if stopwords is None:
        # fmt: off
        stopwords = STOPWORDS.union(
            ["abstract", "due", "overall", "study", "well", "one", "two", "three", "four",
             "five"]
        )
        # fmt: on

    # Preprocess text
    # * Lowercase
    # * Remove jats tags e.g. <jats:p>
    # * Remove French accents
    # * Standardize some spellings (e.g. 'factorization' -> 'factorisation')
    # * Fix some typos (e.g. 'pm 2:5' -> 'pm2.5')
    # * Remove formatting e.g. 'pm&amp;lt;sub&amp;gt;10&amp;lt;/sub&amp;gt;' -> 'pm10'
    # * Replace escaped characters e.g. '&amp;amp;' -> '&'
    # * Remove period from end of words e.g. 'end.' -> 'end'
    text = text.lower()
    text = re.sub("</?jats.+?>", " ", text, flags=re.IGNORECASE)
    text = text.translate(str.maketrans("àâèéêëîïôùûü", "aaeeeeiiouuu"))
    text = text.translate(str.maketrans("ÀÂÈÉÊËÎÏÔÙÛÜ", "AAEEEEIIOUUU"))
    text = re.sub(r"zation\b", "sation", text, flags=re.IGNORECASE)
    text = re.sub(r"\bpm\s+2[\.:]5\b", "PM2.5", text, flags=re.IGNORECASE)
    text = re.sub(r"\bpm\s+10\b", "PM10", text, flags=re.IGNORECASE)
    text = re.sub(r"(\w+)\.(\s|$)", r"\1\2", text)
    text = re.sub(r"&amp;lt;\/?(i|sub|sup)&amp;gt;", "", text)
    text = re.sub("(&amp;)?amp;", "&", text, flags=re.IGNORECASE)
    text = re.sub("(&amp;)?gt;", ">", text, flags=re.IGNORECASE)
    text = re.sub("(&amp;)?lt;", "<", text, flags=re.IGNORECASE)

    cloud = WordCloud(
        width=width,
        height=height,
        max_words=max_words,
        min_font_size=min_font_size,
        stopwords=stopwords,
        random_state=random_state,
        background_color=background_color,
        regexp=regexp,
        min_word_length=min_word_length,
        collocations=collocations,
        collocation_threshold=collocation_threshold,
    )
    cloud.generate(text)

    # from matplotlib import pyplot as plt
    # plt.figure(figsize=(10, 5))
    # plt.imshow(cloud, interpolation="bilinear")
    # plt.axis("off")
    # plt.show()

    return cloud


def get_sheet(write: bool = False) -> gspread.Worksheet:
    """Load the Google Sheet

    Args:
        write: Whether to open with write access (default: False = read-only)
    """

    # Authenticate the Google Sheets API client
    scope = "https://www.googleapis.com/auth/spreadsheets.readonly"
    if write:
        scope = "https://www.googleapis.com/auth/spreadsheets"
    creds = Credentials.from_service_account_file(CONFIG.sheet_key, scopes=[scope])
    client = gspread.authorize(creds)

    # Load the sheet
    logger.info("Opening Google Sheet %s", CONFIG.sheet_url)
    sheet = client.open_by_url(CONFIG.sheet_url).sheet1

    # Confirm the sheet has the expected layout
    validate_sheet(sheet)

    return sheet


def get_csv_papers() -> list[Paper]:
    """Read papers from a CSV"""

    papers_df = read_csv()
    papers = [Paper(**row) for _, row in papers_df.iterrows()]

    return papers


def get_sheet_papers() -> list[Paper]:
    """Read papers from the Google Sheet, deduplicate, and return"""

    sheet = get_sheet()

    logger.info("Reading papers from Google Sheet")
    dois = {}
    hal_ids = {}
    n_duplicates = 0
    papers = []

    for i, record in enumerate(
        sheet.get_all_records(
            head=2, expected_headers=PAPER_TO_SHEET.values(), default_blank=None
        )
    ):
        kwargs = {k: record[v] for k, v in PAPER_TO_SHEET.items()}
        try:
            paper = Paper(**kwargs)
        except ValueError as err:
            raise ValueError(f"Could not parse paper from row {i + 3}: {record}") from err

        # Merge duplicates
        if paper.doi in dois or paper.hal_id in hal_ids:
            # Find the previous occurence of the paper and update the lister
            try:
                original = dois[paper.doi]
            except KeyError:
                original = hal_ids[paper.hal_id]
            logger.debug("Skipping %s (already added by %s)", paper, original.lister)
            if paper.lister != original.lister and any([original.lister, paper.lister]):
                paper.lister = " + ".join(
                    [x for x in [original.lister, paper.lister] if x is not None]
                )
            n_duplicates += 1
            continue
        papers.append(paper)

        # Remember DOI and HAL ID for deduplication
        if paper.has_doi():
            dois[paper.doi] = paper
        if paper.has_hal_id():
            hal_ids[paper.hal_id] = paper

    # Report number of duplicates removed
    if n_duplicates > 0:
        logger.info("Merged %s duplicates", n_duplicates)

    if not any(papers):
        raise ValueError(f"No papers found in Google Sheet {sheet.url}")

    return papers


def papers_to_wordclouds(
    papers: list[Paper],
    by_theme: bool = False,
    force: bool = False,
    hal_only: bool = False,
    weight: int = 1,
    width: int = 1000,
    height: int = 500,
) -> WordCloud:
    """Generate wordclouds from paper abstracts and titles"""

    def make_wordcloud(papers: list[Paper], fields: str | list[str], suffix: str) -> None:
        if isinstance(fields, str):
            fields = [fields]

        # Check output path
        out_path = Path(f"wordcloud_{'+'.join(fields)}{suffix}.png")
        if out_path.exists() and not force:
            raise ValueError(f"File exists: {out_path}. Use --force to overwrite")

        # Get field(s) from all papers
        text = []
        for field in fields:
            field_text = [getattr(p, field) for p in papers if getattr(p, field)]
            if len(field_text) != len(papers):
                n_skipped = len(papers) - len(field_text)
                warn(f"Skipped {n_skipped} papers with no {field}")

            # Possibly give extra weight when team member is first or corresping author
            if weight > 1:
                field_text += [
                    getattr(p, field) for p in papers if p.is_main and getattr(p, field)
                ] * (weight - 1)

            text += field_text

        # Generate and save wordcloud
        cloud = generate_wordcloud("\n".join(text), width=width, height=height)
        cloud.to_file(out_path)
        logger.info("Saved %s", out_path)

    # Possibly exclude papers with no HAL ID
    if hal_only:
        papers = [p for p in papers if p.has_hal_id()]
        if not any(papers):
            raise ValueError("No papers have HAL ID")

    # Possibly group papers by research theme
    groups = {}
    if by_theme:
        for paper in papers:
            theme = paper.theme if paper.theme else "none"
            if theme in groups:
                groups[theme].append(paper)
            else:
                groups[theme] = [paper]
    else:
        groups["all papers"] = papers

    for theme, theme_papers in groups.items():
        suffix = "" if theme == "all papers" else f"_theme-{theme}"
        make_wordcloud(theme_papers, fields="abstract", suffix=suffix)
        make_wordcloud(theme_papers, fields="title", suffix=suffix)
        make_wordcloud(theme_papers, fields=["abstract", "title"], suffix=suffix)


def parse_wordcloud_args(description: str | None = None) -> argparse.Namespace:
    """Parse command-line arguments for wordclouds"""

    parser = argparse.ArgumentParser(description=description)
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
    parser.add_argument("--height", default=500, type=int, help="output height (pixels)")
    parser.add_argument(
        "--weight",
        default=1,
        type=int,
        help="set this to an integer >1 to give extra weight to papers where a team"
        + "member is the first or corresponding author",
    )
    parser.add_argument("--width", default=1000, type=int, help="output width (pixels)")

    return parser.parse_args()


def read_csv(validate: bool = True) -> pd.DataFrame:
    """Read paper bibliographic details from papers.csv

    Args:
        validate: Whether to check the CSV layout (default: True)
    """

    # Read CSV
    csv_path = Path("papers.csv")
    logger.info("Reading %s", csv_path)
    papers_df = pd.read_csv(csv_path).replace({float("nan"): None})

    # Possibly confirm the CSV has the expected layout
    if validate:
        validate_csv(papers_df)

    if papers_df.shape[0] == 0:
        raise ValueError(f"No papers found in {csv_path}")

    return papers_df


def validate_csv(csv: pd.DataFrame) -> None:
    """Confirm CSV file has the expected layout"""

    for i, expected in enumerate(PAPER_TO_SHEET):
        if csv.columns[i].lower().strip() != expected.lower().strip():
            raise ValueError(
                "Unrecognized csv layout."
                + f" Column {i} header should be '{expected}'; got '{csv.columns[i]}'."
            )


def validate_sheet(sheet: gspread.Worksheet) -> None:
    """Confirm the Google Sheet has the expected layout"""

    header_row = 2
    headers = sheet.row_values(header_row)
    for i, expected in enumerate(PAPER_TO_SHEET.values()):
        actual = headers[i] if i < len(headers) else ""
        if actual.lower().strip() != expected.lower().strip():
            cell = string.ascii_uppercase[i] + str(header_row)
            raise ValueError(
                "Unrecognized sheet layout."
                + f" Cell {cell} should contain '{expected}'; got '{actual}'."
            )
