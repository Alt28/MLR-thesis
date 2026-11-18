# MRT-3 reported ridership, 2023-2025

Downloaded November 18, 2026. Start with `prepared/MRT3_RIDERSHIP_2023_2025.xlsx`, or use the hourly/daily CSVs in that folder. The ZIP includes the originals, prepared files, source notes, and verification information.

## Origin and verification limits

The [publisher](https://github.com/ongods/mrt3-ridership-data) attributes the reports to DOTr's FOI process. Its manifest contains no FOI request number, acquisition date, or release letter, so that chain of custody has not been independently confirmed. The files are supplied as reported ridership, not simulated observations. All downloads are pinned to commit `f4f1b40413efef0e7381892f67e43876ea3a99f5`; hashes and URLs are in `download_manifest.json`.

The original workbook hashes match the publisher's manifest. `prepare.py` checks every exported station/system count cell against the supplied Excel workbooks before combining the years. The annual entry totals for 2023 and 2024 match [MRT-3's official announcement](https://www.dotrmrt3.gov.ph/news/mrt-3-logs-135-million-riders-in-2024): 129,030,158 and 135,885,336. Agreement supports consistency; it does not independently authenticate every record.

## Preparation performed here

The prepared tables stack the three years using the existing schema. They exclude 20 date blocks outside their worksheet months, leaving 26,304 hourly rows and 1,096 daily rows. Counts, blanks, and recorded zeros remain unchanged. Each row retains its source workbook, sheet, and row reference. No waiting time, weather, traffic, distance, frequency, or additional passenger episode was generated. CSVs preserve the downloaded numeric text; the convenient Excel copy uses ordinary spreadsheet numerical precision.

Comparison with the separately downloaded January-April 2024 daily PDF found 12 differences among 234 nonblank entry/exit values: two entries and ten exits. Some differences are fractional, while others are larger. Both sources remain unchanged. See `prepared/comparison_with_earlier_2024_report.csv`; do not silently treat the reports as interchangeable. Annual-total agreement does not resolve these daily discrepancies.

## What the dataset can support

These are aggregate counts for 13 MRT-3 stations and system totals. They support analysis of reported ridership by station, report date, and time slot. They have no passenger-level arrival/boarding pairs or measured waiting durations. They are **not a complete input dataset for the current six-predictor waiting-time model**. Entry counts are not automatically the route/direction-specific preceding-hour passenger-arrival measure in that model. Using ridership as the prediction target would require an agreed change to the research design.

Review `source/README.md` and the upstream quality files before analysis. Time-label flags, fractional counts, missing values, and discrepancies between totals are retained. The reporting day includes after-midnight slots; this preparation does not assign them new calendar dates. Do not join external weather on those slots without resolving the timestamp convention. The publisher has not provided reuse terms with the workbooks.

To reproduce the prepared files from the downloaded sources, run `.venv/Scripts/python.exe data/mrt3_ridership_2023_2025/prepare.py` from the project root. This checks conversion fidelity, not the authenticity of the agency release.
