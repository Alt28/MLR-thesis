# Current data preparation and collection guide

Use [the exact six-column schema](SIX_PREDICTOR_MIGRATION.md#input-contract). Prepare separate Bus and Train files. Preserve source observation IDs, exact dates/hours, count windows, transport mode, and source references as metadata or an explicitly keyed Source_Audit sheet.

For supervised training, record passenger arrival and boarding timestamps for the same passenger; their difference in minutes is Actual Waiting Time. Vehicle headway, vehicle dwell, platform delay, and a model prediction are different quantities. No estimate should replace a missing passenger wait.

Predictor-only files can be uploaded and previewed immediately. They require a compatible saved model to obtain predictions and cannot evaluate accuracy. The current NYC and APC candidate exports do not include measured passenger waits.

Passenger Volume and Vehicle Frequency must be available at the intended prediction time. Use completed past windows, not the rest of the current hour. Source definitions must distinguish entries/boardings/arrivals and platform/complex/route coverage. Do not combine unrelated places or dates merely to fill columns.

The field-collection helper creates an empty workbook with Stations, Counts, Passengers, Lists, and Sources_Methodology. Record serving vehicles and passengers in 15-minute blocks; each sampled passenger uses the four completed blocks before arrival. Actual wait comes from observed passenger timestamps. Station and calendar features are derived without numeric severity assignments. Time-of-day boundaries are explicit in Lists and require a consistent collection convention. Separate Bus and Train workbooks are required for model-ready export.

No automatic deletion of duplicate-looking observations is allowed. Source records must remain traceable; the same six predictor values can describe distinct dates/hours or passengers. Review genuine data issues with source evidence through the existing IQR workflow.

See [classification proposal](CLASSIFICATION_RULES.md) before assigning severity to station or calendar categories. Their names have no inherent order.
