"""
VISHWAS step 02 — features.

Streams Wednesday init dates through 01_fetch, decodes the thinned GRIB
messages, computes one row per (gridpoint, lead day), appends to a parquet
feature table, and only then marks the date done.

  python src/02_features.py --years 5
  python src/02_features.py --years 5 --limit 2     # short test run
  python src/02_features.py --finalize              # add climatology anomalies

ORDERING: record_done runs after the parquet write returns. See the contract
in 01_fetch.fetch(). Do not reorder.

ANALYSIS GRID: 0.5 degrees. The reforecast ships two grid families —
hgt/ugrd/vgrd at 0.5, and pwat/cape/apcp at 0.25. Every field is COLOCATED
onto the 0.5 gridpoints. The 0.25 grid contains each 0.5 gridpoint exactly,
so this samples real values rather than interpolating, and it keeps all six
variables aligned to the same points.

TWO DIFFERENT WIND FEATURES — DO NOT CONFLATE THEM.
  flow500_deformation  horizontal deformation of the 500 hPa flow. A real
                       predictor, correctly named. It is NOT wind shear and
                       must never be relabelled as such on a slide or in the
                       report.
  shear_500_850        TRUE vertical wind shear, |V500 - V850|. Added
                       2026-08-27 once 850 hPa u/v were fetched from the
                       plain ugrd_pres/vgrd_pres files.
Both are kept. They measure different things.
"""

import argparse
import datetime
import importlib.util
import os
import sys
import tempfile

import numpy as np
import pandas as pd
import xarray as xr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TABLE = os.path.join(ROOT, "data", "features.parquet")
CLIMATOLOGY = os.path.join(ROOT, "data", "climatology.parquet")

# Anomalies are taken against a climatology that is FITTED ON THE TRAINING
# WINDOW ONLY. See finalize().
ANOMALY_COLUMNS = ["pwat_mean", "cape_mean", "precip_mean"]
CLIMATOLOGY_KEYS = ["lat", "lon", "lead_day", "season"]

# India domain and analysis grid.
LAT_MIN, LAT_MAX = 5.0, 40.0
LON_MIN, LON_MAX = 65.0, 100.0
GRID = 0.5
LEAD_DAYS = list(range(1, 11))

# The canonical analysis grid. Every field is placed on exactly this grid so
# rows from different variables line up gridpoint for gridpoint.
TARGET_LATS = np.arange(LAT_MIN, LAT_MAX + 1e-6, GRID)
TARGET_LONS = np.arange(LON_MIN, LON_MAX + 1e-6, GRID)
EXPECTED_MEMBERS = 11


def load_fetch_module():
    """01_fetch.py starts with a digit, so it needs an explicit import."""
    spec = importlib.util.spec_from_file_location(
        "fetch01", os.path.join(HERE, "01_fetch.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def decode(blob):
    """Decode one GRIB message into a 2-D DataArray."""
    path = tempfile.mktemp(suffix=".grib2")
    with open(path, "wb") as handle:
        handle.write(blob)
    try:
        dataset = xr.open_dataset(path, engine="cfgrib",
                                  backend_kwargs={"indexpath": ""})
        name = list(dataset.data_vars)[0]
        array = dataset[name].load()
        dataset.close()
        return array
    finally:
        os.unlink(path)


def to_india_grid(array):
    """
    Cut to the India box and place the field on the 0.5 degree analysis grid.

    Both grid families are sampled at exactly the analysis gridpoints. The
    0.25 grid contains every 0.5 gridpoint exactly, so this is colocation,
    not interpolation — no value is invented and nothing is offset.

    Block-averaging the 0.25 fields was the first attempt and it was wrong:
    a 2x2 mean over the box lands cell centres on 5.125, 5.625, ... which is
    half a cell off the 0.5 grid, so precip would have been silently paired
    with the wrong gridpoint.
    """
    array = array.sortby("latitude").sortby("longitude")
    return array.sel(latitude=TARGET_LATS, longitude=TARGET_LONS,
                     method="nearest")


def gradient_magnitude(field, lats):
    """
    |grad| of a 2-D field in units per 100 km.

    Longitude spacing shrinks with latitude, so the x-term carries cos(lat).
    """
    metres = GRID * 111_000.0
    d_lat = np.gradient(field, axis=0) / metres
    d_lon = np.gradient(field, axis=1) / (
        metres * np.cos(np.deg2rad(lats))[:, None])
    return np.sqrt(d_lat ** 2 + d_lon ** 2) * 100_000.0


def horizontal_deformation(u_field, v_field, lats):
    """
    Total deformation of the 500 hPa flow, per 100 km.

    NOT vertical wind shear — see the module docstring.
    """
    metres = GRID * 111_000.0
    cos_lat = np.cos(np.deg2rad(lats))[:, None]
    du_dx = np.gradient(u_field, axis=1) / (metres * cos_lat)
    du_dy = np.gradient(u_field, axis=0) / metres
    dv_dx = np.gradient(v_field, axis=1) / (metres * cos_lat)
    dv_dy = np.gradient(v_field, axis=0) / metres
    stretching = du_dx - dv_dy
    shearing = dv_dx + du_dy
    return np.sqrt(stretching ** 2 + shearing ** 2) * 100_000.0


def vertical_shear(u_upper, v_upper, u_lower, v_lower):
    """
    TRUE vertical wind shear: the magnitude of the vector difference between
    two levels, in m/s.

    This is a genuinely different quantity from horizontal_deformation above,
    which never leaves a single level. Over India in the monsoon the 500-850
    difference is typically ~5-20 m/s, driven by the easterly shear between
    the low-level westerly jet and the upper-level easterlies.
    """
    return np.sqrt((u_upper - u_lower) ** 2 + (v_upper - v_lower) ** 2)


def organise(blobs, paths, init):
    """
    Group decoded messages as fields[variable][member][step_key].

    Fails loudly if any member is short — never average over 10 members when
    11 were expected.
    """
    fields = {}
    for blob, path in zip(blobs, paths):
        name = path.split("/")[-1]
        member = name.rsplit("_", 1)[1].replace(".grib2", "")
        variable = name.split("_{}00_".format(init))[0]
        array = decode(blob)
        step = int(array.step.values / np.timedelta64(1, "h")) if "step" in array.coords else None
        fields.setdefault(variable, {}).setdefault(member, {})[step] = array

    for variable, members in fields.items():
        if len(members) != EXPECTED_MEMBERS:
            raise ValueError(
                "{}: {} has {} members, expected {} — refusing to average "
                "over a short ensemble".format(
                    init, variable, len(members), EXPECTED_MEMBERS))
    return fields


def stack_members(per_member, step_filter):
    """Stack one variable's members into (member, lat, lon) for one step."""
    stack = []
    for member in sorted(per_member):
        steps = per_member[member]
        matches = [s for s in steps if step_filter(s)]
        if len(matches) != 1:
            raise ValueError("expected 1 step, got {}".format(len(matches)))
        stack.append(to_india_grid(steps[matches[0]]).values)
    return np.stack(stack)


def daily_precip(per_member, lead_day):
    """
    Daily accumulated precipitation: SUM the four 6-hour buckets.

    apcp resets every 6 hours, so the buckets are disjoint and additive.
    Differencing them would be wrong.
    """
    end = 24 * lead_day
    wanted = [end - 18, end - 12, end - 6, end]
    stack = []
    for member in sorted(per_member):
        steps = per_member[member]
        total = None
        found = 0
        for step_end in wanted:
            for key, array in steps.items():
                if key == step_end:
                    grid = to_india_grid(array).values
                    total = grid if total is None else total + grid
                    found += 1
                    break
        if found != 4:
            raise ValueError(
                "day {}: found {} of 4 precip buckets".format(lead_day, found))
        stack.append(total)
    return np.stack(stack)


def build_rows(fields, init):
    """One row per (gridpoint, lead day) for this init date.

    THIS IS THE FEATURE LIST. Everything emitted here comes from GEFS
    reforecast fields and nothing else — see the FEATURE SOURCE RULE in
    CLAUDE.md. ERA5 and IMD are TRUTH ONLY and must never appear as columns.

    NOT IMPLEMENTED, AND READ THIS BEFORE YOU IMPLEMENT IT: the planned
    "regional error climatology" feature is derived from |forecast - truth|,
    which makes it TRUTH-DERIVED. Computed over the whole record it is a
    direct read of the answer and will inflate every metric silently. It is
    defensible in exactly one form — "the error record we already had before
    the test period began" — meaning computed on the TRAINING WINDOW ONLY and
    then FROZEN, the same discipline finalize() applies to the climatology
    anomalies. If it ships in any other form, it is leakage.
    """
    sample = to_india_grid(
        fields["hgt_pres_abv700mb"]["c00"][24])
    lats = sample.latitude.values
    lons = sample.longitude.values
    lat_grid, lon_grid = np.meshgrid(lats, lons, indexing="ij")

    frames = []
    for day in LEAD_DAYS:
        hours = 24 * day
        exact = lambda s, h=hours: s == h

        gh = stack_members(fields["hgt_pres_abv700mb"], exact)
        u = stack_members(fields["ugrd_pres_abv700mb"], exact)
        v = stack_members(fields["vgrd_pres_abv700mb"], exact)
        u850 = stack_members(fields["ugrd_pres"], exact)
        v850 = stack_members(fields["vgrd_pres"], exact)
        pwat = stack_members(fields["pwat_eatm"], exact)
        cape = stack_members(fields["cape_sfc"], exact)
        precip = daily_precip(fields["apcp_sfc"], day)

        for name, block in [("gh", gh), ("u", u), ("v", v),
                            ("u850", u850), ("v850", v850),
                            ("pwat", pwat), ("cape", cape),
                            ("precip", precip)]:
            assert block.shape[0] == EXPECTED_MEMBERS, \
                "{}: {} members".format(name, block.shape[0])
            assert block.shape[1:] == lat_grid.shape, \
                "{}: shape {} != {}".format(name, block.shape[1:], lat_grid.shape)

        gh_mean = gh.mean(axis=0)
        u_mean = u.mean(axis=0)
        v_mean = v.mean(axis=0)
        u850_mean = u850.mean(axis=0)
        v850_mean = v850.mean(axis=0)

        frame = pd.DataFrame({
            "init": init,
            "lead_day": day,
            "lat": lat_grid.ravel(),
            "lon": lon_grid.ravel(),
            "gh500_mean": gh_mean.ravel(),
            "gh500_spread": gh.std(axis=0, ddof=1).ravel(),
            "u500_mean": u_mean.ravel(),
            "u500_spread": u.std(axis=0, ddof=1).ravel(),
            "v500_mean": v_mean.ravel(),
            "v500_spread": v.std(axis=0, ddof=1).ravel(),
            "pwat_mean": pwat.mean(axis=0).ravel(),
            "pwat_spread": pwat.std(axis=0, ddof=1).ravel(),
            "cape_mean": cape.mean(axis=0).ravel(),
            "cape_spread": cape.std(axis=0, ddof=1).ravel(),
            "precip_mean": precip.mean(axis=0).ravel(),
            "precip_spread": precip.std(axis=0, ddof=1).ravel(),
            "gh500_gradient": gradient_magnitude(gh_mean, lats).ravel(),
            "wind500_speed": np.sqrt(u_mean ** 2 + v_mean ** 2).ravel(),
            "u850_mean": u850_mean.ravel(),
            "v850_mean": v850_mean.ravel(),
            # TRUE vertical shear. Distinct from flow500_deformation below,
            # which is a single-level horizontal quantity.
            "shear_500_850": vertical_shear(
                u_mean, v_mean, u850_mean, v850_mean).ravel(),
            "flow500_deformation": horizontal_deformation(
                u_mean, v_mean, lats).ravel(),
        })
        frames.append(frame)

    rows = pd.concat(frames, ignore_index=True)
    month = int(init[4:6])
    rows["month"] = month
    rows["season"] = ("DJF" if month in (12, 1, 2) else
                      "MAM" if month in (3, 4, 5) else
                      "JJAS" if month in (6, 7, 8, 9) else "ON")
    return rows


def append_parquet(rows):
    """Append one date's rows. Written per date so a kill loses one date."""
    directory = os.path.dirname(TABLE)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    part = TABLE.replace(".parquet", "") + "_parts"
    if not os.path.isdir(part):
        os.makedirs(part)
    target = os.path.join(part, "{}.parquet".format(rows["init"].iloc[0]))
    rows.to_parquet(target, index=False, compression="zstd")
    return target


def finalize(train_end):
    """
    Add climatology-relative anomalies once every date is in.

    THE CLIMATOLOGY IS A FITTED PARAMETER, NOT A DESCRIPTION OF THE DATA.
    It is computed on init dates at or before --train-end and then applied
    unchanged to every row, train and test alike.

    This used to be wrong in a way that was invisible. The old version did
        table.groupby(keys)[column].transform("mean")
    over the WHOLE concatenated table, so each test row's anomaly was taken
    against a mean that already included the test period — and included that
    row itself. It never failed, it never warned; it just quietly inflated
    every downstream metric. That is exactly the failure mode the time-based
    split exists to prevent.

    A test group with no training counterpart gets NaN. It does NOT fall back
    to its own period's mean, which would reintroduce the leak for precisely
    the groups where it does the most damage.
    """
    part = TABLE.replace(".parquet", "") + "_parts"
    files = sorted(os.path.join(part, f) for f in os.listdir(part)
                   if f.endswith(".parquet"))
    if not files:
        print("No parts to finalize.")
        return
    table = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    print("loaded {} rows from {} dates".format(len(table), len(files)))

    # Mixed schemas would silently produce all-NaN columns here.
    missing = [c for c in ANOMALY_COLUMNS + CLIMATOLOGY_KEYS
               if c not in table.columns]
    if missing:
        raise ValueError(
            "parts are missing {} — the parts directory holds mixed schemas. "
            "Rebuild the stale dates rather than finalizing this.".format(missing))

    cutoff = pd.Timestamp(train_end)
    init_date = pd.to_datetime(table["init"], format="%Y%m%d")
    is_train = init_date <= cutoff
    n_train_dates = table.loc[is_train, "init"].nunique()
    n_test_dates = table.loc[~is_train, "init"].nunique()
    print("train window: init <= {}  ({} dates, {} rows)".format(
        cutoff.date(), n_train_dates, int(is_train.sum())))
    print("test  window: init >  {}  ({} dates, {} rows)".format(
        cutoff.date(), n_test_dates, int((~is_train).sum())))
    if n_train_dates == 0:
        raise ValueError(
            "no init dates at or before {} — cannot fit a climatology. "
            "Refusing to fall back to the full-period mean.".format(cutoff.date()))
    if n_test_dates == 0:
        print("  NOTE: every date is in the training window, so this run cannot "
              "demonstrate the leak is fixed. Re-check with a real split.")

    # Fit on train only, then apply to everything.
    climatology = (table[is_train]
                   .groupby(CLIMATOLOGY_KEYS)[ANOMALY_COLUMNS]
                   .mean()
                   .reset_index())
    renamed = {c: c.replace("_mean", "_clim") for c in ANOMALY_COLUMNS}
    climatology = climatology.rename(columns=renamed)

    merged = table.merge(climatology, on=CLIMATOLOGY_KEYS, how="left")
    for column in ANOMALY_COLUMNS:
        anomaly = column.replace("_mean", "_anomaly")
        table[anomaly] = merged[column].values - merged[renamed[column]].values

    # Groups present in test but absent from train become NaN. Report them
    # loudly — a silent NaN column is how this bug hid the first time.
    unmatched = merged[renamed[ANOMALY_COLUMNS[0]]].isna().values
    if unmatched.any():
        print("  {} rows ({:.2f}%) had NO training counterpart -> anomaly = NaN"
              .format(int(unmatched.sum()), 100.0 * unmatched.mean()))
        orphan_test = int((unmatched & (~is_train).values).sum())
        print("     of which {} are test rows".format(orphan_test))
    else:
        print("  every row matched a training climatology group")

    climatology.to_parquet(CLIMATOLOGY, index=False, compression="zstd")
    print("wrote {} ({} groups, fitted on init <= {})".format(
        CLIMATOLOGY, len(climatology), cutoff.date()))

    table.to_parquet(TABLE, index=False, compression="zstd")
    size = os.path.getsize(TABLE) / 1e6
    print("wrote {} ({:.1f} MB, {} rows, {} columns)".format(
        TABLE, size, len(table), len(table.columns)))


def main():
    parser = argparse.ArgumentParser(description="VISHWAS feature build.")
    parser.add_argument("--years", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--finalize", action="store_true")
    parser.add_argument("--train-end", default=None,
                        help="last init date IN THE TRAINING WINDOW, "
                             "e.g. 2015-12-31. Required with --finalize: the "
                             "climatology is fitted on this window only.")
    args = parser.parse_args()

    if args.finalize:
        if not args.train_end:
            parser.error(
                "--finalize requires --train-end (e.g. --train-end 2015-12-31). "
                "There is deliberately no default: a climatology fitted over "
                "the whole record leaks the test period into every anomaly.")
        finalize(args.train_end)
        return
    if args.years is None and args.limit is None:
        parser.print_help()
        sys.exit(1)

    fetch_module = load_fetch_module()
    filesystem = fetch_module.connect()

    def on_date(init, blobs, paths):
        fields = organise(blobs, paths, init)
        rows = build_rows(fields, init)
        target = append_parquet(rows)
        print("      -> {} rows -> {}".format(len(rows),
                                              os.path.basename(target)))

    fetch_module.fetch(filesystem, args.years, args.limit, False, on_date)


if __name__ == "__main__":
    main()
