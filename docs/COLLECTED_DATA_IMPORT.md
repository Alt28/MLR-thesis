# Importing the collected Bus and Train data

The supplied ETL and cached Parquet files were checked on 22?23 November 2026. The system now accepts the generated files through **Transportation Dataset → Dataset Library** or **Upload Dataset**. The source records, unknown values, and audit information remain distinct.

## What is available

| Library entry | Rows | What the system can do now |
|---|---:|---|
| NYC Train – overview | 1,344 | Preview all six predictors and source audit. Predict only with a compatible trained Train model and matching measurement definitions. |
| NYC Train – CSV parts 1–10 | 200,263 total | The full matched train dataset, split into files of at most 20 MiB. No train rows are discarded between parts. |
| AC Transit Bus – overview | 6,016 | Review recorded boardings, station/route IDs, calendar categories, and APC door-event counts. Vehicle Frequency is explicitly missing. |
| AC Transit Bus – CSV part 1 | 6,016 | The same bus subset with its audit fields in one CSV; it is an alternative format, not additional observations. |

The overview workbooks contain `Dataset`, `Source_Audit`, and `Sources_Methodology` sheets. Audit joins use a stable `Record ID`, not matching predictor values or an assumed spreadsheet row order. CSV parts contain the audit columns directly. The original downloads and old output files were preserved.

The **Train overview overlaps the full CSV parts**. Do not concatenate the overview with those parts, or count it as new observations. The overview selects up to 64 observations per date by the smallest SHA-256 hashes of their IDs. It covers the 21 selected local dates in March, July, and November 2025; it is a descriptive subset, not a representative passenger sample.

The Bus export selects up to 64 stop-route-hour groups per date by a deterministic MD5 key ordering, from 17,078,314 eligible hourly groups. This yields 6,016 rows over 94 dates. The cached March, July, and November 2024 source partitions include boundary observations dated August 1 and December 1. Those actual event dates are preserved; they do not provide full August/December seasonal coverage. The exporter inspected 17,671,276 raw rows, used 17,542,353 rows with eligible identifiers/timestamps/nonnegative boardings, and excluded 128,923 rows that failed that combined filter. No excluded value was imputed.

## Where to click

If an older browser tab says **API route not found**, reopen `Start MLR System.bat`. The launcher now checks both the predictor schema and Dataset Library endpoint before reusing a server. It skips an older or occupied local address without stopping that process. A connection failure is shown as **Library unavailable**, rather than an empty dataset library.

1. Open the updated local build at **http://127.0.0.1:8001** and select **Dataset Library** beside **Upload Dataset**.
2. Select **NYC Train - overview** or **AC Transit Bus - overview**.
3. Open **Observation timing and source definitions** to read the measurement notes.
4. Open **View source audit and observation identifiers** to see the original hour, identifiers, sources, and event counts for the preview records. The imported file retains all its rows.

Train shows **6/6 predictors detected**. Bus shows **Imported for source review** and **5/6 predictors complete**. The missing bus frequency is not silently converted to zero. The Analyze button stays disabled for incomplete inputs, even if a trained model is selected. Direct training and prediction API calls still reject missing predictors.

Both sources lack **Actual Waiting Time**. A blank target is acceptable for predictions from an already-trained model, but these files cannot train that waiting-time model or produce MSE/RMSE/MAE/R² by themselves. The new library import performs inspection first and does not automatically create a training experiment. No empirical model comparison or waiting-time labels were generated from these files.

## What the measurements mean

The collection uses automated ETL with exact spatial identifiers and local hourly joins. That describes the processing method; the source definitions still determine what the features measure.

- **Train passenger volume:** MTA estimated paid entries to a station complex. This is not the number of people waiting at one platform. Fare-type rows are summed once; transfers are not added again. [TransitLab documentation](https://docs.transitlab.nyc/datasets/subway-hourly-ridership/)
- **Train frequency:** distinct recorded train trips departing from constituent stops of that complex within the hour. Departure events come from GTFS-realtime feed changes. The last departure per trip/stop is used, then the official stop-to-complex mapping is applied. It is not a passenger-specific route/platform frequency. [Departure documentation](https://docs.transitlab.nyc/datasets/subway-stop-events/), [MTA station crosswalk](https://data.ny.gov/Transportation/MTA-Subway-Stations/39hk-dx4f)
- **Bus passenger volume:** recorded boardings on APC-equipped buses. The community archive documents incomplete, varying fleet coverage. No capture-rate adjustment was invented. [Source dataset and documentation](https://huggingface.co/datasets/somemone/ac-transit-apc)
- **Bus frequency:** unavailable from these fields under the system's serving-vehicles/hour definition. The file has door-event timestamps, without vehicle identifiers or evidence of full fleet capture. `APC Door Events` and `Unique APC Event Timestamps` are retained as metadata. Neither is inserted into the model's Vehicle Frequency column.

The Train merge excludes unmatched complex-hours rather than treating missing service as zero. There were 11,793 departure complex-hours without a matching ridership value. Unmapped stops are reported in the source manifest. A current crosswalk does not independently establish every historic platform configuration. Feed coverage is not the same as complete passenger service coverage.

Repeated or nonexistent local hours at daylight-saving transitions cannot be safely joined to a naive hourly timestamp without an offset. The updated train collector excludes those ambiguous hours and reports the count. Bus timestamps remain as supplied: interpreting them as America/Los_Angeles local time is explicitly marked as an unverified source assumption.

The script's original time bands are preserved: Morning 05–09, Midday 10–13, Afternoon 14–16, Evening 17–20, and Night 21–04. These differ from some field-collection conventions. A trained model must use the same definitions; valid category names alone do not prove compatibility.

These are retrospective hourly data. In particular, MTA ridership estimates are published after the observation period. No prediction timestamp or claim of real-time availability was invented. When pairing recorded waiting times later, use a documented, compatible prediction origin and features that would have been available then. Do not treat a completed hour's total as known at its start.

## Files on this computer

The collector now also has a separate, installed folder: **`C:\Users\clarence\Downloads\Data Collector Merger`**. Double-click `Run Collector.bat` there. It contains four ETL modules, a menu launcher, requirements, its own Python environment, settings, and `READ ME FIRST.txt`. Its `settings.json` reuses the existing raw/download/output paths below and registers finished packages in the system library. Original datasets were not moved or duplicated. `Setup Collector.bat` is available if the environment needs to be recreated.

- Updated user collector: `C:\Users\clarence\Downloads\Data Collection\collect_real_bus_train_six_predictors_v2.py`
- Companion helper: `C:\Users\clarence\Downloads\Data Collection\etl_system_export.py`
- Original collector backup: `collect_real_bus_train_six_predictors_v2_before_system_fix.py`
- New outputs: `C:\Users\clarence\Downloads\Data Collection\system_imports`
- Local system library: `data/collected` within this repository.
- `TRAIN_NYC_COMPLEX_MANIFEST.json` and `BUS_AC_TRANSIT_SOURCE_REVIEW_MANIFEST.json`: source URLs, cached-file SHA-256 hashes, selection/exclusion counts, output hashes, and file inventory.
- `SYSTEM_IMPORT_STATUS.xlsx` in `system_imports`: a concise status report. The original supplied validity workbook is retained as historical preparation notes; its earlier “not downloaded in this runtime” statement does not describe these newly verified local exports.

Collected data and manifests in `data/collected` are local and ignored by Git. Code changes alone do not copy these data to a hosted deployment. Use the commands below or copy the prepared library folder onto the target server. `MLR_DATASET_LIBRARY_DIR` can point to another prepared library directory.

## Run the updated collector again

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-etl.txt
.\.venv\Scripts\python.exe scripts/collect_real_bus_train_six_predictors_v2.py --mode train --cache 'C:\Users\clarence\Downloads\Data Collection\raw_data_downloads' --out 'C:\Users\clarence\Downloads\Data Collection\system_imports' --library-dir 'data\collected'
.\.venv\Scripts\python.exe scripts/collect_real_bus_train_six_predictors_v2.py --mode bus --cache 'C:\Users\clarence\Downloads\Data Collection\raw_data_downloads' --out 'C:\Users\clarence\Downloads\Data Collection\system_imports' --library-dir 'data\collected'
```

Run the two commands sequentially because both update the library manifest. Cached raw downloads are reused. For a full Bus export, add `--bus-rows-per-day 0`; this may produce many gigabytes of CSV parts. It still leaves unverified Vehicle Frequency blank. The default daily subset makes inspection practical without pretending to contain the entire collected bus dataset.

The SUNT alternative remains a separate source exploration option. Its five-minute vehicle-presence counts are not converted into verified distinct hourly arrivals, and it was not registered in this library.

## Collecting a second Bus source

The same collector now accepts `--mode bus-arrivals` through the companion `etl_511_archive.py`. This optional stage retrieves 511 SF Bay's monthly regional archive with `historic=YYYY-MM-so`, including `stop_observations.txt`. The provider documents historical observed arrivals from March 2022 onward. Access requires a free token requested at [511's token page](https://511.org/open-data/token); see [the official archive explanation](https://511.org/about/faq).

An API token is an access code used by the script to request the files. It is not required for the existing Train collection or the existing APC review files. Save the token outside the repository, then provide its local path with `--token-file`; the collector also supports the specific environment variable `TRANSIT_511_API_KEY`. Tokens are excluded from logs and manifests. For example, after obtaining the token:

```powershell
.\.venv\Scripts\python.exe scripts/collect_real_bus_train_six_predictors_v2.py --mode bus-arrivals --months 2024-03 2024-07 2024-11 --token-file 'C:\path\to\511-token.txt' --cache 'C:\Users\clarence\Downloads\Data Collection\raw_data_downloads' --out 'C:\Users\clarence\Downloads\Data Collection\system_imports'
```

**Current status:** the archive downloader was tested with artificial ZIP fixtures; no authenticated 511 archive has been downloaded or merged in this session. The command inventories source columns and refuses archives that provide only scheduled `stop_times.txt`. It does not invent an arrival schema or immediately relabel the contents as verified frequency. The Bus library remains source-review data.

Before an actual merge, verify AC Transit's agency/stop/route mapping in the historical feed, the timestamp meaning and timezone, observed-versus-predicted flags, duplicate trip-stop events, and exact overlap with the APC observation windows. Report missing matches and partial coverage. Use only compatible locations and periods; a Brazilian or New York observation cannot fill an AC Transit row merely because its column name matches. Passenger actual waiting times remain a separate missing target even if observed bus service frequency becomes available.

## Verification

- All 200,263 regenerated Train feature rows exactly matched the prior V2 collected file after normalizing the frequency column name.
- Every row of all 13 registered packages passed the current inspection endpoint's underlying parser. Full Train parts contain 200,263 unique observation IDs with no overlap between parts. Both Bus formats report `source_review`, with frequency and target unfilled.
- 179 Python tests passed, including bounded export parts, audit joins, blank-frequency preview, strict model rejection, missing files/path traversal, DST ambiguity, and source-event aggregation.
- Production frontend build and browser workflow passed. Browser tests use artificial fixtures in isolated storage, including separate Train and Bus library imports; their predictions and screenshots are software tests, not research evidence.

## When Analyze is disabled for a Train file

All six predictors can be valid while no fitted model is available. On 23 November 2026, the local server listed ten saved runs, all incompatible with the current six-predictor schema. None provided a current Train model. The collected Train file also has no measured waiting-time targets, so it cannot train a replacement model.

The system now displays this specific reason immediately above Analyze. The availability checkbox only records an assertion about the timing of the input counts. It does not fit a model. First train both models on a separate Train dataset containing recorded Actual Waiting Time; then use a compatible trained model for new observations with blank targets. Accuracy measurement requires observed targets as well. No predictions or model metrics were fabricated to enable the button.

## Published waiting-time sources collected on 23 November 2026

The collector now has `--mode waiting-sources` (option **5** in the separate collector's menu), implemented in `etl_waiting_sources.py`. This mode downloads and checks two exact published source files, then produces separate Bus and Train workbooks under `system_imports/waiting_time_source_review`. **These are source-review files, not training datasets for the current system.** They are not registered in the Dataset Library.

| File | Recorded content | Remaining incompatibility |
| --- | --- | --- |
| `BUS_RECORDED_WAIT_SOURCE_REVIEW.xlsx` | 866 conservatively extracted observations from Appendix I of Salek and Machemehl's 1999 report, collected in Austin during June-December 1998. Includes station, passenger arrival, bus departure, date, printed wait and scheduled headway. | The observed endpoint is **bus departure**, not passenger boarding. Passenger Volume and observed Vehicle Frequency are missing. |
| `TRAIN_REPORTED_WAIT_SOURCE_REVIEW.xlsx` | 2,927 published survey responses from five Australian cities, surveyed in April-May 2013. Original `wtmins` values are preserved as **self-reported waiting minutes**. | No individual trip date, station, passenger counts or vehicle counts. Peak flags cannot establish the current five time bands. |

Sources: [Characterizing Bus Transit Passenger Wait Times, SWUTC/99/167211-1](https://static.tti.tamu.edu/swutc.tamu.edu/publications/technicalreports/167211-1.pdf); [Paramita et al. (2018), PLOS ONE, with S1 Dataset](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0199449).

The bus report contains 2,491 non-transfer observations. The PDF extraction retained only complete, unambiguous rows satisfying date, station, page/observation sequence, timestamp difference, printed wait-component sum and wait/headway ratio checks. The other 1,625 source IDs and all unparsed PDF lines remain listed for inspection. This subset is **not random**, not a full transcription, and may be affected by extraction selection. Source pages 84 and 158 were visually spot-checked; the entire extract has not been visually audited. Transfer observations in Appendix III were not extracted. Scheduled headway remains labeled as such; it was not converted into observed frequency. Counts of extracted passengers were not substituted for a complete observation-window passenger volume.

The train workbook also includes a copy of the original published Excel file (`TRAIN_ORIGINAL_PUBLISHED_DATA.xlsx`). The paper describes prior survey cleaning; the downloaded file is the published analysis sample, not raw timestamp measurements. Collection dates and city identifiers were not relabeled as trip dates or stations. Both source files have pinned SHA-256 checksums; changed source versions stop extraction until reviewed.

Each review workbook has `Read_First`, `Recorded_Rows`, `Predictor_Check` and `Provenance` sheets. `SOURCE_AUDIT.json` and `READ_FIRST.txt` summarize the remaining gaps. No current predictor values or passenger waits were invented, no models were trained, and these Austin/Australian observations were not joined to unrelated NYC or AC Transit rows.

```powershell
.\.venv\Scripts\python.exe scripts/collect_real_bus_train_six_predictors_v2.py --mode waiting-sources --cache 'C:\Users\clarence\Downloads\Data Collection\raw_data_downloads' --out 'C:\Users\clarence\Downloads\Data Collection\system_imports'
```

Validation: 19 targeted tests passed across waiting-source extraction, standalone packaging, existing ETL integration and the 511 downloader. New fixtures check contradictory timestamps, ambiguous PDF rows, invalid survey targets, changed source checksums, missing-field disclosure and inert spreadsheet text. These tests do not establish statistical suitability of the downloaded sources.

## Train training package with headway-derived waiting times (`--mode train-waits`)

Added 23 November 2026 in `scripts/etl_headway_waits.py`. This is the first library package that can **train** the Train models, because it fills **Actual Waiting Time** from recorded data rather than leaving it blank.

**Target definition.** For each platform direction (GTFS `stop_id` with N/S) and route, the recorded TransitLab departures (last departure per trip-stop) define the time until the next train, `w(t) = next departure − t`. The service-hour wait is the exact mean of `w(t)` over the local hour: the average wait of a passenger arriving at a uniformly random moment who boards the next recorded train of their route. This is the random-arrival result `E[W] = E[H²] / (2·E[H])` (Osuna & Newell, 1971; Larson & Odoni, 1981), computed from the observed headway sequence, so irregular service gives a longer wait than scheduled-frequency `headway/2`. The complex-hour target is the unweighted mean over route-directions that departed from the complex in that hour.

**What it is not.** It is not an individually timed passenger wait. It assumes random passenger arrival (reasonable for frequent urban rail; less so for infrequent service), and it does not represent denied boarding on crowded trains. Describe it in the thesis as an *observation-derived expected platform waiting time*, and state these assumptions when ticking the recorded-target declaration.

**Exclusions** (counted in the manifest, never imputed): route-direction hours with no departure in the hour, any covering headway over 60 minutes (feed gaps or suspensions), hours not fully covered by recorded departures, ambiguous DST hours, unmapped stops, and complex-hours without a ridership match.

**Relationship to the predictors.** Vehicle Frequency is the same complex-level distinct-trip count as the V2 export. The target is computed per route-direction, so it is related to, but not a function of, that predictor. Expect a strong, nonlinear (inverse) frequency effect; that is a property of transit service, not leakage of the target.

Run (uses the cached raw files; about 2 minutes):

```powershell
.\.venv\Scripts\python.exe scripts/collect_real_bus_train_six_predictors_v2.py --mode train-waits --cache 'C:\Users\clarence\Downloads\Data Collection\raw_data_downloads' --out 'C:\Users\clarence\Downloads\Data Collection\system_imports' --library-dir 'data\collected'
```

Outputs: `TRAIN_NYC_HEADWAY_WAITS_part_*.csv` (every matched row with audit columns), an overview workbook, the manifest, and `TRAIN_NYC_HEADWAY_WAITS_TRAINING.csv`, a single compact file under the 25 MB upload limit. `--train-rows` sets its size (default 10,000; deterministic smallest-SHA-256 Record IDs; `0` = all rows). With 424 station categories, 10,000 rows train and evaluate in about 75 seconds. The library lists it as **NYC Train - TRAINING (headway waits)**.

**Bus.** The AC Transit APC records have no direction field, no vehicle IDs, and cover only APC-equipped buses, so stop-level headways cannot be reconstructed reliably. Bus remains without a training target.

**Software test runs, 23 November 2026 (10,000-row package, random 80/20 split, seed 42).** These were run to check that the package trains. They are not a tuned or final thesis result.

| Enhanced interaction | Traditional MSE / R² | Enhanced MSE / R² |
|---|---|---|
| Passenger Volume × Vehicle Frequency (system default) | 5.39 / 0.48 | 6.14 / 0.41 (worse) |
| Vehicle Frequency × Time of Day | 5.39 / 0.48 | 4.90 / 0.53 (better) |

Choose and justify the interaction before looking at held-out results. Selecting it after comparing test scores is a form of overfitting.

**Speed fix.** `variance_inflation` in `src/mlr_model.py` previously ran one regression per design column. With hundreds of station dummies, that took more than 5 minutes even for 2,000 rows. It now uses the exact identity VIF_j = [R⁻¹]_jj from one correlation-matrix inverse. It falls back to the per-column regressions when that matrix is near-singular. The values match the old method to about 1e-13.
