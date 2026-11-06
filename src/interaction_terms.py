"""Reference-category encoding and only the explicitly selected interaction blocks."""
from itertools import product
import json
import numpy as np
import pandas as pd
from .config import PREDICTORS, CATEGORICAL, NUMERICAL


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
        for term in [*self.config.pairwise_interactions, *self.config.higher_order_interactions]:
            for encoded_columns in product(*(self.blocks[col] for col in term)):
                self.interaction_columns[" × ".join(encoded_columns)] = encoded_columns
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
            for name, factors in self.interaction_columns.items():
                frame[name] = frame[list(factors)].prod(axis=1)
        if not np.isfinite(frame.to_numpy()).all():
            raise ValueError("Non-finite model features. Check numerical magnitudes and interaction definitions.")
        return frame

    def unknown_categories(self, data):
        return pd.Series([
            "; ".join(f"{col}={row[col]}" for col in CATEGORICAL if row[col] not in self.categories[col])
            for _, row in data.iterrows()
        ], index=data.index, name="Unseen Categories")

    def encoding_table(self):
        return pd.DataFrame([
            {"Predictor": col, "Category": category, "Reference": i == 0,
             "Encoded Column": "(reference; all contrasts zero)" if i == 0 else self.blocks[col][i - 1]}
            for col in CATEGORICAL for i, category in enumerate(self.categories[col])
        ])
