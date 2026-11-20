# Transit Research Lab

A locally hosted web application for **Enhancement of Multiple Linear Regression Applied to Train and Bus Wait-Time Prediction with Threshold-Based Station Classification**. React + Vite + TypeScript provide the browser interface; FastAPI runs the existing Python research engine. The desktop application has been removed. The command-line research workflow remains available.

**Status:** implemented for controlled thesis experiments. The supplied 40-row workbook declares simulated waiting times and repeated corridor-level context values. It is a prototype dataset, not final thesis evidence; no real-world accuracy claim is made. First use opens with an empty analysis page; later visits restore the last dataset used in this browser.

## Deploy an online demo
https://mlr-sigma.vercel.app/ (system webapp)

The web interface can be hosted on Vercel with its Python API on Render. The deployed demo is public and does not require a login. Everyone can access the same workspace and data, so do not upload confidential, identifying, or sensitive research data.

1. In Render, create a **Blueprint** from this repository. The `render.yaml` service runs on Render's free instance and allows writes from the configured Vercel production domain.
2. In Vercel, connect the same GitHub repository, set **Root Directory** to `frontend`, and deploy with the detected Vite settings (`npm run build`, output `dist`). `frontend/vercel.json` proxies `/api` requests to the Render service.
3. Open the Vercel deployment.

The free Render instance can sleep when idle and uses temporary storage. Experiments, uploaded datasets, and results may be deleted when the instance sleeps, restarts, or is redeployed. Use this only for a temporary demonstration; persistent thesis work requires a paid backend with persistent storage and a backup plan. The API is public, and all visitors share the same data.

## Start on this computer

Double-click **`Start MLR System.bat`**. Your browser opens **http://127.0.0.1:8000**. Keep the server window open while using the app; press Ctrl+C in that window to stop it. The local Python environment, frontend dependencies, and compiled web interface are already installed on this computer.

Or, in PowerShell from this folder:

```powershell
& '.\.venv\Scripts\python.exe' main.py
```

On another Windows computer, install Python 3.12 or later, then run `powershell -ExecutionPolicy Bypass -File .\setup.ps1`. Node.js 22.12 or later is needed to rebuild the frontend; the source ZIP also includes compiled `frontend/dist` assets, so Python alone can serve that included build. Setup downloads dependencies; ordinary use works offline. `requirements-lock.txt` and `frontend/package-lock.json` record tested dependencies.

For a trusted local-network demonstration, run `main.py web --host 0.0.0.0 --no-browser` and visit `http://<server-LAN-address>:8000` from another device. Windows may require a private-network firewall rule. This local thesis implementation has no login or user separation; do not expose it to the public internet. The default launcher binds only to this computer.

![Empty web workspace](docs/web-preview.png)

The interface opens in dark mode with charcoal surfaces and mint accents. Tables, forms, dialogs, and chart previews use the same palette; downloaded figures retain light backgrounds for thesis reports. After updating an already running installation, stop the server with Ctrl+C, reopen the launcher, and refresh the browser with Ctrl+F5.

Navigation contains **Analyze** and **About / Methodology**. The main Analyze page keeps dataset input on the left and results on the right, stacking them on smaller screens. Advanced settings, classification explanations, and research details expand when needed. The dark theme and bundled local font work offline.

During analysis, the bus automatically moves across its scene with rotating wheels and a moving road. The animation has no play/pause control and continues regardless of the device's reduced-motion preference. Results still appear as soon as analysis finishes, with no artificial delay.

## Illustrated SOP guide

The [PDF guide](docs/sop-guide/System_SOP_1_to_3_Illustrated_Guide.pdf) and [editable Word guide](docs/sop-guide/System_SOP_1_to_3_Illustrated_Guide.docx) explain the three SOP solutions with actual application screenshots, click-by-click instructions, and a defense walkthrough. [Full-resolution screenshots](docs/sop-guide/assets) are included. The screenshots use artificial software test records to demonstrate features; their values are not recorded transport findings.

## Dataset library and cloud import

Select **Dataset Library** beside Upload Dataset to open **Dataset library on this server**. The current library contains one 500-row workbook with 250 Bus and 250 Train labels. Its observations are synthetic software examples, not recorded research evidence; its source declarations and units remain in the workbook and Dataset source notes. Selecting it creates a new experiment and preserves previous experiments; it does not bypass research confirmations or train automatically.

The dataset card imports directly into Transit Lab. Successful validation closes the picker and updates Transportation Dataset; select Analyze Dataset when ready. Incomplete MRT-3 ridership and transit schedules are no longer offered in the picker. Their source information remains in `docs/PHILIPPINE_DATA_SOURCES.md`.

The dialog is a direct file list: search, select, load. It has no provider tabs, account connection, or sharing-link form, and it does not reach any cloud storage service. To use your own file, download it from your storage account if necessary and select **Upload Dataset**. The existing shared-link backend endpoint remains for compatibility, but is not part of this interface.

Files retain the 25 MB limit and required-column validation. Failed imports preserve the previous dataset.

Explicit units in a workbook's **Sources_Methodology** sheet (Variable and Unit columns) now fill in automatically on import. Ambiguous or absent units remain editable in Classification definitions. The revised study presets use **vehicles/hour** and **km**, after values are checked or converted. See [measurement amendments](docs/MEASUREMENT_AMENDMENT.md) and the [Philippine data review](docs/PHILIPPINE_DATA_SOURCES.md).

## Using the analysis tool

**Import Dataset > Analyze > View Result**

For mode-specific evaluation, provide a **Transport Mode** column containing **Bus** or **Train**. For a single-mode file without this column, use **Set transport mode** beside the dataset, save, and analyze again. Missing labels stay unspecified. The system reports pooled metrics and additional bus/train metrics on the matching subsets of the same test predictions; it still fits one pooled model.

1. Choose or drop a CSV/XLSX dataset using **Upload Dataset**. Templates are available beside the upload control. Actual Waiting Time can be recorded, entirely blank, or omitted. Recorded waits show **6 predictors + recorded waiting time** and a preview; blank waits show **6/6 predictors detected**. Both use the same **Analyze Dataset** button and **Analysis Result** panel.
2. Click **Analyze Dataset**. An unapproved interaction specification requires an explicit researcher confirmation once. **View configured interaction terms** reveals that specification; **Advanced Settings** allows editing it. Existing approvals are reused when valid.
3. If unusual observations require review, the app opens **Review unusual observations**. Retain, exclude, or correct a row with a reason. Retain is the default; **Continue Analysis** records the shared reason for remaining retained observations and preserves existing corrections/exclusions. No observation is automatically deleted. Previously recorded decisions can be reopened from **Advanced Settings**.
4. **Analysis Result** shows the enhanced **Predicted Waiting Time**, the selected observation's **Station Condition**, and **Enhanced MLR RMSE** in minutes. The primary panel does not show research tables or factor calculations. RMSE is the square root of the mean squared test error: it is expressed in minutes and weights larger errors more heavily than a plain average error. It is not a confidence percentage.
5. Open **View Details** to inspect actual and predicted values, the Traditional/Enhanced MLR comparison, MSE/RMSE, errors, IQR information, interactions, coefficients, and charts. **View Predictions** on the main result opens the table for the active All / Bus / Train filter; selecting a row updates the main prediction and condition. **View Threshold Details** inside this dialog reveals the seven-factor explanation, training-only quartiles, score calculation, and classification bands.
6. Undefined classifications remain **Requires Researcher Decision**. View Details identifies missing definitions or insufficient variation. Provide justified rules/units through **Advanced Settings**, or import appropriate varied recorded data for constant factors, then analyze again. The interface never invents a classification to fill the summary.
7. **Export Results** remains beside View Details and offers the Excel workbook, CSV tables, **Methodology as implemented (.md)**, and the complete reproducibility ZIP. The dark palette, compact typography, navigation, and backend methodology are preserved.

With Actual Waiting Time entirely blank or omitted, **Analyze Dataset** uses the current saved trained models; if the current dataset is not trained, it selects the most recent saved completed run when available. **Model used for predictions**, below the upload control, shows the selected source and lets you change it. Traditional and Enhanced forecasts appear side by side in **Analysis Result** and can be downloaded with Actual Waiting Time left blank. No prediction errors, MSE, or RMSE are assigned to these rows. Fitted models and evaluation metrics remain unchanged. A `Station ID` or `Station` column enables descriptive station summaries: mean score over classifiable rows plus unresolved counts. The scoring disclosure explains all seven factors for a selected forecast. There are no separate home-screen modes or prediction upload controls.

Prediction files are validated even when no trained model is available, but no forecasts can be calculated until both models have been trained on recorded waits. Mixed files containing both known and unknown targets are rejected with instructions to split them; zero is a recorded wait, never a missing-value marker. All six predictors remain required. Prediction uploads are held in the current browser session and do not create training experiments; download the results before leaving or refreshing the page.

**Three SOP solutions**, below the workspace, gives each problem its own explanation, live status, and evidence button:

- **SOP 1:** training-only IQR limits, flagged observations, review decisions and reasons; A vs B isolates recorded data-review changes.
- **SOP 2:** the selected interactions, retained six main effects, fitted coefficients and diagnostics; B vs C isolates interactions on identical reviewed training and test records.
- **SOP 3:** observation-level seven-factor scoring, threshold explanations, unresolved factors, and available station summaries.

The panel distinguishes implementation from evidence of improvement. Equal or worse errors are reported as such. Its evidence belongs to the selected training/evaluation run, not the newly uploaded unknown waits.

The first two configured interactions are thesis examples and require explicit approval. Settings changes clear the current results; rerun the analysis afterward. Already reviewed flags and an approved specification are reused when still valid. Changing the split or IQR screening can reset review decisions. Source data remains unchanged, and the held-out observations are not corrected or excluded through the review interface.

Each training upload is saved separately under `.web-data/`. The last selected dataset is restored across browser refreshes and server restarts. Previous research files remain on disk; **Model used for predictions > Saved model dataset** lets you select them after uploading blank waits, and **View saved model analysis** returns to that run's training data and evaluation results. Export results for an easily accessible copy. Conflicting writes and predictions requested with an outdated model revision are rejected. Stop the server before backing up `.web-data/`.

The UI calls the additive model **Traditional MLR**. Existing research files use **Baseline MLR**, and their **Pending configuration** label corresponds to **Requires Researcher Decision**. Old saved exports remain intact; rerun older analyses to include the newly added selected-interaction table in their workbook/CSV bundle.

The [revision review](docs/SIMPLIFICATION_REVIEW.md) records the original pages, merged components, preserved logic, thesis comparison, and unresolved methodology. The baseline-review design and classification rules not explicitly specified in the PDF require researcher/adviser review before making corresponding thesis claims.

## Dataset contract

| Exact column | Type | Meaning |
| --- | --- | --- |
| Traffic Condition | Category | Observed traffic category; consistent spelling |
| Weather Condition | Category | Observed weather category |
| Passenger Volume | Nonnegative number | Number of passengers in a defined observation window |
| Route Distance | Nonnegative number | Distance in a consistent unit, documented in config |
| Vehicle Frequency | Nonnegative number | Observed service frequency in vehicles/hour under the revised collection definition; verify and declare the actual input unit |
| Time of Day | Category | Defined observation period |
| Actual Waiting Time | Nonnegative number | Observed waiting time in **minutes** |

Do not enter headway in minutes as Vehicle Frequency: these are different measurements. The original thesis Table 3.1 says "number of available vehicles," while the selected system protocol uses observed service frequency in vehicles/hour. This amendment must be reconciled with the adviser-approved thesis. The application does not infer or convert units; verify and declare them for each dataset. Automatic severity direction follows the reviewed-training relationship; configured directions are preserved.

Missing/invalid predictors are rejected with an explanation. Actual Waiting Time is the target, not a seventh predictor: it is required for training and evaluation, and may be entirely blank or omitted for prediction. The program does not impute or create observations. Training requires at least 10 rows to create a usable split; this is a software minimum, not a justified thesis sample size. Substantially more observations are needed to estimate multiple coefficients reliably. Prediction accepts one or more valid rows and uses existing trained models.

Optional metadata such as `Record ID`, `Station ID` (or `Station`), or `Transport Mode` is preserved, **never used as extra predictors**. Station identifiers enable a mean-score summary over classifiable held-out observations; unresolved rows are counted, not assigned scores. This is a descriptive summary for the test period, not a real-time or independently validated station condition. Supplied Record IDs must be unique and nonempty. If absent, the app generates row-position IDs. Keep the source file and its row order unchanged when reusing review decisions. Bus/train metrics are subsets of the same pooled model, not separate mode-specific fits.

## Configuring the experiment

Research defaults are in `src/config.py`. The web forms save per-experiment snapshots without editing those defaults:

- Test fraction and random seed: 0.20 and 42.
- Evaluation split: `random` by default. Set `split_method` to `grouped` (Advanced Settings > Split & IQR settings) to keep every observation of one station identifier inside a single partition. `split_group_column` is blank by default and resolves `Station ID`, then `Station`. Grouped splitting needs a value on every row and at least two distinct groups, and the test fraction then applies to the groups, so partition sizes can differ from the requested fraction. Record the reason for the selected split in Research documentation.
- IQR multiplier: 1.5. Default checks cover Passenger Volume, Route Distance, Vehicle Frequency, and Actual Waiting Time. Remove the target from `IQR_COLUMNS` if your approved protocol limits screening to predictors.
- Initial interaction specification: Passenger Volume × Vehicle Frequency; Passenger Volume × Vehicle Frequency × Time of Day. These come from the supplied examples and require your research justification. No exhaustive search is performed. With `hierarchical_interactions` (default `True`, the hierarchy principle) each selected higher-order term also brings in its missing lower-order interaction components, here Passenger Volume × Time of Day and Vehicle Frequency × Time of Day; they are marked "Added for Hierarchy" in the coefficient and specification tables.
- Interaction centering: `center_interactions` is `True` by default. Numerical factors are centered at their training means before interaction products are formed (main effects stay in original units), which reduces multicollinearity between main effects and interactions. Because the hierarchy principle keeps every lower-order term, centering only reparametrizes the model: predictions and the highest-order coefficients are identical with or without it. Turning hierarchy off while centering is on changes what a higher-order term can represent and is not recommended. Both switches are in Advanced Settings > Split & IQR settings.
- Cross-validation: `cv_folds` 5 and `cv_repeats` 10 (Advanced Settings > Split & IQR settings). Repeated k-fold runs only inside the reviewed training partition; a grouped split also keeps station groups together in every fold.
- Automatic severity rules (`severity_basis`, default `adjusted`): an additive OLS fit on the reviewed training rows measures each factor's effect with the other five held constant. Numerical directions follow the sign of that coefficient; categories score 0 for the most favourable and 3 for the least favourable category of a factor, proportionally in between. A factor whose partial F-test p-value is at least 0.05 has no detectable effect and scores 0 everywhere. This avoids misleading raw relationships, such as more vehicles appearing to lengthen waits only because more vehicles run during crowded peaks. Set `severity_basis` to `marginal` to use raw category means against waiting-time quartiles and Pearson correlation signs instead (Advanced Settings > Classification definitions).
- Category dictionaries and configured numerical directions are optional explicit overrides and always take precedence. The learned mapping, adjusted effect, p-value, thresholds, source, and status are saved separately from configuration. Unseen test categories remain unresolved unless explicitly configured. If the additive fit is unusable (rank-deficient or too few rows), the marginal rules are used and labelled as such.
- Vehicle Frequency and Route Distance units start empty. Both must be documented before any final station label is issued; until then every observation stays **Requires Researcher Decision** and names the missing unit.
- Include optional `Station ID` (or `Station`) metadata for station-level summaries. The generated transportation template includes `Station ID`.
- Waiting-time thresholds and combined-score thresholds are explicit and configurable.

For a frozen or shared run, `main.py run` accepts an exported `config.json` via `--config`. That snapshot overrides the Python defaults for that run; it does not modify `config.py`.

## Methodology details

See [Classification rules and prototype audit](docs/CLASSIFICATION_RULES.md) for the current training-derived rules, variation safeguards, and saved-result compatibility. After updating the backend, restart the server and select **Analyze Dataset** to update an older saved classification. Old exported bundles remain historical artifacts.

Both model specifications use scikit-learn `LinearRegression`, with an intercept and ordinary least squares. The main B/C comparison uses reviewed data; the extra A baseline uses original training records. Both use **the same reviewed training observations** and are evaluated against the same untouched test observations. IQR fences are learned from the original training partition; encoding and classification quartiles are learned from the reviewed training partition. Test values never set the fences, category ordering, or numerical thresholds.

Categorical predictors use training-only reference-category dummy encoding. The alphabetically first observed training category is the reference. Category ordering for encoding is unrelated to severity. For a selected interaction involving a category, each of its non-reference indicator columns is multiplied with the other selected predictor columns. Two categorical factors produce the Cartesian product of their respective contrast blocks. A constant category has no estimable contrast. Every estimable main-effect column is retained.

Categories seen only at test time get zero contrasts and an explicit `Unseen Categories` flag. This is a reference-category fallback, not a learned estimate for that new category. Review this limitation before interpreting those predictions. Missing severity mappings leave classification pending. No test category means are used to resolve it.

Quartiles use pandas linear interpolation. For increasing severity, scores are 0, 1, 2, 3 at `x <= Q1`, `Q1 < x <= Q2`, `Q2 < x <= Q3`, and `x > Q3`. Reverse scoring is `3 - score`. Partially tied quartiles can leave some severity bins empty. If all three quartiles collapse or the variable is constant/effectively constant, its score is missing and its status is **Insufficient Variation for Classification**, even if a direction is configured. No average over fewer than seven factors is produced.

Predicted waiting-time scores are:

| Wait used for classification | Severity |
| --- | --- |
| 0 through 15 minutes | 0 |
| More than 15 through 20 | 1 |
| More than 20 through 25 | 2 |
| More than 25 | 3 |

The notes overlap the endpoints; these intervals explicitly assign each boundary once. A negative OLS prediction is flagged. Its raw value is retained for errors/MSE/RMSE; a separate zero-floored value is used only for station classification. Error is **actual minus predicted**.

The six predictor scores and enhanced waiting-time score are summed and divided by seven. Scores `[0,.75)`, `[.75,1.5)`, `[1.5,2.25)`, and `[2.25,3]` correspond to Normal Operation, Minor Delay, Moderate Delay, and Severe Delay. These are researcher-defined decision-support rules, not validated operational standards or an independently trained classifier. A missing component never becomes a fabricated Normal label.

Both measured numerical predictors require a documented unit: Vehicle Frequency and Route Distance. While either unit is blank, every observation remains **Requires Researcher Decision**, and the reason names the missing unit. The application never infers or converts a unit from the values.

MSE improvement is baseline minus enhanced; negative improvement means the enhanced model is worse. Percentage improvement is undefined when the baseline error is zero. MAE (mean absolute error, minutes) and held-out R² (1 − SSE/SST on the test rows, which can be negative) are reported alongside MSE and RMSE; the recorded conclusion still follows MSE. Rank, residual degrees of freedom, conditioning, and variance inflation factors (VIF; above 10 means strong multicollinearity) are diagnostics. The coefficient table adds classical OLS standard errors, t statistics, two-sided p-values, and 95% confidence intervals; they assume independent, constant-variance errors. Coefficients express conditional model associations, not causal effects. Interaction figures show one term's fitted contribution over observed training interaction values, not the full predicted wait. Residual plots (actual − predicted against predicted) are exported for both models.

The default fixed random split implements the supplied notes. Correlated observations from the same vehicle, journey, station, or adjacent times can make random-split accuracy optimistic, and a completed run reports when the same station identifier appears in both partitions. A grouped split by station identifier is available and recorded in `research_protocol.json` as `grouped_holdout`; selecting it is a methodological decision to justify in the manuscript, and it does not remove dependence between observations inside one group. Chronological splitting is still not implemented. Choose the observation unit and sampling design before claiming generalization. Repeatedly selecting interactions using held-out performance also compromises the test set: fix the specification before evaluating a final test split.

The main comparison is B vs C and isolates interaction specification. Each new complete run additionally fits an original-data Traditional baseline (A). A vs B examines recorded corrections/exclusions; A vs C examines the combined workflow. All three use the same untouched test rows. No changed training records means no demonstrated review benefit.

Statistical checks (View Details > Model Performance > Statistical checks, and the `heldout_significance`, `cv_*`, and `classification_*` tables):

- Paired tests on the held-out rows: the Wilcoxon signed-rank test and the paired t-test on per-observation squared errors for B vs C, A vs B, and A vs C (α = 0.05). They do not model dependence between rows from the same station or period.
- Repeated k-fold cross-validation of B vs C inside the reviewed training partition. Encoding, centering means, and coefficients are re-fitted in every fold; recorded review decisions are kept. The MSE difference across folds is tested with the corrected resampled t-test of Nadeau and Bengio (2003), which accounts for overlapping training folds.
- Classification agreement: every test row is classified with its actual wait and with the Enhanced MLR predicted wait (the other six factors unchanged), giving exact agreement, within-one-level agreement, Cohen's kappa, and a confusion matrix. This measures how prediction error changes the station condition; it does not validate the thresholds operationally.

These checks describe variability within the supplied dataset only and are not causal or real-world validity claims.

See [THESIS_PROTOCOL.md](docs/THESIS_PROTOCOL.md) for exact methods and manuscript amendments, [THESIS_DOCUMENT_UPDATES.md](docs/THESIS_DOCUMENT_UPDATES.md) for the section-by-section manuscript edits that align the paper with this implementation, and [DATA_COLLECTION_GUIDE.md](docs/DATA_COLLECTION_GUIDE.md) for observation-level requirements. Record source information and research rationales in **Advanced Settings > Research documentation**. The additional comparisons appear in **View Details > Model Performance > Separate data review and interaction effects**. Old saved runs remain available; rerun Analyze Dataset to produce the new protocol outputs.

## Command-line usage

```powershell
# Empty templates
& '.\.venv\Scripts\python.exe' main.py template

# Training-only inspection before modeling
& '.\.venv\Scripts\python.exe' main.py inspect 'data\recorded.csv'

# Experiment using config.py
& '.\.venv\Scripts\python.exe' main.py run 'data\recorded.csv'

# Reproduce an explicitly configured experiment
& '.\.venv\Scripts\python.exe' main.py run 'data\recorded.xlsx' --config 'path\config.json' --reviews 'path\review_decisions.json'

# Verification
& '.\.venv\Scripts\python.exe' -m pytest -q
```

Download review decisions from **Export Results ? Other formats & reproducibility files**, or edit the `decisions` dictionary in the review bundle produced by `inspect`. Keep its identifying hashes intact. The dictionary is keyed by flagged training `Record ID`. Each entry contains `action` (`retain`, `exclude`, or `correct`), a nonempty `reason`, and, for corrections, a `corrections` object mapping exact column names to verified values. The CLI rejects a bundle from a different source file, training split, or IQR screening and validates that every referenced record is flagged and belongs to training.

## Export contents

Completed web analysis runs are stored under `.web-data/<experiment-id>/runs/<run-id>/`; CLI runs use `outputs/`. Each complete run contains:

- `experiment.xlsx` and `csv/`: predictions, individual factor scores, labels, metrics (MSE, RMSE, MAE, R²), differences, coefficients with standard errors/p-values/95% intervals, interaction coefficients, interaction centering means, VIF, paired significance tests, cross-validation folds/summary/significance, classification agreement and confusion matrix, selected interaction specifications, IQR flags/fences, review audit, training-only category evidence, severity quartiles, encoding references, model diagnostics, exact split membership, original/reviewed training rows, original test rows, and warnings.
- `figures/`: actual/predicted and residual plots for both models, MSE and RMSE comparisons, cross-validation MSE boxplot, classification distribution (including pending labels), classification agreement matrix, IQR counts, and selected interaction contributions.
- `config.json`: research parameters and explicit overrides.
- `METHODOLOGY.md`: methodology as implemented for that run — dataset and provenance, split design with fraction/seed/group column, IQR fences and review decisions, encoding and selected interaction terms, OLS arms A/B/C with metrics and comparisons, classification units/quartiles/mappings/bands, label distribution with unresolved counts, environment, and recorded limitations. Use it to write Chapters 3 and 4; see [THESIS_DOCUMENT_UPDATES.md](docs/THESIS_DOCUMENT_UPDATES.md).
- `classification_rules.json`: learned category mappings, applied numerical directions, training waiting-time quartiles, methodology version, and numerical tolerances. The workbook and CSV evidence tables include means, sources, statuses, and assigned scores.
- `review_decisions.json`: reusable decisions bound to the source-file hash and training/IQR fingerprint.
- `manifest.json`: source-file hash, config hash, source-module hashes, environment versions, row counts, warnings, and comparison conclusion.
- `models.joblib`: fitted OLS models, encoding rules, classifier thresholds, and run metadata. Only load your own trusted Python model artifacts.
- `SUMMARY.md`: observed comparison and limitations.
- Web runs additionally include `web_experiment.json` (revision, dataset name, interaction approval, configuration/review history) and `experiment-bundle.zip`.

Spreadsheet formula prefixes in text fields are escaped in CSV/Excel; numerical predictions remain numeric. Unique raw observations and source files are preserved. Keep the source-code version alongside the bundle: hashes establish identity but are not a copy of the code.

## Project layout

```text
main.py                       Web server / CLI entry point
Start MLR System.bat          Windows launcher
setup.ps1                     Installation helper
requirements*.txt            Dependencies and tested versions
data/                         Empty collection templates
outputs/                      Unique experiment bundles
models/                       Optional researcher-managed model storage
src/config.py                 Explicit research parameters
src/data_loader.py            Validation and fixed split
src/irregularity_detection.py  Training IQR and review audit
src/interaction_terms.py       Encoding and selected interactions
src/mlr_model.py               Baseline/enhanced OLS, coefficient inference, VIF
src/evaluation.py              MSE, RMSE, MAE, R², and comparisons
src/validation.py              Paired tests, cross-validation, classification agreement
src/field_collection.py        Field workbook -> model-ready recorded dataset (scripts/field_data.py)
src/station_classification.py  Seven-factor severity scoring
src/experiment.py              Shared workflow
src/export.py                 Reports and reproducibility
src/visualization.py           Matplotlib PNG figures
backend/app/main.py           FastAPI startup and compiled frontend serving
backend/app/api/routes.py     Thin HTTP routes
backend/app/schemas/          Validated input contracts
backend/app/services/         Local experiment storage and orchestration
frontend/src/                 Analyze/About pages, research components, API client
frontend/dist/                Compiled offline browser assets
frontend/tests/browser.mjs    Browser workflow and responsive layout checks
.web-data/                    Local source uploads, revisions, saved experiments
tests/                        Artificial software fixtures only
docs/                         Plan, references, and methodology notes
```

## Development and verification

Start the API in one terminal: `.\.venv\Scripts\python.exe main.py web --no-browser`. In a second terminal, run `cd frontend` then `npm.cmd run dev`. Open the Vite address printed in that terminal; it proxies `/api` to port 8000. Rebuild with `npm.cmd run build` before using the ordinary launcher again.

Run Python checks with `.\.venv\Scripts\python.exe -m pytest -q`. Run `npm.cmd run test:e2e` in `frontend/` after building for the browser workflow test. It uses temporary, explicitly artificial fixtures and an isolated server on port 8766; Edge/Chrome is detected on Windows. Elsewhere, set `PLAYWRIGHT_BROWSER_PATH` or install Playwright Chromium. Test data never enters your research workspace.

Run `.\.venv\Scripts\python.exe scripts\demonstrate_enhancement.py` for a known-answer (simulation) check: one simulated dataset with a true Passenger Volume × Vehicle Frequency interaction, one purely additive control, and one with injected data-entry errors. It writes `outputs/enhancement_demonstration/DEMONSTRATION.md` plus full bundles, showing that the workflow recovers effects that exist and reports no gain when none exists. It verifies the method, not real-world waiting times.

The original thesis specifies Python research tools but does not require a web or desktop interface. Document React/Vite/TypeScript and FastAPI in Sections 3.2.2 and 3.3.2 as implementation choices from your web brief. The research contributions remain IQR review, selected OLS interactions, and multi-factor threshold classification.

See `docs/SIMPLIFICATION_REVIEW.md` for the current architecture and thesis comparison, `docs/VALIDATION.md` for test evidence, and `docs/REFERENCES.md` for verified research and GitHub references. No third-party project code or dataset was copied into this implementation.


New research exports include `study_metrics`, `study_comparisons`, `study_predictions`, original-data coefficients/checks, source notes, and research documentation. The complete bundle adds `research_protocol.json`, `data_provenance.json`, and the original-data model in `models.joblib`. The original main metrics, charts, and predictions remain B/C for compatibility; the A/B/C tables explicitly identify each experiment. Source declarations are not independent verification.
