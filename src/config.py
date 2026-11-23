"""Research decisions. Edit these values before an experiment; each run saves a copy.

Categorical severity mappings require explicit methodological approval; none are inferred.
The example interactions are starting specifications, not validated findings.
"""
from dataclasses import dataclass, field, asdict

SCHEMA_VERSION = "station-calendar-v2"
PREDICTORS = ("Passenger Volume", "Vehicle Frequency", "Station / Stop",
              "Time of Day", "Day of Week", "Month of Year")
CATEGORICAL = ("Station / Stop", "Time of Day", "Day of Week", "Month of Year")
NUMERICAL = ("Passenger Volume", "Vehicle Frequency")
CATEGORY_VALUES = {
    "Time of Day": ("Morning", "Midday", "Afternoon", "Evening", "Night"),
    "Day of Week": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
    "Month of Year": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"),
}
TARGET = "Actual Waiting Time"
ROW_ID = "Record ID"
LABELS = ("Normal Operation", "Minor Delay", "Moderate Delay", "Severe Delay")

TEST_SIZE = 0.20
RANDOM_STATE = 42
SPLIT_METHOD = "random"  # "grouped" keeps all observations of one station in a single partition.
SPLIT_GROUP_COLUMN = ""  # Empty resolves Station / Stop; another group key can be explicitly configured.
IQR_MULTIPLIER = 1.5
IQR_COLUMNS = (*NUMERICAL, TARGET)
# Default from the NYC train study: the wait-frequency relation differs by time band (sparser night service).
PAIRWISE_INTERACTIONS = [("Vehicle Frequency", "Time of Day")]
# Default study specification: the frequency effect differs by time band and by weekday/weekend timetables.
HIGHER_ORDER_INTERACTIONS = [("Vehicle Frequency", "Time of Day", "Day of Week")]
CENTER_INTERACTIONS = True  # Numerical factors are centered at training means before forming interaction products.
# Hierarchy principle: a selected higher-order term also brings in its missing lower-order interaction components,
# so centering only reparametrizes the model and results do not depend on where each variable's zero lies.
HIERARCHICAL_INTERACTIONS = True
CV_FOLDS = 5
CV_REPEATS = 10  # Repeated k-fold within the reviewed training partition; the test partition is never used.
NUMERICAL_SEVERITY_DIRECTION = {
    "Passenger Volume": None,
    "Vehicle Frequency": None,
}
VEHICLE_FREQUENCY_UNIT = "vehicles/hour"  # Actual recorded operations in a documented window.
# Predicted-wait bands (minutes) for the classification factor, scaled to observed urban rail waits (mostly 3-12 min).
WAIT_THRESHOLDS = (5.0, 8.0, 12.0)
STATION_THRESHOLDS = (0.75, 1.50, 2.25)
# Numerical directions only: adjusted additive OLS effects or marginal training correlations.
# Neither option assigns categorical severity scores.
SEVERITY_BASIS = "adjusted"
NEGATIVE_WAIT_RULE = "clip_for_classification_only"
# "automatic": station and calendar categories score 0-3 from their mean training wait against the
# training actual-wait quartiles. "manual": only approved researcher mappings are used.
CATEGORY_SCORING = "automatic"


@dataclass
class ResearchConfig:
    schema_version: str = SCHEMA_VERSION
    classification_approved: bool = False
    observed_targets_confirmed: bool = False
    prediction_inputs_available: bool = False
    test_size: float = TEST_SIZE
    random_state: int = RANDOM_STATE
    split_method: str = SPLIT_METHOD
    split_group_column: str = SPLIT_GROUP_COLUMN
    iqr_multiplier: float = IQR_MULTIPLIER
    iqr_columns: tuple = IQR_COLUMNS
    pairwise_interactions: list = field(default_factory=lambda: list(PAIRWISE_INTERACTIONS))
    higher_order_interactions: list = field(default_factory=lambda: list(HIGHER_ORDER_INTERACTIONS))
    center_interactions: bool = CENTER_INTERACTIONS
    hierarchical_interactions: bool = HIERARCHICAL_INTERACTIONS
    cv_folds: int = CV_FOLDS
    cv_repeats: int = CV_REPEATS
    category_severity: dict = field(default_factory=lambda: {col: {} for col in CATEGORICAL})
    numerical_directions: dict = field(default_factory=lambda: dict(NUMERICAL_SEVERITY_DIRECTION))
    vehicle_frequency_unit: str = VEHICLE_FREQUENCY_UNIT
    wait_thresholds: tuple = WAIT_THRESHOLDS
    station_thresholds: tuple = STATION_THRESHOLDS
    severity_basis: str = SEVERITY_BASIS
    negative_wait_rule: str = NEGATIVE_WAIT_RULE
    category_scoring: str = CATEGORY_SCORING

    research_notes: dict = field(default_factory=dict)

    def validate(self):
        import math
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("This model uses an incompatible predictor schema. Train a new model with the current six predictors.")
        for field_name in ("classification_approved", "observed_targets_confirmed", "prediction_inputs_available"):
            if type(getattr(self, field_name)) is not bool:
                raise ValueError(f"{field_name} must be true or false.")
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
            raise ValueError("Category severity must map the four categorical predictor names to score dictionaries.")
        if not isinstance(self.numerical_directions, dict) or not set(self.numerical_directions) <= set(NUMERICAL):
            raise ValueError("Numerical directions must map numerical predictor names to higher, lower, or null.")
        if self.vehicle_frequency_unit != "vehicles/hour":
            raise ValueError("Vehicle Frequency must measure actual recorded operations in vehicles/hour; fleet availability and scheduled frequency are incompatible.")
        if self.classification_approved and not self.research_notes.get("classification_rationale", "").strip():
            raise ValueError("Document the approved classification rationale before enabling category scores.")
        if not 0 < self.test_size < 1:
            raise ValueError("test_size must be between 0 and 1.")
        if self.split_method not in ("random", "grouped"):
            raise ValueError("Split method must be random or grouped.")
        if not isinstance(self.split_group_column, str):
            raise ValueError("Split group column must be text.")
        if type(self.center_interactions) is not bool or type(self.hierarchical_interactions) is not bool:
            raise ValueError("center_interactions and hierarchical_interactions must be true or false.")
        if not self.hierarchical_interactions:
            raise ValueError("Model hierarchy must remain enabled for this study.")
        if type(self.cv_folds) is not int or not 2 <= self.cv_folds <= 20:
            raise ValueError("Cross-validation folds must be an integer from 2 to 20.")
        if type(self.cv_repeats) is not int or not 1 <= self.cv_repeats <= 100:
            raise ValueError("Cross-validation repeats must be an integer from 1 to 100.")
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
            if name in CATEGORY_VALUES and not set(mapping) <= set(CATEGORY_VALUES[name]):
                raise ValueError(f"{name}: severity mappings must use the documented category names.")
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
        if self.category_scoring not in ("automatic", "manual"):
            raise ValueError("Category scoring must be automatic or manual.")
        if self.severity_basis not in ("adjusted", "marginal"):
            raise ValueError("Severity basis must be adjusted or marginal.")
        return self

    def to_dict(self):
        return asdict(self)
