# Research utilities

Current-schema commands are main.py (template, inspect, run) and scripts/field_data.py (new, build). Their inputs follow docs/SIX_PREDICTOR_MIGRATION.md.

`collect_real_bus_train_six_predictors_v2.py` now includes system import exports through `etl_system_export.py`. Install the optional `requirements-etl.txt` dependencies and follow [the collected data guide](../docs/COLLECTED_DATA_IMPORT.md). It preserves unknown waiting times, keeps unverified bus frequency blank, and can register bounded CSV parts and audited Excel overviews in the local Dataset Library.

`build_collector_folder.py DESTINATION --data-folder EXISTING_DATA` packages these scripts into a separate folder with `collector_launcher.py`, setup/run batch files, its own environment, and preserved `settings.json`. The collector works without running the web app and reuses existing raw files. Use `collector_launcher.py --check` to verify installation without collecting or changing data.

`--mode waiting-sources` (menu option 5) uses `etl_waiting_sources.py` to collect Austin observed arrival-to-bus-departure waits and Australian self-reported train waits. It saves two source-review workbooks, a field-availability audit and original-source provenance. Neither source has the current six predictors with the required target definition, so this mode does not register library training data, fill missing predictors, merge unrelated places or train models. See the collected-data guide for the exact source years, definitions and extraction exclusions.

The prepare_demo_library.py, demonstrate_enhancement.py, prepare_bus_train_review.py, prepare_library_sources.py, prepare_philippine_sources.py, build_real_source_review.py, and illustrated-guide generators preserve historical preparation/review work. Their old-schema examples and outputs are not current model inputs. Do not regenerate historical examples as new research evidence or rename their columns to imply measured new variables. Use the current schema tests for software verification.

Historical Word/PDF/screenshot materials remain archived and explicitly marked as superseded. Original source manifests and source-specific extraction scripts are retained for audit.
