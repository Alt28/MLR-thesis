# Manuscript alignment for station-calendar-v2

Use [the complete current methodology record](SIX_PREDICTOR_MIGRATION.md), not the historical screenshots or prototype results.

- Chapter 3 input table: replace the previous predictors with Passenger Volume, Vehicle Frequency, Station / Stop, Time of Day, Day of Week, Month of Year. Define passenger count populations, hourly serving-event frequency, local calendar conventions, and prediction-time availability. Actual Waiting Time is the measured target.
- Chapter 3 preprocessing: two numerical and four reference-coded categorical predictors; training-only fitting; preserved main effects/hierarchy; separately trained Bus and Train models; explicit unseen-category handling.
- Chapter 3 SOP 1: IQR on numerical training fields only, followed by recorded review, never automatic outlier deletion.
- Chapter 3 SOP 2: one default pairwise candidate, optional justified pairwise/higher-order terms, A/B/C evaluation on common held-out rows. A/B isolates review; B/C isolates interactions.
- Chapter 3 SOP 3: mark the revised category-score framework pending until documented approval. No station/calendar thresholds were inferred by software. Explain proposed weights and retained candidate bands and how they will be justified/validated.
- Chapter 4: present real labeled-data results only when available. Predictor-only imports have no accuracy results. Report unresolved classifications and source/coverage limits. No Enhanced advantage or IQR benefit may be claimed without the corresponding result.
- Chapter 5: distinguish implemented features from demonstrated empirical validity. Current unlabeled NYC/APC candidates do not demonstrate predictive performance.

The application's exported METHODOLOGY.md describes the exact run, including approval status, source declarations, schema, preprocessing, metrics, and limitations. Reconcile that report with the manuscript rather than copying historical example numbers.
