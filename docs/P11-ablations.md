
> ⛔ **HISTORICAL PROMPT ARCHIVE — not a statement of current state.**
> The P11 ablation prompt as issued. It ran on 29 Aug and month PASSED at -0.0059.
> All of this work is complete. For what is true now, read `CLAUDE.md` or
> `docs/DECK-TECHNICAL-PACK.md`. Forward-looking wording below ("next",
> "not yet", "no model exists") described the repository on the date this
> file was written and is preserved deliberately. Banner added 30 Aug 2026
> by the consistency audit (`docs/CONSISTENCY-AUDIT.md`).

## P11 — Ablations: is the model learning weather, or the calendar?

```
Read CLAUDE.md first — the "FIRST TRAINED MODEL" section at the top records
tonight's result and the two things still open.

CONTEXT. The model is trained and beats ensemble spread: stratified ROC-AUC
0.728 vs 0.565, margin +0.1634, 95% CI +0.1080 to +0.1926, ahead in all 8
rainfall bins. Nothing was tuned. That result is NOT yet safe to put on a slide,
for one reason, and this prompt exists to settle it.

THE PROBLEM. Bust thresholds are fitted per (region, lead_day) and NOT per
season. Monsoon days therefore carry systematically more busts than winter days
— the test window showed 6.47% overall, but the rehearsal's Jan-Mar slice ran at
1.47%. `month` is a model feature. So `month` can predict busts simply by
identifying the season, which is climatology, not meteorology — the exact
species of artefact this project exists to expose in ensemble spread. If our own
headline rests on it, we have made the incumbent's mistake in our own work.

TASK 1 — ADD A --drop FLAG (small change, unblocks everything below).
src/07_model.py has --with-location but no general way to exclude features. Add:

    --drop month
    --drop precip_mean,precip_spread

a comma-separated list removed from the feature set before fitting. Print the
final feature list every run so the ablation is self-documenting. Do not change
anything else about the script.

TASK 2 — RUN THE ABLATIONS. Same split, same labels, same stratified metric,
same seed. Only the feature set varies.

  a. FULL                     baseline for comparison (expect ~0.728)
  b. --drop month             *** THE DECISIVE TEST ***
  c. --drop precip_mean,precip_spread
                              can it predict busts at all without knowing how
                              hard it is forecast to rain?
  d. --drop shear_500_850,u850_mean,v850_mean
                              did P2's +60% transfer cost buy anything? This
                              has a budget attached: if it bought nothing, the
                              5-year run should skip 850 hPa and save ~46 GB.
  e. SPREAD ONLY              --drop everything except precip_spread. Isolates
                              how much of our edge is a better functional form
                              versus genuinely more information.

Use --bootstrap 500 for these; the CI is already established at 2000 and you
only need each variant's point estimate plus a rough interval. The bootstrap was
optimised earlier today to subset columns before resampling, so it should be
markedly faster than the 14m50s the first run took.

TASK 3 — PERMUTATION IMPORTANCE on the TEST set (not training importance, which
is biased toward high-cardinality features). Report the top 10.

REPORT
  1. One table: variant, stratified AUC, margin over the 0.565 baseline, and the
     change from FULL.
  2. A plain-English paragraph on what the model is actually keying on.
  3. An explicit verdict on `month`, in one of these three forms:
       - drops < 0.02  -> month is incidental; the result stands as published.
       - drops 0.02-0.08 -> month carries some seasonal climatology. Report the
         WITHOUT-month figure as the headline; it is the defensible one.
       - drops > 0.08  -> the model is substantially learning the calendar. Say
         so plainly, make the without-month number the result, and add a line to
         CLAUDE.md and docs/DECK-BRIEF.md recording it.
  4. A recommendation on 850 hPa for the 5-year run, with the GB saved.

CONSTRAINTS
  - Do NOT tune, and do NOT re-pick bins, percentiles or wet-point definitions.
    The comparison is only meaningful because everything except the feature set
    is held fixed.
  - The verdict thresholds above are fixed BEFORE you see results. Do not move
    them afterwards.
  - Never report plain accuracy.
  - If an ablation IMPROVES the model, that is a real finding — report it, do
    not quietly adopt it as the new headline without saying what changed.
  - Ignore any "forecast AND truth > X mm" row in the robustness panel when
    quoting a range. Those condition on the outcome and delete both classes of
    extreme bust. The panel now labels them [truth-filtered] and excludes them
    from the verdict range. The honest range is +0.13 to +0.16.
```

### After P11, if `month` holds up

The number is then safe for the deck, and the remaining order is P12 calibration
(what makes it a *confidence* product rather than a score), P14 metrics at a
matched alert budget (the presentable "same alert budget, we catch X% against
their Y%"), then P13 SHAP and the confidence map for the demo.
