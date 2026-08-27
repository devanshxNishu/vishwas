"""
IMD gridded daily rainfall as a truth source.

WHICH IMD ENDPOINT THIS USES, AND WHY IT MATTERS
------------------------------------------------
IMD publishes daily gridded rainfall through two different endpoints, and only
one of them is usable for this project:

  HISTORICAL (what we use) -- imdlib.get_data()
      imdpune.gov.in/cmpg/Griddata/rainfall.php
      Yearly .grd files, 1901-2024, 0.25 deg, ~25 MB/yr.
      Fully overlaps the 2000-2019 GEFS reforecast.

  REAL-TIME (NOT usable)   -- imdlib.get_real_data()
      imdpune.gov.in/cmpg/Realtimedata/...
      A rolling archive that only starts around 2022, so it does not overlap
      the reforecast at all. An earlier session probed this endpoint, found it
      empty for 2015, and concluded "IMD cannot be used". That conclusion was
      about this endpoint only -- do not repeat it about the historical one.

IMD is gauge-based rainfall OVER LAND. Ocean and out-of-country points are
stored as the undef value -999.0. That is MISSING data, never zero rainfall.
This module converts every -999.0 to NaN on the way out so it cannot be
silently averaged in as a dry day.

Truth only. Nothing in this file may ever be used as a model feature -- see the
FEATURE SOURCE RULE in CLAUDE.md.
"""

import os
import numpy as np
import imdlib

# The IMD historical grid, as documented in CLAUDE.md and verified in P1.
IMD_UNDEF = -999.0
IMD_LAT_FIRST, IMD_LAT_LAST = 6.5, 38.5
IMD_LON_FIRST, IMD_LON_LAST = 66.5, 100.0

# Our analysis grid: 0.5 deg over the India box (CLAUDE.md CONSTRAINTS).
ANALYSIS_LAT = np.arange(5.0, 40.0 + 1e-9, 0.5)
ANALYSIS_LON = np.arange(65.0, 100.0 + 1e-9, 0.5)

# Anchored to the project root, not the current working directory, so the
# cache is the same whether you run from the repo root or from src/.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CACHE = os.path.join(_PROJECT_ROOT, "data", "imd_cache")

# Opening a year means reading a 25 MB file, so keep the last few in memory.
_open_cache = {}


def download_year(year, cache_dir=DEFAULT_CACHE):
    """Download one year of IMD gridded rainfall. Returns the path to the .grd.

    Skips the download if the file is already cached.
    """
    path = os.path.join(cache_dir, "rain", "{}.grd".format(year))
    if os.path.exists(path):
        return path
    os.makedirs(cache_dir, exist_ok=True)
    # fn_format="yearwise" makes imdlib name the file <year>.grd.
    imdlib.get_data("rain", year, year, fn_format="yearwise", file_dir=cache_dir)
    if not os.path.exists(path):
        raise RuntimeError(
            "imdlib reported success but {} is missing. Do not fall back to "
            "another truth source here -- report this instead.".format(path)
        )
    return path


def open_year(year, cache_dir=DEFAULT_CACHE):
    """Return the imdlib IMD object for one year, downloading it if needed."""
    key = (year, cache_dir)
    if key not in _open_cache:
        download_year(year, cache_dir)
        _open_cache[key] = imdlib.open_data(
            "rain", year, year, fn_format="yearwise", file_dir=cache_dir
        )
    return _open_cache[key]


def colocation_index(imd_lat, imd_lon):
    """Map our 0.5 deg analysis grid onto the IMD 0.25 deg grid EXACTLY.

    Returns (lat_idx, lon_idx): integer arrays the same length as ANALYSIS_LAT
    and ANALYSIS_LON, holding the index into the IMD axis, or -1 where our
    point lies outside the IMD domain.

    This is deliberately an exact float match, not a nearest-neighbour lookup.
    The IMD 0.25 grid starts at 6.5/66.5, so every 0.5 step from there lands
    exactly on an IMD point. If that ever stops being true we want a hard
    failure, not a silent 0.25 deg shift in the truth field.
    """
    def match(ours, theirs):
        idx = np.full(len(ours), -1, dtype=int)
        for i, value in enumerate(ours):
            hits = np.nonzero(theirs == value)[0]  # exact equality, on purpose
            if len(hits) == 1:
                idx[i] = hits[0]
            elif len(hits) > 1:
                raise ValueError("duplicate IMD coordinate {}".format(value))
        return idx

    return match(ANALYSIS_LAT, imd_lat), match(ANALYSIS_LON, imd_lon)


def daily_rain(year, day, cache_dir=DEFAULT_CACHE):
    """Daily rainfall in mm on OUR 0.5 deg analysis grid.

    day may be a 1-based day of year (1..365/366) or anything numpy can read as
    a date ("2015-07-15", datetime.date, ...).

    Returns a 2-D array shaped (len(ANALYSIS_LAT), len(ANALYSIS_LON)), i.e.
    always the full 71x71 India box so it stays aligned with the GEFS feature
    grid. Points are NaN when they fall outside the IMD domain OR when IMD
    records them as undef (-999, i.e. ocean / no gauge coverage).
    """
    data = open_year(year, cache_dir)
    imd_lat = np.asarray(data.lat_array)
    imd_lon = np.asarray(data.lon_array)

    if isinstance(day, (int, np.integer)):
        day_index = int(day) - 1
    else:
        start = np.datetime64("{}-01-01".format(year))
        day_index = int((np.datetime64(day) - start) / np.timedelta64(1, "D"))
    if not 0 <= day_index < data.no_days:
        raise IndexError(
            "day {} is outside {} ({} days)".format(day, year, data.no_days)
        )

    # imdlib stores the cube as (time, lon, lat) -- transpose to (lat, lon).
    field = np.asarray(data.data[day_index]).T.astype(float)

    lat_idx, lon_idx = colocation_index(imd_lat, imd_lon)
    out = np.full((len(ANALYSIS_LAT), len(ANALYSIS_LON)), np.nan)
    lat_ok = np.nonzero(lat_idx >= 0)[0]
    lon_ok = np.nonzero(lon_idx >= 0)[0]
    block = field[np.ix_(lat_idx[lat_ok], lon_idx[lon_ok])]
    out[np.ix_(lat_ok, lon_ok)] = block

    # -999 is MISSING, not zero rainfall.
    out[out == IMD_UNDEF] = np.nan
    return out


def land_mask(year=2015, cache_dir=DEFAULT_CACHE):
    """Points on our analysis grid that carry real IMD data.

    A point counts as usable if it is inside the IMD domain and is not undef.
    The undef pattern is the gauge-coverage footprint and is the same every
    day, so one day is enough to derive the mask.
    """
    return np.isfinite(daily_rain(year, 1, cache_dir))
