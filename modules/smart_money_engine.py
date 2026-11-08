"""Normalise Form 4 purchases and validate the published snapshot."""
import json
import os
import tempfile
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree

from modules.sec_client import ACCESSION, filing_url

SNAPSHOT = Path(__file__).resolve().parents[1] / "data/smart_money/latest.json"
HISTORY_DAYS = 90
CLUSTER_DAYS = 30


def positive_decimal(value):
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError) as error:
        raise ValueError("Invalid Form 4 number.") from error
    if not number.is_finite() or number <= 0 or not -30 <= number.adjusted() <= 30:
        raise ValueError("Expected a finite positive Form 4 number.")
    return number


def parse_filing(xml, cik, accession, filed, form):
    root = ElementTree.fromstring(xml)
    for node in root.iter():
        node.tag = node.tag.rsplit("}", 1)[-1]
    if root.tag != "ownershipDocument" or root.findtext("documentType") != form:
        raise ValueError(f"Unexpected Form 4 document for {accession}.")
    issuer_cik = int(root.findtext("issuer/issuerCik", "0"))
    owners = {}
    for owner in root.findall("reportingOwner"):
        owner_cik = int(owner.findtext("reportingOwnerId/rptOwnerCik", "0"))
        owners[owner_cik] = owner.findtext("reportingOwnerId/rptOwnerName", "").strip()
    if issuer_cik != cik:
        # The issuer's submissions may also contain filings it made as an owner.
        if issuer_cik > 0 and cik in owners:
            return None
        raise ValueError(f"Unexpected Form 4 issuer for {accession}.")
    rows = []
    for index, row in enumerate(root.findall("nonDerivativeTable/nonDerivativeTransaction")):
        if (row.findtext("transactionCoding/transactionCode") != "P"
                or row.findtext("transactionAmounts/transactionAcquiredDisposedCode/value") != "A"):
            continue
        price = row.findtext("transactionAmounts/transactionPricePerShare/value")
        # Unpriced and zero-price acquisitions are not usable cash purchases.
        if price is None or not price.strip():
            continue
        try:
            if Decimal(price) == 0:
                continue
        except InvalidOperation as error:
            raise ValueError(f"Invalid Form 4 price for {accession}.") from error
        rows.append({
            "line": index,
            "date": row.findtext("transactionDate/value"),
            "security": row.findtext("securityTitle/value", "").strip(),
            "shares": str(positive_decimal(row.findtext("transactionAmounts/transactionShares/value"))),
            "price": str(positive_decimal(price)),
            "ownership": row.findtext("ownershipNature/directOrIndirectOwnership/value"),
        })
    return {
        "cik": cik, "accession": accession, "filed": filed, "form": form,
        "original_filed": root.findtext("dateOfOriginalSubmission") or None,
        "owners": {str(key): value for key, value in sorted(owners.items())},
        "plan_10b5_1": root.findtext("aff10b5One") in {"1", "true"},
        "rows": rows,
    }


def validate_snapshot(data):
    if data["schema_version"] != 1:
        raise ValueError("Unknown Smart Money snapshot schema.")
    generated = datetime.fromisoformat(data["generated_at"])
    as_of = date.fromisoformat(data["as_of"])
    cutoff = date.fromisoformat(data["cutoff"])
    if (generated.utcoffset() is None or not 0 <= (generated.date() - as_of).days <= 1
            or (as_of - cutoff).days != HISTORY_DAYS - 1):
        raise ValueError("Invalid snapshot dates.")
    universe = data["universe"]
    if not universe or any(not key.isdecimal() or int(key) <= 0
                           or not isinstance(ticker, str) or not ticker.strip()
                           for key, ticker in universe.items()):
        raise ValueError("Invalid or empty SEC universe.")
    if not isinstance(data["unmapped"], list) or any(
        not isinstance(ticker, str) for ticker in data["unmapped"]
    ):
        raise ValueError("Invalid unmapped tickers.")
    seen = set()
    for filing in data["filings"]:
        key = filing["accession"]
        filed = date.fromisoformat(filing["filed"])
        owners = filing["owners"]
        if (not ACCESSION.fullmatch(key) or key in seen or type(filing["cik"]) is not int
                or str(filing["cik"]) not in universe
                or not cutoff <= filed <= as_of or filing["form"] not in {"4", "4/A"}
                or not isinstance(filing["plan_10b5_1"], bool)
                or not owners or any(not k.isdecimal() or int(k) <= 0
                                     or not isinstance(v, str) or not v.strip()
                                     for k, v in owners.items())):
            raise ValueError("Invalid or duplicate Form 4 filing.")
        if filing["original_filed"] and date.fromisoformat(filing["original_filed"]) > filed:
            raise ValueError("Amendment predates its original filing.")
        seen.add(key)
        lines = set()
        for row in filing["rows"]:
            line = row["line"]
            if (type(line) is not int or line < 0 or line in lines or not row["security"]
                    or date.fromisoformat(row["date"]) > filed
                    or row["ownership"] not in {"D", "I"}):
                raise ValueError("Invalid or duplicate Form 4 transaction.")
            positive_decimal(row["shares"])
            positive_decimal(row["price"])
            lines.add(line)
    return data


def load_snapshot(path=SNAPSHOT):
    return validate_snapshot(json.loads(path.read_text(encoding="utf-8")))


def publish_snapshot(data, path=SNAPSHOT):
    validate_snapshot(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     delete=False) as temporary:
        staged = Path(temporary.name)
        try:
            json.dump(data, temporary, indent=2, ensure_ascii=False, allow_nan=False)
            temporary.write("\n")
            temporary.close()
            os.replace(staged, path)
        finally:
            temporary.close()
            staged.unlink(missing_ok=True)


def purchase_history(snapshot):
    amendments = defaultdict(set)
    for filing in snapshot["filings"]:
        if filing["form"] == "4/A":
            amendments[filing["cik"], filing["original_filed"]].update(filing["owners"])

    rows = []
    review_count = 0
    for filing in snapshot["filings"]:
        cik = filing["cik"]
        owners = filing["owners"]
        affected = amendments[cik, filing["filed"]] | amendments[cik, None]
        # A Form 4/A can correct only a subset of lines. Keep both documents
        # in the snapshot and leave affected purchases out of aggregates.
        if filing["form"] == "4/A" or affected.intersection(owners):
            review_count += 1
            continue
        for row in filing["rows"]:
            accession = filing["accession"]
            rows.append({
                **row, "ticker": snapshot["universe"][str(cik)], "cik": cik,
                "owners": tuple(owners), "insider": ", ".join(owners.values()),
                "filed": filing["filed"], "plan_10b5_1": filing["plan_10b5_1"],
                "value": positive_decimal(row["shares"]) * positive_decimal(row["price"]),
                "source": f"{filing_url(cik, accession)}/{accession}-index.html",
            })
    return sorted(rows, key=lambda row: (row["date"], row["filed"]), reverse=True), review_count


def insider_clusters(rows, as_of):
    first = (date.fromisoformat(as_of) - timedelta(days=CLUSTER_DAYS - 1)).isoformat()
    groups = defaultdict(set)
    for row in rows:
        if (first <= row["date"] <= as_of and row["ownership"] == "D"
                and not row["plan_10b5_1"] and len(row["owners"]) == 1):
            groups[row["ticker"]].update(row["owners"])
    return sorted(
        ((ticker, len(owners)) for ticker, owners in groups.items() if len(owners) >= 2),
        key=lambda group: (-group[1], group[0]),
    )
