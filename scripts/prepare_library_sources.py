"""Copy explicitly selected earlier workbooks and researched references into the picker."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil


def prepare(downloads):
    root = Path(__file__).resolve().parents[1]
    target = root / 'frontend/public/assets/datasets'
    target.mkdir(parents=True, exist_ok=True)
    names = ['transportation_dataset_500_demo_validated.xlsx',
             'transportation_dataset_200_demo_fixed.xlsx',
             'transportation_dataset_40_ph_internet_rows.xlsx']
    files = [(downloads / name, name) for name in names]
    references = root / 'data/philippine_sources'
    files += [(references / 'prepared' / name, name) for name in [
        'mrt3_daily_ridership_jan_apr_2024.csv',
        'metro_manila_historical_scheduled_frequency.csv']]
    files += [(references / 'raw/sakay_gtfs/LICENSE.md', 'SAKAY-GTFS-LICENSE.md')]
    if any(not path.is_file() for path, _ in files):
        raise FileNotFoundError('A requested source is missing. Provide --downloads-dir with the three earlier workbooks.')
    manifest = {}
    for source, name in files:
        shutil.copyfile(source, target / name)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        assert hashlib.sha256((target / name).read_bytes()).hexdigest() == digest
        manifest[name] = {'sha256': digest, 'bytes': source.stat().st_size}
    (target / 'source-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Copied {len(files)} source files unchanged; checksums saved.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--downloads-dir', type=Path, default=Path.home() / 'Downloads')
    prepare(parser.parse_args().downloads_dir)
