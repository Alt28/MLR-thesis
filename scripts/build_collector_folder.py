"""Create a standalone collector folder without moving datasets or overwriting settings."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

PROJECT = Path(__file__).resolve().parents[1]
CODE = ['collect_real_bus_train_six_predictors_v2.py', 'etl_system_export.py',
        'etl_511_archive.py', 'etl_waiting_sources.py', 'etl_linked_waits.py', 'collector_launcher.py']


def build(destination, data_folder, library):
    destination = Path(destination).resolve()
    data_folder = Path(data_folder).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    for name in CODE:
        shutil.copy2(PROJECT / 'scripts' / name, destination / name)
    shutil.copy2(PROJECT / 'requirements-etl.txt', destination / 'requirements.txt')
    settings = destination / 'settings.json'
    if not settings.exists():
        settings.write_text(json.dumps({
            'cache_dir': str(data_folder / 'raw_data_downloads'),
            'output_dir': str(data_folder / 'system_imports'),
            'library_dir': str(Path(library).resolve()) if library else '',
            'bus_months': ['2024-03', '2024-07', '2024-11'],
            'train_days': [], 'bus_rows_per_day': 64, 'token_file': '',
        }, indent=2), encoding='utf-8')
    setup = '''@echo off
cd /d "%~dp0"
if not exist ".venv\\Scripts\\python.exe" (
    python -m venv .venv
    if errorlevel 1 exit /b 1
)
".venv\\Scripts\\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
".venv\\Scripts\\python.exe" collector_launcher.py --check
'''
    run = '''@echo off
cd /d "%~dp0"
if not exist ".venv\\Scripts\\python.exe" (
    echo Run Setup Collector.bat first.
    pause
    exit /b 1
)
".venv\\Scripts\\python.exe" collector_launcher.py %*
pause
'''
    (destination / 'Setup Collector.bat').write_bytes(setup.replace('\n', '\r\n').encode())
    (destination / 'Run Collector.bat').write_bytes(run.replace('\n', '\r\n').encode())
    (destination / '.gitignore').write_text('.venv/\n__pycache__/\nsettings.json\n*token*\n', encoding='utf-8')
    guide = '''DATA COLLECTOR MERGER

This folder contains the collector and merger scripts, separate from the web system.
It has its own Python environment. The web server does not need to run during collection.

HOW TO USE
1. Run Setup Collector.bat once if the collector is not yet installed.
2. Double-click Run Collector.bat.
3. Choose Train, Bus, both, 511 archive, or published waiting-time source review.

WHAT EACH OPTION DOES
Train: combines MTA hourly entries, recorded train departures, and the official
station crosswalk by station complex and local hour. Creates six predictor fields.
Bus: processes AC Transit recorded APC boardings. Door counts stay in the audit;
Vehicle Frequency is unverified and stays blank. Default export is a daily subset.
Both: runs Train and then Bus, updating the system library sequentially.
511 archive: downloads an additional bus-arrival source, requiring your own free
511 access token. Downloading alone does not verify or complete a cross-source merge.
Waiting-time sources: downloads real Austin bus observations and an Australian train
survey. Creates SEPARATE source-review workbooks with recorded waits and missing-field
checks. Austin measures arrival to bus departure, not boarding; the train waits are
self-reported. Neither supplies all six current predictors. This option does NOT
register a training dataset, combine unrelated places, train a model, or enable Analyze.
Outputs are under system_imports\\waiting_time_source_review; open READ_FIRST.txt.

YOUR FILES
settings.json points to your EXISTING raw downloads, output folder and system library.
Those large files were not moved or duplicated. Existing cached downloads are reused.
To use different folders later, edit the corresponding paths in settings.json.
Leave library_dir empty to collect without registering outputs in the web system.
Keep the five Python files together; the collector imports its companion helpers.

WHY ANALYZE MAY BE DISABLED IN THE WEB SYSTEM
The original NYC Train and AC Transit Bus files have no passenger waiting times. They cannot train
the waiting-time models. To predict blank waiting times, a compatible model must
first have been trained using a SEPARATE dataset with observed waiting times.
Saved models using the old predictors cannot be reused with the new six predictors.
The input-availability checkbox does not train a model or supply missing values.
The Bus review file also needs verified Vehicle Frequency before prediction.

511 ACCESS
Request a free token at https://511.org/open-data/token.
Store it in a local text file outside this folder; put only its path in token_file
in settings.json. No token is needed for the existing Train or APC source collection.

OPTIONAL COMMANDS (from this folder)
.venv\\Scripts\\python.exe collector_launcher.py --check
.venv\\Scripts\\python.exe collector_launcher.py --mode train
.venv\\Scripts\\python.exe collector_launcher.py --mode bus
.venv\\Scripts\\python.exe collector_launcher.py --mode both
.venv\\Scripts\\python.exe collector_launcher.py --mode waiting-sources
'''
    (destination / 'READ ME FIRST.txt').write_text(guide, encoding='utf-8')
    (destination / 'bundle_manifest.json').write_text(json.dumps({
        'code_sources': {name: hashlib.sha256((destination / name).read_bytes()).hexdigest() for name in CODE},
        'datasets_moved': False, 'settings_preserved_if_existing': True,
    }, indent=2), encoding='utf-8')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--data-folder', type=Path, required=True)
    parser.add_argument('--library', type=Path, default=PROJECT / 'data' / 'collected')
    args = parser.parse_args()
    print(build(args.destination, args.data_folder, args.library))
