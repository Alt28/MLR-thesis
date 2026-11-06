# Software validation

Verified on 4 November 2026 using Windows, Python 3.13.7, Node.js 22.19.0, Microsoft Edge, and the versions recorded in `requirements-lock.txt` and `frontend/package-lock.json`.

## Controlled thesis protocol revision (5 November 2026)

- Full Python suite: **79 passed**. The existing non-failing Starlette HTTPX transport deprecation warning remains.
- Production TypeScript/Vite build and complete isolated browser workflow passed.
- A/B/C checks verify equal test rows, original-model independence from review decisions, reviewed-row exclusions, exact metric calculations, and no claimed review improvement when training data is unchanged. Test-target perturbation cannot alter fitted coefficients.
- Provenance checks cover unknown/recorded/simulated declarations, conflicting recorded declarations, and first-row prototype banners. Read-only inspection identifies the supplied 40-row workbook and newer 200/500-row demo workbooks as prototype data.
- Models, comparisons, source declarations, and protocol metadata survive exports and state restoration. Research-note saving preserves unchanged interaction approval and existing review decisions; the JSON-list/Python-tuple comparison regression is covered.
- Browser checks exercise research documentation, source notices, controlled comparisons, three-arm tables, and the existing review, prediction, classification, drag-to-scroll, export, persistence, keyboard, and responsive flows.
- Existing local saved runs were loaded read-only after the initial server restart. They are retained without silently rerunning analyses. Legacy results explain how to generate the added protocol outputs.
- OLS, feature construction, IQR review rules, and seven-factor scoring are retained. An original-training Traditional fit is added as a documented experiment-design extension.
- Artificial test fixtures establish software behavior, not final thesis accuracy or real-world operational validity.

## Earlier classification revision (5 November 2026)

- Full Python suite: **70 passed**. One existing Starlette HTTPX transport deprecation warning is non-failing.
- Production TypeScript/Vite build and complete isolated browser workflow passed.
- New tests cover all four derived categorical bands, configured overrides, unseen categories, training-only mappings and target quartiles, positive/negative/zero numerical relationships, constant/effectively constant variables, collapsed quartiles with outliers, single-category/constant-target limitations, and reviewed-row exclusions.
- Learned mappings, sources, statuses, and quartiles survive workbook/JSON/model-artifact exports. A restored classifier produces identical classifications.
- A legacy saved result is marked stale without overwriting its stored predictions or exported files. A fresh analysis applies the new version.
- Browser checks confirm generated Weather scores, inferred Route Distance direction, configured category overrides, selected-observation updates, and insufficient-variation explanations inside View Details only. Review, downloads, navigation, keyboard focus, persistence, and mobile checks still pass.
- The supplied 40-row prototype was inspected and analyzed in memory: 32 training rows, 8 test rows, no IQR flags. Passenger Volume and Route Distance are constant and remain unscored. No experimental source data was modified.
- MLR fitting, feature construction, evaluation, data splitting, and IQR review source files were compared byte-for-byte with the previous source package and are unchanged. No stylesheet or page-layout changes were made in this revision.

## Earlier result-summary revision


- Production build and complete isolated browser workflow passed.
- The default result has exactly the three requested headings and two actions. Tests verify that traditional comparison, actual values, factor scores, thresholds, and IQR calculations are absent until View Details opens.
- Enhanced RMSE matches the saved metric rounded to two decimals. Undefined rules remain unresolved. Full metrics, seven-factor scores, training quartiles, and classification bands remain available in the details dialog.
- Observation selection updates the main result and the open breakdown. Nested prediction and details dialogs restore keyboard focus correctly, including on mobile.
- The existing upload, approval, retain/correct/exclude review, no-flag flow, invalidation, chart, export, and persistence checks still pass without JavaScript exceptions.
- Populated desktop and mobile screenshots were visually inspected. The existing 13-14 px supporting text scale is retained. All fixtures remain isolated from user data.
- All 21 Python files under src/ and backend/ are byte-identical to the previous source package; no research calculations or API behavior changed.

## Earlier simplification: prediction-first results

- TypeScript checks passed after the input-flow and result-hierarchy changes. The final production build passed.
- The complete isolated browser workflow passed after the final changes, including reopening previously recorded review decisions from Advanced Settings.
- New assertions verify three preview rows, collapsed settings, prediction/condition/performance order, the enhanced prediction's visual priority, hidden classification bands and full metrics until expanded, and the four-column threshold table.
- Displayed RMSE and expanded MSE match the server results. Selecting another observation updates the enhanced prediction, final condition, score, and all seven severity rows. Missing definitions remain unresolved.
- Existing tests still cover explicit interaction approval, IQR retain/correct/exclude, invalidation, CSV/XLSX input, exports, refresh persistence, keyboard focus, and desktop/tablet/mobile overflow. No JavaScript exceptions occurred.
- Desktop and mobile populated screenshots were visually inspected. Test fixtures use temporary isolated storage, never the user's research workspace.
- All 21 Python files under `src/` and `backend/` match the previous source package byte-for-byte. No new backend/API changes or research-algorithm changes were made. The existing local server was checked to serve the new compiled frontend.

## Earlier single-page revision

- `.venv\Scripts\python.exe -m pytest -q`: **53 passed**.
- `npm.cmd run build` in `frontend/`: TypeScript and production Vite build passed.
- `npm.cmd run test:e2e` in `frontend/`: complete browser workflow passed against the compiled frontend and an isolated real FastAPI server.
- Phases 1–7 passed TypeScript checks before proceeding. The combined analysis action passed all nine API integration checks before final browser verification.
- Nine scientific modules were compared byte-for-byte with the pre-revision source ZIP and were unchanged: config, data loading, irregularity detection, interaction construction, MLR fitting, evaluation, station classification, experiment execution, and visualization. `src/export.py` adds only a selected-interaction specification table.

The Python tests use deliberately artificial fixtures. There is one non-failing Starlette TestClient deprecation warning about its HTTPX test transport. These checks establish software behavior, not predictive accuracy on recorded transportation observations.

## Station Condition presentation revision

- The production frontend build and complete isolated browser workflow passed after this revision.
- Targeted regression checks: `pytest tests/test_classification.py tests/test_experiment.py -q` — **30 passed**, including severity boundaries, seven-factor scoring, and training-only threshold behavior.
- Browser assertions cover the seven factor rows, five breakdown columns, missing mappings with no fabricated score, saved training quartiles, approved categorical mappings, all waiting-time and overall classification bands, the seven-score average, and summary rounding.
- Selecting another observation updates the enhanced wait, condition, score, and all seven severity rows while retaining an open breakdown. A fixture whose combined condition differs from its waiting-time severity confirms that the UI displays the combined classifier output.
- Desktop and mobile breakdown screenshots were visually inspected; the mobile table scrolls within its container without widening the page. Fixtures remain isolated from research data.
- This revision changes the frontend explanation and presentation only. Python scientific modules and backend behavior are unchanged.

## Scientific and API checks

The subsequent readability revision also passed the production build and existing complete browser workflow, including desktop/tablet/mobile overflow checks. Populated desktop and mobile Station Condition screenshots were visually inspected after increasing typography and contrast. This revision changes CSS only.

The suite covers schema validation, CSV/Excel handling, deterministic train/test separation, IQR calculations and zero-IQR cases, retention/correction/exclusion audits, source-bound review validation, selected pairwise and higher-order terms, categorical interaction blocks, consistent training/test feature columns, unseen categories, OLS coefficients, MSE/RMSE, every severity boundary, reverse frequency scoring, explicit category mappings, configurable distance direction, equal seven-factor scoring, negative predictions, and missing definitions.

A leakage test changes only held-out predictors, categories, and targets, then confirms that coefficients, learned encoding, training category evidence, and severity quartiles remain unchanged. Export tests cover the workbook, CSV tables, model artifact, manifest, and figures. CLI checks exercise inspection, configured analysis, and empty-template rejection.

API checks cover invalid/corrupt uploads, original baseline/enhanced training endpoints, interaction approval, stale revision rejection, invalid configuration without mutation, result invalidation, persisted review decisions, result restoration, and chart/CSV/XLSX/ZIP delivery. Dark preview pixels and light downloaded figure pixels are checked separately.

The new analysis endpoint is checked for missing approval, unconfirmed IQR flags, missing retention reasons, and stale writes. Rejected requests do not change approval, revision, or review decisions. A complete run preserves an existing exclusion, retains only explicitly confirmed remaining flags with their reason, and exports those decisions without inventing category mappings.

## Browser checks

The revised test covers:

- Exactly Analyze and About / Methodology navigation, no sidebar, and no invented empty-state metrics.
- Dark mode and the locally bundled font.
- Missing-column validation; valid CSV and XLSX upload; basic preview and full-dataset search.
- Explicit interaction confirmation, adding a chosen term, and leaving other suggestions unchecked.
- IQR correction, exclusion, and default-retain confirmation with a shared reason; persisted decisions verified through the API.
- One-action training of both models; displayed MSE checked against the server result.
- Undefined classification labels, explicit category/unit/direction settings, result invalidation, and rerunning without unnecessary review interruptions.
- Seven factor rows, displayed score equal to their sum divided by seven, and selection of another prediction to inspect.
- Traditional/enhanced prediction and error columns; selected-interaction research table; loaded dark Matplotlib figures.
- Excel, CSV, and complete-bundle downloads; restoration after refresh.
- Invalid replacement files blocking analysis until the earlier valid dataset is explicitly restored.
- Desktop, tablet (1024 px), and mobile (390 px) layouts; no page-level horizontal overflow; dialog Escape and keyboard-focus return, including selecting a prediction on desktop.
- An XLSX dataset with no IQR flags proceeding directly from interaction confirmation to completed results.
- No JavaScript page errors.

The browser test uses temporary artificial fixtures and isolated storage, and stops its own server afterward. It never uploads fixture data to the user's research workspace. Empty desktop, populated desktop, and mobile screenshots were visually inspected. `web-preview.png` shows the empty interface; fixture screenshots are excluded from the source package.

## Research limitations

Collect appropriate recorded data, justify the interaction specification and classification definitions, and settle measurement units before reporting actual results. The implemented comparison uses identical reviewed training rows for both models and therefore isolates interaction effects; it does not separately measure the IQR effect proposed in thesis Section 4.1. The PDF does not fully specify category mappings, numerical directions, or every classification rule. See `SIMPLIFICATION_REVIEW.md` for the disclosed mismatches and items labeled Requires Researcher Decision. Software tests do not establish operational validity of the station thresholds.


## Guided Analyze UX revision

- Production TypeScript/Vite build passed.
- Complete isolated browser workflow passed, including CSV/XLSX uploads, researcher confirmation, unusual-observation review, both models, station conditions, observation switching, exports, persistence, and no-flag analysis.
- New assertions verify single/multiple missing-column guidance; disabled analysis during confirmation and processing; a loading indicator with no fake percentages; Summary, Model Performance, and Prediction Details in order; and Advanced Research Details collapsed with no coefficient table mounted initially.
- Existing seven-factor scores, saved training thresholds, category evidence, insufficient-variation states, and displayed evaluation metrics still agree with backend outputs.
- Desktop, tablet, and mobile overflow checks, animated dialog dismissal, nested keyboard-focus restoration, and reduced-motion behavior passed. Desktop/mobile result screenshots and the initial details dialog were visually inspected.
- All 21 scientific/backend Python files were compared byte-for-byte against the preceding source package and are unchanged. No research calculations or saved user datasets were altered. The current change is frontend presentation and interaction feedback only.
- Browser fixtures use temporary isolated storage; these checks do not establish predictive accuracy on real transportation data.


## Grab-to-scroll tables

Production build and the complete isolated browser workflow passed. New real mouse/keyboard checks verify that dragging left reveals right-hand prediction columns, dragging right moves back, releasing restores the grab cursor, dragging does not select a record, and arrow keys scroll the focused table. The subsequent observation-button selection and desktop/mobile checks continue to pass. Backend calculations are unchanged.


## Result placement and motion revision

The production build and full isolated browser workflow passed. Updated checks exercise Choose Observation and View Predictions from the main result panel, return keyboard focus to their respective triggers, and verify selected ID, waiting time, station condition, and detailed factor scores after choosing a different record. Drag-to-scroll and all export/research-table checks still pass. The result reveal animation is present during normal motion and disabled for reduced-motion users. Desktop/mobile screenshots were visually inspected; responsive overflow checks passed. All 21 scientific/backend Python files remain identical to the previous packaged version.


## Transport output revision (5 November 2026)

- Full Python suite: **82 passed**, with the existing non-failing Starlette HTTPX deprecation warning.
- Production TypeScript/Vite build and complete isolated browser workflow passed.
- Tests cover per-row labels, single-mode declarations, unknown labels, metadata precedence, filtering before pagination, and unsupported filters. Adding transport metadata leaves fitted coefficients, predictions, and metrics unchanged.
- Browser checks verify Bus/Train selection, repeated active-filter clicks, matching prediction rows, no fabricated output for an absent mode, and desktop/mobile layout. Screenshots were visually inspected.
- Transport labels filter existing predictions only. Global evaluation, six-predictor MLR, review rules, and station classification are unchanged. Artificial fixtures are not thesis evidence.


## Cloud import revision (5 November 2026)

- Full Python suite: **100 passed**, with the existing non-failing Starlette HTTPX deprecation warning. Production build and complete isolated browser workflow passed.
- Controlled HTTP responses exercise Google file links/resource keys, personal OneDrive short links, download redirects, filenames, denied access, HTML sign-in pages, unsupported hosts/schemes/ports, empty files, size limits, and redirect limits.
- API tests confirm existing column validation, unapproved/untrained initial state, and preservation of the prior dataset on failure.
- Browser checks exercise the cloud dialog, actionable failure, retry, normal upload validation, and clearing an earlier rejected-upload state after successful import. Existing training/classification/export checks still pass.
- No live user sharing link was provided. Provider behavior is verified with isolated responses, not a live Google/Microsoft account. Some sharing links require authentication or download confirmation and are intentionally rejected with local-upload guidance.
- No MLR or station-classification calculations changed.


## Dataset layout cleanup (5 November 2026)

Production TypeScript/Vite build and the complete isolated browser workflow passed. Desktop/mobile views were visually inspected, including long filenames, stacked mobile import controls, validation and source notices, prediction results, and the cloud-import dialog. File/cloud import, preview access, research settings, training, classification, exports, keyboard focus, and responsive overflow checks remain working. This revision changes frontend presentation only; backend calculations are unchanged.


## Driving bus animation (5 November 2026)

Production build and full isolated browser workflow passed. Tests confirm the bundled bus image loads, road transforms change during loading, the scene is decorative, reduced-motion preferences disable scene animation, mobile has no page overflow, and the scene disappears on completion. Test-only response control makes the pending state observable without delaying real analyses. Desktop/mobile loading screenshots were visually inspected. Backend calculations are unchanged; the MIT asset license is included in the build.

## Automatic loading animation (6 November 2026)

The Play/Pause control and saved motion preference were removed. The bus, wheels, and road autoplay during analysis, including when reduced motion is enabled. The browser test verifies that no animation toggle is shown and that all three elements continue moving. Analysis timing and backend calculations are unchanged.


## Documented unit defaults (5 November 2026)

Full Python suite: **102 passed**, with the existing non-failing Starlette HTTPX deprecation warning. Production build and full isolated browser workflow passed. Unit tests cover recognized workbook declarations, conflicting/unsupported/missing units, no inference from prose, saved defaults, and persistence of researcher edits. Existing classification calculations remain unchanged.

For the active 500-row demo, previously blank units were set from its explicit workbook declarations (vehicles/hour and km) through the revision API. Existing configuration, approvals, and review decisions were preserved; the rerun completed with 100 classified test observations. These remain synthetic demonstration results. Automatic approval review blocked the local server restart, so future-import defaults require a manual restart; the updated current-run results are already available.


## Station condition in View Predictions

Production build and full isolated browser workflow passed. Added assertions verify that Station Condition and Multi-Factor Score occupy the first result columns and match the saved backend classification and score in both Bus and Train views. Existing seven-factor averaging, threshold bands, missing-definition behavior, observation switching, drag scrolling, exports, and responsive checks still pass. The prediction dialog screenshot was visually inspected. Backend calculations are unchanged.

## Measurement revision and Philippine source preparation (6 November 2026)

- Full Python suite: **114 passed**, with the existing non-failing Starlette HTTPX deprecation warning. Production TypeScript/Vite build and complete isolated browser workflow passed.
- Explicit preparation helpers validate serving-event counts and observation windows, convert counts to vehicles/hour, and separately convert scheduled headway seconds to scheduled frequency. They are not silently applied to imported data or model fitting.
- The empty collection workbook's explicit unit declarations are recognized as vehicles/hour and km. Research settings offer these revised study presets without overwriting existing units or changing numeric values.
- The MRT-3 PDF extraction contains 121 calendar days, including four unfilled source days. Extracted entries and exits match each of the four published monthly totals. The report is a third-party-hosted copy and still requires agency verification for final research use.
- The historical Sakay GTFS preparation preserves all 1,864 frequency records through validated joins; derived rates use the documented headway seconds. The source calendar ends 30 June 2020. These are historical schedules, not observed service arrivals.
- Both supporting CSV tables are rejected by normal dataset validation because the required aligned predictors and measured waiting-time target are absent. No real-data MLR performance claim is made.
- OLS fitting, interactions, IQR decisions, training-only classification thresholds, seven-factor scoring, and existing user experiments are unchanged by this revision. Software verification does not establish thesis or operational validity.

## Searchable dataset picker (6 November 2026)

- Inspected the public reference application's Select Cloud Files dialog: a searchable server-hosted case list. Adapted that interaction using Transit Lab's own dark styling, icons, and components; no reference-site files or source code were copied.
- The picker now lists two explicitly synthetic 180-row Bus/Train workbooks, with search, empty state, selectable cards, loading feedback, and disabled controls while loading. Google Drive/OneDrive sharing-link import remains available in a separate view. Local hosting is disclosed instead of claiming an external cloud-account connection.
- Two new isolated Python tests passed: each bundled workbook goes through the existing upload, researcher-confirmation, training and seven-factor classification pipeline. Prototype provenance and units survive; these tests do not assert real-world model validity.
- Production TypeScript/Vite build and complete isolated browser workflow passed. New checks cover both library files, search and no matches, failed-download preservation, retry, busy/close guards, source labels, units, and normal unapproved initial state. Existing cloud-link import, analysis, classification and exports continue to pass.
- Desktop/mobile dialog screenshots were inspected. The cards use short transitions and respect reduced-motion preferences. Research/model code and saved user experiments are unchanged.


## Direct cloud file-list revision (6 November 2026)

The Import Cloud Files button now opens Cloud: Transportation Datasets directly, without provider tabs or a sharing-link form. Files show their names, synthetic labels, observation counts and Select action. Production build and full isolated browser workflow passed; live desktop/mobile checks confirmed the direct picker, empty-search guidance and absence of provider controls without changing any user dataset. The server-based library and existing research pipeline are unchanged.


## Earlier workbooks and researched files in the picker (6 November 2026)

The library contains seven files: two generated 180-row demos, three unchanged earlier 500/200/40-row prototype workbooks, and two Philippine reference CSVs. Source copies are checksum-verified. Reference entries show limitations, source links and download actions without importing incomplete inputs. The historical GTFS license is bundled.

Seven targeted Python tests passed, covering both demo analyses, source declarations and units for earlier workbooks, and rejection of incomplete reference inputs by the normal validator. Production build and full isolated browser workflow passed, including reference download preservation, search, earlier-500 import and existing analysis/export flows. Live read-only checks verified all added files are served and reference headings/mobile layouts display correctly. No research calculations or saved user experiments were changed.


## Direct automatic library import (6 November 2026)

Every dataset card now submits its file through normal upload validation immediately. The reference-download screen and download actions were removed. Complete files close the picker and become the active dataset; incomplete Philippine references show actual missing-column messages and preserve the active experiment. Production build and the full isolated browser workflow passed. Browser tests assert zero download events across valid demo imports and invalid reference attempts. No backend research calculations were changed.


## Visible bus motion and explicit playback control (6 November 2026)

The loading bus now travels horizontally, with rotating DOM wheel spokes, suspension and road motion. Wheel animation was moved out of the image so all motion obeys the same playback control. Play/Pause persists per browser; absent a choice, reduced motion is respected. Explicit Play only overrides motion suppression inside this scene. Production build and full isolated browser workflow passed, including actual transform changes for the bus, road and wheels; default reduced motion; explicit opt-in; pause of all scene parts; and saved playback choice. Desktop/mobile screenshots were inspected. No research calculations or artificial loading delays were introduced.

## Thesis-alignment workflow additions (6 November 2026)

- Full Python suite: **124 passed**, with the existing non-failing Starlette HTTPX transport deprecation warning. The TypeScript/Vite production build and complete isolated browser workflow passed.
- Pooled MSE/RMSE remain unchanged; additional bus/train metrics match manual calculations on the same held-out model predictions and are exported as `mode_metrics`.
- When `Station ID` or `Station` metadata is supplied, the result/export includes mean classifiable held-out score by station, plus test, classifiable, and unresolved record counts. Missing identifiers are reported as ungrouped; unresolved records are never assigned a score.
- After training completes, a prediction-only upload accepts predictor columns without Actual Waiting Time, returns both model predictions and the enhanced-factor classification, and does not change model fits or evaluation metrics. Labeled prediction-only uploads are rejected.
- The downloadable transportation template now includes optional Station ID. The collection/template field does not enter model features.
- These software additions do not alter the attached thesis PDF or establish that the revised measurement and classification choices are adviser-approved.
