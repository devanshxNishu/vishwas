# VISHWAS — Hellfire Labs

Static site + operational dashboard. Both pages are fully self-contained single HTML files (fonts, images and data inlined) — no build step, no server, no dependencies.

```
index.html            → the site (landing / case)
dashboard/index.html  → the operational console
source/               → editable sources (not needed to deploy)
```

The site's "Open console" links point at `dashboard/index.html`, so keep that folder structure.

## Deploy

**GitHub Pages**

```bash
git init
git add .
git commit -m "VISHWAS site + dashboard"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

Then Settings → Pages → Source: `Deploy from a branch` → `main` / `/ (root)`.
Live at `https://<you>.github.io/<repo>/` and `.../dashboard/`.
(`.nojekyll` is included so Pages serves every file as-is.)

**Netlify / Vercel / Cloudflare Pages** — drag the folder in, or connect the repo with:
- build command: *(none)*
- publish / output directory: `/` (repo root)

**Local check**

```bash
python3 -m http.server 8000
# → http://localhost:8000
```

## Notes

- Each page is ~1.5–3 MB because assets are inlined; first load fetches one file, then everything is instant offline.
- `source/` holds the editable component files, the raw images, and the data the pages are built from:
  - `source/site/dashboard-data.json` — the only source for the console: 6 test dates × 10 lead days × 1,252 gridpoints = 75,120 cells, each `[ix, iy, p, verdict]` (+ 3 SHAP drivers when the verdict is uncertain or high risk). Verdicts are decided upstream at full precision; nothing in either page re-derives a call by comparing `p` to the threshold.
  - `source/site/skill-by-lead.json`, `source/site/lead-day-auc.csv` — measured per-lead-day AUC, with the 95% margin interval.
  - `source/assets/aug5.json` — the site's 31 July 2019 map, joined to the same export (real p and verdict for all ten lead days).
  Deleting `source/` does not affect the deployed site.
- Dashboard replays six archived 2019 reforecast dates — all real Wednesdays from the 52-Wednesday test year, chosen by a rule fixed in advance (most active date per season, plus the JJAS median). Prototype data, not a live feed.
