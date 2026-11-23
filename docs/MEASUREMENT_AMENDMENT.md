# Current measurement definitions

This revision supersedes the earlier traffic/weather/distance predictor specification. See [the exact schema and timing contract](SIX_PREDICTOR_MIGRATION.md#input-contract).

Passenger Volume counts recorded passengers in a documented observation period. Preserve whether a provider measures arrivals, station entries, or boardings; these are not interchangeable passenger populations.

Vehicle Frequency is actual recorded serving operations per hour, calculated as 60 times the serving-event count divided by a positive observed window length in minutes. This calculation never supplies Actual Waiting Time. Scheduled headway, available fleet size, repeated GPS presence, and instrumented door events without deduplication are not automatically equivalent to observed service frequency.

Station / Stop, Time of Day, Day of Week, and Month of Year are categorical. Use the relevant local prediction timestamp for calendar features. Existing source boundaries for Morning/Midday/Afternoon/Evening/Night must be documented and applied consistently. The optional field workbook includes a proposed explicit clock convention in Lists; using it for another source requires checking that source's definitions.

Passenger and vehicle windows must end by the prediction time. Full future-hour totals leak future information. If only hourly aggregates exist, define a prediction origin and construct documented lagged windows before matching to genuine measured waits. The system checks supplied window-ending timestamps and otherwise requires a researcher availability declaration.

Source-specific cautions: NYC combines station-complex activity across platforms; AC Transit APC coverage can be partial; SUNT presence records require distinct arrival identification. No system-wide daily ridership or unrelated-location data may be merged into observation-level waits just to fill columns.

The removed Route Distance measurement and traffic/weather severity rules are historical, not current input requirements. Old workbooks/models cannot be reused by renaming columns.
