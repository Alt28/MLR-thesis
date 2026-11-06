"""Bus/train presentation labels only; transport mode never enters the MLR design."""
import pandas as pd

MODE_COLUMNS = ("transport mode", "transportation mode", "mode of transport", "transport type")
MODE_VALUES = {"bus": "bus", "buses": "bus", "train": "train", "trains": "train",
               "rail": "train", "lrt": "train", "mrt": "train", "pnr": "train"}


def transport_labels(frame, config):
    columns = {str(c).strip().lower(): c for c in frame.columns}
    column = next((columns[key] for key in MODE_COLUMNS if key in columns), None)
    if column is not None:
        # Explicit invalid/missing row values stay unspecified, even with a dataset declaration.
        labels = frame[column].fillna("").astype(str).str.strip().str.lower().map(MODE_VALUES).fillna("unspecified")
    else:
        declared = getattr(config, "research_notes", {}).get("transport_mode", "unknown")
        labels = pd.Series(declared if declared in ("bus", "train") else "unspecified", index=frame.index)
    return labels, column


def transport_summary(prepared):
    labels, column = transport_labels(prepared.original, prepared.config)
    def counts(index):
        values = labels.loc[index].value_counts()
        return {mode: int(values.get(mode, 0)) for mode in ("bus", "train", "unspecified")}
    return {"column": column, "dataset_counts": counts(prepared.original.index),
            "test_counts": counts(prepared.test.index),
            "source": "Recorded metadata column" if column else "Researcher dataset declaration"}
