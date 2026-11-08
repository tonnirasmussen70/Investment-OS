from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from modules.sec_client import SecClient
from modules.smart_money_engine import (
    insider_clusters, load_snapshot, parse_filing, publish_snapshot, purchase_history,
)
from scripts.update_smart_money import collect


ACCESSION = "0000000001-26-000001"
NOW = datetime(2026, 11, 7, 6, tzinfo=timezone.utc)
FILED = "2026-11-06"
ROW = """<nonDerivativeTransaction>
<securityTitle><value>Common Stock</value></securityTitle>
<transactionDate><value>2026-11-05</value></transactionDate>
<transactionCoding><transactionCode>P</transactionCode></transactionCoding>
<transactionAmounts>
<transactionShares><value>10</value></transactionShares>
<transactionPricePerShare><value>12.34</value></transactionPricePerShare>
<transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
</transactionAmounts>
<ownershipNature><directOrIndirectOwnership><value>D</value></directOrIndirectOwnership></ownershipNature>
</nonDerivativeTransaction>"""
XML = f"""<ownershipDocument xmlns="urn:ownership">
<documentType>4</documentType><issuer><issuerCik>1</issuerCik></issuer>
<reportingOwner><reportingOwnerId><rptOwnerCik>2</rptOwnerCik>
<rptOwnerName>Example Owner</rptOwnerName></reportingOwnerId></reportingOwner>
<nonDerivativeTable>{ROW}{ROW.replace('<transactionCode>P', '<transactionCode>M')}
{ROW.replace('<value>12.34', '<value>0')}</nonDerivativeTable>
</ownershipDocument>"""


class FixtureSec:
    downloads = 0
    include_filing = True

    def submissions(self, cik, cutoff):
        batch = dict(form=[], filingDate=[], accessionNumber=[], primaryDocument=[])
        if self.include_filing:
            batch = dict(form=["4"], filingDate=[FILED], accessionNumber=[ACCESSION],
                         primaryDocument=["ownership.xml"])
        yield batch
        yield batch

    def ownership_xml(self, *args):
        self.downloads += 1
        return XML


def test_collection_is_idempotent_and_filters_non_purchases(tmp_path):
    client = FixtureSec()
    snapshot = collect(client, {"1": "ABC"}, [], NOW)
    path = tmp_path / "latest.json"
    publish_snapshot(snapshot, path)
    previous = load_snapshot(path)
    assert collect(client, {"1": "ABC"}, [], NOW, previous) == previous
    assert client.downloads == 1
    rows, reviews = purchase_history(previous)
    assert reviews == 0
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-11-05"
    assert rows[0]["filed"] == FILED
    assert rows[0]["value"] == Decimal("123.40")
    assert rows[0]["source"].endswith(f"{ACCESSION}-index.html")


def test_invalid_and_incomplete_refresh_preserve_snapshot(tmp_path):
    client = FixtureSec()
    snapshot = collect(client, {"1": "ABC"}, [], NOW)
    path = tmp_path / "latest.json"
    publish_snapshot(snapshot, path)
    previous = path.read_bytes()
    duplicate = deepcopy(snapshot)
    duplicate["filings"] *= 2
    with pytest.raises(ValueError, match="duplicate"):
        publish_snapshot(duplicate, path)
    client.include_filing = False
    with pytest.raises(ValueError, match="omitted"):
        collect(client, {"1": "ABC"}, [], NOW, snapshot)
    assert path.read_bytes() == previous


def test_amendments_and_joint_owners_do_not_inflate_clusters():
    snapshot = collect(FixtureSec(), {"1": "ABC"}, [], NOW)
    first, = snapshot["filings"]
    second = {**first, "accession": "0000000001-26-000002", "owners": {"3": "Other"}}
    snapshot["filings"].append(second)
    rows, _ = purchase_history(snapshot)
    assert insider_clusters(rows, snapshot["as_of"]) == [("ABC", 2)]
    second["owners"]["2"] = "Example Owner"
    rows, _ = purchase_history(snapshot)
    assert insider_clusters(rows, snapshot["as_of"]) == []
    amendment = {**first, "accession": "0000000001-26-000003",
                 "form": "4/A", "original_filed": FILED}
    snapshot["filings"].append(amendment)
    assert purchase_history(snapshot) == ([], 3)


def test_issuer_mismatch_is_rejected():
    with pytest.raises(ValueError, match="Unexpected Form 4 issuer"):
        parse_filing(XML, 3, ACCESSION, FILED, "4")
    assert parse_filing(XML, 2, ACCESSION, FILED, "4") is None


def test_sec_uses_raw_ownership_xml(monkeypatch):
    client = SecClient("Investment OS test@example.com")
    monkeypatch.setattr(client, "get", lambda url: url)
    assert client.ownership_xml(1, ACCESSION, "xslF345X05/ownership.xml") == (
        "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/ownership.xml"
    )
