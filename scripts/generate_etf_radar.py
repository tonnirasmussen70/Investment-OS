"""Refresh the persisted Yahoo ETF radar; retain last-good data on failure."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.etf_radar import load_or_refresh_etf_radar


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    args = parser.parse_args(argv)
    radar = load_or_refresh_etf_radar(args.data_dir, force=True)
    for note in radar.notes:
        print(note)
    if not radar.refreshed or not radar.persisted:
        print("ETF radar was not refreshed and saved; last-good file was retained.")
        return 1
    print(f"Saved ETF radar: {len(radar.data)} funds; price date {radar.as_of}; generated {radar.generated_at}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
