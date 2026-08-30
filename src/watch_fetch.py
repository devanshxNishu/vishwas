"""
Live progress monitor for the 02_features.py bulk fetch.

Reads data/raw/manifest.jsonl and redraws a progress block in place. Standard
library only, so it runs on the project venv, the system python, or anything
else — no numpy, no pandas.

    python src/watch_fetch.py                  # 2018-2019 run, refresh every 10 s
    python src/watch_fetch.py --interval 30
    python src/watch_fetch.py --years 2018 2019 2020 2021 2022 --total 260

Ctrl-C to stop. This only READS the manifest, so it can never disturb the run.

A NOTE ON THE CLOCK, because it will bite you otherwise.
02_features.py stamps `finished` with datetime.datetime.now() and no timezone,
so the manifest carries the MACHINE'S LOCAL time. Computing an ETA from a shell
running UTC puts every figure 5h30m out. This script reads the timestamps as
naive local time and compares them against local now(), which is correct as
long as it runs on the same machine that wrote them.
"""

import argparse
import datetime
import json
import os
import sys
import time

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MANIFEST = os.path.join(_PROJECT_ROOT, "data", "raw", "manifest.jsonl")

# Speed over the whole run hides a link that is degrading right now, so the
# "recent" figure is what tells you whether to keep waiting.
RECENT_DATES = 5


def read_manifest(path, years):
    """Completed entries for the years under study, oldest first."""
    if not os.path.exists(path):
        return []
    rows = []
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue  # torn last line from a kill mid-write
            if row.get("init", "")[:4] in years:
                rows.append(row)
    rows.sort(key=lambda r: r.get("finished", ""))
    return rows


def bar(done, total, width=34):
    filled = int(round(width * done / total)) if total else 0
    return "[" + "#" * filled + "." * (width - filled) + "]"


def human(seconds):
    if seconds != seconds or seconds < 0:
        return "--"
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return "{}h {:02d}m".format(hours, minutes)
    return "{}m {:02d}s".format(minutes, secs)


def render(rows, total, manifest):
    now = datetime.datetime.now()
    done = len(rows)
    left = total - done

    lines = []
    lines.append("VISHWAS bulk fetch — live")
    lines.append("=" * 58)

    if not done:
        lines.append("no completed dates yet in {}".format(manifest))
        lines.append("(the first date takes ~2 min before it appears)")
        return "\n".join(lines)

    gb = sum(r["bytes"] for r in rows) / 1e9
    first = datetime.datetime.fromisoformat(rows[0]["finished"])
    last = datetime.datetime.fromisoformat(rows[-1]["finished"])
    span = (last - first).total_seconds()

    # Pace measured wall-clock between completions, which includes the
    # per-date overhead the fetch timings alone leave out.
    pace = span / (done - 1) if done > 1 else rows[0]["seconds"]
    recent = rows[-RECENT_DATES:]
    if len(recent) > 1:
        r_span = (datetime.datetime.fromisoformat(recent[-1]["finished"])
                  - datetime.datetime.fromisoformat(recent[0]["finished"])).total_seconds()
        r_pace = r_span / (len(recent) - 1)
        r_bytes = sum(r["bytes"] for r in recent[1:])
        r_speed = r_bytes / r_span / 1e6 if r_span else float("nan")
    else:
        r_pace, r_speed = pace, float("nan")

    avg_speed = sum(r["bytes"] for r in rows) / sum(r["seconds"] for r in rows) / 1e6
    stale = (now - last).total_seconds()

    lines.append("{} {}/{}  ({:.0f}%)".format(
        bar(done, total), done, total, 100.0 * done / total))
    lines.append("")
    lines.append("  downloaded    {:.1f} GB   of ~{:.0f} GB".format(
        gb, gb / done * total))
    lines.append("  speed  now    {:.2f} MB/s   (last {} dates)".format(
        r_speed, len(recent)))
    lines.append("  speed  avg    {:.2f} MB/s   over the whole run".format(avg_speed))
    lines.append("  pace   now    {:.1f} min/date   (avg {:.1f})".format(
        r_pace / 60, pace / 60))
    lines.append("")

    if left <= 0:
        lines.append("  COMPLETE — all {} dates fetched.".format(total))
        lines.append("  finished at {}".format(last.strftime("%H:%M:%S")))
        return "\n".join(lines)

    eta = left * r_pace
    finish = now + datetime.timedelta(seconds=eta)
    lines.append("  remaining     {} dates".format(left))
    lines.append("  time left     {}   (at the current pace)".format(human(eta)))
    lines.append("  finishes      {}{}".format(
        finish.strftime("%H:%M"),
        "" if finish.date() == now.date() else finish.strftime(" on %d %b")))
    lines.append("")

    # A run that has died leaves a manifest that simply stops growing, which
    # looks exactly like a slow date until you notice the clock.
    if stale > max(4 * pace, 600):
        lines.append("  !! no new date for {} — expected one every {:.1f} min.".format(
            human(stale), pace / 60))
        lines.append("     Check the fetch process is still alive.")
    else:
        lines.append("  last date     {} ({} ago)".format(
            last.strftime("%H:%M:%S"), human(stale)))

    lines.append("")
    lines.append("  {}   Ctrl-C to stop watching".format(now.strftime("%H:%M:%S")))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Live view of the bulk fetch.")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--years", nargs="+", default=["2018", "2019"],
                        help="init years belonging to this run")
    parser.add_argument("--total", type=int, default=104,
                        help="dates expected in this run")
    parser.add_argument("--interval", type=float, default=10.0)
    parser.add_argument("--once", action="store_true",
                        help="print one snapshot and exit")
    args = parser.parse_args()

    years = set(args.years)
    try:
        while True:
            frame = render(read_manifest(args.manifest, years),
                           args.total, args.manifest)
            if args.once:
                print(frame)
                return
            sys.stdout.write("\033[2J\033[H" + frame + "\n")
            sys.stdout.flush()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nstopped watching. The fetch is unaffected.")


if __name__ == "__main__":
    main()
