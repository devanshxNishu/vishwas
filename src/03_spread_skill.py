"""
VISHWAS step 03 — the decision number.

Computes corr(log ensemble spread, log |ensemble mean - truth|) per lead day
for daily precipitation over India. If that correlation is already high,
ensemble spread is a good confidence signal on its own and VISHWAS has
little headroom. That is the number this script exists to produce.

  python src/03_spread_skill.py --seasons JJAS,DJF,MAM,ON \
      --years 2012,2015,2018 --dates-per-season 3 \
      --out data/spread_skill_4season.parquet

This script reports the POOLED correlation only. The POOLED NUMBER IS NOT THE
BASELINE — most of it is the wet/dry spatial gradient, not skill. The
conditional number, which is the one that may be quoted, comes from
04_conditional.py. See CLAUDE.md.

TRUTH SOURCE — TWO IMD ENDPOINTS, AND ONLY ONE OF THEM IS USABLE.
An earlier version of this docstring said IMD "CANNOT be used". That was true
of the endpoint it tested and false in general. The distinction:

  HISTORICAL  imdpune.gov.in/cmpg/Griddata/rainfall.php   -> imdlib.get_data()
      Yearly 0.25 deg gridded rainfall, 1901-2024, ~25 MB/yr. Fully overlaps
      the 2000-2019 reforecast. This is --truth imd, the DEFAULT, verified
      2026-08-27 (see VERIFY-IMD in CLAUDE.md). Gauge OBSERVATION.

  REAL-TIME   imdpune.gov.in/cmpg/Realtimedata/...    -> imdlib.get_real_data()
      A rolling archive starting ~2022. Does NOT overlap the reforecast.
      This is the endpoint the old docstring was describing. Never use it here.

  --truth era5 is RETAINED AS THE FALLBACK, not deprecated. ERA5 total
      precipitation is LSP + CP (there is no single `tp` in
      e5.oper.fc.sfc.accumu). It is a REANALYSIS whose model physics partly
      overlaps GEFS, so any number built on it must say so. It is also the
      only route if we ever score a non-rainfall variable. ERA5 files are
      chunked (1, 12, 721, 1440) — one chunk is a whole global field, so
      India-box subsetting saves NO transfer. Files are pulled whole, used,
      deleted.

NEVER MIX TRUTH SOURCES IN ONE COMPARISON. Whatever truth the baseline is
measured on is the truth the model must later be scored on. Every number this
script prints is tagged with the truth source that produced it.

DOMAIN DIFFERS BY TRUTH SOURCE. IMD is gauge-based over land: ocean is undef
(-999, dropped as MISSING, never as zero rainfall) leaving 1252 of our 5041
gridpoints. ERA5 has values everywhere. So an IMD run and an ERA5 run are not
on the same domain by default, and a difference between them is NOT purely a
truth-source effect. Use --restrict-to-imd-land on the ERA5 path to hold the
domain fixed and get a controlled comparison.
"""

import argparse
import datetime
import importlib.util
import os
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd
import xarray as xr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import imd_truth

LAT_MIN, LAT_MAX = 5.0, 40.0
LON_MIN, LON_MAX = 65.0, 100.0
GRID = 0.5
TARGET_LATS = np.arange(LAT_MIN, LAT_MAX + 1e-6, GRID)
TARGET_LONS = np.arange(LON_MIN, LON_MAX + 1e-6, GRID)

# The reforecast carries 5 members on most dates and 11 on Wednesdays. We
# sample Wednesdays, so every date here has 11. CORE_MEMBERS is the size of
# the everyday ensemble, used for the 5-vs-11 sensitivity check.
CORE_MEMBERS = 5

ERA5_ACCUM = "nsf-ncar-era5/e5.oper.fc.sfc.accumu"
SEASON_MONTHS = {"JJAS": (6, 7, 8, 9), "DJF": (12, 1, 2),
                 "MAM": (3, 4, 5), "ON": (10, 11)}

# 03 and 04 must agree on what season a row belongs to, so both derive it from
# the INIT month. A Day-10 valid date can fall in the next season; we do not
# chase that, we just make sure the two scripts never disagree.
def season_of(init):
    month = int(init[4:6])
    for name, months in SEASON_MONTHS.items():
        if month in months:
            return name
    raise ValueError("no season for {}".format(init))


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ----------------------------------------------------------------- ERA5 truth

def era5_files(fs, year, month):
    """The two half-month LSP and CP files covering one month."""
    prefix = "{}/{}{:02d}".format(ERA5_ACCUM, year, month)
    keys = [i["Key"] for i in fs.ls(prefix, detail=True)
            if i.get("type") == "file"]
    return sorted(k for k in keys if "_142_lsp." in k or "_143_cp." in k)


def fetch_era5(fs, keys, workdir):
    """Pull whole files. Subsetting over S3 saves nothing (see docstring)."""
    local = []
    for key in keys:
        target = os.path.join(workdir, key.split("/")[-1])
        if not os.path.exists(target):
            fs.get(key, target)
        local.append(target)
    return local


def era5_daily_precip(paths, day):
    """
    ERA5 total precipitation for the 00Z-00Z day, on the analysis grid.

    ERA5 forecast runs start 06Z and 18Z, each carrying forecast_hour 1..12.
    A run started at H covers (H+h-1) to (H+h) UTC. So a 00Z-00Z day needs
    three pieces:
      00-06  from the 18Z run of the PREVIOUS day, hours 7..12
      06-18  from the 06Z run of THIS day,         hours 1..12
      18-24  from the 18Z run of THIS day,         hours 1..6
    Returns metres; caller converts to mm.
    """
    stores = {}
    for path in paths:
        dataset = xr.open_dataset(path, engine="h5netcdf", decode_times=False)
        name = [v for v in dataset.data_vars if v.upper() in ("LSP", "CP")][0]
        raw = dataset["forecast_initial_time"].values
        units = dataset["forecast_initial_time"].attrs.get("units", "")
        stores.setdefault(name.upper(), []).append((dataset, name, raw, units))

    if set(stores) != {"LSP", "CP"}:
        raise ValueError("need both LSP and CP, got {}".format(set(stores)))

    def piece(variable, when, hours):
        """One run's contribution, colocated to the analysis grid."""
        for dataset, name, raw, units in stores[variable]:
            origin = datetime.datetime.strptime(
                units.split("since")[-1].strip()[:19], "%Y-%m-%d %H:%M:%S")
            stamps = [origin + datetime.timedelta(hours=float(h)) for h in raw]
            for index, stamp in enumerate(stamps):
                if stamp == when:
                    block = dataset[name].isel(
                        forecast_initial_time=index,
                        forecast_hour=[h - 1 for h in hours])
                    block = block.sortby("latitude").sortby("longitude")
                    block = block.sel(latitude=TARGET_LATS,
                                      longitude=TARGET_LONS, method="nearest")
                    return np.asarray(block).sum(axis=0)
        return None

    previous = datetime.datetime.combine(
        day - datetime.timedelta(days=1), datetime.time(18))
    today_06 = datetime.datetime.combine(day, datetime.time(6))
    today_18 = datetime.datetime.combine(day, datetime.time(18))

    total = None
    for variable in ("LSP", "CP"):
        for when, hours in [(previous, range(7, 13)),
                            (today_06, range(1, 13)),
                            (today_18, range(1, 7))]:
            part = piece(variable, when, list(hours))
            if part is None:
                for dataset, _, _, _ in sum(stores.values(), []):
                    dataset.close()
                return None
            total = part if total is None else total + part

    for dataset, _, _, _ in sum(stores.values(), []):
        dataset.close()
    return total * 1000.0   # metres -> mm


# ------------------------------------------------------------ date selection

def pick_inits(all_wednesdays, years, seasons, per_season):
    """Init dates spread ACROSS each season, not clustered at one end of it.

    Two traps this avoids:
      1. Consecutive Wednesdays in one month are close to the same synoptic
         situation, so taking the first N would understate how much the
         answer varies between dates.
      2. Taking index 0 would sample the START of every season in every year
         — for JJAS that is monsoon ONSET, which is not representative of the
         season, and the bias would repeat identically across years.

    So we split each (year, season) block into `take` equal parts and pick the
    CENTRE of each part. With take=1 that is the middle of the season, not its
    first week.
    """
    chosen = []
    for year in years:
        for season in seasons:
            months = SEASON_MONTHS[season]
            pool = [d for d in all_wednesdays
                    if int(d[:4]) == year and int(d[4:6]) in months]
            if not pool:
                print("  WARNING: no init dates for {} {}".format(season, year))
                continue
            take = min(per_season, len(pool))
            centres = (np.arange(take) + 0.5) / take      # 0.5/k, 1.5/k, ...
            idx = np.unique((centres * len(pool)).astype(int))
            chosen.extend(pool[i] for i in idx)
    return sorted(set(chosen))


# ------------------------------------------------------------------- reporting

def report(wet, truth_label, n_inits):
    print()
    print("SPREAD-SKILL CORRELATION  corr(log spread, log |ens_mean - truth|)")
    print("TRUTH = {}".format(truth_label))
    print("{} wet points from {} dates".format(len(wet), n_inits))
    print()
    print("  lead day    r        n")
    for lead in range(1, 11):
        block = wet[wet.lead_day == lead]
        if len(block) < 100:
            continue
        r = block["log_spread"].corr(block["log_error"])
        print("  Day {:<7} {:+.3f}  {:>8}".format(lead, r, len(block)))
    overall = wet["log_spread"].corr(wet["log_error"])
    print()
    print("  ALL LEADS   {:+.3f}   (truth: {})".format(overall, truth_label))
    print()
    print("  This POOLED number is not the baseline. Run 04_conditional.py.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--truth", choices=["imd", "era5"], default="imd",
                        help="imd = gauge observation (default); "
                             "era5 = reanalysis fallback")
    parser.add_argument("--seasons", default="JJAS",
                        help="comma separated: JJAS,DJF,MAM,ON")
    parser.add_argument("--years", default="2015",
                        help="comma separated, e.g. 2012,2015,2018")
    parser.add_argument("--dates-per-season", type=int, default=3,
                        help="init dates per (year, season), evenly spaced")
    parser.add_argument("--restrict-to-imd-land", action="store_true",
                        help="apply the IMD land mask to the ERA5 path too, so "
                             "an ERA5 run and an IMD run share one domain")
    parser.add_argument("--out", default=None,
                        help="output parquet (default depends on --truth)")
    args = parser.parse_args()

    seasons = [s.strip().upper() for s in args.seasons.split(",") if s.strip()]
    years = [int(y) for y in args.years.split(",") if y.strip()]
    for season in seasons:
        if season not in SEASON_MONTHS:
            parser.error("unknown season {}".format(season))

    if args.truth == "imd":
        truth_label = "IMD 0.25 deg gauge-gridded rainfall (observation, land only)"
    else:
        truth_label = "ERA5 LSP+CP (reanalysis, not gauges)"
        if args.restrict_to_imd_land:
            truth_label += ", restricted to the IMD land mask"

    out = args.out or os.path.join(
        ROOT, "data", "spread_skill_{}.parquet".format(args.truth))
    if not os.path.isabs(out):
        out = os.path.join(ROOT, out)

    fetch = load_module("fetch01", "01_fetch.py")
    features = load_module("feat02", "02_features.py")
    fs = fetch.connect()

    inits = pick_inits(fetch.wednesdays(), years, seasons,
                       args.dates_per_season)
    print("TRUTH: {}".format(truth_label))
    print("Sampling {} init dates: {} x {}".format(
        len(inits), ",".join(seasons), ",".join(str(y) for y in years)))
    for init in inits:
        print("   {}  {}".format(init, season_of(init)))
    if not inits:
        print("No init dates matched. Nothing to do.")
        sys.exit(1)

    # The land mask is time invariant, so derive it once.
    land = None
    if args.truth == "imd" or args.restrict_to_imd_land:
        land = imd_truth.land_mask()
        print("IMD land mask: {} of {} gridpoints carry gauge data ({:.1f}%)"
              .format(int(land.sum()), land.size,
                      100.0 * land.sum() / land.size))

    workdir = tempfile.mkdtemp(prefix="vishwas_era5_")
    records = []
    dropped_missing = 0
    kept_points = 0
    try:
        for number, init in enumerate(inits, 1):
            print("[{}/{}] {}  ({})".format(
                number, len(inits), init, season_of(init)), flush=True)
            paths, starts, ends = fetch.plan_init_date(fs, init)
            keep = [i for i, p in enumerate(paths) if "apcp_sfc" in p]
            blobs = fs.cat_ranges([paths[i] for i in keep],
                                  [starts[i] for i in keep],
                                  [ends[i] for i in keep])
            fields = features.organise(blobs, [paths[i] for i in keep], init)

            init_day = datetime.datetime.strptime(init, "%Y%m%d").date()

            local = None
            if args.truth == "era5":
                needed = set()
                for lead in range(1, 11):
                    valid = init_day + datetime.timedelta(days=lead)
                    needed.add((valid.year, valid.month))
                    previous = valid - datetime.timedelta(days=1)
                    needed.add((previous.year, previous.month))
                keys = []
                for year, month in sorted(needed):
                    keys.extend(era5_files(fs, year, month))
                local = fetch_era5(fs, keys, workdir)
                print("      ERA5: {} files".format(len(local)), flush=True)

            for lead in range(1, 11):
                forecast = features.daily_precip(fields["apcp_sfc"], lead)
                mean = forecast.mean(axis=0)
                spread = forecast.std(axis=0, ddof=1)

                # 5-member versions of the SAME dates, for the ensemble-size
                # sensitivity check (see 05_ensemble_size.py). daily_precip
                # stacks members in sorted order, so the first five are
                # c00,p01,p02,p03,p04 — exactly 01_fetch.MEMBERS, the five
                # that every non-Wednesday date would carry. Computed here
                # because it costs nothing once the data is already fetched.
                core = forecast[:CORE_MEMBERS]
                mean_5 = core.mean(axis=0)
                spread_5 = core.std(axis=0, ddof=1)

                valid = init_day + datetime.timedelta(days=lead)

                if args.truth == "imd":
                    try:
                        truth = imd_truth.daily_rain(valid.year, valid.isoformat())
                    except Exception as exc:
                        print("      day {} IMD truth failed: {}".format(lead, exc))
                        continue
                else:
                    truth = era5_daily_precip(local, valid)
                    if truth is None:
                        print("      day {} truth missing".format(lead))
                        continue
                    if args.restrict_to_imd_land:
                        truth = np.where(land, truth, np.nan)

                lat_grid, lon_grid = np.meshgrid(
                    TARGET_LATS, TARGET_LONS, indexing="ij")
                frame = pd.DataFrame({
                    "init": init, "season": season_of(init), "lead_day": lead,
                    "lat": lat_grid.ravel(), "lon": lon_grid.ravel(),
                    "mean": mean.ravel(), "spread": spread.ravel(),
                    "mean_5": mean_5.ravel(), "spread_5": spread_5.ravel(),
                    "truth": truth.ravel()})

                # MISSING truth is dropped, never coerced to zero. For IMD that
                # is the -999 ocean/no-gauge mask, already NaN by this point.
                before = len(frame)
                frame = frame[np.isfinite(frame["truth"])]
                dropped_missing += before - len(frame)
                kept_points += len(frame)
                records.append(frame)
            del blobs, fields
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    if not records:
        print("No records — cannot compute the correlation.")
        sys.exit(1)

    table = pd.concat(records, ignore_index=True)
    print()
    print("missing truth dropped: {} points ({:.1f}% of the grid-lead cells)"
          .format(dropped_missing,
                  100.0 * dropped_missing / max(dropped_missing + kept_points, 1)))
    table["error"] = np.abs(table["mean"] - table["truth"])

    # Wet points only: log of a dry-point zero is meaningless, and including
    # them would manufacture correlation out of the dry mask.
    wet = table[(table["truth"] > 0.1) | (table["mean"] > 0.1)].copy()
    print("wet filter: {} -> {} rows".format(len(table), len(wet)))
    wet["log_spread"] = np.log(wet["spread"] + 0.1)
    wet["log_error"] = np.log(wet["error"] + 0.1)

    report(wet, truth_label, len(inits))

    # Stamp the truth source into the file so a stray parquet can never be
    # mistaken for the other one downstream.
    wet.attrs["truth"] = truth_label
    wet["truth_source"] = args.truth
    wet.to_parquet(out, index=False, compression="zstd")
    print("  saved {}".format(out))


if __name__ == "__main__":
    main()
