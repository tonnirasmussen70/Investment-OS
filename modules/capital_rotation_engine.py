"""Capital rotation scenarios for manual review, never executable orders.

The normal Decision Engine and rebalance plan remain authoritative. This module
shows an explicitly requested, cash-neutral alternative financed by reducing an
existing holding. No account transfers, fees, tax, or broker orders are assumed.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class RotationScenario:
    trades: pd.DataFrame
    status: str
    sell_dkk: float = 0.0
    buy_dkk: float = 0.0


def _asset_group(value: object) -> str:
    text = str(value).strip().casefold()
    if text in {"stock", "equity", "aktie"}:
        return "Aktie"
    if text in {"etf", "fund", "fond"}:
        return "ETF"
    return ""


def review_rotation_sources(plan: pd.DataFrame, score_ceiling: float = 55.0) -> pd.DataFrame:
    """List review candidates, NOT automatic sell signals.

    A weak Hold is eligible for manual scenario modelling, not execution.
    An unconfirmed Reducer is likewise a review item, not an order.
    """
    required = {"Aktiv", "Nuværende vægt", "Decision Score", "Handling", "Asset_Type", "Account"}
    if plan.empty or not required.issubset(plan.columns):
        return pd.DataFrame(columns=["Aktiv", "Account", "Asset_Type", "Decision Score", "Handling"])
    data = plan.copy()
    weight = pd.to_numeric(data["Nuværende vægt"], errors="coerce")
    score = pd.to_numeric(data["Decision Score"], errors="coerce")
    eligible = (
        weight.gt(0.02)
        & score.notna()
        & ((data["Handling"].eq("Reducer")) | (data["Handling"].eq("Hold") & score.lt(score_ceiling)))
        & data["Account"].fillna("").astype(str).str.strip().ne("")
        & data["Asset_Type"].map(_asset_group).ne("")
    )
    return (
        data.loc[eligible, ["Aktiv", "Account", "Asset_Type", "Decision Score", "Handling"]]
        .sort_values(["Decision Score", "Aktiv"])
        .reset_index(drop=True)
    )


def build_rotation_scenario(
    plan: pd.DataFrame,
    *,
    source_asset: str,
    buy_assets: list[str],
    active_market_value_dkk: float,
    sale_weight: float = 0.02,
    minimum_position_weight: float = 0.02,
    maximum_position_weight: float = 0.12,
    maximum_sector_weight: float = 0.20,
    minimum_trade_dkk: float = 5_000.0,
) -> RotationScenario:
    """Model a deliberate, same-account rotation using confirmed buy targets.

    Uses *current* weights as the baseline, rather than silently including the
    otherwise-unfunded rebalance buys. The sale is reduced to the amount that
    can actually be reinvested under the current model targets and risk caps.
    No cash balance or tax basis is inferred.
    """
    empty = pd.DataFrame(columns=[
        "Aktiv", "Konto", "Aktivklasse", "Handling", "Handel DKK",
        "Nuværende vægt", "Scenarievægt", "Decision Score", "Kommentar",
    ])

    def blocked(reason: str) -> RotationScenario:
        return RotationScenario(trades=empty.copy(), status=reason)

    required = {
        "Aktiv", "Nuværende vægt", "Modelmålvægt", "Decision Score",
        "Handling", "Rebalance handling", "Handel DKK", "Asset_Type",
        "Account", "Sector", "AI",
    }
    if not required.issubset(plan.columns):
        return blocked("Mangler nødvendige positions-, konto- eller sektordata – ingen rotation beregnet.")
    if (
        not pd.notna(active_market_value_dkk) or active_market_value_dkk <= 0
        or not 0 < maximum_position_weight <= 1
        or not 0 < maximum_sector_weight <= 1
        or not 0 <= minimum_position_weight < maximum_position_weight
        or sale_weight <= 0
        or minimum_trade_dkk <= 0
    ):
        return blocked("Ugyldige grænser eller aktiv porteføljeværdi.")

    data = plan.copy()
    for column in ["Nuværende vægt", "Modelmålvægt", "Decision Score", "Handel DKK", "AI"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data["Konto"] = data["Account"].fillna("").astype(str).str.strip()
    data["Gruppe"] = data["Asset_Type"].map(_asset_group)
    data["Sektor"] = data["Sector"].fillna("").astype(str).str.strip()

    if data["Aktiv"].duplicated().any():
        return blocked("Dublerede aktivnavne – konto og ticker skal identificere positionerne entydigt.")
    source = data.loc[data["Aktiv"].eq(source_asset)]
    if len(source) != 1:
        return blocked("Finansieringspositionen blev ikke fundet entydigt.")
    seller = source.iloc[0]
    account, group = seller["Konto"], seller["Gruppe"]
    if not account or not group:
        return blocked("Finansieringspositionen mangler gyldig konto eller aktivklasse.")
    if seller["Handling"] not in {"Hold", "Reducer"}:
        return blocked("Kun eksisterende Hold-/Reducer-positioner kan vælges til et manuelt salgsscenarie.")
    seller_weight = seller["Nuværende vægt"]
    if pd.isna(seller_weight) or seller_weight <= minimum_position_weight:
        return blocked("Positionen kan ikke reduceres uden at bryde minimumsvægten.")

    wanted = list(dict.fromkeys(str(name) for name in buy_assets))
    if not wanted or source_asset in wanted:
        return blocked("Vælg mindst én anden aktie eller ETF med bekræftet købssignal.")
    buyers = data.loc[data["Aktiv"].isin(wanted)].copy()
    if len(buyers) != len(wanted):
        return blocked("En eller flere købskandidater blev ikke fundet.")
    if not buyers["Konto"].eq(account).all() or not buyers["Gruppe"].eq(group).all():
        return blocked("Rotation mellem forskellige konti eller aktie-/ETF-universer er ikke tilladt.")
    if not (
        buyers["Handling"].eq("Øg").all()
        and buyers["Rebalance handling"].eq("Køb").all()
        and buyers["Handel DKK"].gt(0).all()
        and buyers["AI"].ge(70).all()
    ):
        return blocked("Kun allerede bekræftede Øg/Køb-signaler kan modtage rotationskapital.")

    if group == "Aktie":
        unknown = {"", "unknown", "ukendt", "other", "n/a", "none"}
        if any(s.casefold() in unknown for s in buyers["Sektor"]):
            return blocked("Mindst én købskandidat mangler verificeret sektor.")
    if (
        buyers["Nuværende vægt"].isna().any()
        or buyers["Modelmålvægt"].isna().any()
        or buyers["Decision Score"].isna().any()
    ):
        return blocked("Manglende vægte eller beslutningsscorer for købskandidater.")

    nav = float(active_market_value_dkk)
    sale_budget = min(float(sale_weight), float(seller_weight) - minimum_position_weight) * nav
    if sale_budget < minimum_trade_dkk:
        return blocked("Foreslået salg er mindre end minimumshandlen.")

    # All sector sums use the same global weight denominator as rebalance_engine.
    stock = data.loc[data["Gruppe"].eq("Aktie")]
    sector_weights = stock.groupby("Sektor")["Nuværende vægt"].sum().to_dict()
    requests: dict[str, float] = {}
    for _, buy in buyers.iterrows():
        current = float(buy["Nuværende vægt"])
        target = float(buy["Modelmålvægt"])
        headroom = max(0.0, min(target, maximum_position_weight) - current)
        requests[str(buy["Aktiv"])] = headroom * nav

    # Existing sector overweights must never generate an additional buy.
    # A sale in the SAME sector may release headroom.
    if group == "Aktie":
        for sector, sector_buyers in buyers.groupby("Sektor"):
            current_sector = float(sector_weights.get(sector, 0.0))
            released = (sale_budget / nav) if seller["Sektor"] == sector else 0.0
            cap_dkk = max(0.0, (maximum_sector_weight - current_sector + released) * nav)
            sum_requests = sum(requests[str(x)] for x in sector_buyers["Aktiv"])
            if sum_requests > cap_dkk and sum_requests > 0:
                scale = cap_dkk / sum_requests
                for name in sector_buyers["Aktiv"]:
                    requests[str(name)] *= scale

    # Allocate proportionally to unfilled model demand, then remove sub-minimum
    # purchases and redistribute. No proceeds from other accounts are used.
    eligible = {key: val for key, val in requests.items() if val >= minimum_trade_dkk}
    while eligible:
        total = sum(eligible.values())
        allocated = {key: min(demand, sale_budget * demand / total) for key, demand in eligible.items()}
        too_small = [key for key, amount in allocated.items() if amount < minimum_trade_dkk - 1e-7]
        if not too_small:
            break
        # Drop only the smallest allocation; the next round may make a
        # remaining buy large enough to clear minimum commission thresholds.
        smallest = min(too_small, key=lambda key: (allocated[key], key))
        eligible.pop(smallest)
    else:
        return blocked("Ingen købskandidater kan finansieres inden for minimumshandel og risikoloft.")

    actual_sale = float(sum(allocated.values()))
    if actual_sale < minimum_trade_dkk or actual_sale / nav > seller_weight - minimum_position_weight + 1e-10:
        return blocked("Rotationen kan ikke gennemføres inden for positions- og handelsgrænser.")

    lines = [{
        "Aktiv": source_asset,
        "Konto": account,
        "Aktivklasse": group,
        "Handling": "Sælg (scenarie)",
        "Handel DKK": -actual_sale,
        "Nuværende vægt": seller_weight,
        "Scenarievægt": seller_weight - actual_sale / nav,
        "Decision Score": seller["Decision Score"],
        "Kommentar": "Manuel finansieringskilde – ikke et automatisk salgssignal",
    }]
    for _, buyer in buyers.sort_values(["Decision Score", "Aktiv"], ascending=[False, True]).iterrows():
        name = str(buyer["Aktiv"])
        if name not in allocated:
            continue
        amount = float(allocated[name])
        lines.append({
            "Aktiv": name,
            "Konto": account,
            "Aktivklasse": group,
            "Handling": "Køb (scenarie)",
            "Handel DKK": amount,
            "Nuværende vægt": buyer["Nuværende vægt"],
            "Scenarievægt": buyer["Nuværende vægt"] + amount / nav,
            "Decision Score": buyer["Decision Score"],
            "Kommentar": "Bekræftet købssignal, begrænset af model- og risikoloft",
        })

    return RotationScenario(
        trades=pd.DataFrame(lines),
        status="Kapitalneutral scenarieberegning – før kurtage, spread, valuta og skat. Ingen ordrer.",
        sell_dkk=actual_sale,
        buy_dkk=actual_sale,
    )
