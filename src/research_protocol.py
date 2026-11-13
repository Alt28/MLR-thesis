"""Explicit comparison protocol and source declarations; no automatic validity claims."""
from pathlib import Path
import re
import numpy as np
import pandas as pd
from .config import ROW_ID, TARGET
from .data_loader import resolve_group_column
from .evaluation import metrics
from .mlr_model import MLRModels

PROTOCOL_VERSION = 1
STUDY_ARMS = {
    "A": "Traditional MLR - original training data",
    "B": "Traditional MLR - reviewed training data",
    "C": "Enhanced MLR - reviewed training data",
}


def source_declarations(source, notes):
    """Treat workbook notes as declarations, never as instructions or verified evidence."""
    entries = []
    if not isinstance(source, pd.DataFrame) and Path(source).suffix.lower() == ".xlsx":
        with pd.ExcelFile(source) as book:
            if "Sources_Methodology" in book.sheet_names:
                # Read the first row as data: some workbooks put a provenance banner above the table.
                frame = pd.read_excel(book, sheet_name="Sources_Methodology", header=None, nrows=200).fillna("")
                entries = [{"Sheet": "Sources_Methodology", "Row": str(i + 1),
                            "Note": " | ".join(str(v) for v in row if str(v).strip())}
                           for i, row in enumerate(frame.itertuples(index=False, name=None))]
    text = " ".join(str(v) for row in entries for v in row.values()).lower()
    declared_prototype = bool(re.search(
        r"dataset is simulated|wait(?:ing)? time is simulated|not final(?: observation-level)? thesis|synthetic\s*/\s*demo|synthetic prototype observation|only for (?:prototype|software) testing", text))
    source_type = notes.get("source_type", "unknown")
    prototype = declared_prototype or source_type == "simulated"
    status = "prototype" if prototype else "recorded_declared" if source_type == "recorded" else "undocumented"
    messages = {
        "prototype": "Prototype data: use these results for software testing, not evidence of real-world predictive performance.",
        "recorded_declared": "Recorded data declared by the researcher. Source authenticity, matching observations, and suitability still require verification.",
        "undocumented": "Data source not documented. Record its origin and observation definition before using results as thesis evidence.",
    }
    return {"status": status, "message": messages[status], "workbook_declares_prototype": declared_prototype,
            "workbook_notes": entries, "researcher_notes": dict(notes)}


def controlled_comparison(prepared, reviewed, models):
    """A vs B measures recorded review decisions; B vs C isolates interactions."""
    original_model = MLRModels(prepared.config).fit(prepared.training, selection="baseline")
    original_prediction = original_model.predict(prepared.test)["Baseline Predicted Waiting Time"]
    reviewed_predictions = models.predict(prepared.test)
    predictions = pd.DataFrame({
        ROW_ID: prepared.test[ROW_ID], TARGET: prepared.test[TARGET],
        "A Predicted Wait": original_prediction,
        "B Predicted Wait": reviewed_predictions["Baseline Predicted Waiting Time"],
        "C Predicted Wait": reviewed_predictions["Enhanced Predicted Waiting Time"],
    }, index=prepared.test.index)
    rows = []
    for arm, name in STUDY_ARMS.items():
        predictions[f"{arm} Error (actual - predicted)"] = predictions[TARGET] - predictions[f"{arm} Predicted Wait"]
        rows.append({"Arm": arm, "Model": name, "Training Rows": len(prepared.training) if arm == "A" else len(reviewed),
                     "Test Rows": len(prepared.test), **metrics(predictions[TARGET], predictions[f"{arm} Predicted Wait"])})
    scores = pd.DataFrame(rows)
    identical_data = prepared.training.equals(reviewed)
    differences = []
    for before, after, question in [("A", "B", "Effect of recorded data-review decisions"),
                                    ("B", "C", "Effect of selected interaction terms"),
                                    ("A", "C", "Combined workflow comparison")]:
        first, second = scores.set_index("Arm").loc[[before, after]].to_dict("records")
        equal = np.isclose(first["MSE"], second["MSE"], rtol=1e-9, atol=1e-12)
        outcome = "Effectively equal error" if equal else "Lower error" if second["MSE"] < first["MSE"] else "Higher error"
        if before == "A" and after == "B" and identical_data:
            outcome = "No training data changed; review benefit was not demonstrated"
        differences.append({"Comparison": f"{before} vs {after}", "Question": question,
                            "MSE reduction": first["MSE"] - second["MSE"],
                            "RMSE reduction (min)": first["RMSE"] - second["RMSE"],
                            "Outcome for second arm": outcome})
    grouped = prepared.config.split_method == "grouped"
    metadata = {
        "version": PROTOCOL_VERSION, "arms": STUDY_ARMS, "review_changed_training_data": not identical_data,
        "same_test_observations": True, "test_record_ids": list(prepared.test.index),
        "split_method": "grouped_holdout" if grouped else "random_holdout",
        "split_group_column": resolve_group_column(prepared.original, prepared.config) if grouped else None,
        "test_fraction": prepared.config.test_size,
        "random_seed": prepared.config.random_state,
        "interpretation": "Descriptive results for one fixed holdout. No statistical significance or generalization guarantee is inferred.",
        "main_comparison": "B vs C (identical reviewed training rows)",
    }
    return {"original_model": original_model, "metrics": scores, "comparisons": pd.DataFrame(differences),
            "predictions": predictions, "metadata": metadata}
