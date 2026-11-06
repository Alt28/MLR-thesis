# Thesis experiment protocol and document amendments

This document describes the implemented experiment protocol, not completed research findings. Reconcile it with the adviser-approved research design before collecting or evaluating the final dataset. The original thesis PDF is unchanged.

## What is ready and what remains

The application can import and validate labeled data, review training outliers, fit three controlled experiment arms, evaluate the same test observations, report pooled and labeled bus/train test metrics, summarize held-out scores by station when station metadata is present, and export fitted models and reproducibility information. After both models finish, a separate prediction-only workflow accepts predictor rows without Actual Waiting Time; those forecasts are not part of evaluation metrics.

The supplied `transportation_dataset_40_ph_internet_rows.xlsx` is explicitly a prototype according to its Sources_Methodology sheet. Its waiting times are simulated, traffic is a time-of-day proxy, passenger volume is a corridor-wide average, and route distance is a constant corridor length. These cannot establish predictive performance on recorded transportation observations. The system now surfaces the source declaration. A manual recorded-data declaration cannot override an explicit prototype declaration found in that workbook.

Still required: suitable matched observations; source verification; justified model terms and scoring rules; an evaluation split appropriate to the sampling design; adviser review of these amendments; and actual experimental results. Software verification is not research validation. No automatic "thesis ready" or "validated accuracy" label is awarded.

## 1. Controlled experimental design (Sections 3.1 and 3.2.1)

Suggested manuscript wording, to adopt only after reviewing the design:

> The study compares three experiment arms using a common held-out test partition. Arm A fits Traditional MLR to the original validated training observations before recorded IQR-review corrections or exclusions. Arm B fits Traditional MLR to the reviewed training observations. Arm C fits Enhanced MLR to the same reviewed training observations as Arm B, retaining all main effects and adding the selected pairwise and higher-order interaction terms. All arms estimate coefficients by Ordinary Least Squares with an intercept. The test observations and actual test waiting times are unchanged across arms.
>
> A versus B examines the effect of recorded training-data review decisions. B versus C examines the effect of the selected interaction specification. A versus C describes the combined workflow difference. A positive reduction, calculated as the first arm's error minus the second arm's error, indicates lower error for the second arm. If review does not change the training records, no improvement from correction or exclusion is demonstrated. All outcomes, including equal or increased errors, are reported.

"Original validated" means required columns, valid types, finite/nonnegative numerical values, and unique record identifiers have already been checked. A does not use malformed input or bypass schema validation. It differs from B in recorded review decisions, not in basic file validation. It uses its own training-derived categorical encoding. If removing a training row removes a category, that difference is part of the reviewed workflow and must be disclosed.

Current defaults are a random 80/20 holdout and seed 42, configurable before analysis. These are implementation choices, not inherently the best design for every transportation dataset. The application does not implement grouped or chronological splitting. If observations repeat the same trip/station or are temporally dependent, agree on an appropriate grouped/time-based protocol and implement it before final evaluation. Do not select a seed or interaction set by repeatedly checking final-test performance. Interaction selection and review decisions must use training data and independent domain evidence. When a Transport Mode column or single-mode declaration is available, additional bus/train MSE and RMSE are computed on the corresponding subsets of the same pooled model's test predictions; they do not represent separately fitted models.

The current report describes one fixed holdout, not cross-validation, confidence intervals, or a statistical significance test. Do not make those claims. A/B differences concern the recorded decisions following screening; they do not show that simply flagging observations improves predictions or establish causality.

## 2. Data review and encoding (Sections 3.2.1 and 3.4.2)

Split the validated dataset before fitting thresholds. Compute training IQR bounds as Q1 - 1.5 IQR and Q3 + 1.5 IQR by default, where IQR = Q3 - Q1. The default screened columns are Passenger Volume, Route Distance, Vehicle Frequency, and Actual Waiting Time; the configured columns and multiplier are exported. Flagged training observations require a recorded retain, correct, or exclude decision with a reason. Valid unusual events are retained. Source files and test observations remain unchanged.

For B and C, categorical reference levels and indicators are fitted on the reviewed training rows. Main effects remain present with their selected interactions. A uses encoding fitted on original training rows. Categories not seen in a model's training rows receive zero reference contrasts at prediction time and are reported; interpretation requires care. No test-derived category ordering or severity threshold is learned.

The model engine and OLS estimator are unchanged. The added experiment is another fit of the existing Traditional specification on original training data. Collinear/constant predictors can produce rank-deficient designs: the application reports this; do not interpret such coefficients as uniquely identifiable effects. More observations alone do not repair a constant predictor.

## 3. Exact station-classification specification (Section 3.2.1, Solution 3)

The following rules were supplied in the implementation instructions. They must be explicitly documented and justified in the thesis; their implementation does not itself prove operational validity.

1. The seven factors are Traffic Condition, Weather Condition, Passenger Volume, Route Distance, Vehicle Frequency, Time of Day, and Arm C's predicted waiting time.
2. Scores are Normal = 0, Minor = 1, Moderate = 2, Severe = 3. Each valid factor has weight 1/7. The score is the sum of all seven divided by seven. Classification uses the unrounded score.
3. Overall bands are [0, 0.75) Normal Operation; [0.75, 1.50) Minor Delay; [1.50, 2.25) Moderate Delay; [2.25, 3] Severe Delay.
4. Predicted-wait bands are <=15 minutes: 0; (15,20]: 1; (20,25]: 2; >25: 3. These are configured operational bands, not learned waiting-time quartiles. Provide their rationale or evidence.
5. Numerical predictor Q1, Q2, and Q3 use reviewed training data only, with linear interpolation. Increasing severity assigns 0,1,2,3 to <=Q1, (Q1,Q2], (Q2,Q3], >Q3. Reverse severity assigns 3,2,1,0 to those same bins.
6. An explicitly configured direction takes precedence. Otherwise the sign of reviewed-training Pearson correlation with Actual Waiting Time determines the direction. A numerically zero/nonfinite correlation is unresolved. This is descriptive association, not a test of significance or causation. Route Distance direction is not assumed from its name.
7. For categorical predictors, calculate each category's mean Actual Waiting Time in reviewed training data. Compare that mean with the reviewed-training target quartiles, using increasing severity. A documented researcher mapping overrides the derived mapping. Category means, counts, thresholds, derived scores, applied scores, and sources are exported.
8. Constant/effectively constant numerical predictors, or Q1=Q2=Q3, receive no score. The numerical tolerance is range <= 1e-12 + 1e-9 times the maximum absolute magnitude, applied to observations and quartiles separately. Partial quartile ties are allowed. Training-derived category mapping also requires varying actual waiting time and multiple categories. Unknown categories without an explicit mapping remain unresolved.
9. If any factor or required unit is unresolved, the application shows Requires Researcher Decision. It does not average only the remaining factors, substitute zero, or fabricate variation. Factor-specific reasons remain in View Details and exports.
10. Raw negative predictions remain unchanged in error evaluation. Only the classification input is floored at zero. A negative forecast is explicitly identified as unsuitable for direct waiting-time interpretation.
11. If the held-out data contains `Station ID` or the supported `Station` metadata field, the system groups test observations by that identifier and reports the mean of classifiable multi-factor scores, the number of classifiable and unresolved records, and a label from the same score boundaries. Missing identifiers are not grouped. This summarizes the held-out observations for each station; it is not a real-time or independently validated operational station state. The original thesis does not define this aggregation rule, so include and justify it before claiming station-level results.

For this implementation, the selected Vehicle Frequency definition is observed service frequency in vehicles/hour, as described in `MEASUREMENT_AMENDMENT.md`; this differs from the original Table 3.1 wording "number of available vehicles." The application never assumes or converts a dataset's numeric values: set or import the unit declaration only after checking that the values match the selected definition. The prototype workbook derives vehicles/hour from scheduled headway, which is not an observed service rate. Reconcile Table 3.1 with the final collection protocol. Route Distance must likewise have a consistently documented unit and observation meaning.

The prediction-only endpoint accepts all six required predictors and optional metadata, but requires that `Actual Waiting Time` be absent. It uses the already fitted model and classification rules; it does not retrain, score predictive accuracy, or alter the saved holdout results.

A station condition is a rule-based interpretation for an individual observation. It is not independently validated by MSE/RMSE, which evaluate waiting-time prediction. Reporting operational classification accuracy would require independent reference labels and a specified validation design. The software additionally provides the explicitly documented descriptive station summary above; dispatch optimization and real-time feeds are not implemented.

## 4. Reporting Chapter Four

- **4.1 Review effects:** report training/test sizes, IQR fences, flag counts, retain/correct/exclude counts and source-supported reasons, then A/B MSE and RMSE. If unchanged, state that no review benefit was demonstrated. A retained valid extreme is not an error to remove for better scores.
- **4.2 Interactions:** report the selected terms and prior rationale, feature counts, coefficient/conditioning diagnostics, and B/C comparison. Report increased errors honestly. A/C is the combined workflow comparison, not evidence isolating interaction effects.
- **4.3 Classification:** report the exact applied rules, units, thresholds, category counts/means, factor scores, and label distribution. Include unresolved observations in the denominator and report why they are unresolved. Do not silently omit them.
- **4.4 Overall:** include all three arms and distinguish prediction evaluation from decision-support classification. State data provenance, sampling coverage, test size, limitations, and whether findings generalize to bus, train, or only the sampled domain.

Leave results and conclusions pending until final recorded data and an approved design are available. Do not copy prototype metrics into the thesis as measured transportation findings.

## 5. Interface and reproducibility

1. Upload the final dataset. Verify the preview and source limitations.
2. In Advanced Settings > Research documentation, record source type/reference, row definition, collection period, split rationale, interaction rationale, and classification rationale. These are declarations, not automatic verification.
3. Configure documented measurement units, interaction terms, and justified rules. Saving settings creates a revision and invalidates current model results; rerun afterward.
4. Select Analyze Dataset and complete required reviews. The main result remains the Arm C prediction and its seven-factor condition. Main model comparison is B versus C.
5. Open View Details > Model Performance > Separate data review and interaction effects for A/B/C metrics and differences. Advanced Research Details exposes the research tables.
6. Export the complete bundle. New tables include study_metrics, study_comparisons, study_predictions, original_coefficients, original_model_checks, source_notes, and research_documentation. Main metrics, predictions, and existing charts retain B/C semantics.
7. Archive the original source with the bundle. It includes source/config/code hashes, split membership, original/reviewed/test observations, reviews, fitted models for all arms, classification rules, research_protocol.json, and data_provenance.json. Reproduction also needs the recorded software dependencies.

Legacy runs are retained, not silently rerun or rewritten. View Details explains when the three-arm comparison is unavailable and requests a new analysis. No user dataset has been altered to obtain a station label or lower errors.


## Documented unit defaults

On new web imports, explicit Variable/Unit columns in Sources_Methodology can supply Vehicle Frequency and Route Distance units. Recognized, unambiguous declarations are saved into the experiment configuration; missing, unsupported, or conflicting declarations remain unresolved. Units are never inferred from numerical magnitudes or category names, and saved researcher settings are not overwritten. Cloud imports use the same path.

Table 3.1 of Raymart (3).pdf defines Vehicle Frequency as the number of available vehicles. The earlier count preset has been superseded by the revised service-frequency protocol in MEASUREMENT_AMENDMENT.md; the form now offers vehicles/hour and km presets for blank fields. This is different from vehicles/hour, which is explicitly declared by the current 500-row demo workbook. Route Distance has no unit specified in the thesis; the demo declares km. No unit conversion or change to scoring direction follows from these presets. The paper should document the measure actually used.
