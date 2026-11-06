"""Research decisions. Edit these values before an experiment; each run saves a copy.

Category overrides use exact recorded names. Missing mappings are learned from reviewed training data.
The example interactions are starting specifications, not validated findings.
"""
from dataclasses import dataclass, field, asdict

PREDICTORS = (
    "Traffic Condition", "Weather Condition", "Passenger Volume",
    "Route Distance", "Vehicle Frequency", "Time of Day",
)
CATEGORICAL = ("Traffic Condition", "Weather Condition", "Time of Day")
NUMERICAL = ("Passenger Volume", "Route Distance", "Vehicle Frequency")
TARGET = "Actual Waiting Time"
ROW_ID = "Record ID"
LABELS = ("Normal Operation", "Minor Delay", "Moderate Delay", "Severe Delay")

TEST_SIZE = 0.20
RANDOM_STATE = 42
IQR_MULTIPLIER = 1.5
IQR_COLUMNS = (*NUMERICAL, TARGET)
PAIRWISE_INTERACTIONS = [("Passenger Volume", "Vehicle Frequency")]
HIGHER_ORDER_INTERACTIONS = [("Passenger Volume", "Vehicle Frequency", "Time of Day")]
TRAFFIC_SEVERITY = {}
WEATHER_SEVERITY = {}
TIME_OF_DAY_SEVERITY = {}
NUMERICAL_SEVERITY_DIRECTION = {
    "Passenger Volume": None,
    "Route Distance": None,  # None derives direction from reviewed-training Pearson correlation.
    "Vehicle Frequency": None,
}
VEHICLE_FREQUENCY_UNIT = ""  # Revised study: vehicles/hour; require source declaration or explicit configuration.
ROUTE_DISTANCE_UNIT = ""  # e.g. "km"; consistent within a dataset.
WAIT_THRESHOLDS = (15.0, 20.0, 25.0)
STATION_THRESHOLDS = (0.75, 1.50, 2.25)
NEGATIVE_WAIT_RULE = "clip_for_classification_only"


@dataclass
class ResearchConfig:
    test_size: float = TEST_SIZE
    random_state: int = RANDOM_STATE
    iqr_multiplier: float = IQR_MULTIPLIER
    iqr_columns: tuple = IQR_COLUMNS
    pairwise_interactions: list = field(default_factory=lambda: list(PAIRWISE_INTERACTIONS))
    higher_order_interactions: list = field(default_factory=lambda: list(HIGHER_ORDER_INTERACTIONS))
    category_severity: dict = field(default_factory=lambda: {
        "Traffic Condition": dict(TRAFFIC_SEVERITY),
        "Weather Condition": dict(WEATHER_SEVERITY),
        "Time of Day": dict(TIME_OF_DAY_SEVERITY),
    })
    numerical_directions: dict = field(default_factory=lambda: dict(NUMERICAL_SEVERITY_DIRECTION))
    vehicle_frequency_unit: str = VEHICLE_FREQUENCY_UNIT
    route_distance_unit: str = ROUTE_DISTANCE_UNIT
    wait_thresholds: tuple = WAIT_THRESHOLDS
    station_thresholds: tuple = STATION_THRESHOLDS
    negative_wait_rule: str = NEGATIVE_WAIT_RULE

    research_notes: dict = field(default_factory=dict)

    def validate(self):
        import math
        allowed_notes = {"transport_mode", "source_type", "source_reference", "observation_definition", "collection_period", "interaction_rationale", "classification_rationale", "split_rationale"}
        if not isinstance(self.research_notes, dict) or not set(self.research_notes) <= allowed_notes:
            raise ValueError("Research notes contain unsupported fields.")
        if any(not isinstance(v, str) or len(v) > 4000 for v in self.research_notes.values()):
            raise ValueError("Research notes must be text of at most 4000 characters per field.")
        if self.research_notes.get("transport_mode", "unknown") not in ("unknown", "bus", "train", "mixed"):
            raise ValueError("Transport mode must be unknown, bus, train, or mixed.")
        if self.research_notes.get("source_type", "unknown") not in ("unknown", "recorded", "simulated"):
            raise ValueError("Data source type must be unknown, recorded, or simulated.")
        if type(self.random_state) is not int or not 0 <= self.random_state < 2**32:
            raise ValueError("Random seed must be an integer from 0 to 4294967295.")
        if not isinstance(self.category_severity, dict) or not set(self.category_severity) <= set(CATEGORICAL):
            raise ValueError("Category severity must map the three categorical predictor names to score dictionaries.")
        if not isinstance(self.numerical_directions, dict) or not set(self.numerical_directions) <= set(NUMERICAL):
            raise ValueError("Numerical directions must map numerical predictor names to higher, lower, or null.")
        if not isinstance(self.vehicle_frequency_unit, str) or not isinstance(self.route_distance_unit, str):
            raise ValueError("Measurement units must be text.")
        if not 0 < self.test_size < 1:
            raise ValueError("test_size must be between 0 and 1.")
        if not math.isfinite(self.iqr_multiplier) or self.iqr_multiplier <= 0:
            raise ValueError("IQR multiplier must be positive and finite.")
        if not self.iqr_columns or not set(self.iqr_columns) <= set((*NUMERICAL, TARGET)):
            raise ValueError("IQR columns must be selected numerical variables or actual waiting time.")
        seen = set()
        for terms, minimum, maximum in [(self.pairwise_interactions, 2, 2), (self.higher_order_interactions, 3, 6)]:
            for term in terms:
                if not minimum <= len(term) <= maximum or len(set(term)) != len(term):
                    raise ValueError(f"Invalid interaction: {term}")
                if not set(term) <= set(PREDICTORS):
                    raise ValueError(f"Unknown predictor in interaction: {term}")
                key = frozenset(term)
                if key in seen:
                    raise ValueError(f"Duplicate interaction: {term}")
                seen.add(key)
        for name in CATEGORICAL:
            mapping = self.category_severity.get(name, {})
            if not isinstance(mapping, dict):
                raise ValueError(f"{name}: severity mapping must be a category-to-score dictionary.")
            if any(not isinstance(k, str) or type(v) is not int or v not in range(4) for k, v in mapping.items()):
                raise ValueError(f"{name}: category scores must be integers 0, 1, 2, or 3.")
        for name in NUMERICAL:
            if self.numerical_directions.get(name) not in (None, "higher", "lower"):
                raise ValueError(f"Invalid severity direction for {name}.")
        for thresholds, limit in [(self.wait_thresholds, float("inf")), (self.station_thresholds, 3)]:
            if len(thresholds) != 3 or not all(math.isfinite(x) for x in thresholds):
                raise ValueError("Exactly three finite thresholds are required.")
            if not 0 < thresholds[0] < thresholds[1] < thresholds[2] < limit:
                raise ValueError("Thresholds must be positive and strictly increasing.")
        if self.negative_wait_rule != "clip_for_classification_only":
            raise ValueError("Supported negative-wait rule: clip_for_classification_only.")
        return self

    def to_dict(self):
        return asdict(self)
