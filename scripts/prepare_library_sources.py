"""Copy explicitly selected earlier demo/prototype workbooks into the picker."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil


def prepare(downloads):
    root = Path(__file__).resolve().parents[1]
    target = root / 'frontend/public/assets/datasets'
    target.mkdir(parents=True, exist_ok=True)
    names = ['transportation_dataset_200_demo_fixed.xlsx',
             'transportation_dataset_40_ph_internet_rows.xlsx']
    files = [(downloads / name, name) for name in names]
    if any(not path.is_file() for path, _ in files):
        missing = [str(path) for path, _ in files if not path.is_file()]
        raise FileNotFoundError('Requested source files are missing: ' + ', '.join(missing))
    manifest_path = target / 'source-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    for source, name in files:
        shutil.copyfile(source, target / name)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        assert hashlib.sha256((target / name).read_bytes()).hexdigest() == digest
        manifest[name] = {'sha256': digest, 'bytes': source.stat().st_size}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Copied {len(files)} source files unchanged; checksums saved.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--downloads-dir', type=Path, default=Path.home() / 'Downloads')
    args = parser.parse_args()
    prepare(args.downloads_dir)
