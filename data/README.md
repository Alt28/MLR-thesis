# Recorded transportation data

The CSV and Excel templates contain headers only. Add real recorded observations; do not put artificial test fixtures in this folder or report them as thesis data.

Define one consistent observation unit and measurement window before collection. Record actual waiting time in minutes. Use consistent category names, Route Distance units, and Vehicle Frequency units. Document the collection dates, source, sampling process, and any source corrections separately.

The revised collection protocol uses service frequency in **vehicles/hour** and route distance in **km**. The new `recorded_observation_template.xlsx` includes empty observations, source-unit declarations, and timing/count metadata. See `docs/MEASUREMENT_AMENDMENT.md` before collecting data. Changing a unit label does not convert values.

`philippine_sources/` contains downloaded supporting records and prepared reference tables. These are not complete model inputs; see `docs/PHILIPPINE_DATA_SOURCES.md`. Missing waiting times and predictors have not been fabricated.

The exact required headers are:

`Traffic Condition`, `Weather Condition`, `Passenger Volume`, `Route Distance`, `Vehicle Frequency`, `Time of Day`, `Actual Waiting Time`.

Additional descriptive metadata may be retained but is excluded from the model. The first Excel worksheet is imported. Use a separate copy of the empty template for collected data.
