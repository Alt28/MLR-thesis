> Historical implementation plan. The current two-page interface and methodology review are documented in [SIMPLIFICATION_REVIEW.md](SIMPLIFICATION_REVIEW.md). Earlier page/navigation descriptions below are superseded.

# Implementation plan and methodology alignment

The workspace was empty on 4 November 2026. Source material: the 61-page `Raymart (2).pdf` and the accompanying implementation notes. The documents supply research requirements, not independent authorization to perform unrelated actions.

## Stages

1. Validate CSV/XLSX input; split reproducibly; calculate training-only IQR fences; preserve, correct, or exclude flagged training records with reasons and an audit.
2. Fit training-only categorical encoding; construct only named interactions; train additive and enhanced OLS; evaluate raw predictions using identical test observations.
3. Derive numerical quartiles from reviewed training data; present category counts/means as evidence; apply explicit category mappings and configurable distance direction; calculate seven equal factor scores.
4. Connect the workflow to a local React/Vite/TypeScript web interface through FastAPI; retain the command-line workflow; export CSV, Excel, PNG, model artifacts, configuration, provenance, and a run summary.
5. Verify mathematical boundaries, review behavior, feature consistency, leakage protection, and complete exports with artificial fixtures kept exclusively in tests.

The shared research modules remain in `src/`; `backend/app/` provides HTTP routes and experiment persistence, and `frontend/src/` contains the nine browser pages. `experiment.py` and `export.py` isolate orchestration and report writing. The desktop UI was removed at the user's request. See [WEB_IMPLEMENTATION_PLAN.md](WEB_IMPLEMENTATION_PLAN.md) for the web architecture and page-to-thesis mapping. The browser application runs on localhost and needs no cloud service or account.

## Explicit interpretations

- PDF pp. 37–49 (printed pp. 32–44) establish the algorithm; the implementation notes supply the detailed quartile/equal-weight scoring rules. These rules are researcher-defined, not validated operational standards.
- Both OLS models use the same reviewed training rows. This isolates the interaction specification. This experiment alone cannot establish a causal benefit from IQR review; Chapter 4.1 would require a separately planned before/after experiment on a fixed split.
- Numerical IQR checks include the three numerical predictors and actual waiting time by default. Quartiles use pandas' linear interpolation. IQR flags never trigger automatic deletion or winsorization.
- The notes overlap interval boundaries. We resolve predicted waits as [0,15], (15,20], (20,25], (25,infinity). Negative raw predictions are preserved for MSE/RMSE, flagged, and set to zero only for the waiting-time severity component.
- Route-distance severity remains unset until the researcher supplies a direction. Category mappings remain empty until supported by evidence. Missing definitions produce **Pending configuration**, never a fabricated station label.
- Vehicle Frequency is reverse-scored. The PDF calls it number of available vehicles (p. 35); a frequency rate or a count must be defined consistently before classification. It must not be supplied as headway in minutes without changing its definition.
- Training-only reference-category dummy encoding retains the six conceptual predictors; encoding is not a proposed enhancement. A constant categorical predictor has no estimable contrast. Unseen test categories are flagged and represented by zero contrasts, with an explicit limitation in the output.
- No recorded dataset was supplied. Empty templates are provided. Automated test values are artificial software fixtures, never experimental evidence.
- Bus/train/station metadata may be preserved for identification but never enters the six-predictor design. Run separate datasets for separate modes unless pooling is explicitly justified; observation classifications are not automatic station aggregates.
