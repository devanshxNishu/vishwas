# What the selected SIH decks actually do

Reviewed 29 Aug 2026: 12 unique decks (11 from SIH 2024, 1 from SIH 2025, plus
one Vadodara hackathon deck). Every one is **exactly 6 pages** and every one
uses the **official SIH template** — the same blue footer, corner logo and
team-name oval. None built a custom design. That settles the format question.

## Patterns common to nearly all of them

**1. Slide 3 always carries an architecture or workflow diagram, plus an
explicit technology stack.** 12 of 12. Usually a left-to-right or top-down box
diagram, alongside a block of framework names — often as a wall of logos
(Tech Pioneers 2025, Laksh, GreenSort, Cannon Crew, Tech Titans).
→ **This was our biggest gap.** The deck had no architecture diagram at all.
Now fixed: slide 3 opens with the six real pipeline stages from
`TECHNICAL-REFERENCE.md` §2 — fetch → features → truth → label → model →
evaluate, each box naming its actual script in `src/` — with a "Built with"
line underneath.

**2. They mirror the template's own prompts as literal headings.** Slide 2
repeats "Proposed Solution", "How it addresses the problem", "Innovation and
uniqueness"; slide 4 repeats "Feasibility of the idea", "Potential challenges
and risks", "Strategies for overcoming". Judges scan for these.
→ Our headings now match: `PROPOSED SOLUTION` / `HOW IT ADDRESSES THE PROBLEM`
/ `INNOVATION AND UNIQUENESS`, and `FEASIBILITY —` / `VIABILITY —` / a banner
reading `POTENTIAL CHALLENGES AND RISKS — AND THE STRATEGY FOR EACH`.

**3. Dense is normal.** These decks are far denser than ordinary presentation
advice allows. They are read, not projected. Ours is comparable and does not
need thinning.

**4. Colour-blocked content.** Coloured boxes, tables and numbered markers
rather than plain bullets. We already do this.

**5. Reference quality varies a lot, and it is a cheap differentiator.**
Weaker decks list bare URLs (Tech Titans, GreenSort). Stronger ones give full
academic citations with authors, venue and year (Laksh).
→ Ours is now at the strong end: Ashrit et al. (2020) NCMRWF, Kumar et al.
(2008) QJRMS, Guan et al. (2022) Mon. Wea. Rev., plus named government reports.

> **Citation corrected 30 Aug.** This line previously read "Hamill et al." for
> the GEFSv12 reforecast dataset paper. Wrong paper and wrong journal. The
> dataset paper is **Guan et al. (2022), *Monthly Weather Review* 150(3),
> 647–665, doi 10.1175/MWR-D-21-0245.1** — Hamill is the 12th of 18 authors.
> The Hamill reforecast paper in *Bull. Amer. Meteor. Soc.* is from 2006 and
> describes a different dataset. Do not cite it for GEFSv12.

## The one idea worth stealing that we have not used

**Tech Pioneers 2025** (SIH25071, "AI-Based Rockfall Prediction and Alert
System for Open-Pit Mines" — the closest analogue to our own problem) puts a
**comparison-with-existing-systems matrix** on slide 6: their product against
four named competitors, feature rows, ticks and crosses.

For VISHWAS the equivalent axis is not competitor products but **methods**:
ensemble spread (the incumbent) vs a learned confidence layer, across rows like
within-regime skill, calibration, explainability and per-gridpoint resolution.
There is no room for it on the current six slides — but **as of 30 Aug every row
of it is now measured** (within-regime skill, calibration, explainability and the
matched-alert-budget comparison all have numbers), so the honesty objection below
no longer applies. It is the natural slide to add for the Grand Finale deck, or a
strong appendix slide for the 20 Sep submission.

## What we already do better than the benchmark

- **A measured result rather than a described plan.** None of the reviewed
  decks put an original measurement on the page.
- **Risks stated with their mitigation**, including one that weakens our own
  claim (the ensemble-size sensitivity).
- **A trained model with a held-out result, and the fair comparison stated
  rather than the flattering one.** Several benchmark decks imply working
  systems without evidence; we report stratified ROC-AUC 0.728 vs 0.565 and
  say out loud that the pooled 0.909 vs 0.885 is an artefact.

---

# Where the deck stands — audit, 29 Aug (deck v11)

Checked against the six rules on the template's own instructions slide, and
against all twelve selected reference decks.

## Rules: 6/6, one with a caveat

1. **Six slides incl. title** — pass, exactly 6.
2. **Avoid paragraphs; use points/diagrams/infographics** — *partial*. Four
   visuals (pipeline diagram + three figures) but the card bodies are prose, and
   slides 5 and 6 carry no figure. Every reference deck is equally dense and the
   rule says "try to avoid", so this stands.
3. **Precise and easy to understand** — pass.
4. **Unique and novel** — pass.
5. **Provided template, pointers unchanged** — pass. All six title fields
   present, in order, labels unchanged. Five deviations, each with precedent in
   a reference deck (see the deviations table above).
6. **PDF only** — pass. **Upload `VISHWAS_SIH.pdf`; the PPTX will be rejected.**

## Standing against the twelve

| Dimension | Standing |
|---|---|
| Original evidence | **Well ahead** — 0 of 12 present a result they measured themselves |
| Primary user research | **Unique** — none interviewed a user |
| References | **Ahead** — 10 authored, dated sources vs bare URLs or generic prose |
| Risk honesty | **Ahead** — named risks with strategies, including self-weakening ones |
| Architecture diagram | Par — 12/12 have one; so do we |
| Template discipline | Par |
| Technology stack | Slightly behind — they use logo walls, we use a text line |
| **Product interface** | **Behind — six slides, no screen shown anywhere** |
| Comparison with alternatives | Behind — Tech Pioneers 2025 has a feature matrix |
| Team | Slightly ahead — members and disciplines on slide 6 |

## The one-line verdict

The deck proves more than any reference deck and shows less. Every gap left is
presentational, not substantive.

## Ranked fixes before 31 Aug

1. Paste the **Team ID** — the only placeholder left.
2. ~~Run the **`month` ablation**~~ — **done 29 Aug and passed** (−0.0059
   against a 0.02 tolerance). 0.728 stands. Three cards and
   `figures/fig4_inversion.png` carry the number.
3. **Show the product** — even a rough forecaster-facing confidence map for one
   real 2019 bust closes the largest gap. Already on the Sunday list.
4. Confirm the **PS title** against the portal.
5. Optional: a stack logo strip. Cosmetic; lowest value.

**Not recommended:** a competitor matrix — but for one reason only, that the
deck is already at the six-slide limit. (The other objection, that it would be
premature, expired on 30 Aug: calibration and explainability are both scored.)
Save it for the Grand Finale deck.

## Update — 29 Aug evening (deck v12)

Two of the five ranked fixes are done.

- **Product interface — closed.** Slide 3 now carries a real confidence map:
  the Day-5 forecast **initialised 31 July 2019, valid 5 August**, 454 of 1,252
  gridpoints busted, ROC-AUC 0.886 on that date, built from
  `data/model_predictions.parquet`, not a mockup. This was the largest gap
  against the reference set.
  **Two corrections, 30 Aug.** (1) The v12 deck labelled this "initialised
  26 July, valid 31 July" — both dates five days early, and 26 July 2019 was a
  Friday, not one of the 52 Wednesday inits. The figure that carried that
  caption (`fig5_confidence_map.png`) has been deleted. **The deck itself still
  shows the wrong date on slide 3 and must be fixed before Monday.**
  (2) The replacement, `figures/fig6_confidence_map.png`, has **three** panels,
  not two: predicted bust probability, observed IMD rainfall, and hits / false
  alarms / misses at the operating point.
- **Technology stack — closed.** A five-group band under the pipeline:
  language and core, data access, model, explain and verify, figures and
  delivery. Text chips rather than a logo wall, which is honest and reads
  cleanly at slide size.
- **Rule 2 (avoid paragraphs) — improved.** The diagnostic map and one prose
  card came off slide 3; slide 5's benefits paragraph became three tiles. Every
  slide except 6 now carries a figure or a diagram, and slide 6 is a reference
  list, where prose is correct.

Remaining from the ranked list: paste the Team ID, and confirm the PS title
against the portal. The `month` ablation has run and passed.
