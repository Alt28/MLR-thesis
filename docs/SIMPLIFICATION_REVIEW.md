# Single-page research tool revision

Reviewed 4 November 2026, before implementation. The review was presented in the conversation before code changes. This document records the review and the resulting implementation.

## Follow-up simplification: prediction first

The user's latest brief was inspected and the following review was reported before frontend edits:

1. Keep the dark theme, Transit Lab identity, readable font scale, spacing, two navigation links, upload validation, exports, and all research logic.
2. De-emphasize model comparison and actual/traditional prediction references. Reduce the dataset preview from five to three observations.
3. Collapse settings, detailed comparison, prediction errors, IQR calculations, interaction terms, coefficients, and threshold calculations.
4. Lead the results with the enhanced predicted wait as the largest value and keep observation selection available.
5. Put Station Condition immediately after the prediction; retain all seven factors and put its explanation in **View Threshold Details**.
6. Follow the condition with a compact two-row RMSE table. Keep MSE and differences in **View Analysis Details**.
7. Keep all backend scientific logic unchanged, including explicit approval and review requirements.
8. Update frontend AnalysisPage, DatasetInput, AnalysisSettings, IQRReview, AnalysisResults, StationCondition, ResearchDetails, AboutPage, and analysis.css; adapt the existing browser workflow and documentation.
9. No API or backend change is required. All 21 Python files under src/ and backend/ were verified unchanged against the previous source package.

Implementation proceeded through the input flow, result hierarchy, and verification. The normal path is **Upload > Analyze Dataset > Predicted Waiting Time > Station Condition > Optional Details > Export**. No research terms are silently approved, no flags are automatically removed, and no missing classifications are fabricated. Previously recorded review decisions remain available in Advanced Settings. Existing data and outputs remain untouched by isolated browser tests.

The numbered sections below document the earlier nine-page-to-two-page revision and its original backend orchestration change; that work is historical, not a new backend modification in this follow-up.

## 1. Previous frontend pages

The previous hash navigation exposed Dashboard, Dataset, Irregularity Detection, Interaction Terms, Model Training, Model Evaluation, Prediction Results, Station Classification, and Results Export. These were separate React page components, not separate scientific pipelines.

## 2. Previous workflow

Upload on Dataset; open another page to review IQR flags; open Interactions to apply a specification; open Classification to define severity mappings; open Training; move among Evaluation, Predictions, Classification, and Export. The researcher had to know which module came next.

## 3. Unnecessary pages

The dashboard, separate interaction editor page, training page, and separate result/export routes were unnecessary for the demonstration. An experiment switcher, page search, dashboard metrics, decorative workflow cards, and visible history navigation added complexity. Their navigation and obsolete page components were removed. Existing local research files and decision records were preserved.

## 4. Components merged

- Upload, required variables, validation, preview, and Run Analysis share the input section.
- IQR flags and retain/correct/exclude forms appear in the run flow as a dialog.
- Interaction editing, split/IQR configuration, and classification definitions are available from Analysis Settings.
- Model comparison, an inspectable prediction, and its seven-factor station condition share the results section.
- Detailed tables and charts move under Research Details. Export Results opens one export dialog.

Working tables and forms were reused and extracted into components rather than reimplementing the research algorithms.

## 5. Functionality preserved

CSV/XLSX validation; the exact six predictors and measured waiting-time target; source preservation; deterministic split; training-only IQR screening; reasoned retain/correct/exclude decisions; explicit interaction approval; all main effects; OLS for both models; identical test observations; raw-error MSE/RMSE; seven-factor explainability; undefined category scores; configurable units and severity definitions; research tables, charts, CSV/XLSX/ZIP exports; local persistence; stale-write rejection; training diagnostics; no fabricated observations or results.

## 6. Information architecture

Only Analyze and About / Methodology remain in navigation. Analyze has a dataset section on the left and results on the right on desktop; the sections stack on mobile. Dark mode remains the default. Advanced Settings and Research Details are collapsed initially.

## 7. Main workflow

Upload and validate → Run Analysis → explicitly confirm an unapplied interaction specification → review flags only when needed → Continue Analysis → compare Traditional and Enhanced MLR → inspect predictions and station conditions → Export Results.

An already approved specification is not reconfirmed. Already recorded IQR decisions are reused; the researcher can reopen the review. Unreviewed flags stay retained by default. Continuing with remaining flags requires a shared reason and explicitly records each remaining retain decision. Existing corrections and exclusions are preserved. No flags means no IQR interruption.

## 8. Backend changes

A small `POST /api/experiments/{id}/analyze` orchestration endpoint validates the revision and research confirmations, records remaining explicit retain decisions, and calls the existing training workflow for both models. Rejected confirmation requests do not mutate the experiment. The earlier endpoints remain compatible. No new database, accounts, external service, or administrative module was added.

Exports gain a `selected_interactions` table so the approved specification is retained even when a categorical term has no estimable contrast. Previously exported files are preserved; rerun an older analysis to generate the expanded workbook and CSV bundle.

## 9. Files modified

- Frontend: `src/App.tsx`, `main.tsx`, `types/index.ts`, `hooks/useExperiment.ts`, `services/api.ts`, `components/Common.tsx`, `components/DataTable.tsx`; new `analysis.css`, `pages/AnalysisPage.tsx`, `pages/AboutPage.tsx`, `components/DatasetInput.tsx`, `AnalysisSettings.tsx`, `IQRReview.tsx`, `ResearchForms.tsx`, `AnalysisResults.tsx`, `StationCondition.tsx`, `ResearchDetails.tsx`, and `services/presentation.ts`.
- Removed old frontend pages: `Dashboard.tsx`, `DataPages.tsx`, `ModelPages.tsx`, `ResultPages.tsx`, `navigation.ts`, and `components/NavigationHelp.tsx`.
- Backend: `app/api/routes.py`, `app/schemas/requests.py`, `app/services/experiments.py`.
- Export reporting: `src/export.py` adds a specification table; numerical calculations are unchanged.
- Verification/delivery: `tests/test_web.py`, `frontend/tests/browser.mjs`, compiled frontend, README, validation/design/implementation notes, preview image, source ZIP.

## 10. Files and data preserved

The numerical implementation in `src/config.py`, `data_loader.py`, `irregularity_detection.py`, `interaction_terms.py`, `mlr_model.py`, `evaluation.py`, `station_classification.py`, `experiment.py`, and `visualization.py` was left unchanged. The launcher and CLI remain available. Existing `.web-data/`, uploads, saved research runs, and `outputs/` were not used for tests or rewritten. Browser fixtures use isolated temporary storage.

## Thesis comparison and unresolved decisions

Primary source: the supplied 61-page `Raymart (2).pdf`, re-read directly for this revision. Page references below are PDF page numbers, followed by printed page numbers where applicable. The document describes the research; instructions for changing the software come from the user's revision brief.

| Thesis requirement | Implementation | Assessment |
| --- | --- | --- |
| Six transportation predictors, waiting time in minutes; Sections 1.5 and 3.1, PDF 19 and 35 (printed 14 and 30) | Same six predictors and actual waiting time | Preserved. Additional input columns remain metadata only. |
| Split before training-only IQR; Section 3.2.1, PDF 37 (32) | Fixed split, training Q1/Q3 and fences | Preserved; no test-derived bounds. |
| Correct/exclude only with justification, retain valid unusual events; PDF 37 and 48 (32 and 43) | Explicit review with reasons, no automatic removal | Preserved; streamlined UI records decisions for export. |
| Main effects plus selected pairwise/higher-order terms; PDF 38–39 (33–34) | Explicit terms, original main effects, training-derived category indicators | Preserved; no exhaustive interaction generation. |
| OLS and same held-out evaluation; PDF 39–40 and 48–49 (34–35 and 43–44) | OLS, identical test observations, MSE/RMSE | Preserved. “Traditional” is the UI name for the existing “Baseline MLR.” |
| Seven factors using the enhanced wait; PDF 40–41 and 49 (35–36 and 44) | All six predictors plus enhanced prediction | Preserved; full per-factor explanation. |
| IPO architecture; PDF 42–43 (37–38) | Dataset → analysis → results | The simplified interface directly reflects this architecture. |
| No real-time GPS/IoT, dispatch or alternative models; PDF 19 (14) | None introduced | Preserved. |

**Baseline treatment — Requires Researcher Decision.** PDF 14 (printed 9), describing Figure 1.1, says the traditional workflow has no additional preprocessing or irregularity detection. Section 4.1, PDF 51 (46), proposes assessing the irregularity-handling effect. The current system gives both models the same reviewed training rows. This is suitable for isolating interaction effects, consistent with Section 4.2's comparison, but does not separately establish IQR's effect. This mismatch was disclosed before edits. No before/after baseline or alternative experimental design was silently introduced.

**Classification details — Requires Researcher Decision.** The PDF lists seven factors and four final labels but does not fully specify equal weighting, quartile cutoffs/directions, category mappings, or numerical final-score bands. The supplied implementation briefs explicitly define the sum/7 rule, scores 0–3, wait bands 15/20/25 minutes, overall boundaries .75/1.50/2.25, and training-derived numerical thresholds. These existing explicit implementation rules were retained. The PDF should be reconciled with the final approved rules. Unmapped categories and undefined distance direction remain unresolved in the application.

**Vehicle Frequency — Requires Researcher Decision.** Table 3.1, PDF 35 (30), defines it as the number of available vehicles. The selected system protocol uses observed vehicles/hour, following the proposed measurement amendment. The application still requires a checked unit declaration; it does not infer a rate from the numeric values. Reconcile the revised measurement with the adviser-approved thesis; headway in minutes is not interchangeable with either definition.

**Other implementation decisions to document.** The PDF does not choose the split fraction/seed, a categorical contrast encoding, a route-distance severity direction, or negative-prediction handling. Existing defaults and explicit settings were preserved. Raw negative predictions stay in evaluation, while only the classification input is floored at zero. The initial interface labeled individual held-out observations. A subsequent thesis-alignment change adds an explicitly disclosed mean-score summary by `Station ID`/`Station`, with unresolved-record counts; this is a descriptive held-out-period summary, not a real-time condition.

The seven required model columns are validated. Extra columns are preserved as identifying metadata, never additional predictors. Rejecting all identifying columns would change an existing useful capability without changing the model specification.

## Incremental implementation and verification

Each of phases 1–7 passed TypeScript checking before the next phase. The new analysis orchestration passed nine API checks. Final validation includes the Python suite (53 passed), the production build, and the complete browser workflow using explicitly artificial temporary data. See `VALIDATION.md` for the final evidence and limitations.
