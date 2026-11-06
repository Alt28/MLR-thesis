"""Local experiment state, revision checks, and calls to the shared research core."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
import json
import uuid
import joblib
import pandas as pd
from fastapi import HTTPException
from src.config import ResearchConfig, ROW_ID, PREDICTORS, TARGET
from src.experiment import prepare_experiment, run_experiment
from src.irregularity_detection import apply_reviews, review_fingerprint
from src.station_classification import StationClassifier, CLASSIFICATION_VERSION
from src.mlr_model import MLRModels
from src.evaluation import metrics
from src.transport_metadata import transport_labels, transport_summary
from src.dataset_units import documented_units
from src.export import export_experiment, result_tables


def now():
    return datetime.now(timezone.utc).isoformat()


def records(frame):
    return json.loads(frame.to_json(orient="records", double_precision=12))


class ExperimentStore:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.sessions = {}
        self.lock = RLock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mlr-local")

    def close(self):
        self.executor.shutdown(wait=True)

    def directory(self, sid):
        try:
            if uuid.UUID(sid).hex != sid: raise ValueError()
        except (ValueError, AttributeError):
            raise HTTPException(404, "Experiment not found.")
        return self.root / sid

    def save(self, session):
        folder = self.directory(session["id"])
        serializable = {k: v for k, v in session.items() if k not in ("prepared", "partials", "result", "folder")}
        temporary = folder / "metadata.tmp"
        temporary.write_text(json.dumps(serializable, indent=2, allow_nan=False), encoding="utf-8")
        temporary.replace(folder / "metadata.json")
        state_tmp = folder / "state.tmp"
        joblib.dump({"revision": session["revision"], "partials": session["partials"], "result": session["result"]}, state_tmp)
        state_tmp.replace(folder / "state.joblib")

    def get(self, sid):
        with self.lock:
            folder = self.directory(sid)
            if sid in self.sessions: return self.sessions[sid]
            path = folder / "metadata.json"
            if not path.exists(): raise HTTPException(404, "Experiment not found.")
            s = json.loads(path.read_text(encoding="utf-8"))
            s["prepared"] = prepare_experiment(folder / s["source_file"], ResearchConfig(**s["config"]))
            if s["prepared"].source_hash != s["source_hash"]:
                raise HTTPException(409, "The stored source file changed. Import it as a new experiment.")
            s.update(folder=folder, partials={}, result=None)
            if (folder / "state.joblib").exists():
                # Only server-created artifacts at generated paths are loaded. Uploads cannot supply this file.
                state = joblib.load(folder / "state.joblib")
                if state["revision"] == s["revision"]:
                    s.update(partials=state["partials"], result=state["result"])
            if s["status"] == "running":
                s.update(status="error", error="The previous training job was interrupted. You can run it again.")
            self.sessions[sid] = s
            return s

    def create(self, name, content):
        suffix = Path(name).suffix.lower()
        if suffix not in (".csv", ".xlsx"): raise ValueError("Upload a CSV or .xlsx Excel dataset.")
        sid = uuid.uuid4().hex
        folder = self.directory(sid)
        folder.mkdir()
        path = folder / ("source" + suffix)
        path.write_bytes(content)
        try:
            config = ResearchConfig(**documented_units(path))
            prepared = prepare_experiment(path, config)
        except Exception as exc:
            path.unlink(missing_ok=True)
            folder.rmdir()
            raise ValueError(f"Could not import the dataset: {exc}") from exc
        s = dict(id=sid, name=Path(name.replace("\\", "/")).name, created=now(), updated=now(), source_file=path.name,
                 source_hash=prepared.source_hash, config=config.to_dict(), revision=1, approved=False,
                 decisions={}, history=[], status="ready", error=None, export_dir=None,
                 prepared=prepared, partials={}, result=None, folder=folder)
        with self.lock:
            self.sessions[sid] = s
            self.save(s)
        return self.summary(s)

    def list(self):
        items = []
        for path in self.root.glob("*/metadata.json"):
            metadata = json.loads(path.read_text(encoding="utf-8"))
            items.append({k: metadata[k] for k in ("id", "name", "created", "revision")})
        return sorted(items, key=lambda s: s["created"], reverse=True)

    def check(self, s, revision):
        if s["status"] == "running": raise HTTPException(409, "Wait for the current training job to finish.")
        if s["revision"] != revision: raise HTTPException(409, "This experiment changed in another tab. Refresh before saving.")

    def invalidate(self, s, event):
        s["history"].append({"at": now(), "revision": s["revision"], **event})
        s.update(revision=s["revision"] + 1, updated=now(), status="ready", error=None, partials={}, result=None, export_dir=None)

    def configure(self, sid, request):
        with self.lock:
            s = self.get(sid)
            self.check(s, request.revision)
            config = ResearchConfig(**request.config).validate()
            prepared = prepare_experiment(s["folder"] / s["source_file"], config)
            reset_reviews = review_fingerprint(prepared) != review_fingerprint(s["prepared"])
            interaction_changed = any([list(term) for term in s["config"][key]] != [list(term) for term in config.to_dict()[key]] for key in ("pairwise_interactions", "higher_order_interactions"))
            self.invalidate(s, {"event": "configuration", "previous": s["config"], "new": config.to_dict(), "reviews_reset": reset_reviews})
            s["approved"] = request.approve_interactions or (s["approved"] and not interaction_changed)
            s["config"] = config.to_dict()
            s["prepared"] = prepared
            if reset_reviews: s["decisions"] = {}
            self.save(s)
            return self.summary(s)

    def review(self, sid, request):
        with self.lock:
            s = self.get(sid)
            self.check(s, request.revision)
            decisions = deepcopy(s["decisions"])
            decision = {"action": request.action, "reason": request.reason.strip(), "corrections": request.corrections}
            decisions[request.record_id] = decision
            apply_reviews(s["prepared"].training, s["prepared"].flags, decisions)
            self.invalidate(s, {"event": "review", "record_id": request.record_id, "previous": s["decisions"].get(request.record_id), "new": decision})
            s["decisions"] = decisions
            self.save(s)
            return self.summary(s)

    def summary(self, s):
        p = s["prepared"]
        train, audit = apply_reviews(p.training, p.flags, s["decisions"])
        classifier = StationClassifier(p.config).fit(train)
        combined = s["result"]
        classification_stale = combined is not None and getattr(combined.classifier, "method_version", 1) != CLASSIFICATION_VERSION
        metric_rows = []
        for label, fitted in s["partials"].items():
            prediction = fitted.predict(p.test)
            prefix = "Baseline" if label == "Baseline MLR" else "Enhanced"
            metric_rows.append({"Model": label, **metrics(p.test[TARGET], prediction[f"{prefix} Predicted Waiting Time"])})
        distribution = combined.predictions["Overall Station Classification"].value_counts().to_dict() if combined is not None else {}
        export = Path(s["export_dir"]) if s["export_dir"] else None
        study = getattr(combined, "study", {}) if combined is not None else {}
        return dict(id=s["id"], name=s["name"], created=s["created"], revision=s["revision"], status=s["status"], error=s["error"],
                    approved=s["approved"], config=s["config"], records=len(p.original), training=len(p.training), reviewed_training=len(train),
                    test=len(p.test), flagged=int(p.flags[ROW_ID].nunique()), reviewed=len(s["decisions"]),
                    metadata=[c for c in p.original.columns if c not in (*PREDICTORS, TARGET, ROW_ID)],
                    trained=list(s["partials"]), metrics=metric_rows, comparison=records(combined.comparison) if combined is not None else [],
                    conclusion=combined.conclusion if combined is not None else None,
                    warnings=combined.warnings if combined is not None else list(dict.fromkeys(w for m in s["partials"].values() for w in m.warnings)), distribution=distribution,
                    evidence=records(classifier.evidence), thresholds=records(classifier.thresholds.reset_index()),
                    figures=[f.stem for f in sorted((export / "figures").glob("*.png"))] if export else [],
                    classification_version=CLASSIFICATION_VERSION, classification_stale=classification_stale,
                    classification_rules=classifier.rule_metadata,
                    transport=transport_summary(p), provenance=getattr(p, "provenance", {}), study_available=bool(study),
                    study_metrics=records(study["metrics"]) if study else [],
                    study_comparisons=records(study["comparisons"]) if study else [],
                    research_protocol=study.get("metadata", {}),
                    export_ready=export is not None and export.exists() and not classification_stale)

    def table(self, sid, name, search="", offset=0, limit=25, transport_mode="all"):
        with self.lock:
            s = self.get(sid)
            p = s["prepared"]
            train, audit = apply_reviews(p.training, p.flags, s["decisions"])
            classifier = StationClassifier(p.config).fit(train)
            tables = {"dataset": p.original, "bounds": p.iqr_bounds.reset_index(),
                      "flags": p.flags.merge(audit, on=ROW_ID, how="left"), "audit": audit,
                      "history": pd.DataFrame([{**e, "Details": json.dumps({k: v for k, v in e.items() if k not in ("at", "revision", "event")})} for e in s["history"]]).reindex(columns=["at", "revision", "event", "Details"]),
                      "thresholds": classifier.thresholds.reset_index(), "evidence": classifier.evidence}
            if s["partials"]:
                tables["coefficients"] = pd.concat([m.coefficients() for m in s["partials"].values()], ignore_index=True)
                tables["diagnostics"] = pd.DataFrame([d for m in s["partials"].values() for d in m.diagnostics])
            if s["result"] is not None:
                tables.update(result_tables(s["result"]))
                output = s["result"].predictions
                tables["classification"] = output[[c for c in output.columns if c not in ("Baseline Error (actual - predicted)", "Enhanced Error (actual - predicted)")]]
            if name not in tables: raise HTTPException(404, "This result is not available yet.")
            frame = tables[name]
            if transport_mode != "all":
                if transport_mode not in ("bus", "train", "unspecified") or name not in ("predictions", "classification", "dataset"):
                    raise HTTPException(400, "Transport filters apply only to dataset and prediction records.")
                labels, _ = transport_labels(p.original, p.config)
                ids = labels.index[labels.eq(transport_mode)]
                frame = frame.loc[frame[ROW_ID].isin(ids)]
            if search:
                mask = frame.astype(str).apply(lambda col: col.str.contains(search, case=False, regex=False)).any(axis=1)
                frame = frame.loc[mask]
            return {"columns": list(frame.columns), "rows": records(frame.iloc[offset:offset + limit]), "total": len(frame), "offset": offset}

    def record(self, sid, record_id):
        s = self.get(sid)
        p = s["prepared"]
        if record_id not in p.original.index: raise HTTPException(404, "Record not found.")
        return {"original": records(p.original.loc[[record_id]])[0], "decision": s["decisions"].get(record_id), "flagged": record_id in set(p.flags[ROW_ID])}

    def analyze(self, sid, request):
        """Confirm explicit research choices, then run the existing two-model workflow."""
        from ..schemas.requests import TrainingRequest
        with self.lock:
            s = self.get(sid)
            self.check(s, request.revision)
            if not s["approved"] and not request.approve_interactions:
                raise HTTPException(409, "Approve the selected interaction terms before analysis.")
            remaining = sorted(set(s["prepared"].flags[ROW_ID]) - set(s["decisions"]))
            if remaining and not request.retain_remaining:
                raise HTTPException(409, "Review the IQR-flagged observations before analysis.")
            if remaining and not request.retain_reason.strip():
                raise ValueError("Provide a reason for retaining the remaining flagged observations.")
            decisions = deepcopy(s["decisions"])
            for rid in remaining:
                decisions[rid] = dict(action="retain", reason=request.retain_reason.strip(), corrections={})
            apply_reviews(s["prepared"].training, s["prepared"].flags, decisions)
            if remaining or not s["approved"]:
                self.invalidate(s, {"event": "analysis_confirmation", "retained_records": remaining,
                                    "retain_reason": request.retain_reason.strip() if remaining else None,
                                    "interaction_specification_approved": True})
                s.update(decisions=decisions, approved=True)
                self.save(s)
            return self.train(sid, TrainingRequest(revision=s["revision"], selection="both"))

    def train(self, sid, request):
        with self.lock:
            s = self.get(sid)
            self.check(s, request.revision)
            if request.selection in ("both", "enhanced") and not s["approved"]:
                raise HTTPException(409, "Apply your interaction specification before training the enhanced model.")
            s.update(status="running", error=None)
            self.save(s)
            self.executor.submit(self._train_job, sid, request.selection)
            return {"status": "running", "revision": s["revision"]}

    def _train_job(self, sid, selection):
        s = self.get(sid)
        try:
            train, _ = apply_reviews(s["prepared"].training, s["prepared"].flags, s["decisions"])
            new_partials = dict(s["partials"])
            for name, value in [("Baseline MLR", "baseline"), ("Enhanced MLR", "enhanced")]:
                if selection in ("both", value): new_partials[name] = MLRModels(s["prepared"].config).fit(train, value)
            result, export_dir = None, None
            if len(new_partials) == 2:
                combined = deepcopy(new_partials["Baseline MLR"])
                enhanced = new_partials["Enhanced MLR"]
                combined.models.update(enhanced.models)
                combined.diagnostics.extend(enhanced.diagnostics)
                combined.warnings = list(dict.fromkeys(combined.warnings + enhanced.warnings))
                result = run_experiment(s["prepared"], s["decisions"], fitted_models=combined)
                export_dir = export_experiment(result, s["folder"] / "runs")
                (export_dir / "web_experiment.json").write_text(json.dumps({"experiment_id": sid, "revision": s["revision"], "dataset_name": s["name"], "interaction_specification_approved": s["approved"], "history": s["history"]}, indent=2), encoding="utf-8")
                # Full bundle includes all research artifacts, without including itself.
                from zipfile import ZipFile, ZIP_DEFLATED
                with ZipFile(export_dir / "experiment-bundle.zip", "w", ZIP_DEFLATED) as archive:
                    for path in export_dir.rglob("*"):
                        if path.is_file() and path.suffix != ".zip": archive.write(path, path.relative_to(export_dir))
            with self.lock:
                s.update(partials=new_partials, result=result, export_dir=str(export_dir) if export_dir else None, status="complete" if result is not None else "partial", updated=now())
                self.save(s)
        except Exception as exc:
            with self.lock:
                s.update(status="error", error=str(exc))
                self.save(s)

    def figure(self, sid, name, theme="light"):
        with self.lock:
            path = self.artifact(sid, "figure", name)
            if theme == "light": return path
            result = self.get(sid)["result"]
            directory = path.parent.parent / "web-figures-dark"
        # Use the same worker as training/export to serialize Matplotlib rendering.
        return self.executor.submit(self._dark_figure, result, directory, name).result()

    @staticmethod
    def _dark_figure(result, directory, name):
        path = directory / f"{name}.png"
        if not path.exists():
            from src.visualization import save_figures
            save_figures(result, directory, dark=True)
        return path

    def artifact(self, sid, kind, name=None):
        s = self.get(sid)
        if not s["export_dir"]: raise HTTPException(409, "Train both models to create a complete result bundle.")
        directory = Path(s["export_dir"])
        if kind == "figure":
            if name not in self.summary(s)["figures"]: raise HTTPException(404, "Figure not found.")
            path = directory / "figures" / f"{name}.png"
        elif kind == "csv":
            allowed = result_tables(s["result"])
            if name not in allowed: raise HTTPException(404, "Table not found.")
            path = directory / "csv" / f"{name}.csv"
        else:
            filenames = {"excel": "experiment.xlsx", "bundle": "experiment-bundle.zip", "config": "config.json", "reviews": "review_decisions.json"}
            if kind not in filenames: raise HTTPException(404, "Export type not found.")
            path = directory / filenames[kind]
        if not path.is_file(): raise HTTPException(404, "Artifact not found.")
        return path
