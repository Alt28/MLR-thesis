# EDSA Busway: published survey summaries, July 2023

**Reference data only. This does not contain measured passenger waiting times or a complete set of six matched predictors.** Dwell time is the time a bus spends stopped at a station. Do not rename it `Actual Waiting Time`.

Source: Ollero, L. J., Vergel, K., and Tiglao, N. C. (2024), *A Microsimulation Model of An Exclusive Bus Lane: The Case of EDSA Busway*, Philippine Transportation Journal, 7(2), pp. 1–40. [Publisher PDF](https://ncts.upd.edu.ph/tssp/wp-content/uploads/2025/01/TSSP2024-Vol7-No2_01-Ollero-Vergel-and-Tiglao.pdf). Retrieved 18 November 2026.

## Files and units

- `edsa_busway_dwell_means_2023.csv`: 80 station/direction/peak-period means in **seconds**, from Table 4, pp. 11–12. These are 40 station-direction combinations with AM and PM means, not 80 independent passengers or individual bus-stop events.
- `edsa_busway_reported_bus_counts.csv`: 12 direction/hour count summaries from Table 3, p. 10, checked against the **Actual** column in Table 5, p. 13. No observation date is supplied for these summaries; no date was assigned.
- `edsa_busway_survey_coverage_2023.csv`: 9 operator/date rows from Table 2, p. 9, covering 8 survey dates, 29 reported bus deployments and 105 roundtrips. These describe survey coverage, not passenger volume.
- `EDSA_BUSWAY_SURVEY_REFERENCE_2023.xlsx`: source notes followed by the three tables above, with filters and frozen headers.

## Preparation and limitations

Numeric values are extracted directly from the publisher's PDF. Station spelling is retained, line wraps are removed, and the coverage dates are converted to ISO format. Source table, page and URL accompany every row. The mean dwell times are identified as survey-derived in section 4.4. Simulated scenario outputs and simulated counts are excluded from the prepared files.

The raw app logs, per-cell sample sizes and individual observation timestamps are not in this package. Published summaries cannot reconstruct those missing observations. Do not repeat these rows across dates to increase sample size, calculate passenger waiting time from these bus counts, or join them to MRT-3 rows merely by row order or station name. A defensible join requires matching measurement units, place and time, with documented keys.

This package supports descriptive reference use. It cannot validate the waiting-time MLR model or produce empirical waiting-time prediction errors.

## Reproducibility

`download_manifest.json` records the publisher URL, retrieval date and SHA-256. The downloaded PDF is kept locally in `source/` for verification; the library links to the publisher and does not redistribute the paper. `source/extracted_tables.json` contains the extracted factual cells.

Run `python data/edsa_busway_field_study_2023/extract_source.py` using Python with `pdfplumber`, then `.venv\Scripts\python.exe data/edsa_busway_field_study_2023/prepare.py` using the project's existing `openpyxl`. The ZIP includes prepared tables, source notes, extracted cells, scripts and checksums. Values are not imputed, simulated or merged with unrelated datasets.
