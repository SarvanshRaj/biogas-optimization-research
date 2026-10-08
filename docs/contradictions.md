# Conflict map: contradictions, their claim links, and what Phase 4 decided

**Status.** Phase 4 artefact, written 2026-10-07. It closes the `G-P-4` row of
`docs/requirements_traceability.md` (conflict map with contradiction → `claim_id` links) and unblocks
the `G-L8` gate: no ranking or recommendation was issued before this file existed. Every measured
number below is **SIMULATED** output from `results/` (seed 11 unless stated); the literature
positions are the retrieved sources listed in `docs/sources.json`. Nothing in this file
is a measurement, a design, or a claim about real digesters.

## 0. Falsifier verdicts this map leans on

Rules are quoted from the frozen `docs/preregistration.md` §8; measurements from the Phase-4 runs.

| Rule | Trigger as frozen | Measured | Verdict |
|---|---|---|---|
| F1 | no retrievable source linking *A. oryzae* (or comparable fungal pre-treatment) to food-waste methane yield | comparable fungal studies exist (CIT-0007 +55.87 %, CIT-0028, CIT-0032); **no pure *A. oryzae*-on-food-waste study exists** | does **not** fire as written; the missing half is carried by claim `C-003` (`partial`) |
| F3 | Ridge ≥ 95 % of the best tree model's test R² (mean over seeds) | Ridge 0.4540 vs boosting 0.8124 = **55.9 %** | does **not** fire → the comparison is informative *about the simulator's nonlinear structure* |
| F5 | ±5 % perturbation changes the recommended region, or recomputed yield < baseline | fires **on the oracle itself, in both tiers**: 26 % (C1) / 32 % (C1+C2) of perturbations feasible; perturbation mean 505.4 / 504.9 below the point 513.9 / 513.8 | **FIRES** → optimum reported artefactual, no "best recipe" claimed |
| F7 | reported metric depends materially on seed, mean ± spread overlapping the dummy's spread | Ridge [0.3397, 0.5683] vs dummy [−0.0480, −0.0164], no overlap; fastest-moving model (MLP) spread 0.082 still clears the dummy band | does **not** fire |

## A. Contradictions between retrieved sources

| # | The contradiction | Claim link | What the frozen model does | What Phase 4 measured |
|---|---|---|---|---|
| A1 | **TS direction.** One study reports better performance up to 20 % TS; another reports *reduced* specific methane yield at 20 % TS | `C-005` (`contested`, cites CIT-0006, counter CIT-0012) | peak-shaped TS response centred at 12 %; the 20 % peak and the monotone form are the sweep's other two levels | `ts_shape monotone` **−65.2 %** median, **−32.1 %** C1 recommendation, −30.7 % C1+C2; `ts_shape 20 %` −24.8 % / −11.7 % / −9.6 %. This is the **largest structural risk found anywhere in the sweep**, and the frozen choice is the optimistic one on the level |
| A2 | **Does Stage-1 pre-treatment help?** +55.87 % biomethane (single two-fungus study naming *A. oryzae*) vs studies finding no improvement or less effectiveness vs the reverse coupling (*A. oryzae* grown on VFAs from AD) vs species-specific signs | `C-003` (`partial`, cites CIT-0005, CIT-0007, CIT-0033, CIT-0028, CIT-0009) | sign-symmetric latent factor, neutral default, uniform spread; never assumed beneficial | `pretreatment_response` 0.90 → −7.7 % median, 1.10 → +9.8 %; **0.0 % on both recommendations**. The factor moves the achievable level and cannot change what the optimiser recommends, so the sweep cannot answer the hypothesis either way (Q2 stays open by construction) |
| A3 | **Rate vs ultimate potential.** Pre-treatment effects act on the *rate* of production at least as often as on the ultimate potential, and apparent size depends on the measurement window | `C-004` (cites CIT-0016, CIT-0031, CIT-0028, CIT-0009; counter CIT-0007) | a single-shot yield with no hydraulic/rate descriptor, the outcome definition cannot represent a rate-only effect | `k_ref` 0.10 / 0.25 → −34.3 % / +22.3 % median but ≤ 5.4 % on the recommendation. A rate-only real-world effect is **invisible to this outcome definition**; recorded as a representational limit, not a measured result |
| A4 | **Lipid/LCFA inhibition threshold**: a unimodal response is plausible above a threshold | `C-002` (`supported`, cites CIT-0015, CIT-0014, CIT-0007) | LCFA inhibition term with half-saturation 1.2 g/L | `eta_lcfa` 0.030 → −24.1 % median / −17.1 % C1 recommendation; `lcfa_half` 0.8–2.0 → −3.9 %/+3.8 % median. The channel is real in the simulator and modest at the recommendation |
| A5 | **Inoculum and I:S ratio**: an inoculum factor changed anchor values; seed pre-incubation affects rates but not ultimate yield | `C-011`, `C-009`; CIT-0031 | I:S is a declared flat descriptor (no effect by construction) | The sweep cannot move it, and reported importance ≈ 0 confirms the declared no-op. The literature's emphasis on I:S is therefore **not representable** here, carried openly rather than papered over |
| A6 | **Ambient relative humidity as a driver**: no retrieved support | `C-008` (`rejected`, resolved by exclusion) | RH excluded; slurry moisture/TS is the process variable | nothing to sweep; exclusion stands |

## B. Contradictions inside our own artefacts

| # | The contradiction | Evidence | How it is carried |
|---|---|---|---|
| B1 | The frozen specification's §4.1 sanity anchors do not all reproduce from its own §3.2/3.3 equations: five of thirteen anchors move by 6–74 mL/g VS, and the pre-treatment family is uniformly ~3 % high | `C-009` (`active`), `C-010`, `docs/known_issues.md` | Anchors pinned as written, divergence recorded, no silent re-fit; the anchor 411.6 ± 1.0 mL CH₄/g VS stays the published yardstick |
| B2 | The brief asks for a baseline comparison, but the declared D6 equal-thirds baseline is **infeasible** on this simulator (C-b, C-c, C-e violations; stress 1.000 > 0.35, pH_eff 6.20 < 6.5) | `results/optimisation/optimiser_metadata.json` | Both numbers reported: the declared baseline 313.70 **and** its pre-declared feasible projection 365.8, which is what the oracle is compared against |
| B3 | The F5 verdict is **configuration-dependent**: it fires in both tiers at study size (500 scenarios / 60 iterations / 200 draws) but at sweep size (250 / 20 / 20) it fires on 22 of 30 C1 rows and only 1 of 30 C1+C2 rows | `results/sensitivity/sensitivity_sweep.csv` | Recorded, not averaged. The verdict reported in `results/README.md` is the study-size one; the sweep's F5 columns are shipped beside it so the difference is inspectable |
| B4 | The model comparison is informative about structure (F3 clean) but **not** about recommending: every non-dummy surrogate over-promises (+76.6 forest C1 → +404.9 ridge C1+C2), and the dummy mis-calibrates in both directions (−199.1 C1, +97.2 C1+C2) | `results/optimisation/optimiser_summary.csv` | Both readings reported side by side; no surrogate is ranked by its own promise |
| B5 | Ridge's *recomputed* yield is below the baseline in both tiers (212.08 / 25.23 vs 313.70) although it "promised" 312.17 / 430.17 | same file | Reported as the sharpest single demonstration that optimising a low-R² linear surrogate is worse than doing nothing on this problem |

## C. The M-decisions deferred here by the Phase-2 disagreement map

| id | The disagreement (Phase 2) | What Phase 4 shows | Status now |
|---|---|---|---|
| M-1 | Should laboratory-only variables be part of the recommendation? | Tier choice does not raise what is achievable (oracle 513.92 C1 vs 513.76 C1+C2), but it widens the surrogates' room to over-promise: ridge's gap +100.1 → +404.9, MLP's +180.2 → +223.4 | **Closed:** both tiers reported separately (S-7). Never rank a surrogate by its own promise; the ranking consequence is this sentence |
| M-2 | Should costs enter the objective? | The objective is already artefactual under F5, its optimum sits against the stability constraint | **Closed as declared:** cost-free objective; cost proxies reported, never optimised. Optimising a second unvalidated quantity would not fix a fragile first one |
| M-3 | Is the model comparison informative at all? | F3 does not fire (55.9 % < 95 %), F7 does not fire; F5 fires on the oracle | **Closed, two-sided:** informative about the simulator's nonlinear structure; *not* informative as evidence about real digesters (C-001, C-007) and not sufficient for recommendation quality. Both verdicts were pre-declared rules, not arguments |
| M-4 | Should composition collinearity be removed by re-parameterisation? | `ph_measured` ranks first in every model (0.92 boosting, 1.05 MLP), OLR second (0.55 / 0.67), total solids third (0.067 / 0.075), and `ph_measured` is a *derived* column | **Retained criticism:** no re-parameterisation; the causal-reading ban stands. The transparency that matters is that the simulator's derived acidification channel is what the models lean on |
| M-5 | Is Stage 1 worth modelling given the weak evidence? | Its factor moves the level (−7.7 % / +9.8 % median) and the recommendation **not at all** (0.0 % / 0.0 %) | **Closed:** Stage 1 stays, it is the study's subject, but the sweep shows the model cannot rank mixtures on it, so no Stage-1 conclusion is drawn. F1's interpretation rule stands |
| M-6 | Does a biochemical simulation speak to the real failure modes? | Not decidable from the artefacts; the limits are claim-level (`C-001`, `C-007`) | **Carried to Phase 5**, where the report's A/B/C tiering decides how much space the real-world limits take. Not silently resolved here |

## D. What this map deliberately does not do

- It issues **no best recipe**: F5 fired on the oracle's own recommendation, and the artefactual
  verdict is the pre-declared consequence.
- It draws **no conclusion about pre-treatment effectiveness**: the factor cannot move the
  recommendation (A2) and no retrieved study tests the exact hypothesis (F1 half, `C-003`).
- It claims **no real-world validity** for any model score, the training target is the simulator
  (`C-001`), and real-digester transfer failure is documented (`C-007`).
- It does not soften the contested TS direction (A1); the sweep's largest effect is a *direction*,
  not a magnitude, and it is reported as the study's main structural risk to the model's level
  prediction.
