import json
from pathlib import Path
import subprocess
import sys
import pandas as pd


def test_cli_inspect_configured_run_and_empty_rejection(tmp_path, fixture_data):
    fixture_path = tmp_path / "ARTIFICIAL_SOFTWARE_FIXTURE.csv"
    fixture_data.to_csv(fixture_path, index=False)
    project = Path(__file__).resolve().parents[1]
    def invoke(*args):
        return subprocess.run([sys.executable, str(project / "main.py"), *map(str, args)], cwd=project, capture_output=True, text=True)
    inspections = tmp_path / "inspections"
    inspect = invoke("inspect", fixture_path, "--output", inspections)
    assert inspect.returncode == 0, inspect.stderr
    folder = next(inspections.iterdir())
    config = json.loads((folder / "config.json").read_text())
    config["category_severity"] = {"Traffic Condition": {"A": 0, "B": 1, "C": 3}, "Weather Condition": {"W0": 0, "W1": 3}, "Time of Day": {"T0": 0, "T1": 3}}
    config["numerical_directions"]["Route Distance"] = "higher"
    config["vehicle_frequency_unit"] = "fixture vehicles/hour"
    config["route_distance_unit"] = "fixture km"
    (folder / "config.json").write_text(json.dumps(config))
    exports = tmp_path / "exports"
    run = invoke("run", fixture_path, "--config", folder / "config.json", "--reviews", folder / "review_decisions.json", "--output", exports)
    assert run.returncode == 0, run.stderr
    bundle = next(exports.iterdir())
    predicted = pd.read_csv(bundle / "csv" / "predictions.csv")
    assert predicted["Multi-Factor Station Score"].notna().all()
    assert not predicted["Overall Station Classification"].eq("Pending configuration").any()
    rejected = invoke("run", project / "data" / "transportation_template.csv")
    assert rejected.returncode == 1
    assert "no observations" in rejected.stderr
