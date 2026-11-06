# Transit Lab dataset library

The two `transit_*_SYNTHETIC_DEMO.xlsx` workbooks contain **synthetic software fixtures**, not real Philippine bus/train observations. Each has 180 fictional rows, explicit transport metadata and a `Sources_Methodology` sheet documenting its simulated origin and units.

The earlier 500-, 200- and 40-row workbooks are copied without alteration from the user's supplied files. They remain demo/prototype data. The 40-row file has constant predictors and undefined units; including it in the picker does not repair those research limitations or guarantee a final classification. The original files do not label per-row transport modes, and none are inferred here.

Two Philippine reference CSV files are also included: MRT-3 daily ridership (121 calendar days, four blanks) and historical Metro Manila GTFS schedules (1,864 windows, calendar ends June 2020). They are incomplete for model fitting: measured waiting times and matching predictors are missing. Source links and limitations are documented in `docs/PHILIPPINE_DATA_SOURCES.md`. The MRT-3 report is hosted by a third party and requires agency verification. The Sakay/DOTC source license is included as `SAKAY-GTFS-LICENSE.md`; no affiliation or endorsement is implied.

`scripts/prepare_library_sources.py` copies the three named earlier workbooks and the prepared research references into this folder and writes `source-manifest.json` with SHA-256 checksums. It does not generate, rescale or relabel their values. Use `--downloads-dir` if the earlier workbooks are stored elsewhere.

Generate them with `.venv\Scripts\python.exe scripts\prepare_demo_library.py`, then rebuild the frontend. Generation uses fixed seeds and an arbitrary software formula, not an empirically validated transportation relationship. In particular, artificial traffic categories in the train file do not establish their suitability for a real rail study.

`frontend/src/services/datasetLibrary.ts` lists the seven entries. Every card sends its file through the ordinary upload API directly, without a browser download. Complete workbooks become the active dataset after validation. The incomplete reference CSVs fail required-column validation, show the missing fields and preserve the previous experiment. No model calculations, automatic approvals, or external cloud-account connections are introduced. Source documentation and the GTFS license remain bundled with the project.

Picker layout reference: https://lung-nodule-detection-system.vercel.app/ (inspected 6 November 2026). This implementation uses Transit Lab's own components and icons; no medical files or source code were copied.
