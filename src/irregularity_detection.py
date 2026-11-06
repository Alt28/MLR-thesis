"""Training-only Tukey fences and traceable, researcher-directed review."""
import json
from hashlib import sha256
import pandas as pd
from .config import PREDICTORS, TARGET, ROW_ID
from .data_loader import validate_data


def fit_iqr(training, columns, multiplier=1.5):
    quartiles = training[list(columns)].quantile([0.25, 0.75], interpolation="linear")
    result = pd.DataFrame({"Q1": quartiles.loc[0.25], "Q3": quartiles.loc[0.75]})
    result["IQR"] = result.Q3 - result.Q1
    result["Lower Bound"] = result.Q1 - multiplier * result.IQR
    result["Upper Bound"] = result.Q3 + multiplier * result.IQR
    result.index.name = "Factor"
    return result


def flag_irregularities(training, bounds):
    records = []
    for col, b in bounds.iterrows():
        mask = (training[col] < b["Lower Bound"]) | (training[col] > b["Upper Bound"])
        for rid, row in training.loc[mask].iterrows():
            records.append({ROW_ID: rid, "Factor": col, "Value": row[col],
                            "Lower Bound": b["Lower Bound"], "Upper Bound": b["Upper Bound"]})
    return pd.DataFrame(records, columns=[ROW_ID, "Factor", "Value", "Lower Bound", "Upper Bound"])


def apply_reviews(training, flags, decisions=None):
    """Decisions apply to flagged training IDs only; the held-out data is untouched."""
    decisions = decisions or {}
    flagged_ids = set(flags[ROW_ID])
    if not set(decisions) <= flagged_ids:
        raise ValueError("Review decisions may only refer to IQR-flagged training record IDs.")
    reviewed = training.copy()
    audit = []
    for rid in sorted(flagged_ids):
        decision = decisions.get(rid, {})
        action = decision.get("action", "retain_unreviewed")
        reason = str(decision.get("reason", "")).strip()
        corrections = decision.get("corrections", {})
        if action not in ("retain_unreviewed", "retain", "exclude", "correct"):
            raise ValueError(f"{rid}: invalid review action.")
        if action != "retain_unreviewed" and not reason:
            raise ValueError(f"{rid}: provide a source-based reason for the review decision.")
        if corrections and action != "correct":
            raise ValueError(f"{rid}: corrections require the correct action.")
        if action == "correct":
            if not corrections or not set(corrections) <= set((*PREDICTORS, TARGET)):
                raise ValueError(f"{rid}: corrections must name existing predictors or actual waiting time.")
            for col, value in corrections.items():
                reviewed.at[rid, col] = value
        if action == "exclude":
            reviewed = reviewed.drop(index=rid)
        original = {c: training.at[rid, c] for c in corrections}
        audit.append({ROW_ID: rid, "Action": action, "Reason": reason,
                      "Original Values": json.dumps(original, default=str),
                      "Corrections": json.dumps(corrections, default=str)})
    if len(reviewed) < 2:
        raise ValueError("Too few training observations remain after review.")
    return validate_data(reviewed), pd.DataFrame(audit, columns=[ROW_ID, "Action", "Reason", "Original Values", "Corrections"])


def review_fingerprint(prepared):
    content = prepared.training.to_csv(index=False) + prepared.flags.to_csv(index=False)
    return sha256(content.encode("utf-8")).hexdigest()


def review_bundle(prepared, decisions):
    apply_reviews(prepared.training, prepared.flags, decisions)
    return {"format": "mlr-review-v1", "source_sha256": prepared.source_hash,
            "training_and_flags_sha256": review_fingerprint(prepared), "decisions": decisions}


def read_review_bundle(prepared, payload):
    if not isinstance(payload, dict) or payload.get("format") != "mlr-review-v1":
        raise ValueError("Use a review bundle saved by the web application or inspection command; it must identify its source dataset and split.")
    if payload.get("source_sha256") != prepared.source_hash or payload.get("training_and_flags_sha256") != review_fingerprint(prepared):
        raise ValueError("Review file does not match this source dataset, training split, or IQR flags.")
    decisions = payload.get("decisions")
    if not isinstance(decisions, dict):
        raise ValueError("Review decisions must be a JSON object.")
    apply_reviews(prepared.training, prepared.flags, decisions)
    return decisions
