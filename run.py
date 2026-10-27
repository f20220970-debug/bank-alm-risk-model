"""Run the bank balance-sheet risk model: IRRBB (EVE and NII), LCR under stress, and checks.

    python run.py      -> results/*.csv, results/summary.md, charts/*.png
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

import balance_sheet as B  # noqa: E402
import irrbb as I  # noqa: E402
import lcr as L  # noqa: E402
import validation as V  # noqa: E402


def main():
    bs = B.load(); t1 = B.TIER1_CAPITAL
    (ROOT / "results").mkdir(exist_ok=True); (ROOT / "charts").mkdir(exist_ok=True)
    dEVE = I.delta_eve(bs); dEVE["share_of_tier1"] = dEVE["delta_eve"] / t1
    nii = pd.DataFrame([{"shift_bp": bp, "delta_nii_12m": I.delta_nii(bs, bp / 10000)} for bp in (-200, -100, 100, 200)])
    gap = I.repricing_gap(bs)
    stress = pd.DataFrame([{"scenario": n, **L.lcr(bs, m, h)} for n, m, h in
                           [("Basel standard", 1.0, 0.0), ("Severe deposit run (1.5x run-off)", 1.5, 0.0),
                            ("Run + 10% HQLA price fall", 1.5, 0.10), ("Extreme (2x run-off, 10% HQLA fall)", 2.0, 0.10)]])
    checks = {"balance": V.balance_check(bs, t1), "pv01": V.pv01_check(bs), "outlier": V.outlier_test(dEVE, t1)}
    hedge = V.rebalance_search(bs, t1) if checks["outlier"]["breach"] else None
    for name, df in {"delta_eve": dEVE, "delta_nii": nii, "repricing_gap": gap, "lcr_stress": stress}.items():
        df.round(4).to_csv(ROOT / f"results/{name}.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(dEVE["scenario"], 100 * dEVE["share_of_tier1"], color=["#C0392B" if v < 0 else "#2C7A7B" for v in dEVE["delta_eve"]])
    ax.axhline(-15, ls="--", color="grey"); ax.text(-0.4, -14, "outlier limit: -15% of Tier 1", fontsize=8)
    ax.set_ylabel("Change in EVE (% of Tier 1)"); ax.set_title("EVE under the six Basel rate shocks"); plt.xticks(rotation=20)
    fig.tight_layout(); fig.savefig(ROOT / "charts/delta_eve.png", dpi=120); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(gap["bucket"], gap["gap"], color="#1F3A5F"); ax.axhline(0, color="black", lw=0.8)
    ax.set_ylabel("Assets - liabilities repricing (INR cr)"); ax.set_title("Repricing gap by time bucket")
    fig.tight_layout(); fig.savefig(ROOT / "charts/repricing_gap.png", dpi=120); plt.close(fig)

    o, p = checks["outlier"], checks["pv01"]
    base, worst_lcr = stress.iloc[0], stress.iloc[-1]
    up100 = nii.set_index("shift_bp").loc[100, "delta_nii_12m"]
    lines = ["# Results summary", "",
             f"- Balance sheet: INR {bs.loc[bs.side == 'asset', 'amount'].sum():,} cr assets, Tier 1 INR {t1:,} cr; balanced: {checks['balance']['balanced']}.",
             "- EVE change by Basel shock (% of Tier 1): " + ", ".join(f"{r.scenario} {100 * r.share_of_tier1:+.1f}%" for r in dEVE.itertuples()) + ".",
             f"- Supervisory outlier test: worst case is {o['worst_scenario']} at {100 * o['share_of_tier1']:.1f}% of Tier 1 "
             f"({'BREACH of' if o['breach'] else 'within'} the 15% limit).",
             (f"- Fix: moving INR {hedge['moved']:,} cr from 10-year to 2-year government bonds brings every shock within the limit "
              f"(worst becomes {hedge['worst_scenario']} at {100 * hedge['share_of_tier1']:.1f}% of Tier 1); a single pay-fixed swap was tested "
              f"but cures the steepener only by breaching short-down." if hedge and hedge.get("moved") is not None else "- No fix needed."),
             f"- NII: a +100bp parallel move changes 12-month NII by INR {up100:+,.0f} cr (short-dated assets reprice faster than deposits).",
             f"- PV01 check: EVE moves INR {p['eve_change_1bp']:,.1f} cr per +1bp; linear for small moves: {p['linear']}.",
             f"- LCR: {100 * base.lcr:.0f}% under Basel run-off rates ({base.rag}); " + "; ".join(f"{r.scenario} {100 * r.lcr:.0f}% ({r.rag})" for r in stress.iloc[1:].itertuples()) + ".",
             ]
    (ROOT / "results/summary.md").write_text("\n".join(lines) + "\n"); print("\n".join(lines))


if __name__ == "__main__":
    main()
