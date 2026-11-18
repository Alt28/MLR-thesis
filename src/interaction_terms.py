"""Reference-category encoding and only the explicitly selected interaction blocks."""
from itertools import combinations, product
import json
import numpy as np
import pandas as pd
from .config import PREDICTORS, CATEGORICAL, NUMERICAL


def interaction_specification(config):
    """Selected terms, plus missing lower-order components of each higher-order term when hierarchy is enabled."""
    terms, seen = [], set()
    for term in [*config.pairwise_interactions, *config.higher_order_interactions]:
        terms.append({"factors": tuple(term), "added_for_hierarchy": False})
        seen.add(frozenset(term))
    if getattr(config, "hierarchical_interactions", False):
        for term in config.higher_order_interactions:
            for size in range(2, len(term)):
                for part in combinations(term, size):
                    if frozenset(part) not in seen:
                        terms.append({"factors": tuple(part), "added_for_hierarchy": True})
                        seen.add(frozenset(part))
    for term in terms:
        term["order"] = "pairwise" if len(term["factors"]) == 2 else "higher-order"
    return terms


class FeatureBuilder:
    def __init__(self, config):
        self.config = config

    def fit(self, training):
        self.config.validate()
        self.categories = {c: sorted(training[c].unique().tolist()) for c in CATEGORICAL}
        self.blocks = {}
        for col in PREDICTORS:
            self.blocks[col] = ([col] if col in NUMERICAL else
                                [f"{col}[{json.dumps(value, ensure_ascii=False)}]" for value in self.categories[col][1:]])
        self.main_columns = [name for col in PREDICTORS for name in self.blocks[col]]
        self.interaction_columns = {}
        self.hierarchy_columns = set()
        self.terms = interaction_specification(self.config)
        for term in self.terms:
            for encoded_columns in product(*(self.blocks[col] for col in term["factors"])):
                name = " × ".join(encoded_columns)
                self.interaction_columns[name] = encoded_columns
                if term["added_for_hierarchy"]:
                    self.hierarchy_columns.add(name)
        # Centering reduces collinearity between main effects and their products; main effects stay unscaled.
        self.centers = ({col: float(training[col].astype(float).mean()) for col in NUMERICAL}
                        if getattr(self.config, "center_interactions", False) else {})
        return self

    def transform(self, data, enhanced=False):
        columns = {}
        for col in PREDICTORS:
            if col in NUMERICAL:
                columns[col] = data[col].astype(float)
            else:
                for value, name in zip(self.categories[col][1:], self.blocks[col]):
                    columns[name] = data[col].eq(value).astype(float)
        frame = pd.DataFrame(columns, index=data.index)
        if enhanced:
            centers = getattr(self, "centers", {})
            factors_frame = frame.assign(**{col: frame[col] - center for col, center in centers.items()})
            for name, factors in self.interaction_columns.items():
                frame[name] = factors_frame[list(factors)].prod(axis=1)
        if not np.isfinite(frame.to_numpy()).all():
            raise ValueError("Non-finite model features. Check numerical magnitudes and interaction definitions.")
        return frame

    def unknown_categories(self, data):
        return pd.Series([
            "; ".join(f"{col}={row[col]}" for col in CATEGORICAL if row[col] not in self.categories[col])
            for _, row in data.iterrows()
        ], index=data.index, name="Unseen Categories")

    def centering_table(self):
        centers = getattr(self, "centers", {})
        return pd.DataFrame([{"Predictor": col, "Training Mean Used for Centering": value} for col, value in centers.items()],
                            columns=["Predictor", "Training Mean Used for Centering"])

    def encoding_table(self):
        return pd.DataFrame([
            {"Predictor": col, "Category": category, "Reference": i == 0,
             "Encoded Column": "(reference; all contrasts zero)" if i == 0 else self.blocks[col][i - 1]}
            for col in CATEGORICAL for i, category in enumerate(self.categories[col])
        ])
