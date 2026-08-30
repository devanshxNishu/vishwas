# VISHWAS — documentation consistency audit

**Run 30 August 2026 (P17), extended the same day (P18).** This is P16 Task 4, which had not previously run:
there is no P16 Task 4 commit in the history and no earlier audit report existed.

**Scope:** every `.md` file in the repository — 16 files, 4,893 lines — audited
against the canonical values below.

**No number was changed.** Every edit below is prose. Where a document
disagreed with the scripts, the scripts won.

**Re-run the check:**

```bash
python scripts/check_docs.py            # exits 0 clean, 1 if anything found
python scripts/check_docs.py --list     # print the canonical table
python scripts/check_docs.py --no-absolve   # show suppressed corrective prose
```

It exits **0** as of this audit.

---

## 0. First: the canonical values were re-derived, not assumed

Before auditing prose against the canonical list, the list itself was checked
against the artifacts. Every value reproduced exactly:

| Canonical claim | Re-derived from | Result |
|---|---|---|
| 23 features | `models/vishwas_model.joblib` → `features` | **23** ✅ |
| 1,302,080 labelled rows, 104 dates | `data/labelled.parquet` | ✅ |
| 651,040 test rows, 52 dates, 6.47% | `data/model_predictions.parquet` | ✅ |
| 488,280 train rows, 4.86% | artifact `config` | ✅ |
| 1,252 gridpoints | predictions, grouped by (lat, lon) | ✅ |
| EIGHT rainfall bins | `qcut(precip_mean, 10, duplicates="drop")` | **8 realised** ✅ |
| bin 0 = 208,065 rows @ 0.15% | recomputed | ✅ |
| bin 7 @ 40.92% | recomputed | ✅ |
| spread = 0.00 on 189,758 rows | recomputed | ✅ |
| forecast mean = 0 on 189,740, strict subset | recomputed | **subset confirmed** ✅ |
| demo 20190731 D5: 454/1,252 = 36.3% | recomputed | ✅ |
| demo panel 395 / 152 / 59 / 646, prec 0.72 rec 0.87 | recomputed | ✅ (see note) |

**Note on the demo threshold.** The published operating point `p >= 0.1535` is
the *rounded display* of the exact top-10% test quantile, **0.153471**. At the
exact value the panel is 547 flags / 395 hits / 152 FA / 59 misses / 646 correct
negatives — the canonical figures. At the rounded 0.1535 one row falls out and
it becomes 546 / 395 / 151 / 59 / 647. **The canonical numbers are correct**;
anyone reproducing them must use the quantile, not the printed constant. No
change made — this is a display-precision footnote, not an error.

**Why eight bins and not ten.** `STRATIFY_BINS = 10` in `src/07_model.py`, but
~32% of test rows have a forecast of exactly 0.00 mm, so three quantile edges
coincide and `duplicates="drop"` removes them. The realised count is **8**. The
code already anticipates this (`07_model.py` comments on it) and reports the
real bin count at runtime. This reconciles "eight bins" with a decile-based
`qcut`, and it is why "decile"/"wettest tenth" is wrong for the *model* result
while remaining correct for the *Phase 1* conditional correlation.

---

## 1. Changes made

| File | Line(s) | Stale claim | Changed to |
|---|---|---|---|
| `docs/DECK-BRIEF.md` | 5 | "internal college PPT 31 Aug (2 days)" | "(tomorrow)", plus an audit banner pointing to the pack as the current numbers document |
| `docs/DECK-BRIEF.md` | 17 | "1.30 million labelled gridpoint-days" attached to the *test* result | "**651,040 test rows**, drawn from a labelled table of 1,302,080" + a warning not to conflate them |
| `docs/DECK-BRIEF.md` | 48–51 | **"The `month` ablation has not run… Do not print a final figure until that test has run."** | "**RESOLVED 29 Aug — it ran and it passed**", −0.0059 against a 0.02 tolerance. "0.728 is final; print it." |
| `docs/DECK-BRIEF.md` | §6 | Asset list named **three** figures | All **eight** current figures, plus an explicit note that `fig5` was deleted |
| `docs/DECK-BRIEF.md` | §7 | "The model is being trained now" | "it works, and it is measured" — 0.728 vs 0.565, with the pre-registered decision rule restated |
| `docs/DECK-BENCHMARK.md` | 39 | **"Hamill et al."** as the GEFSv12 reforecast dataset paper | **Guan et al. (2022), Mon. Wea. Rev. 150(3), 647–665**, doi 10.1175/MWR-D-21-0245.1, with a note that Hamill is the 12th of 18 authors and that the Hamill *BAMS* paper is 2006 and a different dataset |
| `docs/DECK-BENCHMARK.md` | 119 | Ranked fix "Run the `month` ablation — decides whether 0.728 stands" | Struck through; done 29 Aug and passed |
| `docs/DECK-BENCHMARK.md` | 58–62 | Competitor matrix "would be dishonest until the model has been scored" | Every row of it is now measured; only the six-slide limit still argues against it |
| `docs/DECK-BENCHMARK.md` | 127 | "Not recommended… Honest only once calibration and explainability are scored" | Both are scored; the remaining objection is slide count alone |
| `docs/DECK-VERIFICATION.md` | 43 | "**24** features" marked OK — and contradicted by this file's own line 225 | "**23**", sourced to the model artifact, with the 24-non-key-columns / 23-model-inputs distinction spelled out |
| `docs/DECK-VERIFICATION.md` | 154 | **"0.34–0.37 multi-model false-alarm ratio — IMD Monsoon Report 2024" marked OK** | **REMOVED.** Untraceable to any table. The report may be cited for *containing* FAR/POD verification, never as the source of this number |
| `docs/DECK-VERIFICATION.md` | 193 | "Any accuracy figure — **No model exists yet**" | The reason was always the ~6% base rate, not the absence of a model |
| `docs/DECK-VERIFICATION.md` | 200 | "Calibration, SHAP, the confidence map — **Not yet measured.** Slide 3 says they are the next build step" | All three delivered 30 Aug; the slide-3 wording must come off |
| `docs/DECK-VERIFICATION.md` | 198 | "the regenerated `fig4_inversion.png` **does print** the pooled pair in its provenance footnote" | **Corrected — it does not.** See flag F1 below |
| `docs/DECK-TECHNICAL-PACK.md` | 291 | "41% bust rate in the **wettest tenth**" | "the wettest of the eight rainfall bins" |
| `docs/DECK-TECHNICAL-PACK.md` | §4 | (addition) | Added the why-eight-not-ten explanation next to "all 8 rainfall bins", so the qcut(10)→8 question has a written answer |
| `docs/TECHNICAL-REFERENCE.md` | 3 | "verified as of 29 Aug 17:52" | 30 Aug, pointing at this audit |
| `docs/TECHNICAL-REFERENCE.md` | 24 | "**~24** features" as the model input | "**23**" |
| `docs/TECHNICAL-REFERENCE.md` | §4 | "**24 columns**, all derived from GEFS" | "**23 features**", with a note that the table has 24 non-key columns and `season` is built but never fed to the model |
| `docs/TECHNICAL-REFERENCE.md` | §4 table | `month`, `season` listed together as features; `lead_day` missing | `season` marked explicitly as *not* a model input; `lead_day` added |
| `docs/TECHNICAL-REFERENCE.md` | 246 | "24 features verified physically sane" | 24 non-key columns built, **23 fed to the model** |
| `docs/TECHNICAL-REFERENCE.md` | §6 | **"the one to put on a slide once the model exists"** and the placeholder **"catches X% of busts against the current method's Y%"** | The measured result: **64% against 55%**, with the full POD/FAR/CSI/ETS row at the matched 10% budget |
| `docs/TECHNICAL-REFERENCE.md` | §9 | Milestones listed "28 Aug First trained model" and "**Early Sep** — Calibration, SHAP, meteorological metrics" | Moved to Delivered: 29 Aug (bulk run, model, ablations) and 30 Aug (calibration, SHAP, map, operational metrics) |
| `docs/TECHNICAL-REFERENCE.md` | §10 | "the pooled one that would look **four times better**" — not traceable to any measurement | Replaced with the real answer, including the drop-rainfall ablation (0.728 → 0.731) |
| `docs/TECHNICAL-REFERENCE.md` | §11 | Glossary: "If the system says '20% chance of a bust', it should be **wrong** about one time in five" — **inverted** | "a bust should actually **follow** about one time in five" |
| `data/VISHWAS-HANDOFF.md` | header | "State of the project as of 27 August" | 30 August, listing which sections changed |
| `data/VISHWAS-HANDOFF.md` | §2 | "31 Aug — **4 days away**"; "The model does not need to be finished" | "tomorrow"; the model *is* finished |
| `data/VISHWAS-HANDOFF.md` | §4 | **"Bulk run — Not started, deliberately."** | ✅ Complete 29 Aug — 104 dates, 50.3 GB. New-code list extended from 5 scripts to 13 |
| `data/VISHWAS-HANDOFF.md` | §4a | (new section) | The model result, the margin and its CI, the eight bins, and the 64%/55% operational line — this team-facing file previously carried no model numbers at all |
| `data/VISHWAS-HANDOFF.md` | §6 | "Bulk transfer ~122 GB / ~7.6 h — run it after 31 Aug" | Closed; the 2-year run finished at 50.3 GB. Added the one-test-year risk |
| `data/VISHWAS-HANDOFF.md` | §7 | **"after 31 Aug, not before: 1. Bulk run. 2. Train the bust classifier."** | Rewritten as the five real pre-PPT deck fixes, then the post-31-Aug technical items |
| `README.md` | Layout | `src/` listed 7 scripts of 17; `docs/` listed 1 file of 12; no `figures/`, `ablations/`, `scripts/` | Full current layout |
| `README.md` | Status | Operational metrics missing | Added, plus the eight-bin range and the 64%/55% line |
| `VISHWAS-MASTER.md` | 104–105 | Status rows "Trained model ⬜ none yet", "Calibration, SHAP ⬜ next" | Inline ⛔ marker under the table (see §3 — this file is not patched line by line) |
| `VISHWAS-MASTER.md` | 492 | Heading "**Read this first: there is no model yet**" | Heading struck through + ⛔ DO NOT QUOTE block carrying the real result |
| `docs/CLAUDE-CODE-PROMPTS.md`, `PROMPTS-PHASE2-MODEL.md`, `PROMPTS-PHASE3-DEMO.md`, `P11-ablations.md`, `P16-wrapup.md` | top | Forward-looking prompt text readable as current state ("there is currently no label, no model, and no accuracy number of any kind") | ⛔ **HISTORICAL PROMPT ARCHIVE** banner on each, dated, pointing at `CLAUDE.md`. Body text preserved deliberately — an archive that has been edited is no longer an archive |

### P18 changes, 30 August

| File | Stale claim / gap | Changed to |
|---|---|---|
| `deck/` | **Two presentable decks side by side** — v17 and the 29 Aug v1 | v1 pair moved to `deck/archive/` with a README naming the live deck. See F5 |
| `docs/DECK-VERIFICATION.md` | §"TWO STALE IMAGES" described the shipping deck as carrying fig5 and the old fig4 | Marked **RESOLVED** — deck v17 verified by hashing its media |
| `docs/DECK-TECHNICAL-PACK.md` | §0 "THREE FIXES NEEDED IN THE EXISTING DECK" | Marked **ALL THREE DONE**, verified the same way |
| `docs/DECK-TECHNICAL-PACK.md` | §7 still granted fig4 the "one sanctioned exception" to print the pooled pair | Exception **withdrawn**; the pair is Q&A-only |
| `docs/DECK-TECHNICAL-PACK.md` | §4 results table printed `ROC-AUC, pooled 0.885 / 0.909` | Row removed; the crude **margin +0.023** carries the inversion story |
| `docs/DECK-BRIEF.md` | §1 results table printed the same pooled row, and prose quoted "0.885 for free" | Row removed; prose reworded without the number |
| `data/VISHWAS-HANDOFF.md` | §7 listed the three deck fixes as outstanding | All three done in v17; two items remain (Team ID, PS title) |
| `CLAUDE.md` | Sanctioned exception permitting the pooled pair inside fig4 | **Withdrawn.** This was the root cause: a rule permitting what the project had decided against would be restored by the next session, correctly |
| `CLAUDE.md` | Bin-weighting Q&A answer existed only in `ablations/a_full.log` | Recorded in full, with the "drop the driest bin" numbers and the instruction not to concede the premise |
| `CLAUDE.md` | No record that figures had no generators | **ONE GENERATOR PER FIGURE** section added, mapping every figure to its script |
| `src/11_inversion.py` | Rendered a footnote that printed the pooled pair, and did not match the shipped PNG | Renders the shipped footnote; **+0.1322** and the train counts now computed, not pasted |
| `src/11_inversion.py` | Footnote said the margin range spans **"five wet-point definitions"** | **Two.** Three of the five are truth-filtered and excluded from the verdict range. Found by reading the PNG — see the note on `check_docs.py` limits |
| `src/12_fig1_collapse.py` | `fig1_collapse.png` had **no generator at all** | Written. Reproduces 43.9% and 0.17–0.90% from the sample |
| `src/13_fig2_deciles.py` | `fig2_deciles.png` had **no generator** | Written. Reproduces +0.663, +0.041 and the −0.474 driest decile |
| `src/14_fig3_map.py` | `fig3_map.png` had **no generator** | Written. Reproduces 1,252 of 5,041 = 24.8% |
| `src/figstyle.py` | Palette duplicated per script | Shared palette and layout helpers |
| `scripts/check_docs.py` | `0.909` / `0.885` were not forbidden | Added, with ABSOLVING vocabulary for the contexts that may legitimately name them. Immediately caught four documents |
| `README.md` | fig1's subtitle wording | Regenerated figure uses the precise **"43.9% of the variance in forecast error"**, matching the deck card |

**Not changed:** `docs/SIH-COMPLIANCE.md` (no numeric or state claims; clean), `data/README.md`
(clean), `docs/DECK-TECHNICAL-PACK.md` beyond the two items above (rewritten
30 Aug and accurate).

---

## 2. Flags — found, not fixed

These are **not** documentation bugs. Each needs a human decision, and the
governing constraint is that neither the data nor the canonical list may be
edited to make them go away.

### F6 — NOTHING IN THIS REPOSITORY IS COMMITTED — found 30 Aug (P18)

**The single most important finding of either audit, and it was found by
accident.** A P18 edit to `src/11_inversion.py` was silently overwritten in the
working tree at 16:49. The forensics:

```
$ git status --short src/11_inversion.py     →  ?? src/11_inversion.py   (untracked)
$ git log --oneline                          →  debdf6f  Initial VISHWAS project scaffold
$ git reflog                                 →  debdf6f  HEAD@{0}: commit (initial)
```

**The obvious explanation — that a checkout or reset discarded an uncommitted
edit — is ruled out.** Git has never tracked this file, and the reflog holds
exactly one entry, so git has performed no ref-moving operation since the repo
was created. Something outside git rewrote the file, most likely an editor
flushing a stale buffer over it.

**The conclusion is nevertheless correct, and larger than the incident.** The
repository has **one commit** — the scaffold — with **30 untracked files and 5
modified tracked files** on top of it. Every artifact of Phase 2, Phase 3, P17
and P18 is uncommitted working-tree state: the trained-model pipeline
(`06_label.py` through `11_inversion.py`), every figure generator, every deck
document, `scripts/check_docs.py`, and this audit. **There is no recovery point
for any of it.** The working tree is not a safe place to leave decisions, and
right now it is the only place they exist.

**Action:** the P18 work is committed. Committing the rest is the first thing
that should happen after the PPT.

### ~~F1 — `fig4_inversion.png` cannot be reproduced from `src/`~~ — RESOLVED 30 Aug (P18)

**Resolved.** `src/11_inversion.py` now renders the shipped footnote and is the
only generator for the figure. The ad hoc script that produced the shipped PNG
hardcoded its literals and was never committed; it does not survive. Everything
in the caption is now computed from `data/model_predictions.parquet` or read
from `models/vishwas_model.joblib` — including the robustness low end
(**+0.1322**, the "drop the driest bin" variant, previously pasted in) and the
training counts (**39 dates / 488,280 rows**).

**The root cause was in the constitution, not the code.** `CLAUDE.md` carried a
"sanctioned exception" permitting fig4 to print the pooled pair, while the
project owner had decided to remove it. A rule that permits what the project has
decided against will be restored by the next session, correctly. That exception
is now **withdrawn** in `CLAUDE.md` and in `DECK-TECHNICAL-PACK.md` §7; the
pooled pair is Q&A-only. `scripts/check_docs.py` now carries `0.909` / `0.885`
as forbidden patterns, with an ABSOLVING vocabulary for the contexts that may
legitimately name them (a rule forbidding them, an artefact label, a Q&A note).

Adding that rule immediately caught **four** documents still presenting the pair
— results-table rows in `DECK-BRIEF.md` and `DECK-TECHNICAL-PACK.md`, and the
pack's own stale exception paragraph. All four are fixed. The original detail
of the finding follows, for provenance.

#### Original F1 write-up (superseded)

The P17 brief lists as a stale claim: *"any claim that the pooled pair
0.909/0.885 appears inside fig4 — the figure was regenerated on 30 Aug and no
longer prints them."*

**Half of that is right, and the half that is wrong matters.**

- **The rendered `figures/fig4_inversion.png` (30 Aug 04:29) does NOT print
  them.** Verified by opening the image. Its footnote begins *"Left bar:
  VISHWAS's margin when every forecast is pooled together…"* and prints only the
  stratified pair, 0.728 / 0.565. So the brief is correct about the deck asset,
  and `docs/DECK-VERIFICATION.md` line 198 was wrong. That line is now corrected.
- **But `src/11_inversion.py` (30 Aug 03:35) would print them.** Its footnote
  format string reads *"Pooled — the flattering comparison this figure exists to
  discredit: {:.3f} vs {:.3f}…"*, which renders 0.909 vs 0.885. That matches the
  "ONE SANCTIONED EXCEPTION" paragraph in `CLAUDE.md` and pack §7 exactly.
- **The footnote text that is actually in the PNG exists in no file in this
  repository.** `grep -r "Left bar"` returns nothing. The script's mtime is
  *earlier* than the PNG's, so the image was produced by a version of the code
  that was not kept.

**Consequences.** Re-running `python src/11_inversion.py` today produces a
*different figure* from the one in `figures/` — one that prints the pooled pair,
contradicting the corrected line in `DECK-VERIFICATION.md`. The numbers are not
in doubt; they reproduce exactly from `data/model_predictions.parquet`. What is
in doubt is which footnote was intended.

**Decision required (not before the PPT — the current PNG is fine to present):**
either restore the sanctioned-exception footnote in the figure and revert the
`DECK-VERIFICATION.md` line, or amend `CLAUDE.md`'s sanctioned-exception
paragraph to match the figure as rendered. **Do not resolve it by editing the
audit or the canonical list.**

### ~~F2 — Guan et al. (2022) is canonical but cited nowhere~~ — WITHDRAWN 30 Aug (P18)

**False. Guan et al. (2022) is on slide 6** of the shipping deck, under
DATA SOURCES: *"Guan et al. (2022). GEFSv12 reforecast dataset. Mon. Wea. Rev.
150(3), 647–665."* Verified by extracting the slide XML. It sits under DATA
SOURCES rather than under BACKGROUND AND VERIFICATION PRACTICE, which is why a
reader scanning the background block would miss it — but it is there, correctly
attributed, and it is the right section for it.

Also verified on the same slide: the IMD Monsoon Report 2024 is cited for
*containing* false-alarm-ratio, probability-of-detection and threat-score
verification — **not** as the source of the 0.34–0.37 figure. That is exactly
the distinction the canonical rule requires.

### ~~F3 — the deck itself still carries the two stale images~~ — WITHDRAWN 30 Aug (P18)

**False for the deck that ships.** `deck/VISHWAS_SIH.pptx` (v17, built 30 Aug
15:59) was unzipped and its media hashed:

| Media | md5 | Is |
|---|---|---|
| `image4.png` | `f8c47d37…` | `figures/fig1_collapse.png` |
| `image5.png` | `93fead2f…` | **`figures/fig6_confidence_map.png`** — the three-panel replacement |
| `image6.png` | `bd20f5dd…` | **`figures/fig4_inversion.png`** — the regenerated one, byte-identical |

Six media files, all six referenced across slides 1–6, **zero orphans**, and no
`fig5` anywhere in the package. Slide 6 already reads *"the 651,040-row 2019 test
set drawn from a 1,302,080-row labelled table"*, so the conflation fix flagged in
`DECK-TECHNICAL-PACK.md` §0 has also been made.

**Why the audit got this wrong, which is the part worth recording.** P17 did not
open any `.pptx`. It carried F3 over from `DECK-VERIFICATION.md` §"TWO STALE
IMAGES" and `DECK-TECHNICAL-PACK.md` §0, both of which describe a build from
29 August, and it did not check those prose claims against the file on disk. An
audit that hunts stale claims in prose must not accept a prose claim *about a
binary artifact* at face value. **Byte-check the artifact.** Note that the byte
sizes those two documents quote (132,935 and 164,852) match neither deck now
present, so they described a third, intermediate build.

`DECK-VERIFICATION.md` §"TWO STALE IMAGES" and `DECK-TECHNICAL-PACK.md` §0 are
now themselves stale and are marked accordingly.

### F5 — two presentable decks were sitting side by side — RESOLVED 30 Aug (P18)

The real finding underneath F3. `deck/` held **both** `VISHWAS_SIH.pptx` (v17,
30 Aug 15:59) and `VISHWAS_SIH_v1.pptx` (29 Aug 17:01), plus both PDFs — and the
v1 build *does* carry the superseded fig4 and the deleted fig5. Two openable
decks in one folder, the night before someone opens a file to present from, is a
hazard.

**Resolved:** the v1 pair moved to `deck/archive/` with a README stating plainly
that the live deck is `VISHWAS_SIH.pptx`/`.pdf` and that the archived build is
not to be presented from. Moved rather than deleted — reversible, and the
provenance is worth keeping.

### F7 — `figures/fig1_collapse.png` now differs from the copy embedded in deck v17

Regenerating fig1 from its new generator changed the file
(`f8c47d37…` → `06ffa8dc…`). **The deck is unaffected** — v17 carries its own
embedded copy as `image4.png` — but the two are no longer the same image.

The difference is the one you asked for: the old subtitle said *"44% of apparent
skill"*, the regenerated one says **"43.9% of the variance in forecast error"**,
matching the deck card and slide 6. The numbers were always the same.

**Decision needed before the next deck build:** re-embed the regenerated fig1 so
the deck and `figures/` agree, or leave v17 as shipped. Not urgent — the shipped
wording is not wrong, only less precise. `fig2` and `fig3` were also regenerated
but are **not** embedded in the deck, so nothing depends on them.

### F4 — Kusunose & Mahmood (2016) still unopened

`DECK-VERIFICATION.md` marks it **CHECK** — cited from Mahika's brief, never
independently opened. It remains a canonical citation. Left as-is; someone
should open it before it is spoken aloud.

---

## 3. `VISHWAS-MASTER.md` — regenerate, do not patch

**This file was not brought into line, deliberately, and that is the right
call.** It is a snapshot taken at 18:45 on 29 August, *before the model was
trained*. More than half of it — all of Part 0, Part 1 §8, Part 2 §§1 and 4,
Part 2 §6, and all of Part 3 — describes a pre-model state.

It already carried an explicit SUPERSEDED banner (added 30 Aug) naming each dead
section and recommending regeneration. This audit added two **inline** ⛔ markers
at the two places a reader arriving by search or scroll would otherwise be
misled: the Part 1 §8 status table, and the Part 2 §1 heading *"Read this first:
there is no model yet"*.

**A half-corrected file where the reader cannot tell which half is current is
more dangerous than a clearly labelled stale one.** The recommendation stands:
**regenerate this document from `CLAUDE.md`** after the PPT. Until then the
banner plus the two inline markers are the mitigation, and
`scripts/check_docs.py` lists it as exempt with that reason recorded.

The same reasoning applies to the five prompt archives: their forward-looking
text is the historical record of what was asked, and editing it would destroy
the thing they exist to preserve. They get banners, not rewrites.

---

## 4. The canonical list audited against

As of 30 August 2026. This is what the scripts produced. It is duplicated as a
literal table at the top of `scripts/check_docs.py`; **update both together.**

**Phase 1** — spread–error correlation pooled **+0.663**, conditional **+0.041**;
variance explained **43.9%** pooled, **0.17–0.90%** conditional; sample 12
reforecasts, 4 seasons, 2012/2015/2018, **77,425** wet samples, Day 1–10.
Quote as *"under 1% however you slice it"*.

**Data** — **104** forecast dates, 2018–2019, **50.3 GB**, **23** features;
**1,302,080** labelled rows over **1,252** gauge-observed land gridpoints;
1,252 of 5,041 = **24.8%**; train **39** dates / **488,280** rows / **4.86%**;
validation **13** dates / **162,760** rows / **5.43%**; test **52** dates /
**651,040** rows / **6.47%**; train and test both DJF 13, MAM 13, JJAS 17, ON 9.

**Model (final)** — ROC-AUC pooled baseline 0.885 / model 0.909 ← **never on a
slide**; ROC-AUC stratified baseline **0.565** / model **0.728** ← the result;
margin **+0.1634**, 95% CI **+0.1080 to +0.1926**; **quote the margin as +0.13 to
+0.16, never +0.163 alone**; ahead in all **eight** rainfall bins, **+0.079 to
+0.252**; PR-AUC lift **6.29×** baseline / **7.60×** model.

**Ablations** — full 0.728 | no month 0.722 | no precip 0.731 | no 850 hPa 0.726
| spread only 0.562 (baseline as a plain ranking 0.565).

**Calibration** — reliability 0.00014 → **0.00006** (isotonic); resolution
**0.01758** vs 0.01225; Brier skill score **+0.303** vs **+0.215**; isotonic caps
output at **0.75**.

**Operational** — **64%** of busts caught vs **55%**, at a matched alert budget.

**Demo date** — init **20190731**, Day 5, valid 5 Aug 2019, **454/1,252**
busted (**36.3%**); threshold **p ≥ 0.1535** fixed on the full test set;
precision **0.72**, recall **0.87**; panel counts **395 / 152 / 59 / 646**.

**Rainfall bins** — **EIGHT bins, not deciles.** Bin 7 (wettest) bust rate
**40.92%**, bin 0 (driest) **0.15%**; bin 0 holds **208,065** rows; ensemble
spread = 0.00 on **189,758** of them; exact-zero forecast mean is **189,740**
rows, a **strict subset** of those 189,758.

**Forecast decay** — GEFS detects **23%** of heavy-rain events at Day 1, **0.2%**
at Day 10.

**External citations** — MoES Lok Sabha Q. 2953, 17 Dec 2025 (85/73/67/63/58% at
Day 1–5, ~40% improvement on 2014); **Guan et al. (2022), Mon. Wea. Rev. 150(3),
647–665** — the GEFSv12 reforecast dataset paper; Ashrit et al. (2020), Met.
Apps 27(2); Kumar et al. (2008), QJRMS 134; Kusunose & Mahmood (2016), Agric.
Systems 146, 103–110; LeClerc & Joslyn (2015), Risk Analysis 35(3).

---

## 5. About `scripts/check_docs.py`

Four literal tables at the top of the file, each a one-line edit to update:

| Table | Holds |
|---|---|
| `CANONICAL` | the values above, plus the wrong spellings that must never appear |
| `FORBIDDEN` | 13 stale-claim regexes, each with the reason it is wrong |
| `EXEMPT` | files whose findings are **reported but do not fail the run**, each with a stated reason — the pre-model snapshot, the five prompt archives, `CLAUDE.md`, `DECK-VERIFICATION.md`, and this file |
| `ABSOLVING` | correction/prohibition vocabulary that marks a line as *discussing* a stale claim rather than *asserting* it |

**THE CHECKER CANNOT SEE INSIDE A PNG, AND NEVER WILL.** It walks `.md` files.
A wrong number or a stale claim baked into a figure caption is invisible to it —
and figure captions are exactly where the project has twice been wrong. Both
`fig4` faults were found by **opening the image**: the pooled pair (P17) and the
"five wet-point definitions" error, which is **two** (P18). The mitigation is
structural rather than automated: every figure now has a committed generator,
and every number in a caption is computed by that generator rather than retyped
by a person. **Review a figure by rendering it and reading it.**

**`ABSOLVING` is the one place this script can hide a real finding.** A document
that forbids a claim has to name it — *"Never quote +0.035"* must not be reported
as asserting +0.035. The vocabulary is kept narrow, it considers the line and its
two neighbours (corrective framing routinely wraps), the run prints how many
lines it suppressed, and `--no-absolve` shows everything. A genuine stale
assertion that happened to contain the word "not" would be missed; that is the
accepted cost of a checker people will actually keep running.

**Exempt files are reported in full, not hidden** — they appear under NOTED and
simply do not gate the exit code.

**There is no `--fix`, by design.** It reports; a human decides.

**Verified working:** a deliberately injected stale claim (*"the wettest tenth
bust rate"*) was caught and the run exited 1; with it removed, the repository
exits 0.
