#!/usr/bin/env python3
"""VISHWAS — documentation consistency check.

Numbers live in a dozen markdown files and drift silently. A one-off grep gets
done once; this gets run forever.

    python scripts/check_docs.py          exits 0 if clean, 1 if anything found
    python scripts/check_docs.py --list   print the canonical table and exit

IT REPORTS. IT NEVER REWRITES. There is deliberately no --fix: silently
rewriting prose across a repo is how you lose a sentence you meant to keep.
A human reads the report and decides.

TO UPDATE IT, edit one of the three literal tables below — CANONICAL,
FORBIDDEN, EXEMPT. Nothing else in this file should need touching.

Canonical values as of 30 August 2026. They are what the scripts produced, and
they were re-derived from data/model_predictions.parquet and
models/vishwas_model.joblib during the P17 audit. If a script ever contradicts
one of these, that is a real finding: fix neither table until a human has looked.
"""

import argparse
import pathlib
import re
import sys

# ---------------------------------------------------------------------------
# TABLE 1 — CANONICAL VALUES.
#
# Each entry: the label, the correct value, and a list of WRONG spellings that
# should never appear. A wrong spelling is only reported when it sits on a line
# that also mentions the topic, so an unrelated "0.75" elsewhere stays quiet.
# `context` is a regex the line must ALSO match before a hit is reported.
# ---------------------------------------------------------------------------

CANONICAL = [
    # (label, correct, [wrong spellings], context regex or None)
    ("stratified ROC-AUC, model", "0.728", [], None),
    ("stratified ROC-AUC, baseline", "0.565", [], None),
    ("margin", "+0.1634, quote as +0.13 to +0.16", [], None),
    ("margin 95% CI", "+0.1080 to +0.1926", [], None),
    ("PR-AUC lift", "6.29x baseline / 7.60x model", [], None),
    ("rainfall bins", "EIGHT bins, bin 0 driest, bin 7 wettest", [], None),
    ("bin 7 bust rate", "40.92%", [], None),
    ("bin 0 bust rate", "0.15%", [], None),
    ("bin 0 size", "208,065 rows", [], None),
    ("spread ties", "spread = 0.00 on 189,758 test rows", [], None),
    ("zero forecast mean", "189,740 rows, a strict subset of the 189,758", [], None),
    ("feature count", "23", ["24 features", "~24 features", "24 columns"],
     r"feature|column|model sees|input"),
    ("labelled rows", "1,302,080", [], None),
    ("test rows", "651,040", [], None),
    ("train rows", "488,280 over 39 dates, 4.86%", [], None),
    ("validation rows", "162,760 over 13 dates, 5.43%", [], None),
    ("test bust rate", "6.47%", [], None),
    ("gridpoints", "1,252 of 5,041 = 24.8%", [], None),
    ("data fetched", "50.3 GB over 104 forecast dates, 2018-2019", [], None),
    ("season counts", "train and test BOTH DJF 13, MAM 13, JJAS 17, ON 9", [], None),
    ("Phase 1 pooled r", "+0.663", [], None),
    ("Phase 1 conditional r", "+0.041", [], None),
    ("Phase 1 variance", "43.9% pooled, 0.17-0.90% conditional", [], None),
    ("Phase 1 sample", "12 reforecasts, 4 seasons, 2012/2015/2018, 77,425 wet", [], None),
    ("ablations", "full 0.728 | no month 0.722 | no precip 0.731 | "
                  "no 850hPa 0.726 | spread only 0.562", [], None),
    ("calibration reliability", "0.00014 -> 0.00006 isotonic", [], None),
    ("calibration resolution", "0.01758 vs 0.01225", [], None),
    ("Brier skill score", "+0.303 vs +0.215; isotonic caps at 0.75", [], None),
    ("operational", "64% of busts caught vs 55%, matched alert budget", [], None),
    ("demo date", "init 20190731, Day 5, valid 5 Aug 2019", [], None),
    ("demo bust rate", "454/1,252 = 36.3%", [], None),
    # P28, 5 Sep: the constant is the quantile, 0.153471. It used to be
    # recorded here as "p >= 0.1535 (exact 0.153471)", which read as though
    # 0.1535 were the operating point and 0.153471 a footnote. It is the other
    # way round, and the rounding is what produced the 546/547 split.
    ("demo operating point", "0.1534712256035554 = the global 90th percentile "
                             "of test scores, fixed on the full test set and "
                             "pinned in src/confidence.py; quote in prose as "
                             "p >= 0.153, and use NO shortened form as a "
                             "constant (0.1535 gives 546, 0.153471 flips a "
                             "Day 4 cell); 547 flagged = "
                             "395 / 152 / 59 / 646; prec 0.72 rec 0.87",
     [], None),
    ("forecast decay", "GEFS detects 23% of heavy-rain events at Day 1, "
                       "0.2% at Day 10", [], None),
    ("GEFSv12 dataset paper", "Guan et al. (2022), Mon. Wea. Rev. 150(3), 647-665",
     [], None),
    ("theme", "Smart Automation", [], None),
]

# ---------------------------------------------------------------------------
# TABLE 2 — FORBIDDEN PATTERNS.
#
# (regex, why it is wrong, optional context regex the line must also match)
# Case-insensitive. Keep the regexes narrow: a pattern that fires on correct
# prose gets ignored, and an ignored checker is a dead checker.
# ---------------------------------------------------------------------------

FORBIDDEN = [
    (r"\bHamill\b",
     "Wrong paper for the GEFSv12 reforecast dataset. It is Guan et al. (2022), "
     "Mon. Wea. Rev. 150(3), 647-665, doi 10.1175/MWR-D-21-0245.1. Hamill is the "
     "12th of 18 authors; the Hamill BAMS reforecast paper is 2006 and a "
     "different dataset.",
     r"cite|citation|reference|et al|reforecast|GEFS"),

    (r"Bull\.\s*Amer|Bulletin of the American|\bBAMS\b",
     "Wrong journal for the GEFSv12 reforecast dataset paper. It is Monthly "
     "Weather Review 150(3).",
     r"cite|citation|reference|reforecast|GEFS|dataset paper"),

    (r"0\.34\s*[-–]\s*0\.37",
     "The 0.34-0.37 false-alarm ratio was REMOVED on 30 Aug: it could not be "
     "traced to a table. The IMD Monsoon Report 2024 may be cited for CONTAINING "
     "FAR/POD/threat-score verification, never as the source of this number.",
     None),

    (r"(wettest|driest|top|bottom)\s+(tenth|decile)",
     "The model's rainfall stratification is EIGHT BINS, not deciles. Bin 7 is "
     "the wettest, bin 0 the driest. (Deciles are correct for the Phase 1 "
     "conditional correlation only - a different analysis on a different sample.)",
     r"bust|0\.728|0\.565|40\.9|41%|0\.15%|model"),

    (r"fig5_confidence_map",
     "fig5_confidence_map.png was DELETED on 30 Aug - its caption carried a date "
     "that does not exist in the data. Superseded by fig6_confidence_map.png.",
     None),

    (r"\+0\.035",
     "Never quote a margin range containing +0.035. It came from a "
     "'forecast AND truth > X mm' filter, which conditions on the OUTCOME and "
     "deletes both classes of extreme bust. The honest range is +0.13 to +0.16.",
     None),

    (r"[Dd]isaster [Mm]anagement",
     "Smart Automation is the current theme and governs the submission. "
     "SIH re-listed SIH26079. Only acceptable when explicitly describing the "
     "re-listing as history.",
     None),

    # Note the word "exists": "No accuracy figure of any kind" is a RULE we
    # keep (never report accuracy at a ~6% base rate) and must not be flagged.
    # The stale claim is that no accuracy figure EXISTS.
    (r"there is no model yet|no trained model|no accuracy figure exists|"
     r"no ROC-AUC|\bnone exists\b|no accuracy figure — for the model",
     "The model was trained on 29 Aug: stratified ROC-AUC 0.728 vs 0.565. "
     "Ablations, calibration, SHAP and the confidence map are all complete.",
     None),

    (r"\bprovisional\b|pending the month|month ablation has not run|"
     r"not yet safe to put on a slide",
     "The month ablation RAN on 29 Aug and PASSED at -0.0059, far inside the "
     "0.02 tolerance fixed in advance. 0.728 is FINAL, not provisional.",
     r"0\.728|headline|result|model|ablation|slide"),

    (r"(calibration|SHAP|confidence map)[^.\n]{0,80}"
     r"(is next|are next|comes next|the next build|upcoming|not yet measured|"
     r"after the model|Early Sep)",
     "Calibration, SHAP and the confidence map were all DELIVERED on 30 Aug. "
     "Nothing about them is upcoming.",
     None),

    # THE POOLED PAIR IS Q&A-ONLY. Withdrawn from every figure and slide on
    # 30 Aug (P18); CLAUDE.md's sanctioned exception for fig4 is gone. It may
    # still be WRITTEN DOWN as the thing being ruled against - that is what the
    # ABSOLVING table is for - but a document that presents it as a result, or
    # asserts that a figure carries it, is wrong.
    (r"\b0\.909\b|\b0\.885\b",
     "The pooled pair 0.909 / 0.885 is Q&A-ONLY. It appears in no figure, no "
     "slide, no table and no spoken headline. Verified 30 Aug by opening "
     "fig4_inversion.png and by unzipping deck v17: it is nowhere in either. "
     "Quoting it as a measure of performance commits, in our own work, the "
     "exact error this project accuses the incumbent of. The result is the "
     "stratified pair, 0.565 vs 0.728.",
     None),

    (r"fig4[^.\n]{0,120}(0\.909|0\.885)|(0\.909|0\.885)[^.\n]{0,120}fig4",
     "fig4_inversion.png does NOT print the pooled pair, and src/11_inversion.py "
     "no longer renders it either (P18, 30 Aug). Any claim that the figure "
     "carries it is stale.",
     None),

    # THE OPERATING POINT IS 0.153471, NOT ITS FOUR-DECIMAL DISPLAY - P28,
    # 5 Sep. 0.1535 is a display rounding and was never the constant. Rounding
    # UP excludes one cell scoring 0.1534840, which is exactly where the
    # 546/547 discrepancy came from: the deck and CLAUDE.md said 547 (computed
    # at the quantile) while anything recomputing at 0.1535 got 546. Prose
    # should say "p >= 0.153"; the machine-readable form is
    # site/dashboard-data.json meta.threshold plus the per-cell stored verdict.
    # It appears legitimately nowhere as a constant, so the pattern is bare.
    # Lines that NAME the rounding to forbid it are absolved in the usual way.
    (r"\b0\.1535\b",
     "0.1535 is a DISPLAY ROUNDING of the operating point, never the constant. "
     "The threshold is the global 90th percentile of test scores, 0.153471, "
     "and that is what every published count was computed at (547 flagged on "
     "20190731 Day 5 = 395 hits + 152 false alarms). Rounding up drops one "
     "cell scoring 0.1534840 and yields 546. Quote prose as \"p >= 0.153\"; "
     "read site/dashboard-data.json meta.threshold, or a cell's stored "
     "verdict, for the machine-readable form.",
     None),

    (r"bulk (run|download)[^.\n]{0,60}(not started|not yet|after 31 Aug)",
     "The bulk run COMPLETED on 29 Aug: 104 forecast dates, 2018-2019, 50.3 GB.",
     None),

    # CREDIT ATTRIBUTION - P23, 31 Aug. Ankit did not build the fetch and
    # feature pipeline; Devansh did. The PRESENTED deck still carries the wrong
    # line and is left alone on purpose as the record of what was in the room
    # (deck/ is binary and this checker walks .md only, so it is never scanned).
    # The corrected roster line is:
    #   Devansh (data pipeline, model and evaluation) *
    #   Ankit (problem-statement tracking, option analysis)
    (r"Ankit[^.\n]{0,40}(data pipeline|feature pipeline)"
     r"|(data pipeline|feature pipeline)[^.\n]{0,40}Ankit",
     "Stale credit. Ankit did not build the data/feature pipeline - Devansh "
     "did. Ankit's contributions are problem-statement tracking (he caught the "
     "SIH re-listing from Disaster Management to Smart Automation, which "
     "changed the primary user, the framing and the tuning) and the option "
     "analysis against the secondary problem statement. Never replace a wrong "
     "credit with a bare name and no role.",
     None),

    (r"Ankit[^.\n]{0,40}fetch|fetch[^.\n]{0,40}Ankit",
     "Stale credit. The fetch pipeline (01_fetch.py) is Devansh's work, not "
     "Ankit's. See the TEAM ROLES AND CREDIT block in CLAUDE.md.",
     None),

    # TEAM ID GUARD - P24, 1 Sep. The ID is issued after team selection on
    # 3 Sep, so until then these rules FIRE ON PURPOSE and the run exits 1.
    # That is the guard working, not a bug. DO NOT DELETE THESE RULES TO GET
    # A GREEN RUN - the whole point is that a build still carrying the blank
    # cannot reach the 20 September submission unnoticed. After the ID is
    # pasted in, they go quiet on their own.
    (r"paste (the )?\*{0,2}Team ID",
     "Team ID placeholder. The ID is issued after team selection on 3 Sep; "
     "paste it into slide 1 and this goes quiet. Expected to fire before "
     "3 Sep - see the TEAM ID banner at the end of the run.",
     None),

    (r"Team ID\s*[–—-]\s*$",
     "The Team ID field is present but EMPTY. A blank ID field on slide 1 is "
     "how a placeholder reaches the submission unnoticed.",
     None),

    (r"Team ID[^\n]{0,40}(blank|placeholder)",
     "Team ID still recorded as blank or a placeholder. Issued 3 Sep; paste "
     "it into slide 1.",
     None),

    (r"catches X%|current method's Y%|X% of busts",
     "Placeholder left in place of the measured operational result: VISHWAS "
     "catches 64% of busts against the current method's 55% at a matched alert "
     "budget.",
     None),
]

# ---------------------------------------------------------------------------
# TABLE 3 — EXEMPT FILES.
#
# Findings in these files are printed under NOTED and do NOT fail the run.
# Nothing is hidden - they are reported in full, they just do not gate the
# exit code, because the whole point of these files is to quote stale text.
# ---------------------------------------------------------------------------

EXEMPT = {
    "VISHWAS-MASTER.md":
        "Pre-model snapshot. Carries an explicit SUPERSEDED banner and inline "
        "markers; the standing recommendation is to REGENERATE it from "
        "CLAUDE.md rather than patch it.",
    "docs/CLAUDE-CODE-PROMPTS.md": "Historical prompt archive (P1-P7, 26 Aug).",
    "docs/PROMPTS-PHASE2-MODEL.md": "Historical prompt archive (P8-P14, 27 Aug).",
    "docs/PROMPTS-PHASE3-DEMO.md": "Historical prompt archive (P12-P14, 29 Aug).",
    "docs/P11-ablations.md": "Historical prompt archive (P11, 29 Aug).",
    "docs/P16-wrapup.md":
        "Historical prompt archive. Quotes the stale-claim hunt list verbatim, "
        "so it necessarily contains the strings this script hunts.",
    "docs/CONSISTENCY-AUDIT.md":
        "The audit report itself. Quotes every stale claim in order to record "
        "what was fixed.",
    "docs/DECK-VERIFICATION.md":
        "Claim-by-claim verification log. Quotes rejected and corrected claims "
        "by design, each with its verdict beside it.",
    # The presented deck. Binary, so this checker (which walks *.md) never
    # reaches it; listed so the exemption already exists if the walk is ever
    # widened. It must keep its original slide-6 credit line as a historical
    # record - see TEAM ROLES AND CREDIT in CLAUDE.md.
    "deck/VISHWAS_SIH.pptx":
        "The deck as presented on 31 Aug 2026. A historical record; its "
        "slide-6 credit line is corrected in the NEXT build, not this one.",
    "deck/VISHWAS_SIH.pdf":
        "The deck as presented on 31 Aug 2026. A historical record; its "
        "slide-6 credit line is corrected in the NEXT build, not this one.",

    "CLAUDE.md":
        "The project constitution. States the rules by quoting the values they "
        "govern (e.g. the pooled pair, under DO NOT QUOTE).",
}

# ---------------------------------------------------------------------------
# TABLE 3b — SITE ASSERTIONS.
#
# Checked against site/index.html by counting OCCURRENCES with re.findall.
#
# Every number the page animates is wrapped in its own <span data-*-count>,
# so a pattern spanning a number and its surrounding prose will NOT match a
# correct build. Match the span attribute, or prose on one side of it —
# never across it. Two verification recipes have already failed this way.
#
# Count with re.findall, not grep -c: the bundle is one long line and line
# counting collapses three hits to one.
#
# The data-* counts are 2, not 1, and that is the correct value: each derived
# number needs BOTH halves — one <span data-x> in the markup to write into,
# and one querySelector('[data-x]') in the script to write it. If either half
# goes missing the count drops to 1 and this fires, which is exactly the
# failure worth catching (a span nothing fills, or a setter with no target).
#
# (pattern, expected_count, why)
# ---------------------------------------------------------------------------

# The Team ID rules, named so the run can explain itself. Until the ID is
# issued on 3 Sep these fire and the check exits 1 BY DESIGN; main() prints a
# banner saying so, precisely so nobody restores a green run by deleting them.
TEAM_ID_PATTERNS = {
    r"paste (the )?\*{0,2}Team ID",
    r"Team ID\s*[–—-]\s*$",
    r"Team ID[^\n]{0,40}(blank|placeholder)",
}

SITE_FILE = "site/index.html"

SITE_ASSERTIONS = [
    (r"p \u2265 0\.153", 3,
     "Alert threshold, consistent across all captions. The operating point is "
     "the global top-10% cut fitted once on the whole test set (p >= 0.1535), "
     "never re-fitted per date."),

    # The old rule pinned a comment explaining a six-cell artifact at three
    # decimals. That code was deliberately removed: colour now comes from the
    # stored verdict and aug5.json carries four-decimal p. Asserting ZERO
    # threshold constants pins the behaviour rather than prose about it, and
    # cannot be satisfied by a comment.
    (r"0\.1535", 0,
     "No threshold constant in the built pages."),

    (r"0\.153471(?!2)", 0,
     "No short-form threshold constant either."),

    (r"verdict column", 1,
     "Classification is upstream, not a p comparison."),

    (r"data-plotted-count", 2,
     "Plotted-point count is derived, not typed: one span, one querySelector. "
     "A stale hand-typed n is how the caption drifted from the plot before."),

    (r"data-total-count", 2,
     "Sample total is derived, not typed: one span, one querySelector. The "
     "rendered sentence must read '...computed on all 77,425'."),

    (r"data-alert-label", 2,
     "Flagged count derived from the outcome column: one span, one "
     "querySelector. The label is rebuilt as alerts + ' of ' + cells + "
     "' flagged', so the published 547 of 1,252 cannot drift."),
]

# ---------------------------------------------------------------------------
# TABLE 4 — ABSOLVING CONTEXT.
#
# A document that forbids a stale claim has to NAME it. "Never quote +0.035"
# and "fig5 was deleted" must not be reported as asserting +0.035 or as
# referencing fig5. A line matching any of these is treated as DISCUSSING the
# claim rather than MAKING it, and is suppressed.
#
# This is a heuristic and it is the one place this script can hide a real
# finding: a genuine stale assertion that happens to contain the word "not"
# would be missed. It is kept deliberately narrow - correction and prohibition
# vocabulary only - and the run prints how many lines it suppressed, so the
# suppression is never silent. If a finding seems to be missing, re-run with
# --no-absolve to see everything.
# ---------------------------------------------------------------------------

ABSOLVING = [
    r"\bnever\b", r"\bdo not\b", r"\bdon't\b", r"\bmust not\b", r"\bnot\b\s+\ba\b",
    r"\bcorrected\b", r"\bcorrection\b", r"\bpreviously (read|said|stated)\b",
    r"\bused to (read|say)\b", r"\bwas (deleted|removed|wrong|stale|rejected)\b",
    r"\bhas been deleted\b", r"\bdeleted\b", r"\bsuperseded\b", r"\bstale\b",
    r"\bremoved\b", r"\bno longer\b", r"\bwrong\b", r"\bfalse\b", r"\bexpired\b",
    r"\bre-?listed\b", r"\boriginally listed\b", r"\bolder notes\b",
    r"\bpassed\b", r"\bis final\b", r"\bnothing is provisional\b",
    r"~~", r"⛔", r"⚠️", r"\bRESOLVED\b", r"\bCLOSED\b", r"\bDELETED\b",
    r"\bhistorical\b", r"\bhunt\b", r"\bstale claim\b", r"\bforbidden\b",
    # The pooled pair is Q&A-only, so the contexts that may legitimately carry
    # it are: a rule forbidding it, an artefact/do-not-quote label, or a
    # question-and-answer note. Anything else asserting 0.909 / 0.885 fails.
    r"\bartefact\b", r"\bartifact\b", r"\bQ&A\b", r"\bdo not quote\b",
    r"\bdon't quote\b", r"\bnot the result\b", r"\bmisleading\b",
    r"\bpooled pair\b", r"\bwithdrawn\b", r"\bQ&A-only\b",
]

SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", "deck"}


def markdown_files(root):
    for path in sorted(root.rglob("*.md")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


ABSOLVING_RE = re.compile("|".join(ABSOLVING), re.IGNORECASE)


def absolved(lines, n):
    """True if line n (0-based) discusses a stale claim rather than asserting it.

    Looks at the neighbouring lines too: corrective framing routinely wraps
    ("...the deleted\\nfig5_confidence_map.png, whose caption..."), and judging
    a wrapped sentence by one line of it produces false alarms.
    """
    lo = max(0, n - 1)
    hi = min(len(lines), n + 2)
    return bool(ABSOLVING_RE.search("\n".join(lines[lo:hi])))


def scan(path, root, use_absolve=True):
    """Return (hits, n_suppressed).

    hits is a list of (line_no, line_text, rule_label, explanation).
    """
    hits = []
    suppressed = 0
    try:
        lines = path.read_text(encoding="utf-8").split("\n")
    except (OSError, UnicodeDecodeError) as exc:
        return [(0, "", "unreadable", str(exc))], 0

    for n, line in enumerate(lines, 1):
        forgiven = use_absolve and absolved(lines, n - 1)

        for pattern, why, context in FORBIDDEN:
            if not re.search(pattern, line, re.IGNORECASE):
                continue
            if context and not re.search(context, line, re.IGNORECASE):
                continue
            # The Team ID guard is NOT absolvable. ABSOLVING exists for
            # stale-CLAIM rules, where a document has to name the value it
            # forbids. A blank Team ID is a STATE, not a claim about a value,
            # so corrective vocabulary on a neighbouring line says nothing
            # about whether the field is still empty. Measured 1 Sep: without
            # this exemption, docs/DECK-BENCHMARK.md lines 118 and 158 were
            # both suppressed because nearby lines contained "passed" and
            # "~~" - i.e. the guard went quiet on two real placeholders.
            if forgiven and pattern not in TEAM_ID_PATTERNS:
                suppressed += 1
                continue
            hits.append((n, line.strip(), "forbidden: %s" % pattern, why))

        for label, correct, wrongs, context in CANONICAL:
            for wrong in wrongs:
                if not re.search(re.escape(wrong), line, re.IGNORECASE):
                    continue
                if context and not re.search(context, line, re.IGNORECASE):
                    continue
                if forgiven:
                    suppressed += 1
                    continue
                hits.append((n, line.strip(), "canonical: %s" % label,
                             'found "%s"; the canonical value is %s'
                             % (wrong, correct)))

    # One line can match two spellings of the same rule ("24 features" also
    # matches inside "~24 features"). Report each line/rule pair once.
    seen, unique = set(), []
    for hit in hits:
        key = (hit[0], hit[2])
        if key not in seen:
            seen.add(key)
            unique.append(hit)
    return unique, suppressed


def check_site(root):
    """Check site/index.html against SITE_ASSERTIONS.

    Returns (rows, problem). rows is a list of (pattern, expected, got, why);
    problem is None, "missing" or "unreadable".

    Counts OCCURRENCES with re.findall. Line counting (grep -c) is wrong here:
    the built page is one long bundle line, so three hits collapse to one.
    """
    path = root / SITE_FILE
    if not path.exists():
        return [], "missing"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return [], "unreadable"

    rows = [(pattern, expected, len(re.findall(pattern, text)), why)
            for pattern, expected, why in SITE_ASSERTIONS]

    # The Team ID guard applies to the built page too, not only the prose.
    # The site carries no Team ID today, so this is forward cover: if one is
    # ever added and left blank, it is caught here rather than at submission.
    for pattern in sorted(TEAM_ID_PATTERNS):
        got = len(re.findall(pattern, text, re.MULTILINE | re.IGNORECASE))
        if got:
            rows.append((pattern, 0, got,
                         "Team ID placeholder in the built site. Issued 3 Sep."))
    return rows, None


def main():
    ap = argparse.ArgumentParser(
        description="Report documentation drift against the canonical values. "
                    "Reports only; there is no --fix, by design.")
    ap.add_argument("--root", default=None,
                    help="repository root (default: the parent of scripts/)")
    ap.add_argument("--list", action="store_true",
                    help="print the canonical table and exit 0")
    ap.add_argument("--no-absolve", action="store_true",
                    help="do not suppress lines that merely DISCUSS a stale "
                         "claim; shows everything, including the corrective "
                         "prose. Use when checking what the heuristic hides.")
    args = ap.parse_args()

    root = pathlib.Path(args.root) if args.root \
        else pathlib.Path(__file__).resolve().parent.parent

    if args.list:
        print("CANONICAL VALUES — VISHWAS, as of 30 August 2026\n")
        for label, correct, _wrongs, _ctx in CANONICAL:
            print("  %-26s %s" % (label, correct))
        print("\n%d forbidden patterns, %d exempt files."
              % (len(FORBIDDEN), len(EXEMPT)))
        return 0

    failing, noted = {}, {}
    n_files = 0
    n_suppressed = 0
    for path in markdown_files(root):
        n_files += 1
        rel = path.relative_to(root).as_posix()
        hits, suppressed = scan(path, root, use_absolve=not args.no_absolve)
        n_suppressed += suppressed
        if not hits:
            continue
        (noted if rel in EXEMPT else failing)[rel] = hits

    print("VISHWAS documentation check — %d markdown files scanned" % n_files)
    if n_suppressed:
        print("%d line(s) suppressed as corrective prose "
              "(re-run with --no-absolve to see them)." % n_suppressed)
    print("=" * 72)

    if failing:
        print("\nFINDINGS — these fail the check\n")
        for rel in sorted(failing):
            print("  %s" % rel)
            for n, line, rule, why in failing[rel]:
                print("    line %-5d %s" % (n, rule))
                print("      | %s" % (line[:150] or "(blank)"))
                print("      -> %s" % why)
            print()

    if noted:
        print("\nNOTED — reported, but do not fail the check\n")
        for rel in sorted(noted):
            print("  %s" % rel)
            print("    exempt: %s" % EXEMPT[rel])
            for n, line, rule, _why in noted[rel]:
                print("    line %-5d %s" % (n, rule))
                print("      | %s" % (line[:150] or "(blank)"))
            print()

    # ---- site build -------------------------------------------------------
    site_rows, site_problem = check_site(root)
    site_bad = [r for r in site_rows if r[1] != r[2]]

    print("\nSITE BUILD — %s" % SITE_FILE)
    if site_problem == "missing":
        print("  NOT FOUND. Nothing to check; the site is committed, so this")
        print("  means it was deleted or moved.")
    elif site_problem == "unreadable":
        print("  UNREADABLE.")
    elif site_bad:
        print("  %d of %d assertions FAILED\n" % (len(site_bad), len(site_rows)))
        for pattern, expected, got, why in site_bad:
            print("    %-26s expected %d, found %d" % (pattern, expected, got))
            print("      -> %s" % why)
    else:
        print("  %d assertions pass." % len(site_rows))

    n_fail = sum(len(v) for v in failing.values())
    n_note = sum(len(v) for v in noted.values())
    print("=" * 72)
    print("%d finding(s) in %d file(s); %d noted in %d exempt file(s); "
          "%d site assertion(s) failed."
          % (n_fail, len(failing), n_note, len(noted), len(site_bad)))

    # Is every prose finding just the Team ID guard doing its job?
    team_hits = sum(
        1 for hits in failing.values() for _n, _l, rule, _w in hits
        if any(pat in rule for pat in TEAM_ID_PATTERNS))
    if team_hits:
        print("")
        print("-" * 72)
        print("TEAM ID GUARD FIRED — %d hit(s). THIS IS EXPECTED UNTIL 3 SEP." % team_hits)
        print("The ID is issued after team selection on 3 September 2026. Until")
        print("then this check exits 1 on purpose, so that a build still carrying")
        print("the blank cannot reach the 20 September submission unnoticed.")
        print("DO NOT delete the rule to get a green run. Paste the ID into")
        print("slide 1 and the guard goes quiet on its own.")
        print("-" * 72)

    if site_problem:
        print("\nFAIL — %s could not be checked (%s)." % (SITE_FILE, site_problem))
        print("It is a committed file, so this means it was deleted, moved or")
        print("corrupted. Restore it before pushing.")
        return 1

    if site_bad:
        print("\nFAIL — the site build does not match its assertions.")
        print("Every animated number is filled from a <span data-*-count> by a")
        print("querySelector, so a count of 1 where 2 is expected means one half")
        print("is gone: a span nothing fills, or a setter with no target.")
        return 1

    if n_fail:
        print("\nFAIL. Fix the prose, never the data. If a script contradicts a")
        print("canonical value, STOP and report it — that is a real finding,")
        print("not a documentation bug.")
        return 1

    print("\nCLEAN.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
