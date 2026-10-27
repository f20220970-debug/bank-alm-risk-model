"""Liquidity Coverage Ratio (Basel III): HQLA / net cash outflows over 30 stressed days.

HQLA: Level 1 at 100%; Level 2A at 85% (15% haircut) and capped at 40% of total HQLA.
Outflows: balance x run-off rate. Inflows: balance x inflow rate on contractual inflows due
within 30 days (here 1/12 of performing loan balances), capped at 75% of outflows.
"""
import pandas as pd

L2A_HAIRCUT, L2_CAP, INFLOW_CAP = 0.15, 0.40, 0.75


def lcr(bs: pd.DataFrame, runoff_mult: float = 1.0, hqla_haircut_add: float = 0.0) -> dict:
    l1 = bs.loc[bs["hqla"] == "L1", "amount"].sum() * (1 - hqla_haircut_add)
    l2a = bs.loc[bs["hqla"] == "L2A", "amount"].sum() * (1 - L2A_HAIRCUT - hqla_haircut_add)
    l2a = min(l2a, L2_CAP / (1 - L2_CAP) * l1)        # L2 can be at most 40% of the stock
    hqla = l1 + l2a
    out = (bs.loc[bs["flow"] == "outflow", "amount"] * (bs.loc[bs["flow"] == "outflow", "rate_30d"] * runoff_mult).clip(upper=1)).sum()
    inflow = (bs.loc[bs["flow"] == "inflow", "amount"] / 12 * bs.loc[bs["flow"] == "inflow", "rate_30d"]).sum()
    net = out - min(inflow, INFLOW_CAP * out)
    ratio = hqla / net
    return {"hqla": hqla, "outflows": out, "inflows": inflow, "net_outflows": net, "lcr": ratio,
            "rag": "Green" if ratio >= 1.10 else "Amber" if ratio >= 1.00 else "Red"}
