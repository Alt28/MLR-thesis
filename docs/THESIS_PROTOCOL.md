# Current thesis comparison protocol

Schema: station-calendar-v2. Read [the full implementation record](SIX_PREDICTOR_MIGRATION.md) for exact predictor definitions and source limits.

## Data and preprocessing

Each row must align Passenger Volume, Vehicle Frequency, Station / Stop, Time of Day, Day of Week, Month of Year, and (for supervised work) Actual Waiting Time to the same intended observation/prediction context. Keep Bus and Train datasets/models separate. Counts must be available at prediction time. A source declaration does not prove authenticity. Missing passenger waits must remain missing.

Split before fitting IQR bounds, categorical references, centering means, models, or classification numerical quartiles. Two predictors are numerical and four categorical. Reference coding uses observed training categories only. Preserve repeated observations and source IDs. Random holdout is the existing default; grouped splitting and an explicit split rationale are available. A station-grouped holdout tests unseen-station extrapolation, whose zero-contrast fallback is reported; ordinary inference rejects unseen categories. A future deployment study needs a justified temporal validation design.

## Three SOPs

- SOP 1 screens numerical training fields with IQR and records human retain/correct/exclude decisions. Never delete valid extremes just to reduce error. Arm A uses original training rows; B uses reviewed rows with the same additive specification.
- SOP 2 compares B with C on identical reviewed training rows and the same held-out observations. C adds only selected interaction blocks. Keep main effects and hierarchy. Pairwise candidates are volume x frequency, volume x time, frequency x time, and volume x weekday. The default selects only volume x frequency; no higher-order term is selected automatically.
- SOP 3 retains seven factors but leaves station/calendar mappings unscored until a documented revised framework is explicitly approved. See [classification rules](CLASSIFICATION_RULES.md). Do not interpret prediction accuracy as independent validation of station severity.

## Evaluation and reporting

All A/B/C comparisons share test IDs. Report MSE, RMSE, MAE, R2 and diagnostics honestly, including worse Enhanced results, rank deficiency, unseen categories, and negative raw predictions. A/B cannot demonstrate a review benefit when no training data changed. B/C is the isolated interaction comparison. Cross-validation remains within reviewed training data; the final test targets never determine encoding, centering, fences, terms, or category scores. Repeated CV is conditional on the chosen review and is not nested validation of the review process.

Paired tests assume a dependence structure that repeated station/time observations may violate. Report that limitation. Classification agreement uses the same six factors with actual versus predicted wait, so it is sensitivity analysis, not independently labeled operational accuracy.

In Chapter 4, keep four distinctions: IQR flags versus review changes; review effects versus interaction effects; prediction accuracy versus classification validity; software-test results versus recorded transportation findings. Chapter 5 conclusions must follow the actual dataset and evaluation results. No current unlabeled source file supports claims about learned waiting-time accuracy.

## Interface and exports

Upload > Research documentation > review interaction/split settings > Analyze Dataset > View Details / Three SOP solutions > Export Results. Labeled runs require confirmation of recorded waits and count availability. Unlabeled files use compatible saved models only, produce no accuracy metrics, and keep Actual Waiting Time blank.

Exports preserve data/source/code hashes, schema version, source notes, split membership, review audit, all three arms, training-only encoding, coefficients/diagnostics, classification approval/mappings, figures, and a generated METHODOLOGY.md. Older runs and source files remain untouched and are marked incompatible.
