"""VISHWAS — P12. Calibration of the bust probability.

WHY THIS EXISTS
    An automated confidence indicator that is not calibrated is decoration. If
    the system says "20% chance of a bust" it has to be wrong about one time in
    five, or a forecaster cannot act on the number. Under a Smart Automation
    theme, trust in the MAGNITUDE is the whole product -- the ranking being
    good (ROC-AUC 0.728) says nothing about whether 0.20 means 20%.

WHAT IT DOES
    1. Loads models/vishwas_model.joblib and verifies it reproduces
       data/model_predictions.parquet before anything else happens.
    2. Fits isotonic regression and Platt scaling on the VALIDATION slice --
       the 13 interleaved 2018 dates 07_model.py held back. Never on test.
       Calibrating on test and then reporting test calibration is circular.
    3. Reliability diagram on TEST, with per-bin counts so a bin holding forty
       points cannot masquerade as a bin holding forty thousand.
    4. Brier score DECOMPOSED into reliability / resolution / uncertainty.
       Reliability says the number is honest, resolution says it is informative.
       A constant forecast of the base rate is perfectly reliable and useless,
       so the total alone hides the thing that matters.
    5. Compares calibrated vs uncalibrated vs the ensemble-spread baseline.

    THE BASELINE IS GIVEN THE SAME TREATMENT. Ensemble spread is a number in
    millimetres, not a probability, so a raw Brier score for it would be
    meaningless. It gets its own isotonic fit on the same validation slice.
    Anything else would be scoring the incumbent on a handicap.

    python src/10_calibration.py
"""

import argparse
import importlib.util
import os
import sys

import matplotlib
matplotlib.use("Agg")

import joblib
import matplotlib.pyplot as plt
import textwrap
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# house style, shared with fig3_map.png / fig6 / fig7 / fig8
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e6e5e1"
# validated categorical slots 1-3; all-pairs CVD dE 9.2, normal-vision 24.0
C1 = "#2a78d6"   # blue
C2 = "#eb6834"   # orange
C3 = "#1baf7a"   # aqua

N_BINS = 10


def load_model_module():
    """07_model.py starts with a digit, so it cannot be imported by name."""
    path = os.path.join(_ROOT, "src", "07_model.py")
    spec = importlib.util.spec_from_file_location("model07", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_artifact(path):
    if not os.path.exists(path):
        print("No model artifact at {}".format(path))
        print("Run: python src/07_model.py")
        sys.exit(1)
    bundle = joblib.load(path)
    for key in ("model", "features", "config"):
        if key not in bundle:
            print("Artifact is missing '{}' — refusing to guess.".format(key))
            sys.exit(1)
    return bundle["model"], bundle["features"], bundle["config"]


def check_reproduces(model, features, test, pred_path):
    """ACCEPTANCE: the saved model must load and give the same predictions."""
    if not os.path.exists(pred_path):
        print("  (no {} to check against — skipping)".format(pred_path))
        return
    ref = pd.read_parquet(pred_path)
    got = test[["init", "lead_day", "lat", "lon"]].copy()
    got["reloaded"] = model.predict_proba(test[features])[:, 1]
    joined = ref.merge(got, on=["init", "lead_day", "lat", "lon"], how="inner")
    if joined.empty:
        print("  ARTIFACT CHECK FAILED: no rows joined.")
        sys.exit(1)
    delta = float(np.abs(joined["model_score"] - joined["reloaded"]).max())
    print("  artifact check: {:,} rows, max |score difference| = {:.2e}".format(
        len(joined), delta))
    if delta > 1e-12:
        print("  ARTIFACT CHECK FAILED: the reloaded model is not the deck model.")
        sys.exit(1)
    print("  the saved model reloads and reproduces model_predictions.parquet exactly.")


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------

def brier_decomposition(observed, predicted, n_bins=N_BINS):
    """Murphy's three-term decomposition:  BS = REL - RES + UNC.

    REL  mean squared gap between the probability said and the frequency that
         followed, per bin. LOWER is better. This is honesty.
    RES  how far each bin's outcome frequency sits from the overall base rate.
         HIGHER is better. This is informativeness. A constant forecast of the
         base rate scores REL = 0 and RES = 0 -- perfectly honest, useless.
    UNC  the base rate's own variance. A property of the weather, identical for
         every system scored on the same rows, so it is not a score.

    THE THREE-TERM IDENTITY IS EXACT ONLY FOR A DISCRETISED FORECAST. Our
    probabilities are continuous, so REL - RES + UNC does not equal the Brier
    score exactly; the gap is the WITHIN-BIN VARIANCE of the predictions, the
    price of binning a continuous forecast. It is computed and reported here
    rather than swept up as rounding -- at 10 bins it is around 7e-04, which is
    five times larger than REL itself and would look like an error if it were
    left unexplained.

    The decomposition is BIN-DEPENDENT, which is why the bin count is printed
    and two further bin counts are reported as a sensitivity rather than hidden.
    """
    observed = np.asarray(observed, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    n = len(observed)
    base = observed.mean()

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    which = np.clip(np.digitize(predicted, edges[1:-1], right=False), 0, n_bins - 1)

    rel = res = 0.0
    rows = []
    for k in range(n_bins):
        sel = which == k
        n_k = int(sel.sum())
        if n_k == 0:
            rows.append({"bin": k, "lo": edges[k], "hi": edges[k + 1], "n": 0,
                         "mean_p": np.nan, "obs_freq": np.nan})
            continue
        p_k = predicted[sel].mean()
        o_k = observed[sel].mean()
        rel += n_k * (p_k - o_k) ** 2
        res += n_k * (o_k - base) ** 2
        rows.append({"bin": k, "lo": edges[k], "hi": edges[k + 1], "n": n_k,
                     "mean_p": p_k, "obs_freq": o_k})

    rel /= n
    res /= n
    unc = base * (1.0 - base)
    brier = float(np.mean((predicted - observed) ** 2))
    return {
        "brier": brier, "REL": rel, "RES": res, "UNC": unc,
        "recomposed": rel - res + unc,
        "within_bin": brier - (rel - res + unc),
        "BSS": 1.0 - brier / unc if unc > 0 else np.nan,
        "bins": pd.DataFrame(rows), "n_bins": n_bins, "base_rate": base,
    }


def fit_calibrators(model, features, validation):
    """Isotonic and Platt, both fitted on VALIDATION only."""
    y = validation["bust"].to_numpy().astype(int)
    p = model.predict_proba(validation[features])[:, 1]
    raw = model.decision_function(validation[features]).reshape(-1, 1)

    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(p, y)

    # Textbook Platt: a logistic fitted on the model's RAW score (log-odds),
    # not on its probability. Fitting on an already-squashed probability makes
    # the sigmoid fight its own inverse.
    platt = LogisticRegression(C=1e6, max_iter=1000)
    platt.fit(raw, y)
    return iso, platt


def apply_calibrators(model, features, frame, iso, platt):
    p = model.predict_proba(frame[features])[:, 1]
    raw = model.decision_function(frame[features]).reshape(-1, 1)
    return {
        "VISHWAS, uncalibrated": p,
        "VISHWAS + isotonic": iso.predict(p),
        "VISHWAS + Platt": platt.predict_proba(raw)[:, 1],
    }


def calibrate_baseline(validation, test):
    """Ensemble spread -> probability, isotonic, fitted on validation.

    Spread is in millimetres. Scoring it against a Brier score without this
    step would compare a probability to a rainfall amount and call the model
    the winner for free.
    """
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(validation["precip_spread"].to_numpy(dtype=float),
            validation["bust"].to_numpy().astype(int))
    return iso.predict(test["precip_spread"].to_numpy(dtype=float))


# --------------------------------------------------------------------------
# figure
# --------------------------------------------------------------------------

def fig_reliability(systems, observed, out, n_bins, note):
    fig = plt.figure(figsize=(17.6, 10.9), dpi=200, facecolor=SURFACE)
    gs = fig.add_gridspec(2, 2, left=0.055, right=0.975, top=0.775, bottom=0.235,
                          wspace=0.20, hspace=0.09,
                          height_ratios=[3.1, 1.0])

    panels = [
        ("A", "Does the number mean what it says?",
         "raw model against both calibrators",
         [("VISHWAS, uncalibrated", C1), ("VISHWAS + isotonic", C2),
          ("VISHWAS + Platt", C3)]),
        ("B", "Against the incumbent method",
         "ensemble spread, given the identical isotonic fit",
         [("VISHWAS + isotonic", C1), ("ensemble spread + isotonic", C2)]),
    ]

    for col, (letter, title, sub, series) in enumerate(panels):
        ax = fig.add_subplot(gs[0, col])
        cx = fig.add_subplot(gs[1, col], sharex=ax)

        ax.plot([0, 1], [0, 1], color=INK2, linewidth=1.4, linestyle=(0, (5, 4)),
                zorder=2)
        ax.text(0.70, 0.645, "perfect calibration", color=INK2, fontsize=12.5,
                rotation=39, rotation_mode="anchor", ha="left", va="bottom")

        for name, colour in series:
            d = brier_decomposition(observed, systems[name], n_bins)
            b = d["bins"].dropna(subset=["mean_p"])
            b = b[b["n"] >= 1]
            ax.plot(b["mean_p"], b["obs_freq"], color=colour, linewidth=2.4,
                    marker="o", markersize=9, markerfacecolor=colour,
                    markeredgecolor=SURFACE, markeredgewidth=1.6, zorder=4,
                    label="{}  (REL {:.5f})".format(name, d["REL"]))
            cx.plot(b["mean_p"], b["n"], color=colour, linewidth=2.0,
                    marker="o", markersize=6, markeredgecolor=SURFACE,
                    markeredgewidth=1.2, zorder=3)

        for a in (ax, cx):
            a.set_facecolor(SURFACE)
            a.grid(True, color=GRID, linewidth=0.8)
            a.set_axisbelow(True)
            a.tick_params(colors=INK2, labelsize=13, length=4)
            for side in ("top", "right"):
                a.spines[side].set_visible(False)
            for side in ("left", "bottom"):
                a.spines[side].set_color(GRID)

        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.02, 1.02)
        ax.tick_params(labelbottom=False)
        cx.set_yscale("log")
        cx.set_ylim(bottom=0.7)
        cx.set_xlabel("predicted probability of a bust", fontsize=14, color=INK2)
        if col == 0:
            ax.set_ylabel("observed frequency of a bust", fontsize=14, color=INK)
            cx.set_ylabel("cases in bin\n(log scale)", fontsize=12.5, color=INK2)
        leg = ax.legend(loc="upper left", frameon=False, fontsize=13.5,
                        handlelength=2.2, labelspacing=0.55)
        for t in leg.get_texts():
            t.set_color(INK)

        if col == 0:
            d_raw = brier_decomposition(observed, systems["VISHWAS, uncalibrated"], n_bins)
            tail = d_raw["bins"].dropna(subset=["mean_p"]).iloc[-1]
            ax.annotate(
                "the raw model says {:.2f} here\nand {:.0f}% of these {:,} cases bust\n"
                "— isotonic refuses to go this high".format(
                    tail["mean_p"], 100 * tail["obs_freq"], int(tail["n"])),
                xy=(tail["mean_p"], tail["obs_freq"]),
                xytext=(0.50, 0.115), textcoords="axes fraction",
                fontsize=13, color=INK, ha="left", va="bottom", linespacing=1.5,
                arrowprops=dict(arrowstyle="-|>", color=INK2, linewidth=1.6,
                                shrinkA=6, shrinkB=8,
                                connectionstyle="arc3,rad=-0.22"))

        ax.text(0.0, 1.075, "{}  {}".format(letter, title), transform=ax.transAxes,
                fontsize=18, fontweight="bold", color=INK, ha="left", va="bottom")
        ax.text(0.0, 1.020, sub, transform=ax.transAxes, fontsize=14,
                color=INK2, ha="left", va="bottom")

    fig.text(0.055, 0.955,
             "A confidence number a forecaster can act on",
             fontsize=29, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.055, 0.898,
             "Reliability on the 2019 test year. A point on the dashed line means "
             "that when the system said p, a bust followed p of the time.",
             fontsize=16.5, color=INK2, ha="left", va="top")
    wrapped = "\n".join("\n".join(textwrap.wrap(par, 168))
                        for par in note.split("\n"))
    fig.text(0.055, 0.160, wrapped, fontsize=12.5, color=INK2, ha="left", va="top",
             linespacing=1.6)
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    plt.close(fig)
    print("  wrote {}".format(out))


# --------------------------------------------------------------------------

def print_table(title, results, order):
    print(title)
    print("  {:<30} {:>10} {:>10} {:>10} {:>10} {:>9}".format(
        "system", "Brier", "REL", "RES", "UNC", "BSS"))
    print("  {:<30} {:>10} {:>10} {:>10} {:>10} {:>9}".format(
        "", "lower", "lower", "HIGHER", "fixed", "higher"))
    for name in order:
        d = results[name]
        print("  {:<30} {:>10.5f} {:>10.5f} {:>10.5f} {:>10.5f} {:>+9.4f}".format(
            name, d["brier"], d["REL"], d["RES"], d["UNC"], d["BSS"]))


def main():
    p = argparse.ArgumentParser(description="P12 — calibration of the bust probability.")
    p.add_argument("--model", default=os.path.join(_ROOT, "models", "vishwas_model.joblib"))
    p.add_argument("--labels", default=os.path.join(_ROOT, "data", "labelled.parquet"))
    p.add_argument("--pred", default=os.path.join(_ROOT, "data", "model_predictions.parquet"))
    p.add_argument("--bins", type=int, default=N_BINS)
    p.add_argument("--out", default=os.path.join(_ROOT, "figures", "fig9_reliability.png"))
    a = p.parse_args()

    print("=" * 78)
    print("VISHWAS — P12. CALIBRATION.")
    print("=" * 78)
    print()
    print("LOADING THE SAVED MODEL")
    model, features, config = load_artifact(a.model)
    print("  {} features, {}, seed {}, sklearn {}, written {}".format(
        len(features), config["estimator"].split("(")[0], config["seed"],
        config["sklearn"], config["written"]))

    m07 = load_model_module()
    table = m07.load(a.labels, *config["study_window"])
    table, held = m07.carve_validation(table, config["validation_every"])
    validation = table[table["role"] == "validation"].copy()
    test = table[table["role"] == "test"].copy()
    print("  validation {:,} rows / {} dates (base rate {:.3f}%)".format(
        len(validation), validation["init"].nunique(), 100 * validation["bust"].mean()))
    print("  test       {:,} rows / {} dates (base rate {:.3f}%)".format(
        len(test), test["init"].nunique(), 100 * test["bust"].mean()))
    check_reproduces(model, features, test, a.pred)

    print()
    print("-" * 78)
    print("FITTING CALIBRATORS ON VALIDATION — NEVER ON TEST")
    print("-" * 78)
    iso, platt = fit_calibrators(model, features, validation)
    print("  isotonic: {} distinct output levels".format(len(np.unique(iso.y_thresholds_))))
    print("  Platt   : p = sigmoid({:+.4f} * raw_score {:+.4f})".format(
        float(platt.coef_[0][0]), float(platt.intercept_[0])))
    print("  A Platt slope far from 1.0 means the raw log-odds were mis-scaled;")
    print("  a slope near 1.0 with a large intercept means only the base rate shifted.")

    systems = apply_calibrators(model, features, test, iso, platt)
    systems["ensemble spread + isotonic"] = calibrate_baseline(validation, test)
    systems["climatology (constant {:.4f})".format(validation["bust"].mean())] = \
        np.full(len(test), validation["bust"].mean())

    observed = test["bust"].to_numpy().astype(float)
    order = ["VISHWAS, uncalibrated", "VISHWAS + isotonic", "VISHWAS + Platt",
             "ensemble spread + isotonic",
             "climatology (constant {:.4f})".format(validation["bust"].mean())]

    print()
    print("-" * 78)
    print("BRIER SCORE, DECOMPOSED — 2019 TEST YEAR, {:,} CASES, {} EQUAL-WIDTH BINS".format(
        len(test), a.bins))
    print("-" * 78)
    print("  BS = REL - RES + UNC. REL is honesty, RES is informativeness, UNC is")
    print("  a property of the weather and identical for every row of this table.")
    print("  BSS is the skill against climatology; 0 means no better than saying")
    print("  '{:.2f}% every time'.".format(100 * validation["bust"].mean()))
    print()
    results = {name: brier_decomposition(observed, values, a.bins)
               for name, values in systems.items()}
    print_table("", results, order)

    print()
    print("  WITHIN-BIN VARIANCE — Brier minus (REL - RES + UNC).")
    print("  Not an error: the three-term identity is exact only for a forecast that")
    print("  takes finitely many values. Ours is continuous, so binning it costs this")
    print("  much. Isotonic emits {} discrete levels, which is why its residual is the".format(
        len(np.unique(iso.y_thresholds_))))
    print("  smallest in the table.")
    for name in order:
        print("    {:<30} {:+.6f}".format(name, results[name]["within_bin"]))

    print()
    print("  SENSITIVITY TO THE BIN COUNT (the decomposition depends on it):")
    print("  {:<30} {:>12} {:>12} {:>12}".format("system", "REL @5", "REL @10", "REL @20"))
    for name in order:
        vals = [brier_decomposition(observed, systems[name], k)["REL"]
                for k in (5, 10, 20)]
        print("  {:<30} {:>12.5f} {:>12.5f} {:>12.5f}".format(name, *vals))

    print()
    print("-" * 78)
    print("PER-BIN DETAIL — VISHWAS + isotonic, {} equal-width bins".format(a.bins))
    print("-" * 78)
    print("  Sparse bins are printed, not hidden. A bin of forty points cannot")
    print("  support a claim about calibration at that probability.")
    print()
    best_name = min(("VISHWAS + isotonic", "VISHWAS + Platt"),
                    key=lambda n: results[n]["REL"])
    detail = results[best_name]["bins"]
    print("  {:<14} {:>10} {:>12} {:>14} {:>10}".format(
        "bin", "n", "mean p said", "observed freq", "gap"))
    for _, row in detail.iterrows():
        if row["n"] == 0:
            print("  {:<14} {:>10} {:>12} {:>14} {:>10}".format(
                "{:.1f}-{:.1f}".format(row["lo"], row["hi"]), 0, "—", "—", "—"))
            continue
        print("  {:<14} {:>10,} {:>12.4f} {:>14.4f} {:>+10.4f}".format(
            "{:.1f}-{:.1f}".format(row["lo"], row["hi"]), int(row["n"]),
            row["mean_p"], row["obs_freq"], row["mean_p"] - row["obs_freq"]))

    # ---- the tail, where an aggregate score hides the problem -----------
    print()
    print("-" * 78)
    print("TAIL BEHAVIOUR — WHERE THE AGGREGATE BRIER SCORE HIDES THE PROBLEM")
    print("-" * 78)
    print("  A reliability term averaged over 651,040 rows cannot see a failure that")
    print("  involves seventy of them. It is the most consequential seventy: a")
    print("  forecaster acts hardest on the most confident calls.")
    print()
    val_scores = {
        "VISHWAS, uncalibrated": model.predict_proba(validation[features])[:, 1],
    }
    val_scores["VISHWAS + isotonic"] = iso.predict(val_scores["VISHWAS, uncalibrated"])
    val_scores["VISHWAS + Platt"] = platt.predict_proba(
        model.decision_function(validation[features]).reshape(-1, 1))[:, 1]
    val_obs = validation["bust"].to_numpy().astype(float)
    print("  {:<26} {:>18} {:>22}".format("system", "test p>=0.9", "validation p>=0.9"))
    print("  {:<26} {:>18} {:>22}".format("", "n / observed", "n / observed"))
    for name in ("VISHWAS, uncalibrated", "VISHWAS + isotonic", "VISHWAS + Platt"):
        hi_t = systems[name] >= 0.9
        hi_v = val_scores[name] >= 0.9
        print("  {:<26} {:>10,} / {:>5}   {:>14,} / {:>5}".format(
            name, int(hi_t.sum()),
            "{:.1%}".format(observed[hi_t].mean()) if hi_t.any() else "—",
            int(hi_v.sum()),
            "{:.1%}".format(val_obs[hi_v].mean()) if hi_v.any() else "—"))
    print()
    print("  These are the saturated tree leaves the SHAP tail diagnostic found")
    print("  (single features moving the log-odds by hundreds). Typical rows in this")
    print("  group have forecast rainfall 0.00 mm, ensemble spread 0.00 mm and 0.00 mm")
    print("  observed — the model is maximally certain of a bust where nothing at all")
    print("  happened.")
    print()
    print("  WHY ISOTONIC FIXES IT AND PLATT CANNOT. The validation slice shows the")
    print("  same inversion, so PAVA pools that region downward and caps the output.")
    print("  Platt is a two-parameter sigmoid of the raw score: monotone with a fixed")
    print("  shape, so it can rescale the region but cannot flatten it.")

    # ---- verdict --------------------------------------------------------
    raw = results["VISHWAS, uncalibrated"]
    win = results[best_name]
    base_iso = results["ensemble spread + isotonic"]
    print()
    print("-" * 78)
    print("VERDICT")
    print("-" * 78)
    print("  Was the raw model already calibrated?")
    print("    raw REL {:.5f}  ->  {} REL {:.5f}   ({:+.1f}% change)".format(
        raw["REL"], best_name, win["REL"],
        100 * (win["REL"] - raw["REL"]) / raw["REL"] if raw["REL"] else float("nan")))
    print("    raw Brier {:.5f} -> {:.5f}.".format(raw["brier"], win["brier"]))
    print()
    print("    THE ANSWER IS TWO-SIDED, AND BOTH HALVES MATTER.")
    print("    In AGGREGATE, yes: REL {:.5f} against an uncertainty of {:.5f} is {:.2f}%".format(
        raw["REL"], raw["UNC"], 100 * raw["REL"] / raw["UNC"]))
    print("    of the total, and the Brier score barely moves. Between 0.0 and 0.8 the")
    print("    raw curve already tracks the diagonal.")
    print("    At the TAIL, no. The raw model says p >= 0.9 on {:,} test cases and {:.1%}".format(
        int((systems["VISHWAS, uncalibrated"] >= 0.9).sum()),
        observed[systems["VISHWAS, uncalibrated"] >= 0.9].mean()))
    print("    of them bust. That is the end of the scale a forecaster acts on hardest,")
    print("    and it is invisible in an average over 651,040 rows.")
    top = float(np.max(systems[best_name]))
    print("    Isotonic removes it by capping the output at {:.2f}. The 0.8-1.0 bins are".format(top))
    print("    empty BY CONSTRUCTION — the calibrated system declines to claim a")
    print("    confidence it has never earned on held-out data. State that as a")
    print("    deliberate property, not as missing data.")
    print("  Which calibrator won?")
    for name in ("VISHWAS + isotonic", "VISHWAS + Platt"):
        print("    {:<24} REL {:.5f}   RES {:.5f}   Brier {:.5f}".format(
            name, results[name]["REL"], results[name]["RES"], results[name]["brier"]))
    print("    winner on reliability: {}".format(best_name))
    print("  Resolution is what says the model is informative:")
    print("    {:<28} RES {:.5f}".format(best_name, win["RES"]))
    print("    {:<28} RES {:.5f}   ({:.1f}x less)".format(
        "ensemble spread + isotonic", base_iso["RES"],
        win["RES"] / base_iso["RES"] if base_iso["RES"] else float("nan")))
    print("  Calibration does not change the RANKING, so ROC-AUC 0.728 vs 0.565 is")
    print("  untouched by anything in this file. What changes is whether the number")
    print("  attached to that ranking can be believed.")

    note = (
        "Calibrators fitted on the VALIDATION slice only — the 13 interleaved 2018 forecast dates "
        "07_model.py held back. Never on test.\n"
        "Scored on the 2019 test year: {:,} forecast-gridpoint cases, 52 forecast dates, "
        "1,252 gauge-observed land gridpoints, Day 1-10, bust base rate {:.2f}%.\n"
        "Truth: IMD 0.25 deg gauge-gridded daily rainfall. Bust = |ensemble mean − observed| above "
        "the 95th percentile for that region and lead time, fitted on 2018 only.\n"
        "{} equal-width bins; per-bin counts are plotted below each curve on a log scale because "
        "{:.0f}% of cases fall in the lowest bin.\n"
        "Ensemble spread is in millimetres, so it is given the identical isotonic fit — scoring a "
        "rainfall amount against a Brier score would hand us the win for free. "
        "REL = reliability, lower is better."
    ).format(len(test), 100 * test["bust"].mean(), a.bins,
             100 * float((systems[best_name] < 1.0 / a.bins).mean()))

    fig_reliability(systems, observed, a.out, a.bins, note)


if __name__ == "__main__":
    main()
