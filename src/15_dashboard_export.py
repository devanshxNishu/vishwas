"""VISHWAS — export the dashboard dataset (P26).

The problem statement names five Expected Outcomes. Four are built. The fifth,
"Prototype dashboard/API - Simple interface for operational use", needs data
behind it, and this script produces exactly that and nothing else.

    python src/15_dashboard_export.py

NOTHING IS RETRAINED, REFETCHED OR RECOMPUTED. Every probability in the output
is read from data/model_predictions.parquet, the same file the deck is built
on. The model artifact is loaded only to explain those probabilities with
TreeSHAP, and it is checked against the stored scores before that is trusted.

WHY THE REAL LEAD DAYS MATTER
-----------------------------
The site displayed Day 5 and scaled the other nine for its animation. The PS
asks for "Region-wise confidence for Day 1 to Day 10 forecasts". Real Day 1-10
predictions already exist -- 52 dates x 1,252 gridpoints x 10 lead days =
651,040 rows -- so a scaled animation was never necessary. This export carries
the measured value for every lead day.

WHAT IS DELIBERATELY ABSENT: OBSERVED RAINFALL
----------------------------------------------
A forecaster looking at a Day 5 forecast has not observed anything yet. Shipping
truth alongside the probability would turn an operational interface into a
verification tool and quietly change what the product claims. Truth is used
HERE, to choose the six dates, and is then dropped. The site's three-act map
already covers hindsight.

FOUR DECIMALS ON p, NOT THREE
-----------------------------
aug5.json stored three, and six cells landed on exactly 0.154 either side of the
0.1535 operating point -- the site carries a comment about the split it had to
invent. This file is read by an interface that shows per-cell numbers, so the
ambiguity is designed out rather than worked around.
"""

import argparse
import json
import os
import sys

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import confidence                                            # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_PRED = os.path.join(_ROOT, "data", "model_predictions.parquet")
DEFAULT_LABELS = os.path.join(_ROOT, "data", "labelled.parquet")
DEFAULT_MODEL = os.path.join(_ROOT, "models", "vishwas_model.joblib")
DEFAULT_OUT = os.path.join(_ROOT, "site", "dashboard-data.json")

# Grid. Verified against the 1,252 gauge-observed land points in the test set:
# lat 8.5-37.0, lon 68.0-97.0, 0.5 deg, so 59 x 58 with 1,252 of the 3,422 land.
# iy INCREASES NORTHWARD and the renderer draws at (ny - 1 - iy), which is the
# convention aug5.json already uses in site/index.html. Get it wrong and India
# is upside down.
LON0, LAT0, STEP, NX, NY = 68.0, 8.5, 0.5, 59, 58

# Both come from src/confidence.py, which is the single definition. The
# threshold is the global 90th percentile of test scores, fitted ONCE and
# applied unchanged -- never re-fitted per date. Below the floor the model is
# confident and the PS does not ask us to explain it ("Key meteorological
# reasons for LOW confidence"); dropping the SHAP array there is also what
# keeps the file small enough to ship.
THRESHOLD = confidence.THRESHOLD
UNCERTAIN_FLOOR = confidence.UNCERTAIN_FLOOR

# One short phrase per feature, in the language a duty forecaster uses.
# flow500_deformation is NOT wind shear and must never be labelled as such
# (CLAUDE.md, WIND SHEAR): shear_500_850 is the column that means shear.
LABELS = {
    "lead_day":            "forecast lead time",
    "gh500_mean":          "500 hPa height (upper-air pattern)",
    "gh500_spread":        "ensemble disagreement on the upper-air pattern",
    "u500_mean":           "500 hPa westerly wind",
    "u500_spread":         "ensemble disagreement on the 500 hPa westerly wind",
    "v500_mean":           "500 hPa southerly wind",
    "v500_spread":         "ensemble disagreement on the 500 hPa southerly wind",
    "pwat_mean":           "atmospheric moisture (precipitable water)",
    "pwat_spread":         "ensemble disagreement on atmospheric moisture",
    "cape_mean":           "instability (CAPE)",
    "cape_spread":         "ensemble disagreement on instability",
    "precip_mean":         "forecast rainfall amount",
    "precip_spread":       "ensemble disagreement on rainfall",
    "gh500_gradient":      "500 hPa height gradient (upper-air flow strength)",
    "wind500_speed":       "500 hPa wind speed",
    "u850_mean":           "850 hPa westerly wind (monsoon flow)",
    "v850_mean":           "850 hPa southerly wind (moisture transport)",
    "shear_500_850":       "500-850 hPa wind shear",
    "flow500_deformation": "500 hPa flow deformation",
    "month":               "season",
    "pwat_anomaly":        "moisture anomaly against climatology",
    "cape_anomaly":        "instability anomaly against climatology",
    "precip_anomaly":      "rainfall anomaly against climatology",
}

PROVENANCE = ("GEFSv12 reforecast, 2019 test year. Model trained on 2018. "
              "Truth for labelling: IMD 0.25 deg gauge-gridded rainfall.")

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------

def season_of(dates):
    month = dates.dt.month
    return np.select(
        [month.isin([12, 1, 2]), month.isin([3, 4, 5]), month.isin([6, 7, 8, 9])],
        ["DJF", "MAM", "JJAS"], default="ON")


def load_predictions(path):
    if not os.path.exists(path):
        print("No predictions at {}. Run src/07_model.py first.".format(path))
        sys.exit(1)
    pred = pd.read_parquet(path)
    pred["init_date"] = pd.to_datetime(pred["init"], format="%Y%m%d")
    pred["season"] = season_of(pred["init_date"])
    return pred


def pretty_date(stamp):
    return "{} {} {}".format(int(stamp.day), MONTHS[stamp.month - 1], stamp.year)


# --------------------------------------------------------------------------
# 1. date selection -- on observed busts alone, never on model skill
# --------------------------------------------------------------------------

def coherence(block):
    """Share of bust cells that touch another bust cell (08_pick_date.py)."""
    b = block[block["bust"]]
    if len(b) < 5:
        return float("nan")
    keys = set(zip(np.round(b["lat"] * 2).astype(int),
                   np.round(b["lon"] * 2).astype(int)))
    touching = sum(
        any((y + dy, x + dx) in keys for dy in (-1, 0, 1) for dx in (-1, 0, 1)
            if (dy, dx) != (0, 0))
        for (y, x) in keys)
    return touching / len(keys)


def date_table(pred):
    """Observed bust rate per init date, over all ten lead days and at Day 5.

    The dashboard shows Day 1-10, so the ALL-LEAD rate is the ranking criterion;
    the Day 5 column is printed beside it because that is the number CLAUDE.md
    and the deck quote, and the two must be reconcilable by eye.
    """
    rows = []
    day5 = pred[pred["lead_day"] == 5]
    for init, block in pred.groupby("init"):
        five = day5[day5["init"] == init]
        rows.append(dict(
            init=init,
            season=block["season"].iloc[0],
            label=pretty_date(block["init_date"].iloc[0]),
            bust_all=float(block["bust"].mean()),
            bust_d5=float(five["bust"].mean()),
            n_bust_d5=int(five["bust"].sum()),
            coherence_d5=coherence(five)))
    return pd.DataFrame(rows).sort_values("bust_all", ascending=False)


def pick_dates(table):
    """Six dates, by a rule stated in advance and applied without exception.

    RULE. The most active date in each season by observed all-lead bust rate,
    plus the JJAS median date. That yields the deck's demo date 20190731 (the
    highest of all 52) for free, one DJF, one MAM, one ON, and a second JJAS
    that contrasts with the first -- the required spread, with no date chosen
    by hand.

    Model skill plays NO part. Ranking dates by our own AUC and then showing the
    winner is cherry-picking, and 08_pick_date.py already refuses to do it.
    """
    chosen, why = [], {}

    jjas = table[table["season"] == "JJAS"].sort_values("bust_all", ascending=False)
    top_jjas = jjas.iloc[0]["init"]
    second_jjas = jjas.iloc[1]["init"]
    # Median by POSITION in the ranked list, so the pick is an actual date
    # rather than an interpolated rate that belongs to no forecast.
    median_jjas = jjas.iloc[len(jjas) // 2]["init"]

    chosen += [top_jjas, second_jjas, median_jjas]
    why[top_jjas] = "highest bust rate of all 52 test dates; the deck's demo date"
    why[second_jjas] = "second-highest JJAS -- the high-activity contrast"
    why[median_jjas] = "median JJAS date by rank -- a typical monsoon Wednesday"

    for season in ["ON", "MAM", "DJF"]:
        block = table[table["season"] == season].sort_values("bust_all", ascending=False)
        init = block.iloc[0]["init"]
        chosen.append(init)
        why[init] = "most active {} date of {} in the test year".format(
            season, len(block))

    picked = table[table["init"].isin(chosen)].copy()
    picked["why"] = picked["init"].map(why)
    return picked.sort_values("bust_all", ascending=False)


# --------------------------------------------------------------------------
# 2. features, percentiles, SHAP
# --------------------------------------------------------------------------

def load_test_features(labels_path, pred):
    """Test-set feature rows, joined to the stored scores.

    The join is the split: model_predictions.parquet holds exactly the test
    rows, so an inner join cannot leak a training row into the export.
    """
    if not os.path.exists(labels_path):
        print("No labelled table at {}.".format(labels_path))
        sys.exit(1)
    table = pd.read_parquet(labels_path)
    keys = ["init", "lead_day", "lat", "lon"]
    joined = pred[keys + ["model_score", "season", "init_date", "bust"]].merge(
        table.drop(columns=[c for c in ("season", "init_date", "bust")
                            if c in table.columns]),
        on=keys, how="inner")
    if len(joined) != len(pred):
        print("JOIN LOST ROWS: {} predictions -> {} joined. Not exporting a "
              "partial grid.".format(len(pred), len(joined)))
        sys.exit(1)
    return joined


def percentile_lookup(values):
    """Mid-rank percentile of each value against the whole test set.

    Ties get the MIDPOINT of their block, which matters here rather than being a
    pedantic detail: precip_spread is exactly 0.00 mm on 189,758 of the 651,040
    test rows. Reporting that block as the 0th percentile or as the 29th would
    both be a claim the data does not support; the midpoint says plainly that
    the feature cannot rank inside it.
    """
    ordered = np.sort(values)
    n = len(ordered)

    def lookup(query):
        lo = np.searchsorted(ordered, query, side="left")
        hi = np.searchsorted(ordered, query, side="right")
        return np.rint(100.0 * (lo + hi) / 2.0 / n).astype(int)

    return lookup


def shap_for(model, features, frame):
    """TreeSHAP on the uncertain cells. No substitute explainer, ever."""
    try:
        import shap
    except ImportError:
        print("SHAP NOT INSTALLED. Reporting nothing rather than substituting.")
        sys.exit(1)
    print("  shap {} — TreeExplainer on {:,} uncertain cells".format(
        shap.__version__, len(frame)))
    explainer = shap.TreeExplainer(model)
    values = np.asarray(explainer.shap_values(frame[features]))
    if values.ndim == 3:
        values = values[:, :, -1]

    # Additivity: SHAP must reconstruct the model's own log-odds. If it does
    # not, the explanations describe some other function and are worthless.
    base = float(np.asarray(explainer.expected_value).ravel()[-1])
    raw = model.decision_function(frame[features])
    gap = float(np.abs(values.sum(axis=1) + base - raw).max())
    print("  additivity: max |sum(SHAP) + base - raw log-odds| = {:.2e}".format(gap))
    if gap > 1e-4:
        print("  ADDITIVITY FAILED — refusing to export these explanations.")
        sys.exit(1)
    return values


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def write_payload(path, payload):
    """The one writer for this JSON shape.

    Extracted so the operational export (src/20_operational.py) emits the
    SAME shape from the SAME code rather than a second implementation that
    could drift. Separators are compact and deliberate: the published file is
    read over the network by the dashboard.
    """
    with open(path, "w") as handle:
        json.dump(payload, handle, separators=(",", ":"))
    return os.path.getsize(path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pred", default=DEFAULT_PRED)
    p.add_argument("--labels", default=DEFAULT_LABELS)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--floor", type=float, default=UNCERTAIN_FLOOR)
    a = p.parse_args()

    print("VISHWAS — dashboard export (P26)")
    print("=" * 78)

    pred = load_predictions(a.pred)
    print("{:,} test rows, {} dates, {} gridpoints, Day {}-{}".format(
        len(pred), pred["init"].nunique(),
        pred[["lat", "lon"]].drop_duplicates().shape[0],
        pred["lead_day"].min(), pred["lead_day"].max()))

    # ---- 1. dates ------------------------------------------------------
    table = date_table(pred)
    picked = pick_dates(table)
    print()
    print("SIX DATES — chosen on OBSERVED BUSTS ALONE, model skill excluded.")
    print("  {:<10} {:<6} {:>9} {:>9} {:>7} {:>7}   {}".format(
        "init", "season", "bust_all", "bust_d5", "n_d5", "coh_d5", "why"))
    for _, r in picked.iterrows():
        print("  {:<10} {:<6} {:>8.2%} {:>9.2%} {:>7d} {:>7.2f}   {}".format(
            r["init"], r["season"], r["bust_all"], r["bust_d5"],
            r["n_bust_d5"], r["coherence_d5"], r["why"]))
    six = list(picked["init"])

    # ---- 2. model + features -------------------------------------------
    artifact = joblib.load(a.model)
    model, features = artifact["model"], artifact["features"]
    print()
    print("model artifact: {} features, sklearn {}, written {}".format(
        len(features), artifact["config"]["sklearn"], artifact["config"]["written"]))

    missing = [f for f in features if f not in LABELS]
    if missing:
        print("NO LABEL FOR: {} — every feature needs one.".format(missing))
        sys.exit(1)

    test = load_test_features(a.labels, pred)
    stored = test["model_score"].to_numpy()
    reloaded = model.predict_proba(test[features])[:, 1]
    delta = float(np.abs(stored - reloaded).max())
    print("  reload check: max |stored - reloaded| = {:.2e} over {:,} rows".format(
        delta, len(test)))
    if delta > 1e-9:
        print("  THIS IS NOT THE MODEL THE DECK REPORTS. Refusing to explain it.")
        sys.exit(1)

    # Percentiles are against the WHOLE test set, not against the six dates.
    # A cell's moisture being "94th percentile" has to mean 94th of the year,
    # otherwise the number silently rescales with whichever dates we shipped.
    print("  building percentile lookups over all {:,} test rows".format(len(test)))
    lookups = {f: percentile_lookup(test[f].to_numpy()) for f in features}

    # ---- 3. SHAP on the uncertain cells --------------------------------
    show = test[test["init"].isin(six)].copy()
    show = show.sort_values(["init", "lead_day", "lat", "lon"]).reset_index(drop=True)

    # THE VERDICT IS COMPUTED ON THE RAW SCORE AND THEN STORED, and it is what
    # decides everything downstream -- including which cells get explained. p is
    # published at four decimals for display only. Deriving the band from the
    # rounded number is what produced the 546/547 split, so nothing here reads
    # the rounded number for a decision.
    show["p"] = show["model_score"].round(4)
    show["verdict"] = confidence.verdicts_of(show["model_score"].to_numpy())
    uncertain = show["verdict"] >= confidence.UNCERTAIN
    print()
    print("cells: {:,} across six dates, {:,} not-reliable get SHAP ({:.1%})".format(
        len(show), int(uncertain.sum()), uncertain.mean()))
    print("  verdicts: {} reliable, {} uncertain, {} high risk".format(
        int((show["verdict"] == confidence.RELIABLE).sum()),
        int((show["verdict"] == confidence.UNCERTAIN).sum()),
        int((show["verdict"] == confidence.HIGH_RISK).sum())))
    print("  banded on the RAW score at threshold {}, floor {}".format(
        THRESHOLD, UNCERTAIN_FLOOR))

    block = show[uncertain]
    values = shap_for(model, features, block)

    order = np.argsort(-np.abs(values), axis=1)[:, :3]
    pct = np.empty_like(order)
    for slot in range(3):
        fi = order[:, slot]
        for j, feature in enumerate(features):
            hit = fi == j
            if hit.any():
                pct[hit, slot] = lookups[feature](block[feature].to_numpy()[hit])

    drivers = {}
    for row, idx in enumerate(block.index):
        drivers[idx] = [
            [int(order[row, s]),
             round(float(values[row, order[row, s]]), 4),
             int(pct[row, s])]
            for s in range(3)]

    # ---- 4. emit --------------------------------------------------------
    ix = np.rint((show["lon"].to_numpy() - LON0) / STEP).astype(int)
    iy = np.rint((show["lat"].to_numpy() - LAT0) / STEP).astype(int)
    if ix.min() < 0 or ix.max() >= NX or iy.min() < 0 or iy.max() >= NY:
        print("GRID INDEX OUT OF RANGE — refusing to write an off-grid map.")
        sys.exit(1)
    show["ix"], show["iy"] = ix, iy

    dates = []
    for init in six:
        block_date = show[show["init"] == init]
        meta_row = picked[picked["init"] == init].iloc[0]
        leads = {}
        for lead, part in block_date.groupby("lead_day"):
            cells = []
            for idx, r in part.iterrows():
                cell = [int(r["ix"]), int(r["iy"]), float(r["p"]),
                        int(r["verdict"])]
                if idx in drivers:
                    cell.append(drivers[idx])
                cells.append(cell)
            leads[str(int(lead))] = cells
        dates.append({"init": init,
                      "label": meta_row["label"],
                      "season": meta_row["season"],
                      "leads": leads})

    payload = {
        "meta": {
            "grid": {"lon0": LON0, "lat0": LAT0, "step": STEP,
                     "nx": NX, "ny": NY},
            "n_points": int(show[["lat", "lon"]].drop_duplicates().shape[0]),
            "threshold": THRESHOLD,
            "uncertain_floor": a.floor,
            "features": list(features),
            "labels": {f: LABELS[f] for f in features},
            "provenance": PROVENANCE,
        },
        "dates": dates,
    }

    write_payload(a.out, payload)
    size = os.path.getsize(a.out)
    print()
    print("wrote {}  ({:,} bytes, {:.2f} MB)".format(a.out, size, size / 1e6))

    # ---- 5. the label map, printed for review ---------------------------
    print()
    print("meta.labels — REVIEW THIS BEFORE IT REACHES AN INTERFACE")
    for i, f in enumerate(features):
        print("  {:>2}  {:<21} {}".format(i, f, LABELS[f]))

    # Four decimals is a stated guarantee, so it is asserted rather than hoped.
    cells = [c for d in dates for cs in d["leads"].values() for c in cs]
    probs = [c[2] for c in cells]
    bad = [v for v in probs if round(v, 4) != v]
    print()
    print("p precision: {:,} values, {} carrying more than 4 decimals".format(
        len(probs), len(bad)))
    if bad:
        sys.exit(1)

    # THE REASON THE VERDICT EXISTS, printed every run so it stays visible:
    # scores on both sides of the threshold display as the same 4-decimal p.
    straddle = sorted({(c[2], c[3]) for c in cells if 0.1530 <= c[2] <= 0.1540})
    print("  cells displaying p near the threshold, as (p, verdict): {}".format(
        [x for x in straddle if x[0] == 0.1535]))
    print("  -> the same printed p carries different verdicts, which is why the "
          "verdict is stored and never re-derived downstream.")

    # Cell shape: [ix, iy, p, verdict] or [ix, iy, p, verdict, [drivers]].
    shapes = sorted({len(c) for c in cells})
    if shapes != [4, 5]:
        print("UNEXPECTED CELL SHAPES {} — not shipping.".format(shapes))
        sys.exit(1)

    # The explain rule must hold in BOTH directions, and it keys off the STORED
    # verdict rather than off the published number.
    broken = [c for c in cells
              if (len(c) == 5) != (c[3] >= confidence.UNCERTAIN)]
    with_shap = sum(1 for c in cells if len(c) == 5)
    print("cells with a SHAP array: {:,} of {:,}".format(with_shap, len(cells)))
    print("explain-rule violations (not-reliable without SHAP, or reliable "
          "with): {}".format(len(broken)))
    if broken:
        print("  SCHEMA IS INCONSISTENT — not shipping this to an interface.")
        sys.exit(1)

    # Every stored verdict must reproduce from the raw score it was banded on.
    for cell_date in dates:
        block = show[show["init"] == cell_date["init"]]
        want = confidence.verdicts_of(block["model_score"].to_numpy())
        got = np.array([c[3] for lead in sorted(cell_date["leads"], key=int)
                        for c in cell_date["leads"][lead]])
        if not (want == got).all():
            print("VERDICT MISMATCH on {} — not shipping.".format(
                cell_date["init"]))
            sys.exit(1)
    print("stored verdicts reproduce from raw scores on all six dates.")

    # ACCEPTANCE (P28): the deck's demo date and lead must count exactly 547
    # high-risk cells. This is the number every published count was fitted at.
    demo = [d for d in dates if d["init"] == "20190731"]
    if demo:
        flagged = sum(1 for c in demo[0]["leads"]["5"]
                      if c[3] == confidence.HIGH_RISK)
        print("ACCEPTANCE — 20190731 lead 5, verdict == 2: {} (must be 547)"
              .format(flagged))
        if flagged != 547:
            print("  ACCEPTANCE FAILED.")
            sys.exit(1)

    if "truth" in json.dumps(payload["meta"]):
        print("UNEXPECTED FIELD IN OUTPUT.")
        sys.exit(1)


if __name__ == "__main__":
    main()
