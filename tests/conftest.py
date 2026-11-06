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
        "Traffic Condition": rng.choice(["A", "B", "C"], n),
        "Weather Condition": rng.choice(["W0", "W1"], n),
        "Passenger Volume": passenger,
        "Route Distance": rng.uniform(1, 30, n),
        "Vehicle Frequency": frequency,
        "Time of Day": rng.choice(["T0", "T1"], n),
        "Actual Waiting Time": 5 + .03 * passenger + .002 * passenger * frequency,
    }))
