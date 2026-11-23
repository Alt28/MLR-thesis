# Six-predictor implementation and methodology record

**Collected-data follow-up:** The updated collector now registers 13 audited local import packages, including all 200,263 Train rows and a 6,016-row Bus source-review subset. Bus Vehicle Frequency stays blank. See [COLLECTED_DATA_IMPORT.md](COLLECTED_DATA_IMPORT.md); the initial file checks below describe the earlier candidate files.

Updated 22 November 2026. Schema identifier: `station-calendar-v2`.

The existing React/FastAPI/OLS system now uses the same six predictor names for separate Bus and Train datasets. This update changes the input definition, not the research results. No measured waiting times or accuracy results were created for the real-source files.

## Input contract

| Column | Type | Meaning / allowed values |
|---|---|---|
| Passenger Volume | Nonnegative finite number | Recorded passengers during a documented observation window. Preserve whether the source counts entries, boardings, or arrivals; these are different populations. |
| Vehicle Frequency | Nonnegative finite number | Actual recorded serving operations per hour. Neither fleet availability nor a scheduled headway is an equivalent measure. |
| Station / Stop | Categorical text | Station/stop identifier. Leading zeros in text identifiers are preserved. |
| Time of Day | Categorical text | Morning, Midday, Afternoon, Evening, Night. Source-specific clock boundaries must be documented consistently. |
| Day of Week | Categorical text | Monday through Sunday, based on the relevant local prediction timestamp. |
| Month of Year | Categorical text | January through December, based on the relevant local prediction timestamp. |
| Actual Waiting Time | Optional for preview/inference; required for training | Genuine observed passenger wait in minutes. Zero is a recorded value. Missing waits are never calculated from frequency or predictions. |

`Observed Vehicle Frequency` is accepted only as an import alias and immediately renamed to **Vehicle Frequency**. Supplying both names is rejected. Calendar case and surrounding whitespace are normalized; unknown calendar labels and numeric month codes are rejected. Station identifiers remain text, never continuous features. Additional columns are retained as metadata.

CSV and XLSX files use the same validation. Duplicate column names, missing predictor values, invalid numbers, and repeated record IDs are rejected. Duplicate-looking predictor rows are retained because the six columns can omit the true date/hour.

If present, `Observation ID` or `Source Observation ID` supplies the record identifier. An XLSX `Source_Audit` sheet can be joined by a shared unique observation ID or an explicitly exported `Six-column CSV row number`. Keys must match exactly and uniquely; the importer never joins by apparently similar predictor values. Without an audit/identifier, generated record IDs identify file rows only, not verified source events.

The upload limit remains 25 MB. Large source files need smaller, traceable extracts. Do not remove duplicate-looking records to meet that limit.

## What happens after upload

1. The normal **Upload Dataset** control validates either dataset type. Files with an omitted or entirely blank target show a preview without creating a training experiment. Partially recorded targets must be split into labeled and unlabeled files.
2. Labeled files create an experiment. Set Bus or Train and document the source, row definition, windows, and prediction time in **Advanced Settings > Research documentation**. Confirm the recorded target and input availability there. These are declarations; software cannot independently prove source authenticity.
3. The train/test split is made before learning. Reference-category encoding, numerical centering, IQR fences, and fitted rules use training observations only. Calendar and station categories have no numerical ordering. The first sorted observed training category is the reference.
4. **Analyze Dataset** fits the existing comparison arms after interaction confirmation and any IQR review. Test targets are used for evaluation only, not feature fitting or model selection.
5. For unlabeled files, select a compatible model for the same transport mode and confirm that the counts were available at prediction time. Both predictions are shown in separate columns. Actual Waiting Time remains blank and no errors, MSE, RMSE, MAE, or R2 are assigned to the uploaded rows.

Old experiments are preserved on disk. They are marked incompatible in the saved-run list and cannot be loaded into the new workflow or used for inference. New persisted models also carry the schema identifier. No old model is silently retrained or reinterpreted.

Inference rejects any station or categorical level absent from the selected model's training data. The message identifies the unsupported values. This prevents treating an unseen station as the reference station without notice. Held-out evaluation retains the existing zero-contrast fallback and exports a per-row `Unseen Categories` indicator plus a warning. Such evaluation is out-of-support for those categories; inspect it before interpreting aggregate accuracy. A station-grouped holdout therefore measures extrapolation to new stations and is not equivalent to ordinary supported-station inference.

## SOP 1: training-only IQR review

The only numerical predictors are Passenger Volume and Vehicle Frequency. Actual Waiting Time can also be screened within the training partition. IQR is never applied to Station / Stop, calendar categories, or dummy columns.

Fences are Q1 minus k times IQR and Q3 plus k times IQR, using the configured multiplier (default 1.5). A flag requests review. Legitimate high-demand observations remain unless the researcher records a source-supported correction or exclusion. The original file and held-out test observations are unchanged. A versus B isolates these recorded review decisions; if nothing changes, the system says no review benefit was demonstrated.

## SOP 2: additive and interaction models

| Arm | Training observations | Specification |
|---|---|---|
| A | Original training partition | Traditional additive MLR |
| B | Reviewed training partition | Traditional additive MLR |
| C | Same reviewed rows as B | Enhanced MLR with selected interactions |

All three arms use exactly the same test observation IDs. B versus C isolates the interaction specification. All six predictors remain main effects; reference coding means one categorical predictor can expand into several columns.

The default is one pairwise candidate, Passenger Volume x Vehicle Frequency. The picker also offers Passenger Volume x Time of Day, Vehicle Frequency x Time of Day, and Passenger Volume x Day of Week. These are hypotheses, not findings. Categorical interactions multiply the relevant dummy columns; numerical factors are centered using training means. No higher-order term is selected automatically. If a higher-order term is explicitly selected, required lower-order components are added and hierarchy cannot be disabled.

Labeled evaluation reports MSE, RMSE, MAE, R2, design rank/conditioning, coefficients, VIF, paired tests, and repeated cross-validation within the reviewed training partition. No improvement is assumed. Repeated temporal observations may violate independent-error assumptions; a random split can overstate performance. The existing grouped split is available, but a prospective chronological validation protocol is still a research/design task. The current CV evaluates the reviewed partition; it is not a nested validation of human review decisions.

## SOP 3: proposed revised framework, approval pending by default

Traffic and weather mappings and route-distance quartiles no longer apply. Automatic category-mean/OLS-effect severity mappings are disabled for all four new categorical predictors. A station ID, weekday, month, or time-period name does not inherently mean normal, minor, moderate, or severe.

The defensible proposal retained in the application is:

- Keep seven factor slots: the two numerical predictors, four categorical predictors, and Enhanced MLR predicted wait.
- Use reviewed-training numerical quartiles and documented directions as descriptive numerical components. The existing adjusted-effect or correlation direction option remains; a nonsignificant numerical effect is not proof of operational normality and that interpretation needs justification.
- Supply categorical mappings only from a documented, independently justified operational protocol, or a pre-specified training-only calibration study that is separately validated. Category means displayed in the application are descriptive evidence only and never generate scores.
- Explicitly justify any station/calendar severity ordering, reference population, weights, waiting-time bands, and treatment of unseen/rare categories. Do not rank stations by their arbitrary identifier or months by number.
- Record the rationale and explicitly approve the revised framework in **Classification definitions**. Saving proposed mappings alone does not enable them. Missing mappings or insufficient numerical variation remain unresolved even after approval.

The retained historical candidate bands are 15, 20, and 25 minutes for the predicted-wait component and 0.75, 1.50, and 2.25 for the mean of seven complete scores. They are **not newly validated operational standards**. Approval covers those bands and equal weights as well as the category mappings. No new categorical score values were invented in this update.

The four levels remain Normal Operation, Minor Delay, Moderate Delay, and Severe Delay. Until approval and complete definitions, overall classification is pending and the overall score is blank. Regression predictions and numerical prediction evaluation still work. Actual-wait-versus-predicted-wait classification agreement checks sensitivity to prediction error; it is not independent validation of the station conditions.

## Source and timing limitations

| Source | Definition that must remain visible |
|---|---|
| NYC subway | Station-complex ridership can represent estimated fare entries. Distinct departing trips across constituent platforms are not necessarily service on the passenger's platform. |
| AC Transit APC | Boardings and door events may cover only equipped buses. Partial event counts must not be presented as complete fleet frequency. Deduplication and service-event identification need source support. |
| Brazil SUNT | Repeated vehicle-presence records are not automatically distinct hourly arrivals. Identify actual service events before calling the count frequency. |

Passenger Volume and Vehicle Frequency must come from completed windows available at prediction time. Full-hour totals are unavailable at the start or middle of that hour. If the intended prediction is at the beginning of an hour, lagged counts must be constructed and matched to actual waits using explicit timestamps; changing a column label is insufficient.

When `Prediction Timestamp` (or `Passenger Arrival Timestamp`) and `Frequency Window End`, `Passenger Volume Window End`, or `Inputs Available At` are supplied, the importer rejects future-ending/invalid windows. Files containing only the six predictors cannot prove timing; the explicit availability declaration and source audit remain necessary.

Local import checks on the user's files:

- `TRAIN_NYC_6_PREDICTORS_COMPLEX_LEVEL_candidate_V2.csv`: all **200,263 rows** passed schema validation as prediction inputs. The alias was normalized. No target, training, predictions, or accuracy were created.
- `BUS_AC_TRANSIT_APC_observed_subset_SIX_PREDICTORS.csv`: the **first 10,000 rows only** passed the same schema check. The full file is **881,052,075 bytes**, above the app limit. Its manifest warns that the frequency is equipped-bus door events with possible duplicates and no vehicle IDs. Schema acceptance does not resolve that measurement problem.
- These files were read without changing the originals. Neither supplies recorded passenger waiting-time outcomes. The NYC audit includes explicit CSV row numbers; the Bus audit requires a verified observation-key match before joining, because duplicate-looking predictor rows occur.

## Readiness

The implementation supports six-predictor preview, supervised training/evaluation with recorded targets and documented single-mode inputs, and inference using compatible fitted models. The current local real-source candidates support preview only: their missing wait targets do not provide a model to train. The revised seven-factor categorical methodology remains pending until documented approval. No old-schema metrics or artificial test results establish readiness for real-world prediction.

See [validation record](VALIDATION.md) for the executed checks. Historical illustrated guides and screenshots predate this schema and must not be used as the updated method specification.

## Files modified or added

### Research core and command line

- `main.py`
- `src/config.py`
- `src/data_loader.py`
- `src/dataset_units.py`
- `src/experiment.py`
- `src/export.py`
- `src/field_collection.py`
- `src/interaction_terms.py`
- `src/irregularity_detection.py`
- `src/mlr_model.py`
- `src/station_classification.py`
- `src/transport_metadata.py`

### API and saved experiments

- `backend/app/api/routes.py`
- `backend/app/services/experiments.py`

### Frontend components and state

- `frontend/src/components/AnalysisResults.tsx`
- `frontend/src/components/AnalysisSettings.tsx`
- `frontend/src/components/CloudImport.tsx`
- `frontend/src/components/DatasetInput.tsx`
- `frontend/src/components/ResearchDetails.tsx`
- `frontend/src/components/ResearchForms.tsx`
- `frontend/src/components/ResearchProtocol.tsx`
- `frontend/src/components/SOPSolutions.tsx`
- `frontend/src/components/StationCondition.tsx`
- `frontend/src/components/TransportOutputs.tsx`
- `frontend/src/hooks/useExperiment.ts`
- `frontend/src/pages/AboutPage.tsx`
- `frontend/src/pages/AnalysisPage.tsx`
- `frontend/src/services/api.ts`
- `frontend/src/services/datasetLibrary.ts`
- `frontend/src/services/presentation.ts`
- `frontend/src/types/index.ts`

### Verification

- `frontend/tests/browser-schema-v2.mjs`
- `frontend/tests/browser.mjs`
- `tests/conftest.py`
- `tests/test_classification.py`
- `tests/test_cli.py`
- `tests/test_data_review.py`
- `tests/test_dataset_units.py`
- `tests/test_demo_library.py`
- `tests/test_experiment.py`
- `tests/test_field_collection.py`
- `tests/test_models.py`
- `tests/test_research_protocol.py`
- `tests/test_schema_v2.py`
- `tests/test_transport_metadata.py`
- `tests/test_validation.py`
- `tests/test_web.py`

### Templates and documentation

- `README.md`
- `data/transportation_template.csv`
- `data/transportation_template.xlsx`
- `docs/CLASSIFICATION_RULES.md`
- `docs/DATA_COLLECTION_GUIDE.md`
- `docs/MEASUREMENT_AMENDMENT.md`
- `docs/SIX_PREDICTOR_MIGRATION.md`
- `docs/THESIS_DOCUMENT_UPDATES.md`
- `docs/THESIS_PROTOCOL.md`
- `docs/VALIDATION.md`
- `docs/sop-guide/README.md`
- `docs/study-guide/Chapters_3_to_5_Illustrated_Study_Guide.md`
- `docs/study-guide/README.md`
- `scripts/README.md`
- `scripts/chapter_3_to_5_guide_content.md`

