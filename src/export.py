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
        "mode_metrics": result.mode_metrics,
        "station_summary": result.station_summary,
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


def methodology_report(result, manifest):
    """Markdown record of the methods actually applied in this run, for the manuscript."""
    prepared, config = result.prepared, result.prepared.config
    classifier, study = result.classifier, getattr(result, "study", {})
    provenance = getattr(prepared, "provenance", {})
    rules = getattr(classifier, "rule_metadata", {})
    protocol = study.get("metadata", {})
    grouped = config.split_method == "grouped"
    actions = result.audit.Action.value_counts().to_dict() if len(result.audit) else {}
    unresolved = int(result.predictions["Overall Station Classification"].eq("Pending configuration").sum())
    distribution = result.predictions["Overall Station Classification"].value_counts()

    def block(frame):
        return "\n```text\n" + frame.to_string(index=False) + "\n```\n"

    text = [
        "# Methodology as implemented",
        "",
        f"Run `{manifest['run_id']}`, generated {manifest['created_utc']}. Every value below describes this run only.",
        "Use it to align the manuscript with the software; it is not evidence of real-world validity.",
        "",
        "## 1. Dataset and provenance",
        "",
        f"- Source: `{prepared.source}` (SHA-256 `{prepared.source_hash[:16]}…`)",
        f"- Observations: {len(prepared.original)}; six predictors plus Actual Waiting Time in minutes.",
        f"- Declared measurement units: Vehicle Frequency = {rules.get('measurement_units', {}).get('Vehicle Frequency') or 'undeclared'}; "
        f"Route Distance = {rules.get('measurement_units', {}).get('Route Distance') or 'undeclared'}.",
        f"- Source status: {provenance.get('status', 'undocumented')} — {provenance.get('message', '')}",
    ]
    notes = provenance.get("researcher_notes", {})
    text += [f"- Researcher declaration — {key}: {value}" for key, value in notes.items()] if notes else [
        "- No researcher source declaration was recorded for this run."]

    text += [
        "",
        "## 2. Partitioning before any learning",
        "",
        f"- Method: {'grouped holdout' if grouped else 'random holdout'} "
        f"({protocol.get('split_method', 'random_holdout')}), test fraction {config.test_size}, seed {config.random_state}.",
        f"- Training observations: {len(prepared.training)} original, {len(result.training)} after review. Test observations: {len(prepared.test)}.",
    ]
    text.append(
        f"- Grouping column: `{protocol.get('split_group_column')}`; every observation sharing a group stays in one partition."
        if grouped else
        "- Observations were assigned independently; repeated stations or trips can appear in both partitions.")
    text += [
        "- IQR fences, categorical encoding, severity quartiles, and category means are fitted only on training rows.",
        "",
        "## 3. IQR-based irregularity detection (training only)",
        "",
        f"- Screened variables: {', '.join(config.iqr_columns)}; multiplier {config.iqr_multiplier}.",
        "- IQR = Q3 − Q1; Lower Bound = Q1 − 1.5·IQR; Upper Bound = Q3 + 1.5·IQR.",
        f"- Flagged training observations: {prepared.flags[ROW_ID].nunique()}.",
        f"- Recorded decisions: {', '.join(f'{k} = {v}' for k, v in actions.items()) or 'none'}. "
        "`retain_unreviewed` means the observation was kept without an individual decision.",
        "- Flagged rows are never deleted automatically, and the held-out partition is never reviewed.",
        block(prepared.iqr_bounds.reset_index()),
        "## 4. Model specification and estimation",
        "",
        "- Both models keep all six predictors as main effects and are estimated by Ordinary Least Squares with an intercept.",
        "- Categorical predictors use training-only reference-category indicators:",
        block(result.models.features.encoding_table()),
    ]
    terms = [(" × ".join(term), order) for order, group in
             (("pairwise", config.pairwise_interactions), ("higher-order", config.higher_order_interactions))
             for term in group]
    text += [f"- Enhanced-model interaction terms ({len(terms)}): " +
             ("; ".join(f"{name} ({order})" for name, order in terms) or "none selected")]
    text += ["- Fitted design diagnostics:", block(pd.DataFrame(result.models.diagnostics))]

    text += ["## 5. Experiment arms and evaluation", ""]
    if study:
        text += ["- " + f"Arm {arm}: {name}" for arm, name in study["metadata"]["arms"].items()]
        text += [
            f"- All arms are scored on the same {len(prepared.test)} test observations.",
            block(study["metrics"]), block(study["comparisons"]),
        ]
    text += [
        "- Main reported comparison (Traditional vs Enhanced MLR on reviewed training rows):",
        block(result.metrics), block(result.comparison),
        f"- Conclusion recorded for this run: {result.conclusion}",
        "- Error = actual − predicted. MSE and RMSE use raw predictions, including negative values.",
    ]
    if len(result.mode_metrics):
        text += ["- Bus/train metrics are subsets of the same pooled model's test predictions:",
                 block(result.mode_metrics)]

    text += [
        "## 6. Multi-Factor Threshold-Based Station Classification",
        "",
        "- Seven factors: the six predictors plus the Enhanced MLR predicted waiting time; each carries weight 1/7.",
        "- Multi-Factor Station Score = (sum of the seven severity scores) / 7, evaluated unrounded.",
        f"- Predicted-wait severity bands (minutes): ≤ {config.wait_thresholds[0]} = 0; "
        f"≤ {config.wait_thresholds[1]} = 1; ≤ {config.wait_thresholds[2]} = 2; above = 3.",
        f"- Overall bands: [0, {config.station_thresholds[0]}) Normal Operation; "
        f"[{config.station_thresholds[0]}, {config.station_thresholds[1]}) Minor Delay; "
        f"[{config.station_thresholds[1]}, {config.station_thresholds[2]}) Moderate Delay; "
        f"[{config.station_thresholds[2]}, 3] Severe Delay.",
        "- Numerical factors use reviewed-training quartiles with linear interpolation. Direction comes from the "
        "configured setting, otherwise from the sign of the training Pearson correlation with Actual Waiting Time.",
        block(classifier.thresholds.reset_index()),
        "- Categorical factors compare each training category mean against the reviewed-training waiting-time quartiles "
        f"(Q1 = {classifier.target_quartiles[0]:.6g}, Q2 = {classifier.target_quartiles[1]:.6g}, Q3 = {classifier.target_quartiles[2]:.6g}); "
        "a documented researcher mapping overrides the derived score.",
        block(classifier.evidence),
        "- Negative predictions keep their raw value in evaluation; only the classification input is floored at zero.",
        f"- Label distribution across the {len(result.predictions)} test observations:",
        block(distribution.rename("Observations").rename_axis("Overall Station Classification").reset_index()),
        f"- Unresolved observations (Requires Researcher Decision): {unresolved}. "
        "They stay in the denominator and their reasons are exported per observation.",
    ]
    aggregation = result.station_aggregation or {}
    text.append(
        f"- Station summary grouped by `{aggregation.get('grouping_column')}`: {aggregation.get('station_count', 0)} stations, "
        f"{aggregation.get('ungrouped_records', 0)} test rows without an identifier. It averages classifiable scores "
        "for the test period only and is not a real-time station state."
        if aggregation.get("available") else
        f"- Station-level summary unavailable: {aggregation.get('reason', 'no station identifier present')}.")

    text += [
        "",
        "## 7. Environment and reproducibility",
        "",
        f"- Python {manifest['python']}; " + ", ".join(f"{name} {ver}" for name, ver in manifest["packages"].items()) + ".",
        "- The bundle stores the source hash, configuration hash, source-code hashes, split membership, review decisions, "
        "fitted models, and classification rules.",
        "",
        "## 8. Limitations recorded for this run",
        "",
        *[f"- {warning}" for warning in result.warnings],
        "",
        "These statements describe software behavior on the supplied dataset. They do not establish operational validity "
        "of the thresholds or real-world predictive performance.",
        "",
    ]
    return "\n".join(text)


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
        "mode_metrics": result.mode_metrics.to_dict(orient="records"),
        "station_aggregation": result.station_aggregation,
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
    (directory / "METHODOLOGY.md").write_text(methodology_report(result, manifest), encoding="utf-8")
    return directory
