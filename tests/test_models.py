import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import balance_sheet as B  # noqa: E402
import irrbb as I  # noqa: E402
import lcr as L  # noqa: E402
import validation as V  # noqa: E402


def test_balance_sheet_balances():
    assert V.balance_check(B.load(), B.TIER1_CAPITAL)["balanced"]


def test_zero_coupon_bond_pv():
    row = pd.Series({"type": "fixed", "amount": 100.0, "coupon": 0.0, "maturity_y": 2})
    assert I.pv(row) == pytest.approx(100 * np.exp(-I.zero_rate(2.0) * 2))


def test_parallel_up_lowers_long_fixed_asset_value():
    row = pd.Series({"side": "asset", "type": "fixed", "amount": 100.0, "coupon": 0.07, "maturity_y": 10})
    assert I.pv(row, "parallel up") < I.pv(row) < I.pv(row, "parallel down")


def test_shock_shapes():
    t = np.array([0.25, 20.0])
    assert I.shock_curve(t, "steepener")[0] < 0 < I.shock_curve(t, "steepener")[1]
    assert I.shock_curve(t, "flattener")[0] > 0 > I.shock_curve(t, "flattener")[1]


def test_lcr_falls_under_stress_and_l2_cap():
    bs = B.load()
    assert L.lcr(bs, 1.5)["lcr"] < L.lcr(bs)["lcr"]
    r = L.lcr(bs); assert r["net_outflows"] >= 0.25 * r["outflows"] - 1e-9   # inflow cap


def test_pv01_linear():
    assert V.pv01_check(B.load())["linear"]


def test_rebalance_search_finds_compliant_move():
    h = V.rebalance_search(B.load(), B.TIER1_CAPITAL)
    assert h["moved"] is not None and not h["breach"]
