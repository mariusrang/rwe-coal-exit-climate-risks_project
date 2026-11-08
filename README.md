# Is RWE on track for its 2030 coal exit?

Group project for **Climate Risks (IDSI 51003)**, Research and Emerging Topics. Role: **sustainability consultant**.
Team: Victor Henz, Edgar Gusching, Marius Rang, Ylias Guetari.

## Question

The lignite exit on 31 March 2030 is fixed by law. We test whether RWE's transition is credible as a business:
does its new wind + solar replace the output of the coal it closes (capacity-factor-adjusted **replacement ratio ≥ 1**),
and has RWE ever built at the pace this requires?

H0 (from our V0) is evaluated through two criteria set after the V0 feedback, before the final analysis:
* **C1:** P(ratio ≥ 1) ≥ 0.66 under the Current plan scenario;
* **C2:** pace needed ≤ RWE's best 3-year average pace; decisive basis = coverage-adjusted (GEM-visible and RWE-reported are bounds).

## Main results

| | Value |
|---|---|
| Coal to replace (equity, coal part, Eemshaven fixed, CF calibrated on RWE's official Scope 1, B = 0.92) | 7.9 GW → 32.1 TWh/yr |
| Ratio 2030, Track record (GEM-visible) | 0.34 [0.19–0.54] |
| Ratio 2030, **Current plan** (GEM-visible / coverage-adjusted) | **0.51** [0.31–0.72] / 0.57 |
| Ratio 2030, Full delivery (GEM-visible / coverage-adjusted) | 1.02 (P ≈ 0.55) / 1.22 (P ≈ 0.85) |
| Ratio, Germany + Netherlands pipeline only | 0.11 |
| Pace needed / implied by identifiable projects / RWE guidance 2026-31 | 2.23 / 1.15 / 3.17 GW/yr |
| Needed ÷ RWE best 3-year pace (coverage-adjusted, decisive / GEM-visible / RWE-reported) | 1.14 / 1.78 / 0.93 |
| 2030 emission intensity vs SBTi target (0.159 tCO₂e/MWh, from RWE's published 0.55 in 2022) | 0.19–0.22, above target under our model assumptions |

**Verdict:** on identifiable projects H0 cannot be supported (C1 fails, C2 narrowly fails on the decisive basis). In its V0 wording,
the build-rate part of H0 holds, and C1 is met if everything planned before 2030 is built. RWE's coal timeline is aligned with the
IEA NZE milestone; the replacement is not, on the projects visible today. A bridge table in the notebook explains the move from
Lab 5 (1.10) to the current estimate step by step.

## Repo structure

```
data/        GEM Global Integrated Power Tracker, September 2026 V2 (xlsx) – a .pkl cache is created on first run
notebooks/   RWE_coal_exit_final_project.ipynb   <- the full final analysis (start here)
labs/        lab5.ipynb (uncertainty lab) + its figure
results/     tables exported by the notebook (used by the app and the website)
figures/     all figures of the paper (PNG, 200 dpi)
app/         streamlit_app.py  – interactive dashboard + simulator
docs/        index.html        – static website (works on GitHub Pages: Settings → Pages → /docs)
paper/       main.tex + main.pdf – paper for Overleaf (upload main.tex + the figures/ folder)
```

## How to run

```bash
pip install -r requirements.txt
jupyter notebook notebooks/RWE_coal_exit_final_project.ipynb   # Kernel -> Restart & Run All (~1 min first time)
streamlit run app/streamlit_app.py                              # dashboard on http://localhost:8501
# website: open docs/index.html in a browser
```

## Data and license

Global Energy Monitor, *Global Integrated Power Tracker*, September 2026 V2, licensed **CC BY 4.0**
(https://globalenergymonitor.org/projects/global-integrated-power-tracker/).
External figures (RWE press releases and reports, SBTi, IEA Renewables 2025, EU ETS price, offshore project status) are cited
in the notebook next to where they are used. Known limits: GEM sees about 64% of RWE's wind + solar, and only about a third of RWE's
pipeline capacity has a start year.

## Use of AI tools

We used an AI assistant (Claude, Anthropic) to help write and debug code, draft parts of the text and build the app and website.
All modelling choices, sources and results were checked by the team.
