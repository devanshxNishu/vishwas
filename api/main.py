"""VISHWAS — the API half of "Prototype dashboard/API" (P27).

    uvicorn api.main:app --reload --port 8000
    open http://localhost:8000/docs

READ-ONLY. Nothing here trains, writes, or holds state. Every probability is
read from data/model_predictions.parquet, the same file the deck and the
dashboard are built on. The API is a view onto results that already exist.

THE CONSTANTS ARE IMPORTED, NEVER RETYPED. The operating point, the uncertain
floor, the feature order and the plain-language labels all come out of
site/dashboard-data.json's meta block, which src/15_dashboard_export.py wrote.
A threshold living in two places diverges, and this project has already been
bitten by exactly that twice — fig4's footnote disagreeing with its generator,
and aug5.json's three-decimal 0.153/0.154 split. So there is one source.

NO TRUTH IS EVER SERVED. Observed rainfall and bust outcomes are used to LABEL
and to EVALUATE, in the analysis scripts. A forecaster calling /confidence for
a Day 5 forecast has not observed anything yet, and an endpoint that handed
back the answer would quietly turn an operational tool into a verification one.
Truth is loaded here only to report each date's bust rate on /dates, which is
metadata about the historical test year, not about a forecast being served.
"""

import json
import os
import sys

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
# Aliased: the /confidence endpoint function binds the global name
# `confidence`, which would otherwise shadow this module inside it.
import confidence as conf                                    # noqa: E402
PRED = os.path.join(_ROOT, "data", "model_predictions.parquet")
LABELS = os.path.join(_ROOT, "data", "labelled.parquet")
MODEL = os.path.join(_ROOT, "models", "vishwas_model.joblib")
META = os.path.join(_ROOT, "site", "dashboard-data.json")

app = FastAPI(
    title="VISHWAS — forecast confidence API",
    description=(
        "Forecast-bust probability for medium-range weather forecasts over "
        "India, Day 1-10. VISHWAS does NOT forecast weather; it predicts when "
        "the operational forecast is likely to be badly wrong.\n\n"
        "GEFSv12 reforecast, 2019 test year, model trained on 2018. Truth for "
        "labelling is IMD 0.25 deg gauge-gridded rainfall. Read-only."),
    version="1.0")


# --------------------------------------------------------------------------
# startup — everything loads once, 651,040 rows is nothing
# --------------------------------------------------------------------------

def _meta():
    if not os.path.exists(META):
        raise RuntimeError(
            "site/dashboard-data.json is missing — it is the single source of "
            "the threshold, floor and labels. Run src/15_dashboard_export.py.")
    with open(META) as handle:
        return json.load(handle)["meta"]


META_BLOCK = _meta()
THRESHOLD = META_BLOCK["threshold"]
if THRESHOLD != conf.THRESHOLD:
    raise RuntimeError(
        "site/dashboard-data.json was written at threshold {} but "
        "src/confidence.py says {}. Re-run src/15_dashboard_export.py rather "
        "than serving two operating points.".format(
            THRESHOLD, conf.THRESHOLD))
FLOOR = META_BLOCK["uncertain_floor"]
FEATURES = META_BLOCK["features"]
FEATURE_LABELS = META_BLOCK["labels"]
GRID = META_BLOCK["grid"]
PROVENANCE = META_BLOCK["provenance"]

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

PRED_TABLE = pd.read_parquet(
    PRED, columns=["init", "lead_day", "lat", "lon", "model_score", "bust"])
PRED_TABLE["init_date"] = pd.to_datetime(PRED_TABLE["init"], format="%Y%m%d")
_month = PRED_TABLE["init_date"].dt.month
PRED_TABLE["season"] = np.select(
    [_month.isin([12, 1, 2]), _month.isin([3, 4, 5]), _month.isin([6, 7, 8, 9])],
    ["DJF", "MAM", "JJAS"], default="ON")

# Features are needed only by /explain, but loading them lazily inside a
# request would put a multi-second stall on whichever caller happened to be
# first. Only the 23 model columns plus the join keys are read.
# dict.fromkeys dedupes while preserving order: lead_day is BOTH a join key
# and feature 0, and asking parquet for it twice yields duplicate columns,
# after which every boolean mask raises "cannot reindex on an axis with
# duplicate labels".
_FEATURE_COLUMNS = list(dict.fromkeys(["init", "lead_day", "lat", "lon"] + FEATURES))
FEATURE_TABLE = pd.read_parquet(LABELS, columns=_FEATURE_COLUMNS)
if FEATURE_TABLE.columns.duplicated().any():
    raise RuntimeError("duplicate feature columns — /explain cannot mask.")

_artifact = joblib.load(MODEL)
_model = _artifact["model"]
if list(_artifact["features"]) != list(FEATURES):
    raise RuntimeError(
        "Feature order in the model artifact does not match the dashboard "
        "meta block. Refusing to serve explanations against the wrong columns.")

_explainer = None

# Percentiles are against the whole 651,040-row test set, so "94th percentile
# moisture" means 94th of the year rather than 94th of whatever was asked for.
_SORTED = {f: np.sort(FEATURE_TABLE[f].to_numpy()) for f in FEATURES}

DATES = sorted(PRED_TABLE["init"].unique())
LEADS = sorted(int(v) for v in PRED_TABLE["lead_day"].unique())
POINTS = PRED_TABLE[["lat", "lon"]].drop_duplicates()
_GRID_POINTS = POINTS.to_numpy()


def percentile_of(feature, value):
    """Mid-rank percentile against the test set. Ties get their block midpoint —
    precip_spread is exactly 0.00 mm on 189,758 rows, and calling that the 0th
    or the 29th percentile would both overclaim."""
    ordered = _SORTED[feature]
    lo = np.searchsorted(ordered, value, side="left")
    hi = np.searchsorted(ordered, value, side="right")
    return int(round(100.0 * (lo + hi) / 2.0 / len(ordered)))


# VERDICTS COME FROM THE EXPORT, NOT FROM A COMPARISON THIS FILE INVENTS.
# dashboard-data.json stores a verdict per cell, banded upstream on the RAW
# score. Those are served verbatim for the six exported dates. The other 46
# dates are banded here with src/confidence.py -- the SAME function the export
# used -- and the startup check below proves the two agree everywhere they
# overlap, so the served value does not depend on which path produced it.
STORED_VERDICTS = {}


def _load_stored_verdicts():
    with open(META) as handle:
        blob = json.load(handle)
    grid = blob["meta"]["grid"]
    for entry in blob["dates"]:
        for lead, cells in entry["leads"].items():
            for cell in cells:
                lat = grid["lat0"] + cell[1] * grid["step"]
                lon = grid["lon0"] + cell[0] * grid["step"]
                STORED_VERDICTS[(entry["init"], int(lead),
                                 round(lat, 2), round(lon, 2))] = cell[3]


_load_stored_verdicts()


def verdict_of(date, lead, lat, lon, score):
    """The stored verdict where one exists, otherwise the shared banding."""
    key = (date, int(lead), round(float(lat), 2), round(float(lon), 2))
    stored = STORED_VERDICTS.get(key)
    code = conf.verdict_of(score) if stored is None else stored
    return conf.VERDICT_NAMES[code]


def _check_stored_against_shared():
    """The two paths must agree on every cell the export published, or the
    verdict a caller sees would depend on which date they asked about."""
    keys = pd.DataFrame(
        [(d, l, la, lo, v) for (d, l, la, lo), v in STORED_VERDICTS.items()],
        columns=["init", "lead_day", "lat", "lon", "stored"])
    joined = keys.merge(PRED_TABLE[["init", "lead_day", "lat", "lon",
                                    "model_score"]],
                        on=["init", "lead_day", "lat", "lon"], how="left")
    if joined["model_score"].isna().any():
        raise RuntimeError("A stored verdict has no matching prediction row.")
    computed = conf.verdicts_of(joined["model_score"].to_numpy())
    bad = int((computed != joined["stored"].to_numpy()).sum())
    if bad:
        raise RuntimeError(
            "Stored verdicts disagree with src/confidence.py on {} cells. "
            "Re-run src/15_dashboard_export.py.".format(bad))
    return len(joined)


def check_date(date):
    if date not in DATES:
        raise HTTPException(
            status_code=404,
            detail="No forecast for {}. The test year holds {} Wednesday "
                   "initialisations; call /dates for the list.".format(
                       date, len(DATES)))


def check_lead(lead):
    if lead not in LEADS:
        raise HTTPException(
            status_code=404,
            detail="Lead day {} is outside Day {}-{}.".format(
                lead, min(LEADS), max(LEADS)))


def pretty(date):
    stamp = pd.Timestamp(date)
    return "{} {} {}".format(stamp.day, MONTHS[stamp.month - 1], stamp.year)


# --------------------------------------------------------------------------
# endpoints
# --------------------------------------------------------------------------

_CHECKED = _check_stored_against_shared()
print("[vishwas] {:,} stored verdicts agree with src/confidence.py; "
      "threshold {}".format(_CHECKED, THRESHOLD))


@app.get("/health")
def health():
    """Liveness check and the shape of the served dataset."""
    return {"status": "ok", "dates": len(DATES),
            "gridpoints": int(len(POINTS)), "leads": len(LEADS)}


@app.get("/dates")
def dates():
    """The 52 forecast initialisation dates available, with season and the
    observed bust rate of each (historical metadata for the 2019 test year)."""
    out = []
    for init, block in PRED_TABLE.groupby("init", sort=True):
        out.append({
            "date": init,
            "label": pretty(block["init_date"].iloc[0]),
            "season": block["season"].iloc[0],
            "observed_bust_rate": round(float(block["bust"].mean()), 4)})
    return {"n_dates": len(out),
            "note": "observed_bust_rate is hindsight over the 2019 test year, "
                    "reported so a caller can choose an interesting case. It "
                    "is not available for a live forecast.",
            "dates": out}


@app.get("/confidence")
def confidence(
    date: str = Query(..., description="Init date, YYYYMMDD, e.g. 20190731"),
    lead: int = Query(..., description="Lead day, 1-10"),
):
    """Forecast-confidence field for one initialisation and lead day: a bust
    probability and a reliable/uncertain/high_risk verdict per gridpoint."""
    check_date(date)
    check_lead(lead)
    block = PRED_TABLE[(PRED_TABLE["init"] == date)
                       & (PRED_TABLE["lead_day"] == lead)]

    scores = block["model_score"].to_numpy()
    codes = np.array([conf.verdict_of(s) for s in scores])
    points = [
        {"lat": float(r.lat), "lon": float(r.lon),
         "probability": round(float(r.model_score), 4),
         "verdict": verdict_of(date, lead, r.lat, r.lon, r.model_score)}
        for r in block.itertuples()]

    valid = pd.Timestamp(date) + pd.Timedelta(days=lead)
    flagged = int((codes == conf.HIGH_RISK).sum())
    return {
        "date": date,
        "lead_day": lead,
        "valid_date": valid.strftime("%Y%m%d"),
        "valid_label": pretty(valid),
        "grid": GRID,
        "summary": {
            "gridpoints": len(points),
            "flagged": flagged,
            "flagged_fraction": round(flagged / len(points), 4),
            "uncertain": int((codes == conf.UNCERTAIN).sum()),
            "reliable": int((codes == conf.RELIABLE).sum()),
            "threshold": THRESHOLD,
            "uncertain_floor": FLOOR,
            "threshold_note":
                "p >= {} is the global 90th percentile of test scores, "
                "fitted once and applied unchanged — never re-fitted per "
                "date. Read `verdict`, not a comparison against the "
                "four-decimal `probability`: scores either side of the "
                "threshold both display as 0.1535.".format(THRESHOLD)},
        "provenance": PROVENANCE,
        "points": points,
    }


@app.get("/explain")
def explain(
    date: str = Query(..., description="Init date, YYYYMMDD, e.g. 20190731"),
    lead: int = Query(..., description="Lead day, 1-10"),
    lat: float = Query(..., description="Latitude, e.g. 22.5"),
    lon: float = Query(..., description="Longitude, e.g. 78.0"),
):
    """The three meteorological drivers behind one gridpoint's bust
    probability, by exact TreeSHAP; snaps to the nearest gauge-observed point."""
    check_date(date)
    check_lead(lead)

    # Snap, and say so. The 1,252 served points are the gauge-observed land
    # subset, so most (lat, lon) a caller types will not be on the grid.
    distance = np.hypot(_GRID_POINTS[:, 0] - lat, _GRID_POINTS[:, 1] - lon)
    near = _GRID_POINTS[int(np.argmin(distance))]
    use_lat, use_lon = float(near[0]), float(near[1])

    row = FEATURE_TABLE[(FEATURE_TABLE["init"] == date)
                        & (FEATURE_TABLE["lead_day"] == lead)
                        & (FEATURE_TABLE["lat"] == use_lat)
                        & (FEATURE_TABLE["lon"] == use_lon)]
    if row.empty:
        raise HTTPException(status_code=404, detail="No feature row for that "
                                                    "point and lead day.")

    global _explainer
    if _explainer is None:
        import shap
        _explainer = shap.TreeExplainer(_model)

    values = np.asarray(_explainer.shap_values(row[FEATURES]))
    if values.ndim == 3:
        values = values[:, :, -1]
    values = values[0]

    p = float(_model.predict_proba(row[FEATURES])[:, 1][0])
    order = np.argsort(-np.abs(values))[:3]
    drivers = []
    for rank, index in enumerate(order, start=1):
        feature = FEATURES[index]
        drivers.append({
            "rank": rank,
            "feature": feature,
            "label": FEATURE_LABELS[feature],
            "percentile": percentile_of(feature, row[feature].iloc[0]),
            "shap": round(float(values[index]), 4),
            "direction": "raises bust risk" if values[index] > 0
                         else "lowers bust risk"})

    snapped = (abs(use_lat - lat) > 1e-9) or (abs(use_lon - lon) > 1e-9)
    return {
        "date": date,
        "lead_day": lead,
        "requested": {"lat": lat, "lon": lon},
        "gridpoint_used": {"lat": use_lat, "lon": use_lon},
        "snapped": snapped,
        "snap_note": ("Nearest of the 1,252 gauge-observed land gridpoints; "
                      "{:.2f} deg from the request.".format(
                          float(distance.min()))) if snapped else
                     "Exact gridpoint match.",
        "probability": round(p, 4),
        "verdict": verdict_of(date, lead, use_lat, use_lon, p),
        "drivers": drivers,
        "explanation_note":
            "Exact TreeSHAP on the fitted model. `shap` is a signed log-odds "
            "contribution; `percentile` is where this gridpoint sits for that "
            "variable across all 651,040 test forecasts, which is the half a "
            "forecaster can read.",
        "provenance": PROVENANCE,
    }
