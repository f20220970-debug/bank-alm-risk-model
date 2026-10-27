"""A stylised bank balance sheet (amounts in INR crore). Illustrative, not any real bank.

Each line: amount, rate type, coupon, maturity (years), repricing (years, for floating lines),
plus liquidity attributes used by the LCR. Non-maturity deposits use a behavioural maturity
(the time they are expected to stay), as banks do for IRRBB.
"""
import pandas as pd

LINES = [
    # side, name, amount, type, coupon, maturity_y, reprice_y, hqla_level, runoff_or_inflow, flow_type
    ("asset", "Cash and central bank reserves", 2500, "float", 0.000, 0.01, 0.01, "L1", 0.00, "none"),
    ("asset", "Government bonds 2y", 3000, "fixed", 0.068, 2, None, "L1", 0.00, "none"),
    ("asset", "Government bonds 10y", 2000, "fixed", 0.072, 10, None, "L1", 0.00, "none"),
    ("asset", "Corporate bonds AA 5y", 3000, "fixed", 0.078, 5, None, "L2A", 0.00, "none"),
    ("asset", "Home loans (fixed) 15y", 5000, "fixed", 0.088, 15, None, None, 0.00, "none"),
    ("asset", "Home loans (repo-linked, reprice 3m)", 17000, "float", 0.086, 20, 0.25, None, 0.00, "none"),
    ("asset", "Corporate loans (floating 3m)", 22000, "float", 0.095, 3, 0.25, None, 0.50, "inflow"),
    ("asset", "Personal loans 3y", 9000, "fixed", 0.135, 3, None, None, 0.50, "inflow"),
    ("liability", "Retail deposits - stable", 22000, "fixed", 0.035, 4, None, None, 0.05, "outflow"),
    ("liability", "Retail deposits - less stable", 12000, "fixed", 0.045, 1.5, None, None, 0.10, "outflow"),
    ("liability", "Term deposits 1y", 4000, "fixed", 0.068, 1, None, None, 0.00, "none"),
    ("liability", "Corporate deposits (non-operational)", 12500, "fixed", 0.060, 0.5, None, None, 0.40, "outflow"),
    ("liability", "Wholesale funding (floating 3m)", 4500, "float", 0.072, 1, 0.25, None, 0.40, "outflow"),
    ("liability", "Senior bonds 5y", 3000, "fixed", 0.078, 5, None, None, 0.00, "none"),
]
TIER1_CAPITAL = 5500         # equity / Tier 1 capital (INR crore)


def load() -> pd.DataFrame:
    cols = ["side", "name", "amount", "type", "coupon", "maturity_y", "reprice_y", "hqla", "rate_30d", "flow"]
    return pd.DataFrame(LINES, columns=cols)
