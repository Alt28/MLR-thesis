# Measurement amendment for the thesis

Prepared 6 November 2026. This is proposed replacement wording for the revised study; it does not claim that Raymart (3).pdf already specifies these definitions. The original PDF is unchanged.

## Replace the Vehicle Frequency definition in Table 3.1

**Vehicle Frequency:** The observed rate of vehicles serving the selected station or stop, route, and direction, expressed in vehicles per hour. For buses, one serving bus counts as one vehicle event; for rail, one arriving train set counts as one event, regardless of its number of cars. The rate is measured over the 60-minute interval immediately preceding the passenger's arrival at the waiting area. Vehicles that do not serve the selected stop are excluded.

**Route Distance:** The total length of the selected service route in the relevant direction, expressed in kilometers, obtained from an operator record or a documented route geometry. This quantity is not the passenger's remaining distance unless the observation protocol is explicitly revised to use that alternative consistently.

**Passenger Volume:** The observed number of passengers arriving for the same service, stop, and direction during the 60-minute interval immediately preceding the sampled passenger's arrival. Network-wide daily ridership is not substituted for this observation-level count.

**Actual Waiting Time:** The elapsed time, in minutes, between the sampled passenger's arrival at the designated waiting area and boarding the selected service. It includes the wait caused by inability to board an earlier full vehicle. Travel time inside a vehicle, train lateness, dwell time, a published arrival prediction, and half of the headway are not treated as the measured target.

## Insert in Data Collection / Operational Definitions

Each dataset row represents one observed passenger waiting episode at an identified stop or station, route, direction, and transport mode. The prediction instant is the passenger arrival timestamp. All predictor information must be available at or before that instant. Timestamps use Asia/Manila time (UTC+08:00). Boarding time is recorded subsequently only to calculate the actual waiting-time target. No passenger name or identifying information is required.

Observed service frequency is calculated as:

`Vehicle Frequency (vehicles/hour) = 60 × N / W`

where `N` is the number of serving vehicle events in a completed observation window and `W` is that window's duration in minutes. This revised protocol fixes `W = 60`; a different window requires a documented protocol amendment and consistent application. Zero observed events yield zero observed frequency. Missing or incomplete observations are not recorded as zero.

The term **available vehicles** previously used in Table 3.1 refers to fleet availability and is replaced by **service frequency**. Fleet size cannot be converted into arrival frequency merely by changing the unit label. Counts require both a serving-event definition and a known counting interval.

For a separate schedule-based experiment, scheduled frequency may be derived as `60 / H` when the documented headway `H` is in minutes, or `3600 / Hs` when it is in seconds. This is labeled scheduled frequency, not observed frequency. Scheduled and observed rates are not silently mixed in the same final experiment. A schedule is not evidence of actual waiting time. See the [GTFS frequencies definition](https://gtfs.org/documentation/schedule/reference/#frequenciestxt).

Traffic and weather are independently observed and linked to the same station and prediction time. Time of Day is derived from the passenger arrival timestamp using period boundaries fixed before evaluation. The data dictionary must define traffic categories and their relevance to each transport mode; rail observations must not receive an invented road-traffic category merely to satisfy the schema.

Observation episodes sharing the same service window or trip may be dependent. The current system uses random holdout splitting; grouped or chronological evaluation would need an explicitly implemented and documented extension before claiming independence for such records. Report incomplete or censored waiting episodes rather than assigning arbitrary targets or silently hiding them.

## Insert in Classification / Preprocessing

Unit standardization is a data-preparation step. It does not change Ordinary Least Squares, the selected interaction terms, IQR review decisions, or seven-factor scoring. The application does not automatically rescale imported values when a unit label is edited. Distance in meters must be divided by 1,000 before being labeled kilometers. Frequency derived from counts or headway must retain its source values, interval, and observed/scheduled basis as metadata.

Category means, numerical quartiles, and severity directions are still fitted using reviewed training data only. Defining frequency in vehicles/hour does not force a reverse severity direction: the current implementation uses the training relationship unless a documented researcher configuration overrides it. This empirical relationship is not a causal conclusion. Constant variables and missing rules remain unclassified; a unit change cannot create variation.

## Existing demonstration data

The 500-row workbook explicitly declares vehicles/hour and km, so no numeric conversion is needed for that file. Its rows are synthetic; changing unit documentation does not make them recorded observations. The old 40-row prototype also contains constant corridor-level values and simulated waits. Neither establishes final predictive accuracy.

## System and collection files

- Classification definitions now offer **Use study frequency unit** (`vehicles/hour`) and **Use study distance unit** (`km`) only for blank fields. These presets replace the earlier count preset; use them only after checking/converting the values.
- Explicit workbook Variable/Unit declarations still fill settings during new imports; existing saved settings are preserved. Bare CSV files cannot prove their units and still require documentation.
- `data/recorded_observation_template.xlsx` is the empty collection workbook, with definitions and audit metadata. It contains no invented observations.
- `src/measurements.py` provides explicit count/window and scheduled-headway conversion helpers. These are preparation utilities, not silent model transformations.

This wording resolves the unit inconsistency but still needs to be adopted in the final research protocol and reviewed with the adviser before collecting/evaluating final data.
