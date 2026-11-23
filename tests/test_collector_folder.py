"""Verify the separate runner preserves paths, settings and sequential library writes."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_collector_folder import build
from collector_launcher import settings, command


def test_bundle_preserves_existing_data_and_reuses_directories(tmp_path):
    data = tmp_path / 'Existing Data'
    raw = data / 'raw_data_downloads'; raw.mkdir(parents=True)
    original = raw / 'source.txt'; original.write_text('Existing artificial fixture')
    target = build(tmp_path / 'Collector', data, tmp_path / 'system library')
    config = settings(target / 'settings.json')
    assert config['cache_dir'] == str(raw.resolve())
    assert config['output_dir'] == str((data / 'system_imports').resolve())
    assert original.read_text() == 'Existing artificial fixture'
    assert not (target / 'raw_data_downloads').exists()
    assert len(json.loads((target / 'bundle_manifest.json').read_text())['code_sources']) == 6
    config['bus_rows_per_day'] = 12
    (target / 'settings.json').write_text(json.dumps(config))
    build(target, data, tmp_path / 'different library')
    assert settings(target / 'settings.json') == config


def test_runner_resolves_settings_paths_and_keeps_mode_arguments_separate(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text(json.dumps({'cache_dir': 'raw data', 'output_dir': 'output data',
                               'library_dir': 'system library', 'bus_months': ['2024-03'],
                               'token_file': 'credentials/file.txt', 'bus_rows_per_day': 7}))
    config = settings(path)
    assert config['cache_dir'] == str((tmp_path / 'raw data').resolve())
    bus = command('bus', config)
    assert bus[bus.index('--cache') + 1] == config['cache_dir']
    assert bus[bus.index('--bus-rows-per-day') + 1] == '7'
    assert '--token-file' not in bus
    train = command('train', config)
    assert '--months' not in train and '--token-file' not in train
    arrivals = command('bus-arrivals', config)
    assert '--library-dir' not in arrivals
    assert arrivals[arrivals.index('--token-file') + 1] == config['token_file']
    waiting = command('waiting-sources', config)
    assert '--library-dir' not in waiting and '--token-file' not in waiting and '--months' not in waiting
