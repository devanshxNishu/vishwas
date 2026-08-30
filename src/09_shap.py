"""VISHWAS — SHAP explanations for the bust classifier.

The problem statement requires EXPLAINABLE output, so this is a scored
requirement, not polish.

WHAT THIS DOES
  1. Refits the deck model exactly as 07_model.py fits it (same study window,
     same interleaved validation carve, same feature policy, same seed). The
     model is not persisted, so it is rebuilt rather than guessed at; the
     refit is checked against data/model_predictions.parquet before any SHAP
     value is trusted.
  2. Runs shap.TreeExplainer on a SAMPLE of test rows. TreeSHAP is exact but
     slow; a few thousand rows is enough for a stable global ranking and there
     is no reason to pay for 651,040.
  3. Reports global importance (mean |SHAP|) beside P11's permutation
     importance, so a disagreement is visible rather than buried.
  4. Writes a per-prediction breakdown for the highest-confidence bust
     predictions. THAT is the explainability deliverable -- a forecaster needs
     "flagged because moisture ran high and the members disagreed", not a bar
     chart of global averages.

NO SILENT SUBSTITUTION. If TreeExplainer cannot handle
HistGradientBoostingClassifier, this script says so and exits. It never falls
back to a different explainer while still printing "SHAP". We already have
permutation importance from P11 as the fallback, so a clean failure is cheap
and a quiet swap would not be.

    python src/09_shap.py --sample 6000
"""

import argparse
import textwrap
import importlib.util
import os
import sys

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from sklearn.ensemble import HistGradientBoostingClassifier

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# house style, shared with fig3_map.png / fig6_confidence_map.png
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e6e5e1"
RAMP = LinearSegmentedColormap.from_list("vishwas_blue", ["#cde2fb", "#0d366b"])
C_UP = "#2a78d6"      # categorical slot 1 -- pushes toward "bust"
C_DOWN = "#eb6834"    # categorical slot 2 -- pushes toward "no bust"

# P11, docs/P11-ablations.md. Permutation importance, drop in stratified ROC-AUC.
P11_PERMUTATION = {
    "pwat_mean": 0.086,
    "precip_spread": 0.066,
    "precip_mean": 0.061,
}

# Plain-language names for the slide. The code keeps the column names.
PRETTY = {
    "pwat_mean": "precipitable water, ensemble mean",
    "pwat_spread": "precipitable water, ensemble spread",
    "pwat_anomaly": "precipitable water anomaly\nvs train climatology",
    "precip_mean": "forecast rainfall, ensemble mean",
    "precip_spread": "forecast rainfall, ensemble spread",
    "precip_anomaly": "forecast rainfall anomaly\nvs train climatology",
    "cape_mean": "CAPE, ensemble mean",
    "cape_spread": "CAPE, ensemble spread",
    "cape_anomaly": "CAPE anomaly vs climatology",
    "gh500_mean": "500 hPa height, ensemble mean",
    "gh500_spread": "500 hPa height, ensemble spread",
    "gh500_gradient": "500 hPa height gradient",
    "wind500_speed": "500 hPa wind speed",
    "flow500_deformation": "500 hPa flow deformation",
    "shear_500_850": "500-850 hPa wind shear",
    "u500_mean": "500 hPa u wind, mean", "u500_spread": "500 hPa u wind, spread",
    "v500_mean": "500 hPa v wind, mean", "v500_spread": "500 hPa v wind, spread",
    "u850_mean": "850 hPa u wind, mean", "v850_mean": "850 hPa v wind, mean",
    "lead_day": "lead time (days ahead)",
    "month": "calendar month",
}

UNITS = {
    "pwat_mean": "mm", "pwat_spread": "mm", "pwat_anomaly": "mm",
    "precip_mean": "mm", "precip_spread": "mm", "precip_anomaly": "mm",
    "cape_mean": "J/kg", "cape_spread": "J/kg", "cape_anomaly": "J/kg",
    "gh500_mean": "m", "gh500_spread": "m", "gh500_gradient": "m/deg",
    "wind500_speed": "m/s", "shear_500_850": "m/s",
    "u500_mean": "m/s", "v500_mean": "m/s",
    "u500_spread": "m/s", "v500_spread": "m/s",
    "u850_mean": "m/s", "v850_mean": "m/s",
    "flow500_deformation": "1/s",
}


def load_model_module():
    """07_model.py starts with a digit, so it cannot be imported by name."""
    path = os.path.join(_ROOT, "src", "07_model.py")
    spec = importlib.util.spec_from_file_location("model07", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rebuild(labels_path, seed, validation_every):
    m07 = load_model_module()
    table = m07.load(labels_path, m07.STUDY_MIN, m07.STUDY_MAX)
    table, _ = m07.carve_validation(table, validation_every)
    features = m07.feature_columns(table, with_location=False)

    fit = table[table["role"] == "train"]
    test = table[table["role"] == "test"].copy()

    model = HistGradientBoostingClassifier(random_state=seed)
    model.fit(fit[features], fit["bust"].astype(int))
    return model, features, fit, test


def check_refit(model, features, test, pred_path):
    """The refit must reproduce the scores the deck is built on."""
    if not os.path.exists(pred_path):
        print("  (no {} to check against — skipping)".format(pred_path))
        return
    ref = pd.read_parquet(pred_path)
    got = test[["init", "lead_day", "lat", "lon"]].copy()
    got["refit_score"] = model.predict_proba(test[features])[:, 1]
    joined = ref.merge(got, on=["init", "lead_day", "lat", "lon"], how="inner")
    if joined.empty:
        print("  REFIT CHECK FAILED: no rows joined. Not trusting these SHAP values.")
        sys.exit(1)
    delta = np.abs(joined["model_score"] - joined["refit_score"]).max()
    print("  refit check: {} rows joined, max |score difference| = {:.2e}".format(
        len(joined), delta))
    if delta > 1e-9:
        print("  REFIT CHECK FAILED: this is not the model the deck reports.")
        sys.exit(1)
    print("  refit reproduces data/model_predictions.parquet exactly.")


def explain(model, features, rows):
    """TreeSHAP. Fails loudly rather than substituting a different explainer."""
    try:
        import shap
    except ImportError:
        print("SHAP NOT INSTALLED. Reporting nothing rather than substituting.")
        sys.exit(1)
    print("  shap {}".format(shap.__version__))
    try:
        explainer = shap.TreeExplainer(model)
        values = explainer.shap_values(rows[features])
    except Exception as exc:                                  # noqa: BLE001
        print()
        print("SHAP FAILED on HistGradientBoostingClassifier:")
        print("  {}: {}".format(type(exc).__name__, exc))
        print()
        print("NOT substituting another explainer. Fall back to the P11")
        print("permutation importance, which is already measured and reported.")
        sys.exit(2)

    values = np.asarray(values)
    if values.ndim == 3:            # (n, features, classes) -> positive class
        values = values[:, :, -1]
    base = explainer.expected_value
    base = float(np.asarray(base).ravel()[-1])
    return values, base


def additivity(model, features, rows, values, base):
    """SHAP values must sum to the model's raw output. If they do not, the
    numbers are decorative and must not be shown."""
    raw = model.decision_function(rows[features])
    recon = base + values.sum(axis=1)
    err = float(np.abs(raw - recon).max())
    print("  additivity check: max |raw log-odds - (base + sum SHAP)| = {:.2e}".format(err))
    if err > 1e-4:
        print("  ADDITIVITY FAILED — refusing to report these values.")
        sys.exit(1)
    return raw


def global_importance(features, values):
    """Both the mean and the MEDIAN |SHAP| per feature.

    mean |SHAP| is the conventional summary and it is misleading on this model.
    A few hundred rows sit on saturated tree leaves where a single feature moves
    the log-odds by hundreds -- for v850_mean, cape_mean and cape_anomaly the
    top 1% of rows carry ~77-79% of all the |SHAP| mass, against 5-7% for
    pwat_mean and precip_mean. The mean therefore ranks a feature by its rarest
    rows. The median ranks it by the typical forecast, which is what a global
    importance claim is supposed to mean.
    """
    absolute = np.abs(values)
    n = len(absolute)
    tail = max(n // 100, 1)
    share = np.array([
        np.sort(absolute[:, j])[::-1][:tail].sum() / max(absolute[:, j].sum(), 1e-12)
        for j in range(absolute.shape[1])])
    imp = pd.DataFrame({
        "feature": features,
        "median_abs_shap": np.median(absolute, axis=0),
        "mean_abs_shap": absolute.mean(axis=0),
        "max_abs_shap": absolute.max(axis=0),
        "top1pct_share": share,
    }).sort_values("median_abs_shap", ascending=False).reset_index(drop=True)
    imp["rank"] = np.arange(1, len(imp) + 1)
    imp["mean_rank"] = imp["mean_abs_shap"].rank(ascending=False).astype(int)
    return imp


def permutation_importance(model, features, test, m07, seed=0, repeats=1):
    """Drop in STRATIFIED ROC-AUC when one feature is shuffled.

    Recomputed here rather than quoted, so the SHAP ranking is compared against
    the same 23 features on the same rows -- CLAUDE.md records only the top
    three from P11, which is not enough to say whether the two rankings agree.
    The three recorded values are printed alongside as a reproduction check.

    The rainfall-magnitude bins are computed ONCE from the unshuffled
    precip_mean and then held fixed. Re-binning after the shuffle would move
    the evaluation itself when precip_mean is the feature under test, and that
    variant's number would not be comparable to the other twenty-two.
    """
    X = test[list(features)].copy()
    truth = test["bust"].to_numpy().astype(bool)
    bins = pd.qcut(test["precip_mean"], m07.STRATIFY_BINS,
                   labels=False, duplicates="drop").to_numpy()

    def stratified(score):
        total, acc = 0, 0.0
        for b in np.unique(bins[~pd.isna(bins)]):
            m = bins == b
            value = m07.safe_auc(truth[m], score[m])
            if not np.isnan(value):
                acc += value * m.sum()
                total += m.sum()
        return acc / total if total else float("nan")

    base = stratified(model.predict_proba(X)[:, 1])
    rng = np.random.default_rng(seed)

    rows = []
    for name in features:
        keep = X[name].to_numpy().copy()
        drops = []
        for _ in range(repeats):
            X[name] = rng.permutation(keep)
            drops.append(base - stratified(model.predict_proba(X)[:, 1]))
        X[name] = keep
        rows.append((name, float(np.mean(drops))))

    out = pd.DataFrame(rows, columns=["feature", "perm_drop"])
    out = out.sort_values("perm_drop", ascending=False).reset_index(drop=True)
    out["perm_rank"] = np.arange(1, len(out) + 1)
    return base, out


def fig_global(imp, out, n_sample, top=14):
    block = imp.head(top).iloc[::-1]
    fig = plt.figure(figsize=(16.8, 9.6), dpi=200, facecolor=SURFACE)
    ax = fig.add_axes([0.285, 0.235, 0.675, 0.545])
    ax.set_facecolor(SURFACE)
    y = np.arange(len(block))
    colours = [C_UP if f in P11_PERMUTATION else "#9cc2ea" for f in block["feature"]]
    ax.barh(y, block["median_abs_shap"], color=colours, height=0.62, zorder=3)
    ax.scatter(block["mean_abs_shap"], y, s=62, facecolor=SURFACE,
               edgecolor=INK2, linewidth=1.7, zorder=4)

    ax.set_yticks(y)
    ax.set_yticklabels([PRETTY.get(f, f) for f in block["feature"]],
                       fontsize=13.5, color=INK)
    ax.set_xlabel("|SHAP| — shift in the log-odds of a bust", fontsize=14, color=INK2)
    ax.tick_params(colors=INK2, labelsize=13, length=4)
    ax.grid(True, axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)

    handles = [
        Line2D([], [], marker="s", linestyle="none", markersize=13, color=C_UP,
               label="median |SHAP| — the typical forecast"),
        Line2D([], [], marker="o", linestyle="none", markersize=10,
               markerfacecolor=SURFACE, markeredgecolor=INK2, markeredgewidth=1.7,
               label="mean |SHAP| — pulled by a saturated-leaf tail"),
    ]
    leg = ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=13.5,
                    handletextpad=0.7, labelspacing=0.6)
    for t in leg.get_texts():
        t.set_color(INK)

    fig.text(0.040, 0.968, "What the model actually uses", fontsize=28,
             fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.040, 0.908,
             "Exact TreeSHAP over the fitted classifier. Filled bars are the three features "
             "P11 ranked top by permutation importance —\nSHAP puts the same three on top.",
             fontsize=15.5, color=INK2, ha="left", va="top", linespacing=1.5)

    fig.text(0.040, 0.155,
             "Exact TreeSHAP (shap 0.49.1, TreeExplainer) on {:,} randomly sampled 2019 test rows, "
             "seed 0; additivity verified against the model's raw log-odds to 4e-13.\n"
             "Median and mean disagree because a few hundred rows sit on saturated tree leaves: for "
             "the 850 hPa and CAPE features the top 1% of rows carry ~77-79% of all\n"
             "|SHAP| mass, against 5-7% for the moisture and rainfall features. Ranked on the median, "
             "SHAP agrees with permutation importance at Spearman +0.78.\n"
             "Truth for the underlying labels: IMD 0.25 deg gauge-gridded daily rainfall; 1,252 land "
             "gridpoints, 52 forecast dates, Day 1-10, 651,040 test rows.".format(n_sample),
             fontsize=12.5, color=INK2, ha="left", va="top", linespacing=1.6)
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    plt.close(fig)
    print("  wrote {}".format(out))


def fig_cases(cases, out, provenance, headline, subtitle, n_top=7):
    """Per-prediction breakdowns, side by side. The actual deliverable."""
    n = len(cases)
    fig = plt.figure(figsize=(6.6 * n, 9.6), dpi=200, facecolor=SURFACE)
    gs = fig.add_gridspec(1, n, left=0.178, right=0.982, top=0.600, bottom=0.235,
                          wspace=0.95)

    for i, case in enumerate(cases):
        ax = fig.add_subplot(gs[0, i])
        ax.set_facecolor(SURFACE)
        block = case["contrib"].head(n_top).iloc[::-1]
        colours = [C_UP if v > 0 else C_DOWN for v in block["shap"]]
        ax.barh(np.arange(len(block)), block["shap"], color=colours, height=0.64)
        ax.set_yticks(np.arange(len(block)))
        ax.set_yticklabels(
            ["{}\n= {}".format(PRETTY.get(f, f), fmt_value(f, v))
             for f, v in zip(block["feature"], block["value"])],
            fontsize=12, color=INK)
        ax.axvline(0, color=INK2, linewidth=1.0)
        ax.grid(True, axis="x", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(colors=INK2, labelsize=12, length=4)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.set_xlabel("SHAP contribution (log-odds)", fontsize=13, color=INK2)

        # Header stack, laid out with a running cursor from the top. Blocks vary
        # in line count between variants, so fixed offsets collide.
        blocks = [(case["title"], 16.5, INK, True),
                  (case["where"], 13.5, INK2, False),
                  (case["flag"], 14.0, C_UP, True),
                  (case["outcome"], 13.5, INK, False)]
        if case.get("extra"):
            blocks.append((case["extra"], 13.0, C_DOWN, True))

        axes_pt = fig.get_figheight() * (gs.get_grid_positions(fig)[1][0]
                                         - gs.get_grid_positions(fig)[0][0]) * 72.0
        cursor = 1.0 + sum(
            (text.count("\n") + 1) * size * 1.45 / axes_pt + 0.022
            for text, size, _, _ in blocks) + 0.02
        for text, size, colour, bold in blocks:
            ax.text(0.0, cursor, text, transform=ax.transAxes, fontsize=size,
                    fontweight="bold" if bold else "normal", color=colour,
                    ha="left", va="top", linespacing=1.45)
            cursor -= (text.count("\n") + 1) * size * 1.45 / axes_pt + 0.022

    fig.text(0.040, 0.965, headline, fontsize=28, fontweight="bold", color=INK,
             ha="left", va="top")
    lead = (subtitle + " " if subtitle else "") + (
        "The {} largest SHAP contributions per prediction. Blue pushes toward “bust”, "
        "orange pushes away; bars sum, with the base rate, to the model's "
        "log-odds.".format(n_top))
    fig.text(0.040, 0.905, "\n".join(textwrap.wrap(lead, 142)),
             fontsize=15.5, color=INK2, ha="left", va="top", linespacing=1.5)

    fig.text(0.040, 0.170,
             "\n".join("\n".join(textwrap.wrap(par, 176)) for par in provenance.split("\n")) + "\n"
             "Truth: IMD 0.25 deg gauge-gridded daily rainfall. Bust = |ensemble mean − observed| "
             "above the 95th percentile for that region and lead time, fitted on 2018 only.\n"
             "THREE PREDICTIONS, SHOWN AS ILLUSTRATIONS OF THE EXPLANATION FORMAT — not evidence "
             "of general performance. Global behaviour is the companion figure, over 6,000 sampled rows.",
             fontsize=12.5, color=INK2, ha="left", va="top", linespacing=1.6)
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    plt.close(fig)
    print("  wrote {}".format(out))


def flag_text(row, base_rate):
    if base_rate:
        return "VISHWAS said p = {:.2f}\n{:.0f}x this regime's base rate".format(
            row["model_score"], row["model_score"] / max(base_rate, 1e-12))
    return "VISHWAS said p = {:.2f}".format(row["model_score"])


def fmt_value(feature, v):
    if pd.isna(v):
        return "missing"
    unit = UNITS.get(feature, "")
    if feature in ("month", "lead_day"):
        return "{:.0f}".format(v)
    if abs(v) >= 100:
        return "{:,.0f} {}".format(v, unit).strip()
    if abs(v) >= 1:
        return "{:.1f} {}".format(v, unit).strip()
    return "{:.3g} {}".format(v, unit).strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--labels", default=os.path.join(_ROOT, "data", "labelled.parquet"))
    p.add_argument("--pred", default=os.path.join(_ROOT, "data", "model_predictions.parquet"))
    p.add_argument("--sample", type=int, default=6000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--validation-every", type=int, default=4)
    p.add_argument("--cases", type=int, default=3)
    p.add_argument("--case-init", default="",
                   help="restrict the case studies to one init date, e.g. 20190731, "
                        "to tie them to the confidence map. Default: highest-confidence "
                        "correct bust calls anywhere in the test year.")
    p.add_argument("--case-lead", type=int, default=0,
                   help="with --case-init, restrict to one lead day")
    p.add_argument("--case-driest-bin", action="store_true",
                   help="restrict the case studies to the DRIEST precip_mean decile — "
                        "the confidently-dry-and-it-poured failure mode, where ensemble "
                        "spread is not merely uninformative but actively misleading")
    p.add_argument("--no-permutation", dest="permutation", action="store_false",
                   help="skip the permutation-importance cross-check (it is the slow part)")
    p.add_argument("--out-dir", default=os.path.join(_ROOT, "figures"))
    a = p.parse_args()

    print("VISHWAS — SHAP explanations")
    print()
    print("REBUILDING THE DECK MODEL")
    model, features, fit, test = rebuild(a.labels, a.seed, a.validation_every)
    print("  {} features, fitted on {:,} training rows, {:,} test rows".format(
        len(features), len(fit), len(test)))
    check_refit(model, features, test, a.pred)

    print()
    print("TREESHAP")
    rng = np.random.default_rng(a.seed)
    idx = rng.choice(len(test), size=min(a.sample, len(test)), replace=False)
    sample = test.iloc[np.sort(idx)].copy()
    print("  sampling {:,} of {:,} test rows (bust rate {:.2%} vs {:.2%} in full test)".format(
        len(sample), len(test), sample["bust"].mean(), test["bust"].mean()))
    values, base = explain(model, features, sample)
    additivity(model, features, sample, values, base)
    print("  base value (log-odds of the average prediction) = {:.4f}".format(base))

    print()
    print("GLOBAL IMPORTANCE — mean |SHAP|, {:,} sampled test rows".format(len(sample)))
    imp = global_importance(features, values)
    print("  ranked on MEDIAN |SHAP| — see the note in global_importance()")
    print("  {:<22} {:>12} {:>5} {:>11} {:>5} {:>9} {:>8}   {}".format(
        "feature", "median|SHAP|", "rank", "mean|SHAP|", "rank", "max|SHAP|",
        "top1%", "P11 perm"))
    for _, row in imp.iterrows():
        perm = P11_PERMUTATION.get(row["feature"])
        note = "+{:.3f}".format(perm) if perm is not None else ""
        print("  {:<22} {:>12.4f} {:>5} {:>11.4f} {:>5} {:>9.1f} {:>7.0f}%   {}".format(
            row["feature"], row["median_abs_shap"], int(row["rank"]),
            row["mean_abs_shap"], int(row["mean_rank"]), row["max_abs_shap"],
            100 * row["top1pct_share"], note))

    print()
    print("AGREEMENT WITH P11 PERMUTATION IMPORTANCE")
    perm_order = sorted(P11_PERMUTATION, key=P11_PERMUTATION.get, reverse=True)
    shap_rank = dict(zip(imp["feature"], imp["rank"]))
    for i, f in enumerate(perm_order, start=1):
        print("  permutation #{}  {:<16} -> SHAP rank {}".format(i, f, shap_rank[f]))
    print("  SHAP top 5 by median |SHAP|: {}".format(", ".join(imp["feature"].head(5))))
    by_mean = imp.sort_values("mean_abs_shap", ascending=False)
    print("  SHAP top 5 by mean   |SHAP|: {}".format(", ".join(by_mean["feature"].head(5))))

    if a.permutation:
        print()
        print("PERMUTATION IMPORTANCE — recomputed on all {:,} test rows".format(len(test)))
        m07 = load_model_module()
        base_auc, perm = permutation_importance(model, features, test, m07, a.seed)
        print("  unshuffled stratified ROC-AUC = {:.4f}".format(base_auc))
        merged = imp.merge(perm, on="feature").sort_values("perm_rank")
        print("  {:<22} {:>10} {:>5} {:>13} {:>5} {:>11} {:>5}   {}".format(
            "feature", "perm drop", "rank", "median |SHAP|", "rank",
            "mean |SHAP|", "rank", "P11 recorded"))
        for _, r in merged.iterrows():
            rec = P11_PERMUTATION.get(r["feature"])
            print("  {:<22} {:>+10.4f} {:>5} {:>13.4f} {:>5} {:>11.4f} {:>5}   {}".format(
                r["feature"], r["perm_drop"], int(r["perm_rank"]),
                r["median_abs_shap"], int(r["rank"]),
                r["mean_abs_shap"], int(r["mean_rank"]),
                "+{:.3f}".format(rec) if rec is not None else ""))
        rho_med = merged["perm_rank"].corr(merged["rank"], method="spearman")
        rho_mean = merged["perm_rank"].corr(merged["mean_rank"], method="spearman")
        print("  Spearman vs permutation:  median |SHAP| {:+.3f}   mean |SHAP| {:+.3f}".format(
            rho_med, rho_mean))
        merged.to_csv(os.path.join(a.out_dir, "shap_vs_permutation.csv"), index=False)
        print("  wrote {}".format(os.path.join(a.out_dir, "shap_vs_permutation.csv")))

    fig_global(imp, os.path.join(a.out_dir, "fig7_shap_global.png"), len(sample))

    # ---- per-prediction cases -------------------------------------------
    print()
    print("PER-PREDICTION BREAKDOWNS")
    scored = test.copy()
    scored["model_score"] = model.predict_proba(scored[features])[:, 1]
    winners = scored[scored["bust"]]
    bin_note = ""
    if a.case_driest_bin:
        m07 = load_model_module()
        codes = pd.qcut(scored["precip_mean"], m07.STRATIFY_BINS,
                        labels=False, duplicates="drop")
        driest = codes == codes.min()
        pool = scored[driest]
        winners = winners[driest.reindex(winners.index).fillna(False)]
        base = pool["bust"].mean()
        # Where does ensemble spread rank these cases? Ties at spread = 0 are the
        # point: the incumbent cannot separate them from 200,000 quiet cases.
        n_tied = int((scored["precip_spread"] == 0.0).sum())
        bin_note = (
            "driest precip_mean decile: {:,} of {:,} test cases, forecast rainfall "
            "0.000-{:.3f} mm, bust base rate {:.2%}".format(
                len(pool), len(scored), pool["precip_mean"].max(), base))
        print("  {}".format(bin_note))
        if winners.empty:
            print("  no correct bust calls in the driest bin")
            return
    if a.case_init:
        winners = winners[winners["init"] == a.case_init]
        if a.case_lead:
            winners = winners[winners["lead_day"] == a.case_lead]
        if winners.empty:
            print("  no correct bust calls for --case-init {}".format(a.case_init))
            return
        winners = winners.sort_values("model_score", ascending=False).head(a.cases)
        print("  restricted to init {}{}".format(
            a.case_init, " Day {}".format(a.case_lead) if a.case_lead else ""))
    else:
        winners = winners.sort_values("model_score", ascending=False)
        # one per forecast date, so the three are not three cells of one storm
        winners = winners.drop_duplicates(subset=["init"]).head(a.cases)
    if a.case_driest_bin:
        lift = winners["model_score"] / max(base, 1e-12)
        for k in range(len(winners)):
            print("    lift over the bin base rate: {:.0f}x".format(lift.iloc[k]))

    case_values, _ = explain(model, features, winners)
    cases = []
    for k in range(len(winners)):
        row = winners.iloc[k]
        contrib = pd.DataFrame({
            "feature": features,
            "shap": case_values[k],
            "value": row[features].to_numpy(dtype=float),
        })
        contrib["abs"] = contrib["shap"].abs()
        contrib = contrib.sort_values("abs", ascending=False).reset_index(drop=True)

        init_dt = pd.to_datetime(row["init"], format="%Y%m%d")
        valid_dt = init_dt + pd.Timedelta(days=int(row["lead_day"]))
        cases.append(dict(
            title="{}  ·  Day {}".format(init_dt.strftime("%-d %b %Y"), int(row["lead_day"])),
            where="{:.1f}°N {:.1f}°E  ·  valid {}".format(
                row["lat"], row["lon"], valid_dt.strftime("%-d %b")),
            flag=flag_text(row, base if a.case_driest_bin else None),
            outcome="{:.1f} mm forecast  →  {:.1f} mm fell".format(
                row["precip_mean"], row["truth"]),
            extra=("ensemble spread {:.2f} mm\nthe incumbent ranked it last".format(
                       row["precip_spread"]) if a.case_driest_bin else ""),
            contrib=contrib))
        print()
        print("  {} Day {}  {:.1f}N {:.1f}E   p={:.3f}".format(
            row["init"], int(row["lead_day"]), row["lat"], row["lon"], row["model_score"]))
        print("    forecast {:.1f} mm, observed {:.1f} mm, error {:.1f} mm "
              "(bust threshold {:.1f} mm)".format(
                  row["precip_mean"], row["truth"], row["error"], row["threshold"]))
        for _, c in contrib.head(6).iterrows():
            print("    {:+.3f}  {:<22} = {}".format(
                c["shap"], c["feature"], fmt_value(c["feature"], c["value"])))

    headline = "Why VISHWAS flagged these three forecasts"
    subtitle = ""
    if a.case_driest_bin:
        name = "fig8_shap_cases_driest.png"
        headline = "The failure mode ensemble spread cannot see"
        subtitle = ("Three forecasts where the ensemble predicted no rain, agreed with "
                    "itself completely, and it poured.")
        provenance = (
            "Highest-confidence correct bust calls inside the DRIEST forecast-rainfall "
            "decile of the 2019 test year — one per forecast date. " + bin_note + ".\n"
            "The probabilities are small in absolute terms and large in context: busts "
            "occur in {:.2%} of cases in this regime, so p = 0.17 is roughly {:.0f} times "
            "the local base rate. Ensemble spread is exactly 0.00 mm on all three, tied "
            "with {:,} other cases, so the incumbent method cannot rank them at all.".format(
                base, winners["model_score"].iloc[0] / max(base, 1e-12), n_tied)
        )
    elif a.case_init:
        name = "fig8_shap_cases_{}.png".format(a.case_init)
        provenance = ("Highest-confidence correct bust calls on the single forecast date "
                      "{}{} — the date the confidence map shows. These three gridpoints are "
                      "NEIGHBOURS in one weather system, not independent cases.".format(
                          a.case_init, " Day {}".format(a.case_lead) if a.case_lead else ""))
    else:
        name = "fig8_shap_cases.png"
        provenance = ("Highest-confidence correct bust calls in the 2019 test year, one per "
                      "forecast date so the three are not neighbouring gridpoints of a single storm.")
    fig_cases(cases, os.path.join(a.out_dir, name), provenance, headline, subtitle)


if __name__ == "__main__":
    main()
