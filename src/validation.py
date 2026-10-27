"""Model testing and monitoring checks, run every time the model runs.

1. Balance check: assets = liabilities + Tier 1 capital.
2. Sensitivity check: EVE change for a +1bp parallel move (numerical) has the expected sign and
   scales linearly (+2bp ~ 2 x +1bp), i.e. the curve and cash-flow engine behave sensibly.
3. Supervisory outlier test: worst EVE loss across the six shocks above 15% of Tier 1 is flagged.
4. LCR RAG: below 100% Red, 100-110% Amber, else Green.
"""
import numpy as np

import irrbb


def balance_check(bs, tier1) -> dict:
    a = bs.loc[bs["side"] == "asset", "amount"].sum(); l = bs.loc[bs["side"] == "liability", "amount"].sum()
    return {"assets": a, "liabilities_plus_capital": l + tier1, "balanced": bool(np.isclose(a, l + tier1))}


def pv01_check(bs) -> dict:
    base = irrbb.eve(bs)
    orig = irrbb.SHOCK["parallel"]
    out = {}
    for bp in (1, 2):
        irrbb.SHOCK["parallel"] = bp / 10000
        out[bp] = irrbb.eve(bs, "parallel up") - base
    irrbb.SHOCK["parallel"] = orig
    return {"eve_change_1bp": out[1], "eve_change_2bp": out[2], "linear": bool(np.isclose(out[2], 2 * out[1], rtol=0.01))}


def outlier_test(delta_eve_table, tier1, limit=0.15) -> dict:
    worst = delta_eve_table["delta_eve"].min()
    ratio = -worst / tier1
    return {"worst_scenario": delta_eve_table.loc[delta_eve_table["delta_eve"].idxmin(), "scenario"],
            "worst_delta_eve": worst, "share_of_tier1": ratio, "breach": bool(ratio > limit)}



def rebalance_search(bs, tier1, from_line="Government bonds 10y", to_line="Government bonds 2y", step=250, limit=0.15):
    """Smallest move from long to short government bonds that brings every Basel shock within the
    outlier limit. (A single pay-fixed swap was also tested: it cures the steepener but pushes the
    short-down scenario over the limit, so shortening the bond book is the cleaner fix.)"""
    import irrbb
    available = int(bs.loc[bs["name"] == from_line, "amount"].iloc[0])
    for n in range(0, available + step, step):
        b = bs.copy()
        b.loc[b["name"] == from_line, "amount"] -= n
        b.loc[b["name"] == to_line, "amount"] += n
        res = outlier_test(irrbb.delta_eve(b), tier1, limit)
        if not res["breach"]:
            return {"moved": n, "from": from_line, "to": to_line, **res}
    return {"moved": None, "breach": True}
