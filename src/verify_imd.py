"""
VERIFY-IMD: the four conditions from CLAUDE.md that must pass before we are
allowed to describe the ERA5 -> IMD truth switch as real.

Verification only. This script does not modify any pipeline stage.
Run:  python src/verify_imd.py
"""

import sys
import numpy as np

import imd_truth as it


results = {}


def report(condition, passed, detail=""):
    results[condition] = passed
    print("  {} {}".format("PASS" if passed else "FAIL", condition))
    if detail:
        for line in detail.strip().splitlines():
            print("       " + line)


print("=" * 72)
print("VERIFY-IMD  (truth source: IMD historical gridded rainfall, 0.25 deg)")
print("=" * 72)

# ---------------------------------------------------------------- condition a
print("\n[a] imdlib installs, imports, and returns real 2015 data")
try:
    import imdlib
    path = it.download_year(2015)
    data = it.open_year(2015)
    cube = np.asarray(data.data)
    finite = cube[cube != it.IMD_UNDEF]
    report(
        "a. imdlib works and 2015 is real data",
        cube.shape[0] in (365, 366) and finite.size > 0,
        "imdlib {} on Python {}.{}, no GDAL required\n"
        "cached file: {}\n"
        "cube shape (time, lon, lat): {}\n"
        "days: {}  range: {} to {}\n"
        "valid-value range: {:.2f} to {:.2f} mm".format(
            imdlib.__version__, sys.version_info[0], sys.version_info[1],
            path, cube.shape, data.no_days, data.start_day, data.end_day,
            finite.min(), finite.max(),
        ),
    )
except Exception as exc:
    report("a. imdlib works and 2015 is real data", False, repr(exc))
    print("\nSTOPPING: nothing downstream can be checked without data.")
    sys.exit(1)

# ---------------------------------------------------------------- condition b
print("\n[b] Grid geometry matches what CLAUDE.md records")
imd_lat = np.asarray(data.lat_array)
imd_lon = np.asarray(data.lon_array)
checks = [
    ("lon count == 135", len(imd_lon) == 135, len(imd_lon)),
    ("lat count == 129", len(imd_lat) == 129, len(imd_lat)),
    ("lon step == 0.25", np.allclose(np.diff(imd_lon), 0.25), np.diff(imd_lon)[0]),
    ("lat step == 0.25", np.allclose(np.diff(imd_lat), 0.25), np.diff(imd_lat)[0]),
    ("first point 6.5N / 66.5E",
     imd_lat[0] == it.IMD_LAT_FIRST and imd_lon[0] == it.IMD_LON_FIRST,
     (imd_lat[0], imd_lon[0])),
    ("last point 38.5N / 100.0E",
     imd_lat[-1] == it.IMD_LAT_LAST and imd_lon[-1] == it.IMD_LON_LAST,
     (imd_lat[-1], imd_lon[-1])),
]
for label, ok, got in checks:
    print("       {} {:<28} got {}".format("ok  " if ok else "BAD ", label, got))

# Units: the file is exactly nlon*nlat*ndays float32 values, which is itself
# evidence the decode is right -- a wrong header would not divide evenly.
import os
expected_bytes = 135 * 129 * data.no_days * 4
actual_bytes = os.path.getsize(path)
size_ok = expected_bytes == actual_bytes
print("       {} float32 byte count       {} expected, {} on disk".format(
    "ok  " if size_ok else "BAD ", expected_bytes, actual_bytes))
report("b. grid geometry matches CLAUDE.md",
       all(c[1] for c in checks) and size_ok)

# ---------------------------------------------------------------- condition c
print("\n[c] Colocation is EXACT (no nearest-neighbour fallback)")
lat_idx, lon_idx = it.colocation_index(imd_lat, imd_lon)
lat_in, lon_in = lat_idx >= 0, lon_idx >= 0

# Hard assertion: every in-domain point must be an exact float match.
assert np.all(imd_lat[lat_idx[lat_in]] == it.ANALYSIS_LAT[lat_in]), "lat drift"
assert np.all(imd_lon[lon_idx[lon_in]] == it.ANALYSIS_LON[lon_in]), "lon drift"

lat_out = it.ANALYSIS_LAT[~lat_in]
lon_out = it.ANALYSIS_LON[~lon_in]
total = len(it.ANALYSIS_LAT) * len(it.ANALYSIS_LON)
kept = int(lat_in.sum()) * int(lon_in.sum())
report(
    "c. exact colocation, domain shrinkage quantified",
    True,
    "our analysis grid: 0.5 deg, {} lat x {} lon = {} points\n"
    "exact float match, zero interpolation, for every in-domain point\n"
    "lat outside IMD: {}\n"
    "lon outside IMD: {}\n"
    "kept {} lat x {} lon = {} points  ({} dropped, {:.1f}% of the box)".format(
        len(it.ANALYSIS_LAT), len(it.ANALYSIS_LON), total,
        [round(v, 2) for v in lat_out] or "none",
        [round(v, 2) for v in lon_out] or "none",
        int(lat_in.sum()), int(lon_in.sum()), kept,
        total - kept, 100.0 * (total - kept) / total,
    ),
)

# ---------------------------------------------------------------- condition d
print("\n[d] Land mask: -999 is MISSING, never zero")
mask = it.land_mask(2015)
land = int(mask.sum())

# Do not assume the undef footprint is constant -- check it across the year.
sample_days = [1, 60, 121, 182, 244, 305, 365]
varies = [d for d in sample_days
          if not np.array_equal(np.isfinite(it.daily_rain(2015, d)), mask)]

# Surviving points per latitude row, as a coverage profile.
per_row = mask.sum(axis=1)
profile = "\n".join(
    "  {:>5.1f}N : {:>2d} / {} land points".format(lat, int(n), mask.shape[1])
    for lat, n in zip(it.ANALYSIS_LAT, per_row) if n > 0
)
report(
    "d. land mask derived, undef treated as missing",
    land > 0 and not varies,
    "usable land points: {} / {} of the full box  ({:.1f}%)\n"
    "                    {} / {} of the in-IMD-domain box  ({:.1f}%)\n"
    "undef footprint identical on days {}: {}\n"
    "-999 -> NaN, never 0.0\n"
    "coverage by latitude row:\n{}".format(
        land, total, 100.0 * land / total,
        land, kept, 100.0 * land / kept,
        sample_days, "yes" if not varies else "NO, differs on {}".format(varies),
        profile,
    ),
)

# --------------------------------------------------------- physics sanity
print("\n[physics] Monsoon July must be dramatically wetter than January")
def all_india_mean(datestr):
    field = it.daily_rain(2015, datestr)
    return np.nanmean(field)

july = ["2015-07-{:02d}".format(d) for d in (5, 10, 15, 20, 25)]
january = ["2015-01-{:02d}".format(d) for d in (5, 10, 15, 20, 25)]
jul_vals = [all_india_mean(d) for d in july]
jan_vals = [all_india_mean(d) for d in january]
for label, days, vals in (("JUL", july, jul_vals), ("JAN", january, jan_vals)):
    print("       {}  {}".format(
        label, "  ".join("{}={:5.2f}".format(d[-2:], v) for d, v in zip(days, vals))))
jul_mean, jan_mean = float(np.mean(jul_vals)), float(np.mean(jan_vals))
physics_ok = jul_mean > 3.0 and jul_mean > 5 * jan_mean
print("       July mean {:.2f} mm/day vs January mean {:.2f} mm/day  ({:.0f}x)".format(
    jul_mean, jan_mean, jul_mean / max(jan_mean, 1e-9)))
report("physics: monsoon signal present in the decode", physics_ok)

# ---------------------------------------------------------------- verdict
print("\n" + "=" * 72)
for name, ok in results.items():
    print("  {}  {}".format("PASS" if ok else "FAIL", name))
verdict = all(results.values())
print("\nVERIFY-IMD: {}".format("ALL CONDITIONS PASS" if verdict else "FAILED"))
print("=" * 72)
sys.exit(0 if verdict else 1)
