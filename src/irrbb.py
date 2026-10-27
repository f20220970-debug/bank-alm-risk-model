"""Interest rate risk in the banking book (IRRBB): economic value of equity (EVE) and net
interest income (NII) under the six Basel standard shock scenarios.

Cash flows: fixed lines pay annual coupons and repay at maturity; floating lines are treated as
repaying at their next repricing date (standard for EVE). Discounting uses a zero curve with
continuous compounding. Shock shapes follow the Basel IRRBB standard (2016):
  parallel up/down; short up/down (decays with maturity, factor e^(-t/4));
  steepener = -0.65*|short| + 0.9*|long|; flattener = +0.8*|short| - 0.6*|long|.
Shock sizes use the Basel INR calibration: parallel 400bp, short 500bp, long 300bp.
"""
import numpy as np
import pandas as pd

TENORS = np.array([0.25, 0.5, 1, 2, 3, 5, 7, 10, 15, 20])
BASE_ZERO = np.array([6.55, 6.60, 6.70, 6.85, 6.95, 7.05, 7.12, 7.20, 7.28, 7.32]) / 100   # illustrative INR curve
SHOCK = {"parallel": 0.04, "short": 0.05, "long": 0.03}


def shock_curve(t: np.ndarray, scenario: str) -> np.ndarray:
    s_short = SHOCK["short"] * np.exp(-t / 4)
    s_long = SHOCK["long"] * (1 - np.exp(-t / 4))
    return {"base": 0 * t,
            "parallel up": SHOCK["parallel"] + 0 * t, "parallel down": -SHOCK["parallel"] + 0 * t,
            "short up": s_short, "short down": -s_short,
            "steepener": -0.65 * s_short + 0.9 * s_long,
            "flattener": 0.8 * s_short - 0.6 * s_long}[scenario]


SCENARIOS = ["parallel up", "parallel down", "short up", "short down", "steepener", "flattener"]


def zero_rate(t, scenario="base"):
    t = np.asarray(t, dtype=float)
    r = np.interp(t, TENORS, BASE_ZERO) + shock_curve(t, scenario)
    return np.maximum(r, 0.0)          # floor at zero


def cashflows(row) -> list:
    if row["type"] == "float":
        t = row["reprice_y"]
        return [(t, row["amount"] * (1 + row["coupon"] * t))]
    years = np.arange(1, int(np.ceil(row["maturity_y"])) + 1, dtype=float)
    years[-1] = row["maturity_y"]
    flows = [(t, row["amount"] * row["coupon"]) for t in years]
    flows[-1] = (years[-1], flows[-1][1] + row["amount"])
    return flows


def pv(row, scenario="base") -> float:
    return sum(cf * np.exp(-zero_rate(t, scenario) * t) for t, cf in cashflows(row))


def eve(bs: pd.DataFrame, scenario="base") -> float:
    sign = np.where(bs["side"] == "asset", 1, -1)
    return float(sum(s * pv(r, scenario) for s, (_, r) in zip(sign, bs.iterrows())))


def delta_eve(bs: pd.DataFrame) -> pd.DataFrame:
    base = eve(bs)
    return pd.DataFrame([{"scenario": s, "eve": eve(bs, s), "delta_eve": eve(bs, s) - base} for s in SCENARIOS])


def delta_nii(bs: pd.DataFrame, shift: float, horizon=1.0) -> float:
    """12-month NII change for a parallel shift: lines that reprice or mature within the horizon
    earn/pay the new rate for the remainder of the year (repricing-gap method)."""
    total = 0.0
    for _, r in bs.iterrows():
        t = r["reprice_y"] if r["type"] == "float" else r["maturity_y"]
        if t < horizon:
            sign = 1 if r["side"] == "asset" else -1
            total += sign * r["amount"] * shift * (horizon - t)
    return total


def repricing_gap(bs: pd.DataFrame, buckets=(0.25, 1, 3, 5, 10, 30)) -> pd.DataFrame:
    rows, lo = [], 0
    for hi in buckets:
        t = np.where(bs["type"] == "float", bs["reprice_y"], bs["maturity_y"])
        m = (t > lo) & (t <= hi)
        a = bs.loc[m & (bs["side"] == "asset"), "amount"].sum()
        l = bs.loc[m & (bs["side"] == "liability"), "amount"].sum()
        rows.append({"bucket": f"{lo}-{hi}y", "assets": a, "liabilities": l, "gap": a - l})
        lo = hi
    return pd.DataFrame(rows)
