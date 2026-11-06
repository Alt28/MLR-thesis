import numpy as np
import pandas as pd
import pytest
from src.config import ResearchConfig, PREDICTORS, TARGET
from src.interaction_terms import FeatureBuilder
from src.mlr_model import MLRModels
from src.evaluation import metrics, compare_models
from src.data_loader import split_dataset


def test_selected_pairwise_higher_order_and_main_effects(fixture_data):
    builder = FeatureBuilder(ResearchConfig()).fit(fixture_data)
    main = builder.transform(fixture_data)
    full = builder.transform(fixture_data, enhanced=True)
    pd.testing.assert_frame_equal(main, full[main.columns])
    pair = "Passenger Volume × Vehicle Frequency"
    triple = 'Passenger Volume × Vehicle Frequency × Time of Day["T1"]'
    np.testing.assert_allclose(full[pair], fixture_data["Passenger Volume"] * fixture_data["Vehicle Frequency"])
    np.testing.assert_allclose(full[triple], full[pair] * fixture_data["Time of Day"].eq("T1"))
    assert len(full.columns) == len(main.columns) + 2
    assert set(builder.blocks) == set(PREDICTORS)


def test_categorical_interaction_cross_product(fixture_data):
    config = ResearchConfig(pairwise_interactions=[("Traffic Condition", "Weather Condition")], higher_order_interactions=[])
    b = FeatureBuilder(config).fit(fixture_data)
    x = b.transform(fixture_data, True)
    assert len(b.interaction_columns) == 2
    for term, factors in b.interaction_columns.items():
        np.testing.assert_array_equal(x[term], x[factors[0]] * x[factors[1]])


def test_training_only_encoding_and_consistent_features(fixture_data):
    train, test = split_dataset(fixture_data, ResearchConfig())
    b = FeatureBuilder(ResearchConfig()).fit(train)
    test["Traffic Condition"] = "UNSEEN"
    assert "UNSEEN" not in b.categories["Traffic Condition"]
    assert b.transform(train, True).columns.tolist() == b.transform(test, True).columns.tolist()
    assert b.unknown_categories(test).str.contains("UNSEEN").all()


def test_metrics_and_no_assumed_improvement():
    result = metrics([1, 2, 3], [2, 2, 1])
    assert result["MSE"] == pytest.approx(5 / 3)
    assert result["RMSE"] == pytest.approx(np.sqrt(5 / 3))
    table, diff, conclusion = compare_models([1, 2], pd.DataFrame({"Baseline Predicted Waiting Time": [1, 2], "Enhanced Predicted Waiting Time": [3, 4]}))
    assert "higher" in conclusion and diff["Improvement (%)"].isna().all()
    assert metrics([0], [-3])["MSE"] == 9


def test_ols_coefficients_and_predictions(fixture_data):
    train, test = split_dataset(fixture_data, ResearchConfig())
    fitted = MLRModels(ResearchConfig()).fit(train)
    predicted = fitted.predict(test)
    np.testing.assert_allclose(predicted["Enhanced Predicted Waiting Time"], test[TARGET], atol=1e-8)
    coef = fitted.coefficients()
    pair = coef[(coef.Model == "Enhanced MLR") & (coef.Term == "Passenger Volume × Vehicle Frequency")]
    assert pair.iloc[0].Coefficient == pytest.approx(.002)
    assert "intercept" in set(coef.Type)


def test_invalid_specifications():
    with pytest.raises(ValueError):
        ResearchConfig(pairwise_interactions=[("Passenger Volume", "Added predictor")]).validate()
    with pytest.raises(ValueError):
        ResearchConfig(pairwise_interactions=[("Passenger Volume", "Passenger Volume")]).validate()
