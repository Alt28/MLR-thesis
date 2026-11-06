"""Launch the local web application, or run reproducible CLI experiments."""
import argparse
import json
from pathlib import Path
import sys
from src.config import ResearchConfig
from src.data_loader import write_templates
from src.experiment import prepare_experiment, run_experiment
from src.export import export_experiment, spreadsheet_safe
from src.station_classification import StationClassifier
from src.irregularity_detection import review_bundle, read_review_bundle


def launch_web(host="127.0.0.1", port=8000, open_browser=True):
    import threading
    import time
    import urllib.request
    import webbrowser
    import uvicorn

    root = Path(__file__).resolve().parent
    if not (root / "frontend" / "dist" / "index.html").is_file():
        raise ValueError("Build the web interface first: run setup.ps1, or npm run build in frontend/.")
    browser_host = "127.0.0.1" if host == "0.0.0.0" else host
    url = f"http://{browser_host}:{port}"

    def running():
        try:
            with urllib.request.urlopen(url + "/api/health", timeout=1) as response:
                return json.load(response).get("application") == "transit-lab"
        except (OSError, ValueError):
            return False

    if running():
        print(f"Transit Lab is already running at {url}")
        if open_browser: webbrowser.open(url)
        return
    print(f"Transit Lab web application: {url}\nKeep this window open. Press Ctrl+C to stop the local server.")
    if open_browser:
        def browser_when_ready():
            for _ in range(60):
                if running():
                    webbrowser.open(url)
                    return
                time.sleep(.5)
        threading.Thread(target=browser_when_ready, daemon=True).start()
    uvicorn.run("backend.app.main:app", host=host, port=port, log_level="info")


def main():
    parser = argparse.ArgumentParser(description="Local thesis MLR research system")
    sub = parser.add_subparsers(dest="command")
    web = sub.add_parser("web", help="Start the local web application (default)")
    web.add_argument("--host", default="127.0.0.1", help="Use 0.0.0.0 only for a trusted local network")
    web.add_argument("--port", type=int, default=8000)
    web.add_argument("--no-browser", action="store_true", help="Do not open a browser automatically")
    template = sub.add_parser("template", help="Write empty CSV and Excel templates")
    template.add_argument("--directory", default="data")
    for name in ("inspect", "run"):
        command = sub.add_parser(name, help="Inspect training data" if name == "inspect" else "Train, evaluate, and export")
        command.add_argument("dataset", help="Recorded CSV or XLSX dataset")
        command.add_argument("--config", help="Optional JSON configuration snapshot; otherwise src/config.py")
        command.add_argument("--output", default="outputs")
        if name == "run": command.add_argument("--reviews", help="Dataset-bound JSON bundle of flagged-training review decisions")
    args = parser.parse_args()
    try:
        if args.command in (None, "web"):
            launch_web(getattr(args, "host", "127.0.0.1"), getattr(args, "port", 8000), not getattr(args, "no_browser", False))
            return 0
        if args.command == "template":
            write_templates(args.directory)
            print(f"Empty templates are in {Path(args.directory).resolve()}")
            return 0
        config = (ResearchConfig(**json.loads(Path(args.config).read_text(encoding="utf-8")))
                  if args.config else ResearchConfig())
        prepared = prepare_experiment(args.dataset, config)
        if args.command == "inspect":
            from datetime import datetime, timezone
            from uuid import uuid4
            folder = Path(args.output) / ("inspection_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + uuid4().hex[:6])
            folder.mkdir(parents=True, exist_ok=False)
            classifier = StationClassifier(config).fit(prepared.training)
            for name, frame in {"iqr_flags": prepared.flags, "iqr_bounds": prepared.iqr_bounds.reset_index(),
                                "category_evidence": classifier.evidence, "numerical_quartiles": classifier.thresholds.reset_index()}.items():
                spreadsheet_safe(frame).to_csv(folder / f"{name}.csv", index=False, encoding="utf-8-sig")
            (folder / "config.json").write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
            (folder / "review_decisions.json").write_text(json.dumps(review_bundle(prepared, {}), indent=2), encoding="utf-8")
            print(f"Training-only inspection saved to {folder.resolve()}")
            print(f"Training: {len(prepared.training)}; test: {len(prepared.test)}; flagged training rows: {prepared.flags['Record ID'].nunique()}")
        else:
            reviews = read_review_bundle(prepared, json.loads(Path(args.reviews).read_text(encoding="utf-8"))) if args.reviews else None
            result = run_experiment(prepared, reviews)
            folder = export_experiment(result, args.output)
            print(result.metrics.to_string(index=False))
            print(result.conclusion)
            for warning in result.warnings: print("Note:", warning)
            print(f"Exported: {folder}")
        return 0
    except (ValueError, TypeError, OSError, KeyError) as exc:
        print(f"Cannot complete experiment: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
