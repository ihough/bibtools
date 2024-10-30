import subprocess
from pathlib import Path
from warnings import warn

import yaml


class Configure:
    """Global configuration"""

    CONFIG_FILE = "configuration.yml"
    KEYS_DIR = Path("keys")

    def __init__(self) -> None:
        # Load configuration.yml
        config = yaml.safe_load(Path(self.CONFIG_FILE).read_text("utf-8"))

        # Google Sheets url and authentication key
        self.sheet_url = config["sheet_url"]
        try:
            self.sheet_key = list(Path(self.KEYS_DIR).glob("*.json"))[0]
        except IndexError:
            raise FileNotFoundError(f"No json key found in {self.KEYS_DIR}/")

        # Email for polite crossref queries; if unset will be configured on first access
        self._crossref_email = config.get("crossref_email")
        self._crossref_email_configured = self._crossref_email is not None

        # Scopus API key; will be configured on first access
        self._scopus_key = None
        self._scopus_key_configured = False

    @property
    def crossref_email(self) -> str:
        """Email for polite crossref queries"""

        # Configure on first run
        if not self._crossref_email_configured:
            msg = "Crossref email not configured; using impolite crossref queries"
            try:
                result = subprocess.run(
                    ["git", "config", "user.email"], capture_output=True, check=False
                )
                if result.returncode == 0:
                    email = result.stdout.decode("utf-8").strip()
                    self._crossref_email = email
                    msg = f"Using git email ({email}) for polite crossref queries"
            except FileNotFoundError:
                pass  # don't raise if git not found

            warn(msg)
            self._crossref_email_configured = True

        return self._crossref_email

    @property
    def scopus_key(self) -> str | None:
        """Scopus API key"""

        # Configure on first run
        if not self._scopus_key_configured:
            key_path = self.KEYS_DIR / "scopus_api_key"
            if key_path.exists():
                key = key_path.read_text("utf-8").strip()
                self._scopus_key = key if key != "" else None
            if self._scopus_key is None:
                warn("No Scopus API key; will not search Scopus for abstracts")
            self._scopus_key_configured = True

        return self._scopus_key
