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
import requests_cache
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
    "is_main": "Is a team member the first or corresponding author (or last author)?",
    "theme": "Theme",
    "note": "Note",
    "title": "Title",
    "author": "First Author",
    "year": "Year",
    "journal": "Journal",
    "volume": "Volume",
    "issue": "Issue",
    "page": "Page",
    "orcid": "First Author ORCID",
    "abstract": "Abstract",
}

# Enable caching
requests_cache.install_cache("bibtools_cache", backend="sqlite")


@dataclass()
class Requester:
    """Parent class for shared methods relating to issuing REST API requests"""

    rate_limit: int = field(init=False, repr=False, default=50)

    def check_ratelimit(self, response: requests.Response) -> int:
        """Warn if the response rate limit has changed"""

        limit = int(
            int(response.headers.get("x-ratelimit-limit", self.rate_limit))
            / int(response.headers.get("x-ratelimit-interval", "1s")[:-1])
        )
        if limit != self.rate_limit:
            warn(f"API rate limit changed from {self.rate_limit}/sec to {limit}/sec")
            self.rate_limit = limit

    def get(
        self, url: str, headers: dict | None = None, timeout: int = 10
    ) -> requests.Response:
        """GET a url and raise if request times out or status != 200"""

        # Add User-Agent header with contact email, if configured, to Crossref queries
        # This routes queries to Crossref's 'polite' API pool. For details see
        # https://github.com/CrossRef/rest-api-doc#good-manners--more-reliable-service
        if "api.crossref.org" in url:
            if headers is None:
                headers = self.user_agent_header()
            elif self.user_agent_header() is not None:
                headers |= self.user_agent_header()

        try:
            return requests.get(url, headers=headers, timeout=timeout)
        except requests.exceptions.ReadTimeout as err:
            raise requests.exceptions.Timeout(f"Timed out querying {url}") from err

    def user_agent_header(self) -> dict | None:
        """Return User-Agent header with contact email, if configured"""

        if CONFIG.contact_email is not None:
            return {"User-Agent": f"bibtools/0.0.1 (mailto:{CONFIG.contact_email})"}


@dataclass()
class Reference(Requester):
    """Class to represent a reference identifying a scientific publication

    Args:
        text: Text of the reference
    """

    text: str
    doi: str | None = None
    citekey: str | None = None
    author: str | None = None
    year: str | None = None
    title: str | None = None
    journal: str | None = None
    score: float | None = None

    def __repr__(self) -> str:
        if self.score is not None:
            return (
                "Reference(\n"
                + f"  citekey: '{self.citekey}'\n"
                + f"  score: {round(self.score, 1)}\n"
                + f"  doi: '{self.doi}'\n"
                + f"  title: '{self.title}'\n"
                + f"  journal: '{self.journal}'\n"
                + ")"
            )
        return f"Reference(text='{self.text}')"

    def encode_text(self) -> str:
        """Return the URL-encoded text"""

        return requests.utils.quote(self.text)

    def format_author(self, item: dict) -> str:
        """Return last name, given names for first author of a crossref item"""

        author = item.get("author", [{}])[0]
        family = author.get("family")
        given = author.get("given")
        if not any([family, given]):
            msg = "\n  ".join(
                [
                    "Match has no author:",
                    f"Query: {self.text}",
                    f"Match:  {self.format_crossref_item(item)} {item['DOI']}",
                ]
            )
            warn(msg)
            return None

        return ", ".join([x for x in [family, given] if x is not None])

    def format_citekey(self, item: dict) -> str:
        """Return a citation key for a crossref item"""

        author = item.get("author", [{}])[0]
        author = author.get("family", "NoAuthor")
        year = item["issued"]["date-parts"][0][0]
        if year is None:
            year = "NoYear"

        return author + str(year)

    def format_crossref_item(self, item: dict) -> str:
        """Return a text summary of a crossref item"""

        return " ".join([self.format_citekey(item), item["title"][0]])

    def lookup_details(self) -> None:
        """Get and set bibliographic details from crossref.org"""

        # Limit to 2 responses as suggested by
        # https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/
        url = (
            f'https://api.crossref.org/works?query.bibliographic="{self.encode_text()}"'
            + "&rows=2&select=score,DOI,author,issued,title,container-title,volume,issue"
            + ",page,type"
        )
        response = self.get(url, timeout=20)

        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise ValueError(f"Error: status {response.status_code} from {url}")

        # Monitor the API rate limit
        self.check_ratelimit(response)

        # Check the response
        items = response.json()["message"]["items"]
        if not any(items):
            warn(f"No matches for '{self.text}'")
            return None

        # Compute normalized score for each match as suggested by
        # https://community.crossref.org/t/query-affiliation/2009/5
        scores = [x["score"] / len(self.text.split()) for x in items]

        # Skip if top two matches are tied
        if scores[0] == scores[1]:
            msg = "\n  ".join(
                [
                    f"Top matches have same score ({round(scores[0], 3)}); skipping:",
                    f"Query: {self.text}",
                    f"Best:  {self.format_crossref_item(items[0])} {items[0]['DOI']}",
                    f"Next:  {self.format_crossref_item(items[1])} {items[1]['DOI']}",
                ]
            )
            warn(msg)
            return None

        # Skip first match if it is a component e.g. supplemental information, figure
        if items[0]["type"] == "component":
            msg = "\n  ".join(
                [
                    "Best match is a component; using next-best match:",
                    f"Query: {self.text}",
                    f"Best:  {self.format_crossref_item(items[0])} {items[0]['DOI']}",
                    f"Next:  {self.format_crossref_item(items[1])} {items[1]['DOI']}",
                ]
            )
            warn(msg)
            items = items[1:]
            scores = scores[1:]

        # Warn if best match has low normalized score
        if scores[0] < 3:
            msg = "\n  ".join(
                [
                    f"Best match has low normalized score ({round(scores[0], 3)})",
                    f"Query: {self.text}",
                    f"Match: {self.format_crossref_item(items[0])} {items[0]['DOI']}",
                ]
            )
            warn(msg)

        # Extract and set details
        match = items[0]
        self.doi = match["DOI"]
        self.citekey = self.format_citekey(match)
        self.title = re.sub(r"\s+", " ", match["title"][0]).strip()
        self.author = self.format_author(match)
        self.year = match["issued"]["date-parts"][0][0]
        journal = match.get("container-title", [None])[0]
        if journal is not None:
            journal = journal.replace("&amp;", "&")
        self.journal = journal
        self.volume = match.get("volume")
        self.issue = match.get("issue")
        self.page = match.get("page")
        self.score = scores[0]


@dataclass(kw_only=True)
class Paper(Requester):
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
        volume: The paper's journal volume (default: None)
        issue: The paper's journal issue (default: None)
        page: The paper's journal page number (default: None)
        orcid: The first author's ORCID (default: None)
        abstract: The paper's abstract (default: None)
    """

    doi: str | None = None
    hal_id: str | None = None
    author: str | None = None
    year: int | None = None
    title: str | None = field(default=None, repr=False)
    journal: str | None = field(default=None, repr=False)
    volume: str | None = field(default=None, repr=False)
    issue: str | None = field(default=None, repr=False)
    page: str | None = field(default=None, repr=False)
    abstract: str | None = field(default=None, repr=False)
    orcid: str | None = field(default=None, repr=False)

    # Additional attributes for Google Sheets columns
    is_main: bool | str | None = field(default=None, repr=False)
    theme: int | None = field(default=None, repr=False)
    lister: str | None = field(default=None, repr=False)
    note: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.doi = parse_doi(self.doi, raise_on_fail=True)
        self.hal_id = self.parse_hal_id(self.hal_id)
        if not self.has_doi() and not self.has_hal_id():
            args = {k: v for k, v in vars(self).items() if v is not None}
            raise ValueError(f"Paper must have DOI or HAL ID. Got: {args}")
        self.is_main = str(self.is_main).strip().lower() in ["true", "yes", "y", "oui"]

    def clean_abstract(self, abstract: str) -> str:
        """Strip extra whitespace and JATS tags from abstract text"""

        abstract = re.sub(r"</?jats:[\w\-]+>", " ", abstract)
        abstract = re.sub(r"</?(div|p)>", " ", abstract)
        abstract = re.sub(r"^ *[Aa]bstract\.?", " ", abstract)
        abstract = re.sub(r"^ *ABSTRACT\.?", " ", abstract)
        abstract = re.sub(r"\s+", " ", abstract)
        abstract = abstract.strip()

        return abstract

    def doi_link(self) -> str | None:
        """Return the DOI link e.g. https://doi.org/10.1000/182"""

        if self.has_doi():
            return f"https://doi.org/{self.doi}"
        return None

    # Recommended by https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/#optimize-your-requests-and-pay-attention-to-errors
    def encode_doi(self) -> str:
        """Return the URL-encoded DOI"""

        if self.has_doi():
            return requests.utils.quote(self.doi)
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
            f"https://api.elsevier.com/content/article/doi/{self.encode_doi()}"
            + f"?apiKey={CONFIG.scopus_key}&field=dc:description"
        )
        headers = {"Accept": "application/json"}
        response = self.get(url, headers)

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            raise ValueError(f"Error: status {response.status_code} from {url}")

        data = response.json()["full-text-retrieval-response"]["coredata"]
        abstract = data["dc:description"]
        if abstract is not None:
            abstract = self.clean_abstract(abstract)

        return abstract

    def get_abstract_semanticscholar(self) -> str | None:
        """Query semanticscholar.org for paper abstract

        Only used if abstract not found on crossref or hal.science
        """

        url = (
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{self.encode_doi()}"
            + "?fields=abstract"
        )
        response = self.get(url)

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            raise ValueError(f"Error: status {response.status_code} from {url}")

        abstract = response.json()["abstract"]
        if abstract is not None:
            abstract = self.clean_abstract(abstract)

        return abstract

    def get_bibtex(self) -> str:
        """Return BibTeX entry for paper"""

        # If DOI is missing, try to get it from hal.science
        if not self.has_doi():
            self.doi = self.get_details_hal().get("doi", "no doi")

        # Prefer DOI-based BibTeX from Crossref
        if self.has_doi():
            return self.get_bibtex_crossref()

        # Fall back on HAL ID-based BibTeX from hal.science
        return self.get_bibtex_hal()

    def get_bibtex_crossref(self) -> str:
        """Query crossref.org with the paper's DOI and return a BibTeX entry"""

        url = f"https://api.crossref.org/works/{self.encode_doi()}/transform"
        headers = {"Accept": "application/x-bibtex"}
        response = self.get(url, headers=headers)

        # If not found, warn and return an error comment in BibTeX format
        if response.status_code == 404:
            msg = f"No Crossref BibTeX for paper doi:{self.doi}"
            warn(msg)
            return f"% Error: {msg}"

        if response.status_code != 200:
            raise ValueError(f"Error: status {response.status_code} from {url}")

        return response.text.strip()

    def get_bibtex_hal(self) -> str:
        """Query hal.science with the paper's HAL ID and return a BibTeX entry"""

        url = (
            f"https://api.archives-ouvertes.fr/search/?q=halId_id:{self.hal_id}&wt=bibtex"
        )
        response = self.get(url)

        if response.status_code != 200:
            raise ValueError(f"Error: status {response.status_code} from {url}")

        data = response.text.strip()

        # If not found, warn and return an error comment in BibTeX format
        if data == "":
            msg = f"No HAL BibTeX for paper hal:{self.hal_id}"
            warn(msg)
            return f"% Error: {msg}"

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

        # Note: this does not allow choosing which fields are returned but is still much
        # faster than alternative of querying 'works?filter=doi:DOI&rows=1&select=...'
        url = f"https://api.crossref.org/works/{self.encode_doi()}"
        response = self.get(url)

        # Return if DOI not found
        if response.status_code == 404:
            return {}

        if response.status_code != 200:
            raise ValueError(f"Error: status {response.status_code} from {url}")

        # Monitor the API rate limit
        self.check_ratelimit(response)

        # Parse response
        data = response.json()["message"]
        details = {
            "doi": data["DOI"],
            "title": re.sub(r"\s+", " ", data["title"][0]).strip(),
            "year": data["issued"]["date-parts"][0][0],
        }
        if "author" in data:
            author = data["author"][0]
            details["author"] = ", ".join([author["family"], author["given"]])
            if author.get("ORCID") is not None:
                details["orcid"] = author.get("ORCID")
        try:
            details["journal"] = data["container-title"][0]
        except IndexError as err:
            pass
        details["volume"] = data.get("volume")
        details["issue"] = data.get("issue")
        details["page"] = data.get("page")
        abstract = data.get("abstract")
        if abstract is not None:
            details["abstract"] = self.clean_abstract(abstract)

        return details

    def get_details_datacite(self) -> dict:
        """Query datacite.org with a DOI and return details"""

        url = f"https://api.datacite.org/dois/{self.encode_doi()}"
        response = self.get(url)

        # Return if DOI not found
        if response.status_code == 404:
            return {}

        if response.status_code != 200:
            raise ValueError(f"Error: status {response.status_code} from {url}")

        data = response.json()["data"]["attributes"]
        author = data["creators"][0]
        details = {
            "doi": data["doi"],
            "author": ", ".join([author["familyName"], author["givenName"]]),
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
            details["abstract"] = self.clean_abstract(abstract)

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
        query = self.hal_id if self.has_hal_id() else f"doiId_id:{self.encode_doi()}"
        url = (
            f"https://api.archives-ouvertes.fr/search/?q={query}&fl=doiId_s,halId_s"
            + ",authFirstName_s,authLastName_s,producedDateY_i,title_s,journalTitle_s"
            + ",volume_s,issue_s,page_s,abstract_s"
        )
        response = self.get(url)

        if response.status_code != 200:
            raise ValueError(f"Error: status {response.status_code} from {url}")

        data = response.json()["response"]

        # Return empty dict if no record found
        if data["numFound"] == 0:
            return {}

        if data["numFound"] != 1:
            raise ValueError(f"Found {data["numFound"]} HAL records matching {query}")

        data = data["docs"][0]
        author = ", ".join([data["authLastName_s"][0], data["authFirstName_s"][0]])
        details = {
            "doi": data.get("doiId_s", "no doi").lower(),
            "hal_id": data["halId_s"],
            "author": author,
            "title": data["title_s"][0],
            "year": data["producedDateY_i"],
        }
        details["journal"] = data.get("journalTitle_s")
        details["volume"] = data.get("volume_s")
        details["issue"] = data.get("issue_s")
        details["page"] = data.get("page_s")
        abstract = data.get("abstract_s", [None])[0]
        if abstract is not None:
            details["abstract"] = self.clean_abstract(abstract)

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

    def lookup_details(self, get_hal_id: bool = True, get_abstract: bool = True) -> None:
        """Get and set bibliographic details

        Args:
            get_hal_id: Whether to look up the paper's HAL ID (default: True)
            get_abstract: Whether to look up the paper's abstract (default: True)
        """

        # Possibly look up details from hal.science (searches by DOI or HAL ID)
        # Do this first b/c can only get HAL ID from hal.science
        info = {}
        if get_hal_id or not self.has_doi():
            info = self.get_details_hal()

            # Set HAL ID if HAL record was found. HAL records may have multiple IDs, so
            # this ensures that the 'main' ID is used. It also sets the HAL ID if it was
            # missing and the record was found by DOI.
            self.hal_id = info.get("hal_id", "no hal id")

            # Set DOI if it is missing and was found on HAL
            # Warn and don't overwrite existing DOI if HAL-provided DOI differs
            if "doi" in info:
                if not self.has_doi():
                    self.doi = info["doi"]
                elif info["doi"] != "no doi" and info["doi"] != self.doi:
                    warn(
                        f"HAL returned DOI {info['doi']} for Paper(doi='{self.doi}'" +
                        f", hal_id='{self.hal_id}'). Please check DOI and HAL ID."
                    )

        # If paper has a DOI, look up details from Crossref (and other sources)
        # Do this even if paper is on HAL b/c Crossref metadata is often more complete
        if self.has_doi():
            info |= self.get_details_crossref()  # prefer info from crossref

            # If no info, query DataCite (in case the 'paper' is a dataset or software)
            if not any(info):
                info = self.get_details_datacite()

            # Possibly look up abstract
            # Prefer Semantic Scholar, fall back on Scopus (if API key configured)
            if get_abstract and info.get("abstract") is None:
                abstract = self.get_abstract_semanticscholar()
                if abstract is None:
                    abstract = self.get_abstract_scopus()
                info["abstract"] = abstract

        # Warn if could not find bibliographic details
        if not any(info):
            msg = f"No HAL, Crossref, or DataCite record for {self}. Check the DOI"
            msg += " and HAL ID." if self.has_hal_id() else "."
            warn(msg)

        # Set bibliographic attributes
        self.author = info.get("author")
        self.orcid = info.get("orcid")
        self.title = info.get("title")
        self.year = info.get("year")
        self.journal = info.get("journal")
        if self.journal is not None:
            self.journal = self.journal.replace("&amp;", "&")
        self.volume = info.get("volume")
        self.issue = info.get("issue")
        self.page = info.get("page")
        self.abstract = info.get("abstract")

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
    # * Standardize spellings: *isation -> *ization e.g. factorisation -> factorization
    # * Standardize spellings: *ell(ed|er|ing) -> *el(ed|er|ing) e.g. modelled -> modeled
    # * Fix PM10 + PM2.5 e.g. pm 2:5 -> pm2.5
    # * Remove formatting e.g. pm&amp;lt;sub&amp;gt;10&amp;lt;/sub&amp;gt; -> pm10
    # * Replace escaped characters e.g. &amp;amp; -> &
    # * Remove period from end of words e.g. end. -> end
    text = text.lower()
    text = re.sub("</?jats.+?>", " ", text, flags=re.IGNORECASE)
    text = text.translate(str.maketrans("àâèéêëîïôùûü", "aaeeeeiiouuu"))
    text = text.translate(str.maketrans("ÀÂÈÉÊËÎÏÔÙÛÜ", "AAEEEEIIOUUU"))
    text = re.sub(r"isation\b", r"ization", text, flags=re.IGNORECASE)
    text = re.sub(r"ell(ed|er|ing)\b", r"el\1", text, flags=re.IGNORECASE)
    text = re.sub(r"\bpm\s*2[\.:]5\b", "PM2.5", text, flags=re.IGNORECASE)
    text = re.sub(r"\bpm\s*10\b", "PM10", text, flags=re.IGNORECASE)
    text = re.sub(r"&amp;lt;\/?(i|sub|sup)&amp;gt;", "", text)
    text = re.sub("(&amp;)?amp;", "&", text, flags=re.IGNORECASE)
    text = re.sub("(&amp;)?gt;", ">", text, flags=re.IGNORECASE)
    text = re.sub("(&amp;)?lt;", "<", text, flags=re.IGNORECASE)
    text = re.sub(r"(\w+)\.(\s|$)", r"\1\2", text)

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
    if CONFIG.sheet_key is None:
        raise ValueError("No Google Sheets key in keys/")
    creds = Credentials.from_service_account_file(CONFIG.sheet_key, scopes=[scope])
    client = gspread.authorize(creds)

    # Load the sheet
    if CONFIG.sheet_url is None:
        raise ValueError("No Google Sheets URL in configuration.yml")
    logger.info("Opening Google Sheet %s", CONFIG.sheet_url)
    sheet = client.open_by_url(CONFIG.sheet_url).sheet1

    # Confirm the sheet has the expected layout
    validate_sheet(sheet)

    return sheet


def get_csv_papers(path: str) -> list[Paper]:
    """Read papers from a CSV"""

    items = read_csv(path)
    validate_csv_has_id_column(items)
    papers = []
    for i, row in items.iterrows():
        # Ignore unrecognized columns
        try:
            papers.append(Paper(**{k: v for k, v in row.items() if k in PAPER_TO_SHEET}))
        except ValueError as err:
            err.add_note(f"Error caused by row {i + 1} of {path}")
            raise

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

        # Merge duplicates. Duplicates may remain if a paper was listed once with only DOI
        # and again with only HAL ID.
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


def get_txt_references(path: str) -> list[Reference]:
    """Read references from a text file and deduplicate"""

    logger.info("Reading references from %s", path)
    items = Path(path).read_text().splitlines()

    if not any(items):
        raise ValueError(f"No references found in {path}")

    # Deduplicate
    items = list(dict.fromkeys(items))

    return [Reference(ref) for ref in items]


def papers_to_wordclouds(
    papers: list[Paper],
    by_theme: bool = False,
    force: bool = False,
    hal_only: bool = False,
    weight: int = 1,
    width: int = 1000,
    height: int = 500,
    collocations: bool = True,
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
        cloud = generate_wordcloud(
            ".\n".join(text), width=width, height=height, collocations=collocations
        )
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


def parse_doi(doi: str, raise_on_fail: bool = False) -> str | None:
    """Parse a DOI and return in a standardized format

    Args:
        doi: The DOI to parse
        raise_on_fail: Whether to raise an error if the input is not a recognized DOI

    Recognized DOI formats:
        - <DOI>
        - doi:<DOI>
        - [http[s]://][dx.]doi.org/<DOI>
        - [http[s]://]doi-org.<subdomain>.grenet.fr/<DOI>
        - [http[s]://]<domain and path>/doi/[full/]/<DOI>
        - 'no doi'
    """

    if doi is None or doi.strip() == "":
        return None
    doi = doi.lower().strip()
    doi = re.sub("^https?://", "", doi)

    doi_pattern = r"(10\.\d{4}.+)"
    patterns = [
        # <DOI>
        r"^" + doi_pattern,
        # doi:<DOI>
        r"^doi:" + doi_pattern,
        # [dx.]doi.org/<DOI>
        r"^(?:dx\.)?doi\.org\/" + doi_pattern,
        # doi-org.*.grenet.fr/<DOI>
        r"^doi-org\.[\w-]+\.grenet\.fr\/" + doi_pattern,
        # */doi/[full/]<DOI>
        r"^[\w\.]+\/doi\/(?:full\/)?" + doi_pattern,
        # No DOI indicator
        r"^(no doi)$",
    ]
    for pattern in patterns:
        if re.match(pattern, doi):
            doi = re.sub(pattern, r"\1", doi)
            return doi

    if raise_on_fail:
        raise ValueError(f"Unrecognized DOI: {doi}")


def read_csv(path: str = None) -> pd.DataFrame:
    """Read paper bibliographic details from a CSV"""

    logger.info("Reading %s", path)
    items = pd.read_csv(path).replace({float("nan"): None})
    items.columns = items.columns.str.lower()

    if items.shape[0] == 0:
        raise ValueError(f"No references found in {path}")

    return items


def validate_csv_has_id_column(csv: pd.DataFrame) -> None:
    """Confirm the CSV file has a 'doi' or 'hal_id' column"""

    columns = [x.lower().strip() for x in csv.columns]
    if not "doi" in columns and not "hal_id" in columns:
        raise ValueError("CSV must have 'doi' or 'hal_id' column.")


def validate_csv_matches_sheet(csv: pd.DataFrame) -> None:
    """Confirm CSV file columns match the Google Sheet's columns"""

    for i, expected in enumerate(PAPER_TO_SHEET):
        if csv.columns[i].lower().strip() != expected.lower().strip():
            raise ValueError(
                "CSV layout does not match Google Sheet."
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


def wordcloud_argparser(description: str | None = None) -> argparse.ArgumentParser:
    """Return a parser that for command-line arguments for wordclouds"""

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
        "--unigrams",
        action="store_true",
        help="only consider individual words (no collocations)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="display DEBUG level messages"
    )
    parser.add_argument(
        "--weight",
        default=1,
        type=int,
        help="set this to an integer >1 to give extra weight to papers where a team"
        + " member is the first or corresponding author",
    )
    parser.add_argument("--width", default=1000, type=int, help="output width (pixels)")

    return parser
