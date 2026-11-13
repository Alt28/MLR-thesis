# Training-derived station classification

Implemented from the user's explicit classification brief on 5 November 2026. This supersedes the earlier requirement for manual-only categorical mappings; it does not change either MLR model or the current page design.

## Inspection before changes

The previous classifier already applied training-only numerical quartiles, increasing/reverse scoring, 15/20/25-minute waiting-time bands, equal seven-factor weighting, and the four final bands. It calculated training category means as evidence but did not use them for scores. Route Distance required a configured direction. It did not reject constant numerical quartiles. The saved prototype configuration had no category mappings, no Route Distance direction, and no Vehicle Frequency unit.

The affected files are the classifier, classification configuration, export evidence, backend summary compatibility, existing classification/settings explanations, and regression tests. MLR fitting, interaction construction, evaluation, splitting, IQR review, and the visual stylesheet remain unchanged.

## Learning and precedence

All learning uses the reviewed training partition after corrections/exclusions. Test observations and their actual waiting times never determine mappings, correlations, or thresholds.

- Numerical factors use their training Q1, median/Q2, and Q3 with pandas linear interpolation.
- A configured numerical direction takes precedence. Otherwise the sign of training Pearson correlation with Actual Waiting Time determines the direction: positive means higher severity for higher values; negative means the reverse. A nonfinite or numerically zero correlation remains unresolved. New configurations use automatic direction; existing saved choices remain configured choices.
- Pearson direction is descriptive association in this training sample, not proof of causation, significance, stability, or operational validity. No unsupported significance cutoff is imposed. Researchers can explicitly configure a direction with documented rationale.
- Each categorical training group uses its mean Actual Waiting Time, compared with the training target's Q1/Q2/Q3. Explicit category overrides take precedence. Both the derived candidate and applied score/source are retained. A category seen only in test data has no generated score; an explicit configured mapping can cover it without inventing a training mean/count.
- Generated categorical scores require variation in training Actual Waiting Time and at least two observed categories for the factor. A single training category cannot establish a learned category effect. A documented configured mapping is distinguishable from this learned rule.
- Enhanced predicted waiting time retains the fixed 15/20/25-minute bands. Raw negative predictions stay in evaluation; the established zero-floor rule remains limited to classification.

Increasing quartile scoring uses <=Q1: 0, (Q1,Q2]: 1, (Q2,Q3]: 2, >Q3: 3. Reverse scoring is 3 minus that score. Categories use increasing mean-wait severity. Every valid factor contributes exactly 1/7. Final bands are [0,.75), [.75,1.50), [1.50,2.25), [2.25,3].

## Station-level reporting extension

When held-out records include `Station ID` or `Station`, the system groups by that metadata value and reports the mean of classifiable seven-factor scores, the total/classifiable/unresolved record counts, and the same configured overall band for the mean. Rows with empty station identifiers are counted as ungrouped; unresolved records are counted but excluded from the mean. This describes the held-out observations grouped by station. The thesis PDF does not define this aggregation, and the result is not a time-specific station condition or validated operational classification.

## Required measurement units

Updated 13 November 2026. A station condition requires a documented unit for both measured numerical predictors: Vehicle Frequency and Route Distance. While either declaration is blank, every observation keeps the Pending configuration status, the Multi-Factor Station Score stays empty, and the reason explicitly names the missing unit. The applied declarations are stored in `classification_rules.json` under `measurement_units` and exported with the run.

This is a documentation requirement, not a conversion: the application still never infers or rescales values from a unit label. Earlier runs saved before this rule retain their stored results; rerun Analyze Dataset after declaring the units to obtain labels under the current rule.

## Variation safeguard

A numerical factor cannot receive a score if it is constant/effectively constant or Q1/Q2/Q3 all collapse. A configured direction cannot bypass this check. Values and quartiles are tested separately using range <= 1e-12 + 1e-9 * maximum absolute magnitude. These are documented numerical-resolution tolerances, not minimum scientifically important differences. Partial quartile ties are allowed; unoccupied severity bins are not manufactured.

Training correlations require usable predictor/target variation. Correlations of absolute magnitude <=1e-12 are treated as numerical zero. Missing factors stay missing; there is no imputation, rescaling over the remaining factors, fabricated threshold, or automatic Normal label. The existing measurement-unit requirement is preserved.

## Prototype audit

File: `transportation_dataset_40_ph_internet_rows.xlsx`. Existing default split: 32 training and 8 test observations; no IQR flags. Reviewed training therefore equals original training for this inspection.

| Factor | Training evidence | Result |
| --- | --- | --- |
| Passenger Volume | All 32 values and Q1/Q2/Q3 = 182655 | Insufficient Variation for Classification |
| Route Distance | All 32 values and Q1/Q2/Q3 = 28 | Insufficient Variation for Classification; direction cannot be inferred |
| Vehicle Frequency | Q1 = 6.666667, Q2 = 8.571429, Q3 = 12; Pearson r approximately -0.356405 | Reverse direction is supported descriptively; units still need documentation |
| Traffic, Weather, Time of Day | Multiple training categories and variable actual waits | Category scores can be generated |
| Enhanced prediction | Existing model output | Fixed waiting-time severity applies |

Training Actual Waiting Time quartiles: **8.98, 14.93, 23.9375 minutes**. Example generated mappings: Traffic Light = 1, Moderate = 2, Heavy = 3; Weather Clear = 1, Cloudy = 1, Heavy Rain = 3. These come from observed training means, not assumptions about category names. They are descriptive results for this prototype split, not independently validated transportation rules.

The prototype cannot yield a complete seven-factor condition, even after its frequency unit is documented. Correctly varied, appropriately recorded observations are required for Passenger Volume and Route Distance; changing a direction or supplying an arbitrary score does not fix absent variation.

## Reproducibility and saved results

The fitted classifier stores mappings, direction sources, correlations, statuses, target quartiles, and method version. The workbook/CSV category_evidence and severity_thresholds tables expose the evidence. classification_rules.json and the manifest record the learned rules separately from explicit config.json overrides; models.joblib preserves the fitted classifier.

Version-1 results are hidden from the current summary until Analyze Dataset is run with version 2. Their saved predictions and export folders are retained. This prevents presenting old classifications alongside newly learned evidence. The main interface remains three results and two actions; missing-factor explanations appear only in View Details.
