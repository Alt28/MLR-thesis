# Data required for the final thesis experiment

Use recorded, traceable observations matched at the same station/route and observation period. A website or GitHub origin does not make data observational: check whether the source describes simulation or generated values. The supplied 40-row workbook explicitly describes simulated waiting times and is for prototype testing.

## Define the observation before collection

Agree on what one row means: for example, one observed waiting episode or a defined station/time interval. Specify whether actual wait is an individual duration or an interval aggregate, how its start/end are measured, and how all predictors are aligned to it. Do not mix definitions across rows without an approved modeling design.

| Required column | What must be recorded or defined |
| --- | --- |
| Traffic Condition | An independently observed/category-defined condition for that observation, with a consistent coding protocol. Avoid inferring it from the waiting-time target. |
| Weather Condition | Recorded condition for the same place/time; document its source and categories. |
| Passenger Volume | Count relevant to the same station/interval or event, with a documented counting window. A network daily total repeated in every row is not an observation-level count. |
| Route Distance | Consistent definition and unit: route length, remaining distance, or other explicitly justified measure. One fixed route may legitimately be constant; do not change it to create variation. The present quartile classifier cannot score a constant factor. |
| Vehicle Frequency | Revised protocol: observed service frequency in vehicles/hour for the same stop/route/direction during the preceding 60 minutes. Count serving events, not available fleet size. Preserve the count and window; scheduled rates belong to a separately declared experiment. See MEASUREMENT_AMENDMENT.md. |
| Time of Day | Recorded time mapped using a documented, fixed period definition. |
| Actual Waiting Time | Recorded minutes measured using the study's waiting-time definition. Synthetic target values cannot establish real-world error rates. |

Useful identifying metadata: Record ID, Station ID (or `Station`), Route, Transport Mode, Observation Timestamp, Observation Period, and Source Record Reference. Extra columns are retained as metadata; they do not automatically enter the regression. Add a consistent station identifier to obtain station summaries. Avoid unnecessary passenger-identifying information.

## Dataset checks before final evaluation

- Verify source authenticity, definitions, units, and the link between each row's predictors and target.
- Check duplicates, repeated trips/stations, and chronological dependence before choosing the split. The current implementation uses a random holdout; grouped/time-based splits need a separately agreed implementation if those dependencies matter.
- Ensure actual coverage supports the claims: bus-only observations do not demonstrate train performance. Do not simply add a Transport Mode metadata column and assume mode is modeled.
- Examine category counts, numerical variation, feature count, rank, and conditioning. No universal row count is guaranteed sufficient by this software; justify sample size against the design and number of estimable terms with the adviser.
- Decide interactions, classification rules, and evaluation protocol before examining the final test results. Do not keep changing seeds to report the best run.
- Preserve unusual valid transportation events. Correct/exclude only with independent source evidence and record the reason.
- If all routes have the same length or passenger volumes are constant, discuss the classification design. Do not fabricate variation or silently omit factors to obtain a final label.
- Independently justify operational station labels. Successful seven-score calculation alone does not validate the severity interpretation.

## Current prototype specifics

The workbook's own source notes say Passenger Volume 182,655 is a system-wide daily average, Route Distance 28 is corridor length in km, Traffic Condition is a time-of-day proxy, Actual Waiting Time is simulated, and Vehicle Frequency is 60 divided by scheduled interval (vehicles/hour equivalent). These disclosures explain why the file is useful for demonstrations but does not meet the final recorded-data requirement. Setting frequency units resolves only that unit field; it does not resolve constant factors or simulated outcomes.


The newer 200-row and 500-row demo workbooks saved in the local application also explicitly label their data prototype/synthetic in Sources_Methodology. Their extra variation is useful for testing thresholds, but increasing the number of generated rows does not turn them into independent measured observations. The application reads first-row provenance banners as well as tabular source notes.


## Labeling bus and train outputs

Include **Transport Mode** with **Bus** or **Train** for each row. For a single-mode file without a mode column, use **Set transport mode** beside the dataset, save, and analyze again. Do not label a mixed file as a single mode. Recorded row labels take precedence; missing or unrecognized labels remain Unspecified. Route, Transit Line, and Station metadata provide output context.

The regression remains one pooled model. In addition to pooled MSE/RMSE, the system reports bus and train metrics on the corresponding labeled subsets of the same held-out predictions. A single-mode researcher declaration can label a dataset without a row-level mode column; missing/unrecognized labels in a mixed dataset remain unspecified. These are subgroup metrics, not separately trained models.

When `Station ID` or `Station` is present, the held-out results also include one summary per station: the mean multi-factor score among classifiable records, classifiable/unresolved record counts, and the corresponding band label. This is a descriptive average across the station's test observations, not a time-specific station condition or an independently validated classification.
