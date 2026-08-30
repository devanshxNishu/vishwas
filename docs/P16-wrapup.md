
> ⛔ **HISTORICAL PROMPT ARCHIVE — not a statement of current state.**
> The P16 prompt as issued, including its own canonical list and stale-claim hunt list. Its Task 4 was completed on 30 Aug as P17.
> All of this work is complete. For what is true now, read `CLAUDE.md` or
> `docs/DECK-TECHNICAL-PACK.md`. Forward-looking wording below ("next",
> "not yet", "no model exists") described the repository on the date this
> file was written and is preserved deliberately. Banner added 30 Aug 2026
> by the consistency audit (`docs/CONSISTENCY-AUDIT.md`).

## P16 — Finish P14, then make every document tell the same story

```
Read CLAUDE.md first.

Phase 3 is essentially complete: model trained and validated, ablations done,
confidence map built, SHAP done, calibration done, model persisted. The internal
PPT is Monday 31 Aug. This prompt closes the last loose end and then does the
boring job that actually protects you in Q&A — making sure no document contains
a number that contradicts another.

TASK 1 — FINISH OR KILL src/08_met_metrics.py. TIME-BOXED TO 30 MINUTES.

That file is 486 lines that have never been executed once. A script that looks
finished and is not is worse than no script, so this ends one way or the other
today.

RUN IT. src/met_metrics.py underneath it is already written and its self-test
passes — import it, do not rewrite it. What the output must contain:
  - EVENT = BUST, never rain. H = flagged and it busted. M = busted, missed.
    FA = flagged, forecast was fine.
  - OPERATING POINT chosen on the VALIDATION slice (13 held-out 2018 dates),
    NEVER on test. Primary: flag the top 10% by predicted probability. Print
    the threshold and the achieved alert rate every time.
  - THE HEAD-TO-HEAD AT A MATCHED ALERT BUDGET. Model vs ensemble spread, both
    flagging exactly 10%. Report POD, FAR, CSI, ETS side by side, and sweep the
    rate at 5%, 10%, 20%.
    The deliverable is this sentence with real numbers in it:
      "Given the same number of alerts a forecaster would tolerate, VISHWAS
       catches X% of busts against the current method's Y%."
  - One caution specific to this comparison: ensemble spread is 0.00 mm on
    189,758 test rows — a third of the set is one enormous tie. Say how you
    broke it (random within-tie order is the honest choice; anything else
    quietly advantages or handicaps the baseline) and report how many flagged
    cases came out of the tied block.
  - Stratify within rainfall bins as well as pooled.
  - Weight precision over recall when choosing the operating point, and say
    why: Smart Automation theme, an assistant that cries wolf gets switched off.
  - ETS IS computable from the four counts: H_rand = (H+FA)(H+M)/N. Paras's
    guide says otherwise and is wrong on that point.

IF IT CANNOT BE MADE TO RUN CORRECTLY IN 30 MINUTES, DELETE IT and say so.
Do not leave it sitting in src/ half-alive.

TASK 2 — CHECK figures/fig4_inversion.png.
Nobody has described this file. Open it. Report what it shows, whether its
numbers match the canonical list below, and whether it is deck-worthy. If it
visualises the +0.023 crude vs +0.163 fair inversion it may be the second-best
image in the set; if it is stale or wrong, delete it like fig5.

TASK 3 — WRITE PHASE 3 INTO CLAUDE.md.
You offered and it has not been done. Add, concisely: the calibration result,
the driest-bin SHAP cases, the demo-date choice and its method, and the model
artifact path. CLAUDE.md is the constitution — a future session must not have
to reconstruct tonight from chat logs.

TASK 4 — DOCUMENTATION CONSISTENCY AUDIT. This is the one that protects you.

Numbers now live in CLAUDE.md, README.md, data/VISHWAS-HANDOFF.md,
VISHWAS-MASTER.md, docs/DECK-TECHNICAL-PACK.md, docs/DECK-BRIEF.md,
docs/TECHNICAL-REFERENCE.md, docs/PROMPTS-PHASE*.md and whatever the deck
session has written. Several predate the model. Grep every one of them against
this canonical list and fix or flag every disagreement.

CANONICAL VALUES — anything conflicting with these is wrong:

  Phase 1 (baseline measurement)
    spread-error correlation      pooled +0.663, conditional +0.041
    variance explained            43.9% pooled, 0.17-0.90% conditional
    quote as                      "under 1% however you slice it"

  Data
    104 forecast dates, 2018-2019, 50.3 GB fetched
    1,302,080 labelled rows, 1,252 gauge-observed land gridpoints
    train 39 dates / 488,280 rows / 4.86%   (13 more held as validation)
    validation 13 dates / 162,760 rows / 5.43%
    test 52 dates / 651,040 rows / 6.47%
    train and test BOTH: DJF 13, MAM 13, JJAS 17, ON 9

  Model (FINAL, not provisional)
    ROC-AUC pooled       baseline 0.885   model 0.909   <- never quote
    ROC-AUC stratified   baseline 0.565   model 0.728   <- the result
    margin +0.1634, 95% CI +0.1080 to +0.1926
    QUOTE THE MARGIN AS +0.13 TO +0.16, never +0.163 alone
    ahead in all 8 rainfall bins, +0.079 to +0.252
    PR-AUC lift 6.29x baseline / 7.60x model

  Ablations
    full 0.728 | no month 0.722 | no precip 0.731 | no 850hPa 0.726
    spread only 0.562 (baseline as a ranking: 0.565)

  Calibration
    reliability 0.00014 -> 0.00006 (isotonic), resolution 0.01758 vs 0.01225
    Brier skill score +0.303 vs +0.215, isotonic caps output at 0.75

  Demo date
    init 20190731, Day 5, valid 5 Aug 2019, 454/1252 busted (36.3%)
    threshold p >= 0.1535 fixed on the full test set, precision 0.72, recall 0.87

  Driest bin
    208,065 rows, base rate 0.15%, spread = 0.00 on 189,758 rows

STALE CLAIMS TO HUNT AND KILL — these appear in older documents:
  - "there is no model yet" / "no accuracy figure exists" / "none exists"
  - the model number described as PROVISIONAL or pending the month ablation
  - any reference to fig5_confidence_map.png (deleted)
  - any margin range quoting +0.035 (from the truth-filtered rows, which
    condition on the outcome and are not a fair robustness check for AUC)
  - "Disaster Management" as the current theme (it is Smart Automation now)
  - any claim that calibration, SHAP or the confidence map are "next"

REPORT: a table of file, line, stale claim, and what you changed it to. If a
document is so out of date that patching is worse than regenerating, say so
rather than leaving a half-corrected file.

CONSTRAINT: do not change any NUMBER to make documents agree. If two documents
disagree, the value computed by the scripts wins, and the canonical list above
is what the scripts produced. Fix the prose, never the data.
```
