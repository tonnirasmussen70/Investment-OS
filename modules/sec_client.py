"""Read public EDGAR data under SEC fair-access guidelines."""
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DATA = "https://data.sec.gov"
WWW = "https://www.sec.gov"
ACCESSION = re.compile(r"[0-9]{10}-[0-9]{2}-[0-9]{6}")
MAX_BYTES = 16 * 1024 * 1024


class SecClient:
    def __init__(self, user_agent):
        if not re.search(r"\S+@\S+\.\S+", user_agent):
            raise ValueError("Set SEC_USER_AGENT to an organisation and contact email.")
        self.user_agent = user_agent
        self.next_request = 0

    def get(self, url):
        for attempt in range(4):
            time.sleep(max(0, self.next_request - time.monotonic()))
            self.next_request = time.monotonic() + 0.25
            try:
                request = Request(url, headers={"User-Agent": self.user_agent})
                with urlopen(request, timeout=30) as response:
                    payload = response.read(MAX_BYTES + 1)
                if len(payload) > MAX_BYTES:
                    raise ValueError("SEC response exceeds size limit.")
                return payload
            except HTTPError as error:
                if error.code not in {429, 500, 502, 503, 504} or attempt == 3:
                    raise
                retry_after = error.headers.get("Retry-After", "")
                if retry_after.isdecimal():
                    if int(retry_after) > 120:
                        raise
                    time.sleep(int(retry_after))
            except (URLError, TimeoutError):
                if attempt == 3:
                    raise
            time.sleep(2 ** attempt)

    def json(self, url):
        return json.loads(self.get(url))

    def submissions(self, cik, cutoff):
        data = self.json(f"{DATA}/submissions/CIK{cik:010d}.json")
        if int(data["cik"]) != cik:
            raise ValueError("SEC submissions issuer mismatch.")
        yield data["filings"]["recent"]
        for history in data["filings"]["files"]:
            if history["filingTo"] >= cutoff:
                name = history["name"]
                if not re.fullmatch(rf"CIK{cik:010d}-submissions-[0-9]+\.json", name):
                    raise ValueError("Unexpected SEC history filename.")
                yield self.json(f"{DATA}/submissions/{name}")

    def ownership_xml(self, cik, accession, document):
        if not ACCESSION.fullmatch(accession):
            raise ValueError("Invalid SEC accession.")
        # EDGAR submissions may prefix the raw XML filename with an XSL viewer path.
        name = document.rsplit("/", 1)[-1]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+\.xml", name, re.IGNORECASE):
            raise ValueError(f"Unexpected ownership document for {accession}.")
        return self.get(f"{filing_url(cik, accession)}/{name}")


def filing_url(cik, accession):
    return f"{WWW}/Archives/edgar/data/{cik}/{accession.replace('-', '')}"
