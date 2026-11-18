# Transit Lab dataset library

The library contains five demo/prototype workbooks for software testing. These are not recorded observations suitable for final empirical research results.

- `transit_bus_SYNTHETIC_DEMO.xlsx`: 180 fictional bus observations.
- `transit_train_SYNTHETIC_DEMO.xlsx`: 180 fictional train observations.
- `transportation_dataset_500_demo_validated.xlsx`: earlier 500-row demo.
- `transportation_dataset_200_demo_fixed.xlsx`: earlier 200-row prototype.
- `transportation_dataset_40_ph_internet_rows.xlsx`: original 40-row prototype, with constant predictors and undefined units.

The bus and train demos include explicit transport metadata and a Sources_Methodology sheet documenting their simulated origin. Generate them with `.venv\Scripts\python.exe scripts\prepare_demo_library.py`. The earlier workbooks preserve their original values and do not imply an observed transport mode. `scripts/prepare_library_sources.py` copies only those three earlier workbooks and writes checksums in `source-manifest.json`; use `--downloads-dir` if needed. Rebuild the frontend after updating assets.

Incomplete MRT-3 ridership, EDSA Busway survey and historical schedule references were removed from the application library and its public downloads at the user's request on 18 November 2026. The research source copies remain under `data/` for traceability. They lack measured passenger waiting times and the complete matched predictors, so they cannot supply valid waiting-time model results. The preparation script no longer republishes them.

Library selections go through the ordinary upload validator. Source labels and research approval checks remain in place. Use Upload Dataset for recorded research observations.
