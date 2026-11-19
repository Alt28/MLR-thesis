# Transit Lab dataset library

The picker offers one prototype workbook for software testing. It does not contain recorded observations suitable for final empirical research results.

- `transportation_dataset_500_bus_train.xlsx`: 500-row transportation workbook labelled with 250 bus and 250 train transport modes.

Other synthetic/prototype workbooks remain in this folder only for automated tests and are no longer listed in the picker: `transit_bus_SYNTHETIC_DEMO.xlsx`, `transit_train_SYNTHETIC_DEMO.xlsx`, `transportation_dataset_200_demo_fixed.xlsx`, and `transportation_dataset_40_ph_internet_rows.xlsx`. `scripts/prepare_library_sources.py` copies the earlier workbooks and writes checksums in `source-manifest.json`; use `--downloads-dir` if needed. Rebuild the frontend after updating assets.

Incomplete MRT-3 ridership, EDSA Busway survey and historical schedule references were removed from the application library and its public downloads at the user's request on 18 November 2026. The research source copies remain under `data/` for traceability. They lack measured passenger waiting times and the complete matched predictors, so they cannot supply valid waiting-time model results. The preparation script no longer republishes them.

Library selections go through the ordinary upload validator. Source labels and research approval checks remain in place. Use Upload Dataset for recorded research observations.
