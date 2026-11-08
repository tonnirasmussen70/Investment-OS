"""Update the standalone EDGAR snapshot from the published IOS universe."""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.sec_client import WWW, SecClient
from modules.smart_money_engine import (
    HISTORY_DAYS, SNAPSHOT, load_snapshot, parse_filing, publish_snapshot,
)

US_MIC = {"XNYS", "XNAS", "XASE", "ARCX", "BATS"}
US_EXCHANGES = {"NYSE", "Nasdaq", "NYSE American", "NYSE Arca", "Cboe", "CBOE"}


def us_ticker(value):
    symbol, _, mic = str(value or "").strip().upper().partition(":")
    if (not mic or mic in US_MIC) and re.fullmatch(r"[A-Z]{1,6}(?:-[A-Z])?", symbol):
        return symbol
    return None


def resolve_universe(client, directory):
    portfolio = json.loads((directory / "portfolio_snapshot.json").read_text(encoding="utf-8"))
    agent = json.loads((directory / "compounder_agent.json").read_text(encoding="utf-8"))
    rows = [row for row in portfolio["positions"] if row["Asset_Type"] == "Stock"]
    rows.extend(portfolio["watchlist"])
    symbols = {
        us_ticker(row.get("Yahoo_Ticker")) or us_ticker(row.get("Ticker")) for row in rows
    }
    symbols.update(us_ticker(row["ticker"]) for row in agent["candidates"])
    symbols.discard(None)

    feed = client.json(f"{WWW}/files/company_tickers_exchange.json")
    matches = {}
    for values in feed["data"]:
        row = dict(zip(feed["fields"], values, strict=True))
        ticker = row["ticker"].replace(".", "-")
        if row["exchange"] in US_EXCHANGES and ticker in symbols:
            cik = str(int(row["cik"]))
            matches.setdefault(ticker, set()).add(cik)
    mapped = {}
    for ticker, ciks in sorted(matches.items()):
        if len(ciks) == 1:
            cik, = ciks
            mapped.setdefault(cik, ticker)
    return mapped, sorted(symbols - {ticker for ticker, ciks in matches.items() if len(ciks) == 1})


def collect(client, universe, unmapped, now, previous=None):
    as_of = now.astimezone(ZoneInfo("America/New_York")).date()
    cutoff = (as_of - timedelta(days=HISTORY_DAYS - 1)).isoformat()
    cached = {row["accession"]: row for row in previous["filings"]} if previous else {}
    filings = {}
    for key in universe:
        cik = int(key)
        owner_only = set()
        for batch in client.submissions(cik, cutoff):
            for form, filed, accession, document in zip(
                batch["form"], batch["filingDate"], batch["accessionNumber"],
                batch["primaryDocument"], strict=True,
            ):
                if form not in {"4", "4/A"} or not cutoff <= filed <= as_of.isoformat():
                    continue
                if accession in owner_only:
                    continue
                existing = filings.get(accession) or cached.get(accession)
                if existing is not None:
                    if (existing["filed"], existing["form"]) != (filed, form):
                        raise ValueError(f"Inconsistent SEC metadata for {accession}.")
                    if existing["cik"] == cik:
                        filings[accession] = existing
                    elif key not in existing["owners"]:
                        raise ValueError(f"Inconsistent SEC issuer for {accession}.")
                else:
                    xml = client.ownership_xml(cik, accession, document)
                    filing = parse_filing(xml, cik, accession, filed, form)
                    if filing is None:
                        owner_only.add(accession)
                    else:
                        filings[accession] = filing

    # A transiently incomplete SEC response must not erase already validated filings.
    missing = {key for key, row in cached.items()
               if str(row["cik"]) in universe and row["filed"] >= cutoff} - filings.keys()
    if missing:
        raise ValueError(f"SEC response omitted {len(missing)} previously validated filings.")
    return {
        "schema_version": 1, "generated_at": now.isoformat(),
        "as_of": as_of.isoformat(), "cutoff": cutoff, "universe": universe,
        "unmapped": unmapped,
        "filings": sorted(filings.values(), key=lambda row: (row["filed"], row["accession"])),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=SNAPSHOT)
    args = parser.parse_args()
    client = SecClient(os.environ.get("SEC_USER_AGENT", ""))
    now = datetime.now(timezone.utc)
    try:
        previous = load_snapshot(args.output)
    except FileNotFoundError:
        previous = None
    universe, unmapped = resolve_universe(client, ROOT / "data")
    if not universe:
        raise ValueError("No IOS tickers resolved to SEC issuers.")
    snapshot = collect(client, universe, unmapped, now, previous)
    publish_snapshot(snapshot, args.output)
    print(f"Validated {len(snapshot['filings'])} filings across {len(universe)} issuers.")


if __name__ == "__main__":
    main()
