# Biogas Optimization Research

A simulation study of a two-stage food-waste-to-biogas idea. Stage 1 is a fungal pre-treatment with
*Aspergillus oryzae*, stage 2 is a simplified digestion model, and the last part is a constrained
optimiser over feed mixtures and process settings. Everything is computed from equations in
`src/simulate_data.py`.

**All of it is simulated.** There is no laboratory work here, no digester, and no measured biogas.
Every CSV, figure and metric carries the `SIMULATED` marker, and a model trained on this data learns
the assumptions in the simulator rather than anything about real food waste. The optimiser's favourite
mixture is a property of those equations, not a recipe.

## Running it

```bash
# dependencies (this image is externally managed, hence the flag)
python3 -m pip install --break-system-packages -r requirements.txt

ruff check src tests
mypy
pytest --cov=src --cov-branch --cov-report=term-missing

# regenerate the synthetic datasets for all five seeds
python -m src.simulate_data --all-seeds --ood --outdir data/synthetic

# the study run, about 15 minutes on 2 vCPU
python -m src.evaluate --seeds 11,23,37,41,59 --n-scenarios 500 --ood-scenarios 60 --outdir results
python -m src.optimize --seed 11 --n-scenarios 500 --models dummy,ridge,random_forest,hist_gradient_boosting,mlp --perturbation-draws 200 --max-iterations 60 --population-size 15 --outdir results/optimisation
python -m src.sensitivity --seed 11 --n-scenarios 250 --models ridge,hist_gradient_boosting --max-iterations 20 --population-size 8 --perturbation-draws 20 --outdir results/sensitivity
```

Built with Python 3.11.2, numpy 2.4.6, pandas 3.0.6, scikit-learn 1.9.1, scipy 1.17.1, matplotlib
3.11.2, pytest 9.1.1, hypothesis 6.168.5, pytest-cov 7.1.0, ruff 0.16.10, mypy 2.4.0.
`.github/workflows/ci.yml` runs the same commands; it has not executed on GitHub (the permissions
check returned 403), so CI is added but unverified.

## Layout

```
src/config.py         constants, ranges, seeds, grids, constraints, provenance labels
src/simulate_data.py  the simulator, the CSV writer, a validator and a CLI
src/train_models.py   grouped split, leakage guards, the five models, tuning, saving
src/evaluate.py       five-seed evaluation, F3/F7 decision rules, importance, figures
src/optimize.py       constrained optimiser: three arms, two tiers, perturbation test, F5
src/sensitivity.py    the ten-assumption sweep, three levels each
tests/                343 tests over 14 modules, including property tests and a content guard
data/synthetic/       the committed dataset: 5 seeds x 4000 rows, plus held-out families
results/              metrics per seed, summary and held-out tables, figures, optimiser, sweep
docs/                 model notes, literature review, parameter table, references, known issues
report.md             the write-up: 12 sections, a plain-language explanation, 10 viva questions
```

## What the code does

1. **Simulator.** First-order conversion from food-waste composition through a pre-treatment step to
   methane, with declared noise, 2 % missing pH readings and 1.5 % missing temperatures so the
   imputation and leakage guards have real work to do. Constants are either sourced or labelled
   assumptions with a sweep range.
2. **Split and preprocessing.** Grouped by scenario, so all eight replicates of a scenario stay
   together and near-duplicates cannot straddle train and test. Imputers and scalers are fitted on
   the training split only. The two latent factors that generate the pre-treatment effect never reach
   the model-facing file.
3. **Models.** Exactly five: dummy mean, Ridge, random forest, scikit-learn gradient boosting, small
   MLP. Mean and spread over five seeds, next to the dummy, plus a held-out family outside the
   sampled ranges.
4. **Optimiser.** Constrained search over the mixture (fractions sum to one, hard bounds) with
   stability, ammonia, pH and retention constraints, a 5 % perturbation test on the recommendation,
   and every model prediction re-checked against the simulator at the same point.

## Limits worth reading before the numbers

- The simulator is an assumption set. Some constants come from sources, the rest are declared choices
  with sensitivity ranges.
- Feature importance describes how the simulator is built, not how a digester behaves.
- The models fail outside the sampled ranges: held-out R-squared is negative in 24 of the 25
  model-seed cells, the exception is ridge at seed 59, and every model's five-seed mean is negative.
  Report section 9.
- The declared equal-thirds baseline mixture is infeasible on this simulator, so the comparison uses
  its pre-declared feasible projection (365.8 against the oracle's 513.9).
- Nothing physical was done and nothing here is a procedure for doing it. Any real testing needs
  qualified adult supervision plus engineering and biosafety review.

## The 2025 programme

The original project description, kept for provenance. It describes the 2025 Sakura Science Exchange
Programme concept, a mechanical fermentation prototype, which was cleared for elimination and not
selected. That programme ended before any software or modelling stage, so nothing in this repository
was part of it and no data from it appears here.

> A project focused on optimizing biogas yield through predictive modeling and controlled
> fermentation. The goal is to evaluate the biogas yield of various organic substrates
> (carbohydrates, proteins, fats) and optimize the mixture ratios using a 2-stage fermentation system
> utilizing *Aspergillus oryzae*. Roadmap: sensor array calibration, baseline fermentation data,
> initial predictive model, validation against two-stage fermentation results.

That roadmap needs laboratory and hardware work. None of it is delivered here.

## Licence and disclosure

Code (`src/`, `tests/`, `.github/`, configuration) is MIT, see `LICENSE`. Written material
(`report.md`, `docs/`, `results/`, the data documentation) is CC BY 4.0, see `LICENSE-docs`.

I built this with an AI coding assistant (Arena.ai Agent Mode), which drafted code, tests and
documentation under my direction and review. The plan, the decisions and the acceptance criteria are
mine, and they were fixed before results existed. If a school or programme needs a disclosure
statement, quote this paragraph.
