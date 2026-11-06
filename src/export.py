"""Complete experiment bundles with configuration, provenance, and review history."""
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import json
import platform
import uuid
import joblib
import pandas as pd
from .config import ROW_ID
from .visualization import save_figures
from .irregularity_detection import review_bundle


def spreadsheet_safe(frame):
    """Escape spreadsheet formula prefixes in source text; numeric values stay numeric."""
    return frame.map(lambda x: "'" + x if isinstance(x, str) and x.startswith(("=", "+", "-", "@", "\t", "\r")) else x)


def result_tables(result):
    prepared = result.prepared
    split = pd.DataFrame({ROW_ID: list(prepared.training.index) + list(prepared.test.index),
                          "Partition": ["training"] * len(prepared.training) + ["test"] * len(prepared.test)})
    split["Used for Training"] = split[ROW_ID].isin(result.training.index)
    split["Used for Original Training (A)"] = split.Partition.eq("training")
    split["Used for Reviewed Training (B/C)"] = split["Used for Training"]
    flags = prepared.flags.merge(result.audit, on=ROW_ID, how="left")
    coefficients = result.models.coefficients()
    tables = {
        "predictions": result.predictions,
        "metrics": result.metrics,
        "comparison": result.comparison,
        "coefficients": coefficients,
        "interaction_coefficients": coefficients[coefficients.Type.isin(["pairwise", "higher-order"])],
        "selected_interactions": pd.DataFrame([
            {"Order": order, "Predictors": " × ".join(term), "Main Effects Retained": True}
            for order, terms in (("pairwise", prepared.config.pairwise_interactions),
                                 ("higher-order", prepared.config.higher_order_interactions))
            for term in terms
        ], columns=["Order", "Predictors", "Main Effects Retained"]),
        "iqr_flags": flags,
        "iqr_bounds": prepared.iqr_bounds.reset_index(),
        "review_audit": result.audit,
        "category_evidence": result.classifier.evidence,
        "severity_thresholds": result.classifier.thresholds.reset_index(),
        "category_encoding": result.models.features.encoding_table(),
        "model_diagnostics": pd.DataFrame(result.models.diagnostics),
        "split_membership": split,
        "original_training": prepared.training,
        "reviewed_training": result.training,
        "original_test": prepared.test,
        "warnings": pd.DataFrame({"Warning": result.warnings}),
    }
    study = getattr(result, "study", {})
    if study:
        original_coefficients = study["original_model"].coefficients().copy()
        original_coefficients["Model"] = "A: Traditional MLR - original training data"
        tables.update(study_metrics=study["metrics"], study_comparisons=study["comparisons"],
                      study_predictions=study["predictions"], original_coefficients=original_coefficients,
                      original_model_checks=pd.DataFrame(study["original_model"].diagnostics))
    provenance = getattr(prepared, "provenance", {})
    if provenance:
        tables["source_notes"] = pd.DataFrame(provenance.get("workbook_notes", []))
        if tables["source_notes"].empty:
            tables["source_notes"] = pd.DataFrame(columns=["Sheet", "Row", "Note"])
        tables["research_documentation"] = pd.DataFrame([
            {"Field": "Source status", "Value": provenance.get("status", "undocumented")},
            {"Field": "Interpretation", "Value": provenance.get("message", "")},
            *[{"Field": k, "Value": v} for k, v in provenance.get("researcher_notes", {}).items()],
        ])
    return tables


def export_experiment(result, output_root="outputs"):
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid.uuid4().hex[:6]
    directory = Path(output_root).resolve() / run_id
    directory.mkdir(parents=True, exist_ok=False)
    csv_dir = directory / "csv"
    csv_dir.mkdir()
    tables = result_tables(result)
    with pd.ExcelWriter(directory / "experiment.xlsx", engine="openpyxl") as writer:
        for name, table in tables.items():
            safe = spreadsheet_safe(table)
            safe.to_csv(csv_dir / f"{name}.csv", index=False, encoding="utf-8-sig")
            safe.to_excel(writer, sheet_name=name[:31], index=False)
            sheet = writer.sheets[name[:31]]
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for column in sheet.columns:
                sheet.column_dimensions[column[0].column_letter].width = min(48, max(14, len(str(column[0].value)) + 2))
    rules = getattr(result.classifier, "rule_metadata", {"classification_version": 1})
    (directory / "classification_rules.json").write_text(json.dumps(rules, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    provenance = getattr(result.prepared, "provenance", {})
    study = getattr(result, "study", {})
    (directory / "data_provenance.json").write_text(json.dumps(provenance, indent=2, ensure_ascii=False), encoding="utf-8")
    (directory / "research_protocol.json").write_text(json.dumps(study.get("metadata", {}), indent=2, ensure_ascii=False), encoding="utf-8")
    config = result.prepared.config.to_dict()
    decisions = {row[ROW_ID]: {"action": row["Action"], "reason": row["Reason"],
                              "corrections": json.loads(row["Corrections"])}
                 for _, row in result.audit.iterrows() if row["Action"] != "retain_unreviewed"}
    (directory / "review_decisions.json").write_text(json.dumps(review_bundle(result.prepared, decisions), indent=2), encoding="utf-8")
    config_text = json.dumps(config, indent=2, ensure_ascii=False)
    (directory / "config.json").write_text(config_text, encoding="utf-8")
    packages = {name: version(name) for name in ("numpy", "pandas", "scikit-learn", "matplotlib", "openpyxl", "joblib")}
    source_root = Path(__file__).resolve().parent.parent
    code_paths = [source_root / "main.py", *sorted((source_root / "src").glob("*.py")), *sorted((source_root / "backend").rglob("*.py"))]
    code_hashes = {str(p.relative_to(source_root)): sha256(p.read_bytes()).hexdigest() for p in code_paths}
    manifest = {
        "run_id": run_id, "created_utc": datetime.now(timezone.utc).isoformat(),
        "source": result.prepared.source, "source_sha256": result.prepared.source_hash,
        "config_sha256": sha256(config_text.encode("utf-8")).hexdigest(),
        "python": platform.python_version(), "packages": packages, "source_code_sha256": code_hashes,
        "training_original": len(result.prepared.training), "training_reviewed": len(result.training), "test": len(result.prepared.test),
        "quantile_interpolation": "linear", "metrics_use_raw_predictions": True,
        "route_distance_training_pearson_correlation": result.classifier.distance_correlation,
        "classification_rules": rules, "research_protocol": study.get("metadata", {}), "data_provenance": provenance,
        "comparison_conclusion": result.conclusion, "warnings": result.warnings,
    }
    joblib.dump({"original_baseline": study.get("original_model"), "models": result.models, "classifier": result.classifier, "config": config, "manifest": manifest}, directory / "models.joblib")
    manifest["figures"] = save_figures(result, directory / "figures")
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    summary = "# MLR experiment\n\n" + result.conclusion + "\n\n" + result.metrics.to_string(index=False)
    summary += "\n\n## Interpretation\n\nThis conclusion applies only to this held-out split. Classification uses reviewed-training thresholds and category means with recorded configuration overrides; constant factors remain unresolved. These are descriptive decision-support rules, not independently validated station conditions. Both models use identical reviewed training rows.\n"
    if study:
        summary += "\n\n## Controlled comparisons\n\n" + study["metrics"].to_string(index=False)
        summary += "\n\n" + study["comparisons"].to_string(index=False)
        summary += "\n\nA vs B examines recorded review decisions; B vs C examines interactions; A vs C examines the combined workflow. Positive reductions mean lower error for the second arm. If training records are unchanged, no review benefit is demonstrated.\n"
    summary += "\n\n## Data source\n\n" + provenance.get("message", "Data source not documented.")
    summary += "\n## Review and limitations\n\n" + ("\n".join("- " + w for w in result.warnings) or "No automatic diagnostic warnings.")
    summary += "\n\nRaw predictions are retained for evaluation. Negative enhanced predictions are floored at zero for classification only. Error columns mean actual minus predicted. Text beginning with spreadsheet formula prefixes is escaped in CSV/Excel exports.\n"
    (directory / "SUMMARY.md").write_text(summary, encoding="utf-8")
    return directory
