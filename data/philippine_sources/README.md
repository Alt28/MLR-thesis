# Philippine supporting data pack

Retrieved 6 November 2026. **These files are not complete Transit Lab training datasets.**

- `prepared/philippine_supporting_datasets.xlsx`: readable workbook with a readiness assessment first, followed by MRT-3 daily ridership and historical GTFS service frequencies.
- `prepared/mrt3_daily_ridership_jan_apr_2024.csv`: 121 calendar days, four source blanks retained. Whole-line daily counts, not passenger episodes or station-hour demand.
- `prepared/metro_manila_historical_scheduled_frequency.csv`: 1,864 source schedule windows; frequency explicitly calculated from headway. Calendar ends 30 June 2020. No claim of current service or observed arrivals.
- `raw/mrt3_ridership_april_2024_mirror.pdf`: the four-page January-April report hosted by [Mediaworld Advertising](https://mediaworldadvertising.b-cdn.net/wp-content/uploads/2024/06/RIDERSHIP-REPORT-2024.pdf), identifying DOTr-MRT3 as the report author. Verify against an agency original before final research use.
- `raw/sakay_gtfs/`: relevant source tables, README and license from [Sakay.ph](https://github.com/sakayph/gtfs). Data provided by the Department of Transportation and Communications, modified by Sakay.ph. No agency affiliation or endorsement is implied. Preserve the included license with these data.
- `manifest.json`: local SHA-256 checksums and row-count summary. GitHub text snapshots were normalized to UTF-8/newline text when saved; these checksums identify the local copies.

Read `docs/PHILIPPINE_DATA_SOURCES.md` for the search assessment and `docs/MEASUREMENT_AMENDMENT.md` for the revised observation protocol. Keep `recorded_observation_template.xlsx` empty until actual aligned observations are collected. Do not fill missing model fields from unrelated daily totals, synthetic values, or schedule-derived waiting-time targets.
