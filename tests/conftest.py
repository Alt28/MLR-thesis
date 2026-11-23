"""Artificial unit-test fixtures only. These are NOT transportation observations."""
import numpy as np
import pandas as pd
import pytest
from src.data_loader import validate_data


@pytest.fixture
def fixture_data():
    rng = np.random.default_rng(17)
    n = 80
    passenger = rng.integers(1, 200, n)
    frequency = rng.integers(1, 20, n)
    return validate_data(pd.DataFrame({
        "Station / Stop": rng.choice(["A", "B", "C"], n),
        "Day of Week": rng.choice(["Monday", "Tuesday"], n),
        "Passenger Volume": passenger,
        "Month of Year": rng.choice(["January", "February"], n),
        "Vehicle Frequency": frequency,
        "Time of Day": rng.choice(["Morning", "Night"], n),
        "Actual Waiting Time": 5 + .03 * passenger + .002 * passenger * frequency,
    }))


def declared_config(**kwargs):
    """Explicit declarations for ARTIFICIAL software fixtures only, never research evidence."""
    from src.config import ResearchConfig
    notes = {"transport_mode": "bus", "source_type": "simulated", **kwargs.pop("research_notes", {})}
    kwargs.setdefault("category_scoring", "manual")  # Automatic scoring has its own explicit tests.
    return ResearchConfig(observed_targets_confirmed=True, prediction_inputs_available=True,
                          research_notes=notes, **kwargs)


def classification_config(**kwargs):
    from src.config import CATEGORICAL
    # Arbitrary TEST rules exercise the approval workflow; not operational thresholds.
    mappings = {"Station / Stop": {"A": 0, "B": 1, "C": 3},
                "Time of Day": {"Morning": 0, "Night": 3},
                "Day of Week": {"Monday": 0, "Tuesday": 1},
                "Month of Year": {"January": 0, "February": 1}}
    return declared_config(classification_approved=True, category_severity=mappings,
        numerical_directions={"Passenger Volume": "higher", "Vehicle Frequency": "lower"},
        research_notes={"classification_rationale": "Artificial test mappings; not research evidence."}, **kwargs)
