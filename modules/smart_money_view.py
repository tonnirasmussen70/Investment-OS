"""Read-only Streamlit presentation of the published SEC snapshot."""
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from modules.smart_money_engine import insider_clusters, load_snapshot, purchase_history


def render_smart_money():
    st.subheader("Smart Money · SEC Form 4")
    try:
        snapshot = load_snapshot()
    except FileNotFoundError:
        st.info("Trackeren afventer første validerede SEC-opdatering.")
        return
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        st.warning("SEC-snapshottet kunne ikke valideres.")
        return

    updated = datetime.fromisoformat(snapshot["generated_at"])
    st.caption(
        f"SEC EDGAR · Indberetninger {snapshot['cutoff']} til {snapshot['as_of']} · "
        f"{len(snapshot['universe'])} selskaber · Opdateret {updated:%d-%m-%Y %H:%M %Z}"
    )
    now = datetime.now(timezone.utc)
    # The schedule runs on weekdays. Allow the normal weekend gap.
    max_age = timedelta(hours=96 if now.weekday() in {0, 5, 6} else 48)
    if now - updated > max_age:
        st.warning("SEC-data er forældede. Viser sidste validerede snapshot.")
    st.caption(
        "Kode P viser køb på åbent marked eller privat. Oversigten omfatter "
        "prissatte køb af ikke-derivative værdipapirer."
    )
    if snapshot["unmapped"]:
        st.caption("Uden entydigt SEC-match: " + ", ".join(snapshot["unmapped"]))

    rows, review_count = purchase_history(snapshot)
    if review_count:
        st.caption(f"{review_count} indberetninger med tilknytning til Form 4/A er udeladt til manuel kontrol.")
    clusters = insider_clusters(rows, snapshot["as_of"])
    if clusters:
        st.markdown("**Købsklynger · seneste 30 kalenderdage**")
        st.caption("Mindst to forskellige indberettere med direkte køb. Fællesindberetninger og 10b5-1-planer er udeladt.")
        st.dataframe(pd.DataFrame(clusters, columns=["Ticker", "Indberettere"]), hide_index=True)
    if not rows:
        st.info("Ingen kvalificerede køb i de indsamlede indberetninger.")
        return
    table = pd.DataFrame([{
        "Ticker": row["ticker"], "Indberetter": row["insider"], "Papir": row["security"],
        "Handelsdato": row["date"], "Indberettet": row["filed"],
        "Ejerskab": "Direkte" if row["ownership"] == "D" else "Indirekte",
        "10b5-1 markeret": row["plan_10b5_1"], "Antal": row["shares"],
        "Pris pr. enhed": row["price"], "Handelsværdi": str(row["value"]),
        "SEC": row["source"],
    } for row in rows])
    st.dataframe(table, hide_index=True, column_config={"SEC": st.column_config.LinkColumn("SEC")})
