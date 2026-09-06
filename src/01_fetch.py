"""
VISHWAS step 01 — fetch.

Two modes:

  python src/01_fetch.py --probe
      Walk the public S3 buckets and print what is ACTUALLY there.

  python src/01_fetch.py --years 5
      Download the India subset for N years, using the confirmed prefixes.

Everything here uses anonymous S3 access. No credentials, no paid tier.

Honesty rule from CLAUDE.md: this script never invents data. If a bucket
or prefix is missing, it says so and stops.

LAYOUT CONFIRMED BY PROBE (2026-08-25) — these are no longer guesses:

  GEFSv12 reforecast
    noaa-gefs-retrospective/GEFSv12/reforecast/{YYYY}/{YYYYMMDDHH}/
        {member}/Days:1-10/{var}_{level}_{YYYYMMDDHH}_{member}.grib2
    years 2000-2020, members c00 p01 p02 p03 p04 (5 — exactly our budget),
    one grib2 file per variable, plus a .idx sidecar.

  ERA5 truth
    nsf-ncar-era5/e5.oper.an.pl/{YYYYMM}/
        e5.oper.an.pl.128_{code}_{var}.ll025sc.{start}_{end}.nc   (daily files)
    nsf-ncar-era5/e5.oper.an.sfc/{YYYYMM}/
        e5.oper.an.sfc.128_{code}_{var}.ll025sc.{start}_{end}.nc  (monthly files)
    months 194001 onward.

  Operational GEFS (live dashboard only, NOT for the core claim)
    noaa-gefs-pds/gefs.{YYYYMMDD}/{HH}/...     (2017-01-01 onward, 31 members)

  Gotchas confirmed by probe:
    - hgt_pres / ugrd_pres / vgrd_pres stop at 800 mb. NO 500 hPa.
      500 hPa lives in the *_abv700mb files.
    - apcp_sfc is bucketed, not running: alternating T..T+3 and T..T+6
      windows. The 40 six-hour buckets tile 0-240h with no gaps, so a
      daily total is a SUM of 4 buckets, not a difference.
    - reforecast/2020/ holds one misfiled 2010 date. Real range is 2000-2019.
    - 11-member dates are WEDNESDAYS (p05-p10 present). All others carry 5.
"""

import argparse
import concurrent.futures
import datetime
import json
import os
import re
import sys

import s3fs

# India domain, from CLAUDE.md.
LAT_MIN, LAT_MAX = 5, 40
LON_MIN, LON_MAX = 65, 100

# Confirmed by --probe. Descend from these, not from the bucket root.
GEFS_ROOT = "noaa-gefs-retrospective/GEFSv12/reforecast"
ERA5_PL = "nsf-ncar-era5/e5.oper.an.pl"
ERA5_SFC = "nsf-ncar-era5/e5.oper.an.sfc"
GEFS_OPER_ROOT = "noaa-gefs-pds"

PROBE_TARGETS = [
    ("GEFSv12 reforecast (ensemble)", GEFS_ROOT),
    ("ERA5 truth — pressure levels", ERA5_PL),
    ("ERA5 truth — surface", ERA5_SFC),
    ("Operational GEFS (dashboard only)", GEFS_OPER_ROOT),
]

# The 5 reforecast members. c00 is the control run, p01-p04 are perturbed.
# Wednesdays additionally carry p05-p10 (11 total) — see MEMBERS_WEEKLY.
MEMBERS = ["c00", "p01", "p02", "p03", "p04"]
MEMBERS_WEEKLY = MEMBERS + ["p05", "p06", "p07", "p08", "p09", "p10"]

# Corrected variable list. The 500 hPa fields are in the *_abv700mb files.
VARS_500MB = [
    "hgt_pres_abv700mb",   # 500 hPa geopotential -> gradient feature
    "ugrd_pres_abv700mb",  # 500 hPa u wind -> shear
    "vgrd_pres_abv700mb",  # 500 hPa v wind -> shear
]
# 850 hPa lives in the PLAIN *_pres files, NOT the *_abv700mb files. The plain
# files carry 1000/975/950/925/900/850/800 mb and contain no 500 hPa at all;
# the abv700mb files are the mirror image. So true 500-850 vertical shear needs
# BOTH families — that is why this list exists separately from VARS_500MB.
VARS_850MB = [
    "ugrd_pres",   # 850 hPa u wind -> vertical shear against 500 hPa
    "vgrd_pres",   # 850 hPa v wind -> vertical shear against 500 hPa
]
VARS_INSTANT = ["pwat_eatm", "cape_sfc"]   # single level, instantaneous
VAR_ACCUM = "apcp_sfc"                     # single level, bucketed accumulation

# Day 1-10 confidence map -> daily lead steps are enough. No 3-hourly.
DAILY_STEPS = [24 * day for day in range(1, 11)]

# Wednesday-only sampling: every Wednesday carries 11 members, and 7-day
# spacing is closer to synoptically independent than 3-day.
WEDNESDAY = 2                      # datetime.date.weekday() code
ARCHIVE_START = datetime.date(2000, 1, 1)
ARCHIVE_END = datetime.date(2019, 12, 31)   # 2020/ holds one misfiled date

# How many daily-step messages each variable must contribute PER MEMBER. apcp
# is 40 because a daily total is the sum of four 6-hour buckets; everything else
# is one message per lead day.
EXPECTED_MESSAGES = {
    "apcp_sfc": 40, "cape_sfc": 10, "pwat_eatm": 10,
    "hgt_pres_abv700mb": 10, "ugrd_pres_abv700mb": 10, "vgrd_pres_abv700mb": 10,
    "ugrd_pres": 10, "vgrd_pres": 10,
}

# Dates the archive cannot serve completely. Found 2026-09-06 by scanning every
# 2015-2019 Wednesday's index: four dates carry a member whose *_abv700mb files
# hold only some of the ten daily steps (e.g. 20160224 p08 has 4 of 10). The
# 0.25 deg families are complete on all four; only the 0.5 deg ones are short.
#
# THESE DATES ARE SKIPPED, NOT PATCHED. The two alternatives are both worse:
# dropping the short member gives that date a 10-member ensemble, and CLAUDE.md's
# own 5 -> 11 sensitivity shows ensemble size moves the spread baseline (about
# +0.015 conditional), so a mixed-size record would put an inhomogeneity inside
# the incumbent we are measuring against; and taking the member's missing steps
# as absent would silently shorten the lead-time axis for one date.
# Skipped dates are recorded in INCOMPLETE, never marked done, and printed in
# the run summary, so the loss is visible rather than inferred from a row count.
INCOMPLETE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "data", "raw", "incomplete.jsonl")

# Resume state. The download WILL be interrupted; restarting from zero is a day.
MANIFEST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "raw", "manifest.jsonl")

# How many entries to show per directory level, so the output stays readable.
SAMPLE = 12


# botocore defaults to 10 pooled connections. One init date is ~1,210 byte-range
# GETs, so the pool — not the link — is what limits the fetch: measured on
# 2026-09-06, four unfetched dates, 200 messages each, alternating settings so a
# recovering network could not flatter the later run,
#     default pool (10)   4.43 MB/s
#     pool = 128          6.09-6.44 MB/s
# This is a TRANSPORT setting only. The same byte ranges are requested and the
# same GRIB messages come back; every blob is still checked for its GRIB/7777
# envelope in fetch(). Raising it further did not help — batch_size 256 with a
# 256 pool measured slower than the default batch size at pool 128.
POOL_CONNECTIONS = 128


def connect():
    """Anonymous read-only S3 filesystem."""
    return s3fs.S3FileSystem(
        anon=True, config_kwargs={"max_pool_connections": POOL_CONNECTIONS})


def list_path(fs, path):
    """
    List one S3 path.

    s3fs echoes the directory itself back as an entry, which sends a naive
    walk into an infinite loop. Drop that self-entry here.
    """
    try:
        entries = fs.ls(path, detail=False)
    except Exception as err:
        print("    ! could not list {}: {}".format(path, err))
        return []
    wanted = path.rstrip("/")
    return sorted(e for e in entries if e.rstrip("/") != wanted)


def parse_idx(idx_text, file_size):
    """
    Turn a .idx sidecar into [(start, end, description), ...].

    A GRIB message runs from its own offset to the next one; the last runs
    to end of file. Those byte ranges are what we hand to S3.
    """
    lines = [l for l in idx_text.strip().split("\n") if l]
    offsets = [int(l.split(":")[1]) for l in lines]
    messages = []
    for i, line in enumerate(lines):
        start = offsets[i]
        end = offsets[i + 1] if i + 1 < len(offsets) else file_size
        messages.append((start, end, line))
    return messages


def wanted_500mb(line):
    """500 hPa, and only the daily lead steps."""
    if ":500 mb:" not in line:
        return False
    return any(":{} hour fcst".format(h) in line for h in DAILY_STEPS)


def wanted_850mb(line):
    """850 hPa, and only the daily lead steps.

    Mirrors wanted_500mb exactly. The plain *_pres files carry every level
    from 1000 to 800 mb at 3-hourly steps, so without both filters this would
    pull roughly 8x more data than we need.
    """
    if ":850 mb:" not in line:
        return False
    return any(":{} hour fcst".format(h) in line for h in DAILY_STEPS)


def wanted_instant(line):
    """Single-level instantaneous field, daily lead steps only."""
    return any(":{} hour fcst".format(h) in line for h in DAILY_STEPS)


def wanted_accum(line):
    """
    Keep the six-hour precipitation buckets.

    apcp_sfc alternates T..T+3 and T..T+6 windows and RESETS every 6 hours.
    The forty 6-hour buckets tile 0-240h exactly, so a daily total is the
    SUM of four of them. Do not thin these to ten steps and do not difference
    them — differencing a bucketed field gives nonsense.
    """
    match = re.search(r":(\d+)-(\d+) hour acc", line)
    if not match:
        return False
    start, end = int(match.group(1)), int(match.group(2))
    return end - start == 6


def probe_path(fs, label, path, depth=4):
    """Print the first few levels below one path so we can see its real layout."""
    print("=" * 70)
    print("{}  ->  s3://{}/".format(label, path))
    print("=" * 70)

    if not fs.exists(path):
        print("  PATH NOT FOUND — the prefix in this script is wrong.")
        print()
        return

    for level in range(depth):
        entries = list_path(fs, path)
        if not entries:
            break

        indent = "  " * (level + 1)
        print("{}level {}: {} entries under {}/".format(
            indent, level, len(entries), path))
        for entry in entries[:SAMPLE]:
            print("{}  {}".format(indent, entry.split("/")[-1]))
        if len(entries) > SAMPLE:
            print("{}  ... and {} more".format(indent, len(entries) - SAMPLE))

        # Descend into the first subdirectory, if there is one.
        subdirs = [e for e in entries if fs.isdir(e)]
        if not subdirs:
            print("{}  (leaf level — these are files)".format(indent))
            break
        path = subdirs[0]

    print()


def probe(fs):
    """Probe every path we care about."""
    print()
    print("VISHWAS probe — confirming real bucket layout")
    print("Domain of interest: lat {}-{}N, lon {}-{}E".format(
        LAT_MIN, LAT_MAX, LON_MIN, LON_MAX))
    print()
    for label, path in PROBE_TARGETS:
        probe_path(fs, label, path)
    print("Probe done.")


def fetch(fs, years, limit=None, dry_run=False, on_date=None):
    """
    Stream Wednesday init dates, skipping ones already in the manifest.

    Nothing is kept on disk. Each date's GRIB is fetched, handed to
    `on_date(init, blobs, paths)`, and dropped.

    ORDERING CONTRACT — do not rearrange:
      `on_date` must durably commit the feature rows before it returns.
      record_done() runs ONLY after it returns cleanly. If on_date raises,
      the date is NOT marked done and will be retried on the next run.
      Marking a date done after the fetch but before the features are
      committed creates silent gaps that no later run will fill.

    With no `on_date` this refuses to write a manifest at all, so a bare
    fetch can never leave dates falsely marked complete.
    """
    dates = wednesdays()
    if years:
        cutoff = ARCHIVE_END - datetime.timedelta(days=365 * years)
        dates = [d for d in dates
                 if datetime.datetime.strptime(d, "%Y%m%d").date() >= cutoff]

    done = load_manifest()
    known_incomplete = load_incomplete()
    todo = [d for d in dates
            if d not in done and d not in known_incomplete]
    if limit:
        todo = todo[:limit]

    print("Wednesday sampling: {} dates in range, {} already done, {} to go."
          .format(len(dates), len(done), len(todo)))
    if known_incomplete:
        print("  {} date(s) skipped as unservable by the archive: {}".format(
            len(known_incomplete), ", ".join(sorted(known_incomplete))))
    if not todo:
        print("Nothing left to fetch.")
        return

    if dry_run:
        print("Dry run — would fetch: {} ... {}".format(todo[0], todo[-1]))
        return

    if on_date is None:
        print()
        print("No feature callback supplied. Refusing to run a bare fetch:")
        print("it would mark dates complete with no features written.")
        print("Use 02_features.py, which passes its own on_date.")
        sys.exit(1)

    skipped = []
    for number, init in enumerate(todo, 1):
        clock = datetime.datetime.now()
        paths, starts, ends = plan_init_date(fs, init)

        # Integrity BEFORE transfer. A date the archive cannot serve in full is
        # skipped and recorded; it must never become a short ensemble, and it
        # must never crash the run three hours in. See INCOMPLETE above.
        short = shortfall(init, paths)
        if short:
            record_incomplete(init, short)
            skipped.append(init)
            print("  [{}/{}] {}  SKIPPED — archive incomplete: {}".format(
                number, len(todo), init,
                "; ".join("{} {}".format(v, m) for v, m in sorted(short.items()))))
            continue

        blobs = fs.cat_ranges(paths, starts, ends)

        bad = [i for i, b in enumerate(blobs)
               if not (b[:4] == b"GRIB" and b[-4:] == b"7777")]
        if bad:
            print("  {} — {} malformed messages, e.g. {}".format(
                init, len(bad), paths[bad[0]]))
            sys.exit(1)

        n_bytes = sum(len(b) for b in blobs)

        # Features first. If this raises, we never reach record_done.
        on_date(init, blobs, paths)
        del blobs

        seconds = (datetime.datetime.now() - clock).total_seconds()
        record_done(init, len(paths), n_bytes, seconds)
        print("  [{}/{}] {}  {} msgs  {:.1f} MB  {:.1f} s".format(
            number, len(todo), init, len(paths), n_bytes / 1e6, seconds))

    if skipped:
        print()
        print("SKIPPED {} date(s) the archive could not serve in full: {}".format(
            len(skipped), ", ".join(skipped)))
        print("Recorded in {}. They are NOT in the feature table.".format(INCOMPLETE))


def shortfall(init, paths):
    """Which (variable, member) pairs the archive cannot serve in full.

    Reads the PLAN, so it costs nothing beyond the index fetch that already
    happened — the check runs before a single message byte is transferred.
    """
    counts = {}
    for path in paths:
        name = path.split("/")[-1]
        member = name.rsplit("_", 1)[1].replace(".grib2", "")
        variable = name.split("_{}00_".format(init))[0]
        counts[(variable, member)] = counts.get((variable, member), 0) + 1

    short = {}
    for variable, expected in EXPECTED_MESSAGES.items():
        for member in MEMBERS_WEEKLY:
            got = counts.get((variable, member), 0)
            if got != expected:
                short.setdefault(variable, {})[member] = got
    return short


def load_incomplete():
    """Dates already found unservable. Skipped without re-planning them."""
    if not os.path.exists(INCOMPLETE):
        return {}
    out = {}
    with open(INCOMPLETE) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                out[row["init"]] = row.get("shortfall", {})
            except (ValueError, KeyError):
                continue
    return out


def record_incomplete(init, short):
    """Record one unservable date. Never written to the manifest: `done` means
    the features exist, and for these dates they deliberately do not."""
    directory = os.path.dirname(INCOMPLETE)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    with open(INCOMPLETE, "a") as handle:
        handle.write(json.dumps({
            "init": init, "shortfall": short,
            "found": datetime.datetime.now().isoformat(timespec="seconds")}) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def wednesdays(start=ARCHIVE_START, end=ARCHIVE_END):
    """Every Wednesday init date in the archive, as YYYYMMDD strings."""
    day = start
    while day.weekday() != WEDNESDAY:
        day += datetime.timedelta(days=1)
    out = []
    while day <= end:
        out.append(day.strftime("%Y%m%d"))
        day += datetime.timedelta(days=7)
    return out


def load_manifest():
    """Init dates already completed. Missing manifest just means nothing done."""
    if not os.path.exists(MANIFEST):
        return set()
    done = set()
    with open(MANIFEST) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                done.add(json.loads(line)["init"])
            except (ValueError, KeyError):
                # A torn last line from a kill mid-write. Skip it; that date
                # simply gets redone, which is cheaper than guessing.
                continue
    return done


def record_done(init, n_messages, n_bytes, seconds):
    """
    Append one line per completed init date, and flush to disk immediately.

    Append-only and one-line-per-date so an interrupted run can never
    corrupt earlier entries.
    """
    directory = os.path.dirname(MANIFEST)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    row = {"init": init, "messages": n_messages, "bytes": n_bytes,
           "seconds": round(seconds, 1),
           "finished": datetime.datetime.now().isoformat(timespec="seconds")}
    with open(MANIFEST, "a") as handle:
        handle.write(json.dumps(row) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def plan_init_date(fs, init):
    """
    Work out every byte range we need for one init date.

    Both steps are batched on purpose: run serially this took 31.6 s per
    date, batched it takes about 5 s.
    """
    year = init[:4]
    base = "{}/{}/{}00".format(GEFS_ROOT, year, init)
    members = [m for m in MEMBERS_WEEKLY]

    with concurrent.futures.ThreadPoolExecutor(len(members)) as pool:
        listings = list(pool.map(
            lambda m: fs.ls("{}/{}/Days:1-10".format(base, m), detail=True),
            members))

    sizes = {}
    for listing in listings:
        for item in listing:
            if item.get("type") == "file":
                sizes[item["Key"]] = item["size"]

    selectors = ([(v, wanted_500mb) for v in VARS_500MB]
                 + [(v, wanted_850mb) for v in VARS_850MB]
                 + [(v, wanted_instant) for v in VARS_INSTANT]
                 + [(VAR_ACCUM, wanted_accum)])

    keys = []
    for member in members:
        for var, _ in selectors:
            keys.append("{}/{}/Days:1-10/{}_{}00_{}.grib2".format(
                base, member, var, init, member))

    idx_blobs = fs.cat([k + ".idx" for k in keys])

    paths, starts, ends = [], [], []
    i = 0
    for member in members:
        for var, keep in selectors:
            key = keys[i]
            i += 1
            for start, end, line in parse_idx(
                    idx_blobs[key + ".idx"].decode(), sizes[key]):
                if keep(line):
                    paths.append(key)
                    starts.append(start)
                    ends.append(end)
    return paths, starts, ends


def main():
    parser = argparse.ArgumentParser(description="VISHWAS data fetch.")
    parser.add_argument("--probe", action="store_true",
                        help="list bucket structure and exit")
    parser.add_argument("--years", type=int, default=None,
                        help="number of years back from 2019 to fetch")
    parser.add_argument("--limit", type=int, default=None,
                        help="stop after N init dates (for testing)")
    parser.add_argument("--dry-run", action="store_true",
                        help="show what would be fetched, transfer nothing")
    args = parser.parse_args()

    if not args.probe and args.years is None and args.limit is None:
        parser.print_help()
        sys.exit(1)

    fs = connect()

    if args.probe:
        probe(fs)
    else:
        fetch(fs, args.years, args.limit, args.dry_run)


if __name__ == "__main__":
    main()
