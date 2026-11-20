# Philippine data search and suitability review

## Prediction-only follow-up: 20 November 2026

The application now accepts an entirely blank or omitted Actual Waiting Time for predictions from saved models. This removes the target requirement for prediction uploads, not the requirement for six aligned predictors. This follow-up did not verify a complete Philippine bus/train prediction dataset with those six measurements.

Two source workbooks were saved to `C:/Users/clarence/Downloads/real_philippine_transport_sources_2026-11-20/`. Neither is a complete model input and neither was added to the application's dataset library:

- `train_recorded_sources_and_weather_REFERENCE.xlsx`: 651 MRT-3 Taft Avenue hourly slots for July 2023, each matched to one observed RPLL airport weather report at exactly the interval start in Asia/Manila time. Source station entries/exits are preserved. After-midnight slots are excluded because the reporting-day convention is unresolved. Airport weather is contextual, not represented as a station measurement; entries have no train direction and are not renamed to the study's preceding-hour passenger-arrival variable. Waiting time remains blank.
- `bus_recorded_survey_sources_REFERENCE.xlsx`: 12 published direction/hour bus counts, 80 survey-derived station dwell means, and 9 survey-coverage records. The count summaries do not specify their exact observation dates. No weather join was made, and train entries were not substituted for bus passenger arrivals.

The train source is the [MRT-3 report repository](https://github.com/ongods/mrt3-ridership-data/tree/f4f1b40413efef0e7381892f67e43876ea3a99f5), already checked against its supplied workbooks locally. Its publisher attributes the files to DOTr FOI; the release letter/request number was not supplied, so full chain of custody remains unverified. Weather was downloaded from the [Iowa Environmental Mesonet observation archive](https://mesonet.agron.iastate.edu/request/download.phtml?network=PH__ASOS), using its [documented API](https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?help). The 775 RPLL reports cover July 2023; missing weather codes are not treated as clear weather, and unavailable non-US precipitation amounts are not filled with zero.

Bus facts come from [Ollero, Vergel and Tiglao (2024), Philippine Transportation Journal 7(2)](https://ncts.upd.edu.ph/tssp/wp-content/uploads/2025/01/TSSP2024-Vol7-No2_01-Ollero-Vergel-and-Tiglao.pdf), Tables 2-4, excluding simulated scenario results. Dwell time is not passenger waiting time.

Additional candidates examined included Mendeley's Cebu transport-mode-choice survey (preferences rather than operational measurements), annual transport/AADT datasets (wrong time granularity), GTFS (schedules rather than observed vehicle events), and the public STPH trip-segmentation sample. The inspected STPH Route 9 CSV contained TEST identifiers, mixed regions, and unresolved mode/timezone; it was not accepted as verified recorded bus data. A successful FOI webpage without a downloadable attachment was not treated as a delivered dataset.

`scripts/build_real_source_review.py` generates the two workbooks from retained local sources and the downloaded weather CSV. It checks unchanged rail counts, unique record IDs, exact weather timestamps, blank targets, bus source row counts, and no join multiplication. The package includes source URLs, source row references, SHA-256 hashes, and a six-field readiness check. **Model-ready rows: 0.** Matching traffic observations, observed service frequency, and predictor-definition alignment remain unresolved. This is a documented partial source preparation, not a completed forecasting dataset or evidence of model accuracy.

Checked 6 November 2026. Scope: Philippine datasets only, as requested.

**No complete, verified public dataset was found in this search containing the six predictors and measured passenger waiting time aligned to the same observations.** The downloaded files below are useful supporting data. They cannot truthfully be turned into an analysis-ready file by inserting invented weather, traffic, passenger counts, or waiting times.

## Downloaded and inspected

| Source | Local result | What it supports | What it cannot establish |
| --- | --- | --- | --- |
| [DOTr-MRT3 ridership report, Jan-Apr 2024, hosted by Mediaworld Advertising](https://mediaworldadvertising.b-cdn.net/wp-content/uploads/2024/06/RIDERSHIP-REPORT-2024.pdf) | `data/philippine_sources/prepared/mrt3_daily_ridership_jan_apr_2024.csv`: 121 calendar dates, 117 with entries/exits and 4 blank source days | Published daily MRT-3 system totals; extracted sums agree with every published monthly total. The PDF identifies the figures as system-generated. | It is a third-party copy, not a directly downloaded agency original. It has no passenger wait or station-hour volumes. Daily line totals must not be repeated as each episode's Passenger Volume. Blank days were retained, not filled with zeros. |
| [Sakay.ph Metro Manila GTFS](https://github.com/sakayph/gtfs) | `data/philippine_sources/prepared/metro_manila_historical_scheduled_frequency.csv`: 1,864 trip/time-window records | Historical route/service metadata and scheduled headways; explicit conversion `3600 / headway_secs` to vehicles/hour. The upstream README traces the feed to DOTC's Philippine Transit App Challenge and notes Sakay modifications. | The inspected calendar ends **2020-06-30**. This is not current 2026 service, observed frequency, or measured waiting time. Road-transit codes may include jeepneys; do not relabel all records as bus observations. |

The combined supporting workbook is `data/philippine_sources/prepared/philippine_supporting_datasets.xlsx`. Its first sheet states why neither dataset is ready for MLR. Source files, Sakay's license, and a SHA-256 manifest are retained locally. They have not been uploaded over your current experiment or reported as thesis model results.

Extraction can be repeated with `python scripts/prepare_philippine_sources.py` after the downloaded source files are present. It requires pandas, openpyxl, and pypdf. Monthly-total checks detect extraction mismatches. No missing MLR predictor or target is generated by this script.

## Official sources for the remaining measurements

| Source | Evidence and access | Intended use |
| --- | --- | --- |
| [DOTr FOI: hourly/daily/monthly MRT-3 station ridership, 2018-2023](https://www.foi.gov.ph/requests/hourly-daily-and-monthly-ridership-of-each-station-of-mrt-line-3-from-2018-to-2023/) | Successful request, tracking DOTr-743938106122. Agency says the data was emailed to the requester; the page does not expose that dataset for direct download. | Request equivalent station/time-level records for your chosen study dates, plus event logs if retained. Ridership alone is still insufficient for observed passenger wait. |
| [LRTA FOI: monthly/annual ridership, 2000-2023](https://www.foi.gov.ph/requests/lrt1-and-lrt-2-monthly-and-annual-ridership-data-2000-2023/) | Official attachment listed. The attachment returned HTTP 503 during this search; it was not downloaded or claimed available locally. | Background ridership; request finer station/time granularity for predictor alignment. |
| [PAGASA climate data requests](https://www.pagasa.dost.gov.ph/climate/climate-data) | Official academic raw-data request route lists school identification, research proposal, terms of use, and adviser-endorsed letter. | Request observed weather at the nearest relevant station and matching dates/times. Climate normals or forecasts are not substitutes for weather observed at an episode. |
| [UP NCTS Data and Information Unit](https://ncts.upd.edu.ph/library/) | Lists transport holdings including ridership, passenger movement, and bus operators. Availability of a complete episode-level dataset was not established. | Ask about existing passenger-wait surveys or bus dispatch/arrival records and access conditions. |

For bus data, request route/direction-specific dispatch and stop-arrival timestamps from the operator and relevant DOTr/LTFRB office. Use roadside or operator observations for passenger counts and waits if these records do not exist. No request has been sent on your behalf.

## Sources rejected as measured training data

- [MRT-3 crowd-patterns GitHub dataset](https://github.com/russperez/mrt3-crowd-patterns-dataset): its own README describes weighted estimates from a daily baseline, not measured station-hour counts. Its 1,638 rows do not provide observed waiting-time targets.
- [Passenger-demand forecasting GitHub project](https://github.com/farizqadeer/passenger-demand-forecasting): the README explicitly describes augmenting 54 rows to 3,240. Augmented rows cannot be represented as independent recorded observations.
- The existing local 40/200/500-row workbooks identify themselves as prototype or synthetic. More generated rows do not resolve the evidence gap.

## Practical route to a valid test

Use `data/recorded_observation_template.xlsx` for a documented set of waiting episodes. Collect the target and six predictors for the same route, station, direction, and timestamp. Start with the mode for which all six predictors can be independently justified; bus-only data does not validate train performance. Request official matching weather and service records where needed. Do not merge the historical GTFS and 2024 daily report into fabricated passenger episodes.

The current system should reject the downloaded supporting tables as incomplete model input. That rejection protects the intended methodology. Real-data model testing remains pending until the missing aligned records are collected or obtained.
