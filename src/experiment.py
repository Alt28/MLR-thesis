"""Reproducible orchestration shared by the web and command-line interfaces."""
from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
import pandas as pd
from .config import TARGET, ROW_ID
from .data_loader import load_dataset, validate_data, split_dataset
from .irregularity_detection import fit_iqr, flag_irregularities, apply_reviews
from .mlr_model import MLRModels
from .evaluation import compare_models
from .station_classification import StationClassifier
from .research_protocol import source_declarations, controlled_comparison


@dataclass
class PreparedExperiment:
    config: object
    original: pd.DataFrame
    training: pd.DataFrame
    test: pd.DataFrame
    iqr_bounds: pd.DataFrame
    flags: pd.DataFrame
    source: str
    source_hash: str
    provenance: dict = field(default_factory=dict)


@dataclass
class ExperimentResult:
    prepared: PreparedExperiment
    training: pd.DataFrame
    audit: pd.DataFrame
    models: MLRModels
    classifier: StationClassifier
    predictions: pd.DataFrame
    metrics: pd.DataFrame
    comparison: pd.DataFrame
    conclusion: str
    warnings: list
    study: dict = field(default_factory=dict)


def prepare_experiment(source, config):
    config = deepcopy(config).validate()
    if isinstance(source, pd.DataFrame):
        data = validate_data(source)
        source_name = "in-memory dataset"
        source_hash = sha256(data.to_csv(index=False).encode("utf-8")).hexdigest()
    else:
        source = Path(source)
        data = load_dataset(source)
        source_name = str(source.resolve())
        source_hash = sha256(source.read_bytes()).hexdigest()
    train, test = split_dataset(data, config)
    bounds = fit_iqr(train, config.iqr_columns, config.iqr_multiplier)
    return PreparedExperiment(config, data, train, test, bounds, flag_irregularities(train, bounds), source_name, source_hash, source_declarations(source, config.research_notes))


def run_experiment(prepared, decisions=None, fitted_models=None):
    config = prepared.config
    train, audit = apply_reviews(prepared.training, prepared.flags, decisions)
    models = fitted_models if fitted_models is not None else MLRModels(config).fit(train)
    predictions = models.predict(prepared.test)
    classifier = StationClassifier(config).fit(train)
    classified = classifier.classify(prepared.test, predictions["Enhanced Predicted Waiting Time"])
    # Prefix any metadata collisions; metadata never enters either model.
    originals = prepared.test.copy()
    originals = originals.rename(columns={c: f"Source metadata: {c}" for c in originals.columns if c in predictions or c in classified})
    output = pd.concat([originals, predictions, classified], axis=1)
    evaluation, comparison, conclusion = compare_models(prepared.test[TARGET], predictions)
    warnings = list(models.warnings)
    unreviewed = int(audit.Action.eq("retain_unreviewed").sum())
    if unreviewed:
        warnings.append(f"{unreviewed} flagged training observations retained without completed review.")
    unseen = int(predictions["Unseen Categories"].ne("").sum())
    if unseen:
        warnings.append(f"{unseen} test rows contain categories absent from training; zero reference contrasts were used.")
    pending = int(output["Overall Station Classification"].eq("Pending configuration").sum())
    if pending:
        warnings.append(f"{pending} observations have unresolved classification factors or measurement units. See Missing Classification Definitions.")
    negative = int(predictions[["Baseline Negative Prediction", "Enhanced Negative Prediction"]].any(axis=1).sum())
    if negative:
        warnings.append(f"{negative} test rows have negative predictions. Metrics use raw predictions; classification floors the enhanced wait at zero.")
    if not config.pairwise_interactions and not config.higher_order_interactions:
        warnings.append("No interactions were selected; baseline and enhanced specifications are identical.")
    if prepared.original.drop(columns=ROW_ID).duplicated().any():
        warnings.append("Duplicate observations exist. Confirm these are independent recordings; random splitting may overstate generalization for repeated or correlated observations.")
    study = controlled_comparison(prepared, train, models)
    warnings.extend("Original-data baseline: " + warning for warning in study["original_model"].warnings)
    provenance = getattr(prepared, "provenance", {})
    if provenance.get("status") != "recorded_declared":
        warnings.append(provenance.get("message", "Data source not documented."))
    if not study["metadata"]["review_changed_training_data"]:
        warnings.append("IQR review did not change training data; no benefit from correction/exclusion is demonstrated by this run.")
    warnings.append(f"Evaluation uses one fixed holdout of {len(prepared.test)} observations. Do not infer statistical significance or real-world validity from this run alone.")
    return ExperimentResult(prepared, train, audit, models, classifier, output, evaluation, comparison, conclusion, warnings, study)
