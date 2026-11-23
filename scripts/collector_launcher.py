"""Run the standalone collector bundle using its explicit data directories."""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def settings(path):
    config = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    for name in ('cache_dir', 'output_dir'):
        if not str(config.get(name, '')).strip():
            raise ValueError(f'{name} is required in settings.json.')
    # Relative folders follow the configuration file, not the invoking shell.
    for name in ('cache_dir', 'output_dir', 'library_dir', 'token_file'):
        value = config.get(name)
        if value:
            target = Path(value).expanduser()
            config[name] = str((Path(path).resolve().parent / target).resolve() if not target.is_absolute() else target.resolve())
    return config


def command(mode, config):
    args = [sys.executable, str(ROOT / 'collect_real_bus_train_six_predictors_v2.py'),
            '--mode', mode, '--cache', config['cache_dir'], '--out', config['output_dir']]
    if config.get('library_dir') and mode not in ('bus-arrivals', 'waiting-sources', 'linked-waits'):
        args += ['--library-dir', config['library_dir']]
    if mode in ('bus', 'bus-arrivals') and config.get('bus_months'):
        args += ['--months', *config['bus_months']]
    if mode == 'train' and config.get('train_days'):
        args += ['--days', *config['train_days']]
    if mode == 'bus':
        args += ['--bus-rows-per-day', str(config.get('bus_rows_per_day', 64))]
    if mode == 'bus-arrivals' and config.get('token_file'):
        args += ['--token-file', config['token_file']]
    return args


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['train', 'bus', 'bus-arrivals', 'waiting-sources', 'linked-waits', 'both'])
    parser.add_argument('--settings', type=Path, default=ROOT / 'settings.json')
    parser.add_argument('--check', action='store_true', help='Check this folder without collecting or changing datasets')
    args = parser.parse_args()
    config = settings(args.settings)
    required_files = ['collect_real_bus_train_six_predictors_v2.py', 'etl_system_export.py', 'etl_511_archive.py', 'etl_waiting_sources.py', 'etl_linked_waits.py']
    missing_files = [name for name in required_files if not (ROOT / name).is_file()]
    missing_packages = [name for name in ('duckdb', 'openpyxl', 'tzdata') if importlib.util.find_spec(name) is None]
    if (args.check or args.mode in (None, 'waiting-sources')) and importlib.util.find_spec('pypdf') is None:
        missing_packages.append('pypdf')
    if args.check or args.mode in (None, 'linked-waits'):
        for name in ('access_parser', 'zipfile_deflate64'):
            if importlib.util.find_spec(name) is None: missing_packages.append(name)
    if missing_files: raise ValueError('Collector files are missing: ' + ', '.join(missing_files))
    if missing_packages: raise ValueError('Run Setup Collector.bat first. Missing packages: ' + ', '.join(missing_packages))
    if args.check:
        print('Collector scripts and dependencies are ready.')
        for name in ('cache_dir', 'output_dir', 'library_dir'):
            print(f'{name}: {config.get(name) or "Not connected to a system library"}')
        print('511 token file configured:', bool(config.get('token_file')))
        print('No data downloaded, merged, or changed by this check.')
        return 0
    mode = args.mode
    if not mode:
        print('DATA COLLECTOR MERGER\n1. Collect and merge Train sources\n2. Prepare Bus APC source review\n3. Run Train then Bus\n4. Download 511 Bus arrival archive (access token required)\n5. Collect published waiting-time sources for review (not training-ready)\n6. Merge official Chile Bus/Train waiting-time survey tables (source review)\n0. Exit')
        choice = input('Choose an option: ').strip()
        if choice == '0': return 0
        mode = {'1': 'train', '2': 'bus', '3': 'both', '4': 'bus-arrivals', '5': 'waiting-sources', '6': 'linked-waits'}.get(choice)
        if not mode: raise ValueError('Choose one of the listed menu options.')
    for task in (['train', 'bus'] if mode == 'both' else [mode]):
        print(f'Running {task} collection...', flush=True)
        result = subprocess.run(command(task, config), cwd=ROOT, check=False)
        if result.returncode: return result.returncode
    print('Finished. See the configured output folder and source manifests.')
    return 0


if __name__ == '__main__':
    try: raise SystemExit(main())
    except (ValueError, OSError) as exc: raise SystemExit(str(exc)) from None
