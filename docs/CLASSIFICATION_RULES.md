# Revised seven-factor classification

Current schema: station-calendar-v2; classifier version 4. The full proposal, approval decisions, and interpretation limits are in [the migration record](SIX_PREDICTOR_MIGRATION.md#sop-3-proposed-revised-framework-approval-pending-by-default).

The factors are Passenger Volume, Vehicle Frequency, Station / Stop, Time of Day, Day of Week, Month of Year, and Enhanced MLR predicted waiting time. The four levels remain Normal Operation, Minor Delay, Moderate Delay, and Severe Delay.

The previous traffic/weather severity rules, route-distance quartiles, and automatic categorical OLS-effect/category-mean scores are inapplicable. No station/calendar severity is inferred. Evidence tables show training counts and means for inspection only.

Numerical quartiles are learned from reviewed training observations. Configured directions take precedence; the retained automatic numerical option uses adjusted additive coefficients or training correlations. Constant or collapsed quartiles remain unresolved. A nonsignificant coefficient is not independent evidence of normal station operations; the retained numerical rule and its interpretation require justification in the revised approval.

Categorical mappings must be explicitly specified, documented, and approved. Missing mappings stay unresolved. In Advanced Settings > Classification definitions, record the rationale and check the explicit approval control. Merely saving proposed mappings does not apply them. Changing mappings, directions, or bands in this form clears the approval until consciously renewed.

The retained candidate waiting-time bins are <=15, (15,20], (20,25], and >25 minutes, scoring 0 to 3. Negative predictions are floored only for this classification component; evaluation uses raw predictions. Once all seven factors resolve and the framework is approved, the score is their equal-weight mean. Scores below 0.75 are Normal Operation; [0.75,1.50) Minor Delay; [1.50,2.25) Moderate Delay; [2.25,3] Severe Delay. These historical candidate thresholds are not newly validated standards.

Without approval or a complete set of factors, the overall score remains blank and the condition is pending. Regression training, predictions, and genuine-target accuracy evaluation continue independently.

Station / Stop groups observation scores into descriptive station summaries. Unresolved counts remain visible. Comparison of labels using actual versus predicted waits measures sensitivity to prediction error, not operational classification accuracy against an independent ground truth.

## Automatic category scoring (default since classification version 5, 24 November 2026)

`category_scoring = "automatic"` (the default) scores every Station / Stop, Time of Day, Day of Week and Month of Year category 0–3. The score comes from the category's **mean actual wait in the reviewed training data**, compared with the training actual-wait quartiles: ≤ Q1 = 0 Normal, (Q1, Q2] = 1 Minor, (Q2, Q3] = 2 Moderate, > Q3 = 3 Severe. Test observations are never used. Approved manual mappings take precedence. Categories with no training observations stay unresolved. With all seven factors scored, the Multi-Factor Station Score and Station Condition are produced without a separate approval step.

Select `category_scoring = "manual"` in **Classification definitions** to return to the previous behaviour: only explicitly approved researcher mappings are used. Results saved under version 4 are marked stale; run **Train & evaluate** again.

Thesis wording: *"Categorical factors were scored by the quartile position of their mean training-set waiting time."* This is a data-driven, descriptive rule. It is not an independently validated measure of station condition.
