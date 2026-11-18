import numpy as np
import pandas as pd
import pytest
from scipy import stats
from src.config import ResearchConfig, PREDICTORS, TARGET
from src.interaction_terms import FeatureBuilder
from src.mlr_model import MLRModels, ols_inference, variance_inflation
from src.evaluation import metrics, compare_models
from src.data_loader import split_dataset


def test_selected_pairwise_higher_order_and_main_effects(fixture_data):
    builder = FeatureBuilder(ResearchConfig(center_interactions=False, hierarchical_interactions=False)).fit(fixture_data)
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


def test_centered_interactions_use_training_means_and_reduce_conditioning(fixture_data):
    train, test = split_dataset(fixture_data, ResearchConfig())
    centered = FeatureBuilder(ResearchConfig()).fit(train)
    pv, vf = train["Passenger Volume"].mean(), train["Vehicle Frequency"].mean()
    x = centered.transform(test, True)
    np.testing.assert_allclose(x["Passenger Volume × Vehicle Frequency"], (test["Passenger Volume"] - pv) * (test["Vehicle Frequency"] - vf))
    pd.testing.assert_series_equal(x["Passenger Volume"], test["Passenger Volume"].astype(float))
    pairwise_only = dict(higher_order_interactions=[])
    raw = MLRModels(ResearchConfig(center_interactions=False, **pairwise_only)).fit(train)
    shifted = MLRModels(ResearchConfig(**pairwise_only)).fit(train)
    # With all lower-order terms present, centering only reparametrizes the model.
    np.testing.assert_allclose(raw.predict(test)["Enhanced Predicted Waiting Time"], shifted.predict(test)["Enhanced Predicted Waiting Time"])
    condition = {m.config.center_interactions: m.diagnostics[1]["Condition Number"] for m in (raw, shifted)}
    assert condition[True] < condition[False]


def test_hierarchy_adds_lower_order_parts_and_makes_centering_a_reparametrization(fixture_data):
    train, test = split_dataset(fixture_data, ResearchConfig())
    builder = FeatureBuilder(ResearchConfig()).fit(train)
    added = {" × ".join(t["factors"]) for t in builder.terms if t["added_for_hierarchy"]}
    assert added == {"Passenger Volume × Time of Day", "Vehicle Frequency × Time of Day"}
    assert builder.hierarchy_columns == {'Passenger Volume × Time of Day["T1"]', 'Vehicle Frequency × Time of Day["T1"]'}
    raw = MLRModels(ResearchConfig(center_interactions=False)).fit(train)
    centered = MLRModels(ResearchConfig()).fit(train)
    np.testing.assert_allclose(raw.predict(test)["Enhanced Predicted Waiting Time"],
                               centered.predict(test)["Enhanced Predicted Waiting Time"], atol=1e-8)
    coef = centered.coefficients()
    assert coef.loc[coef.Term.isin(builder.hierarchy_columns), "Added for Hierarchy"].all()
    # The highest-order coefficient does not depend on centering once the model is hierarchical.
    triple = 'Passenger Volume × Vehicle Frequency × Time of Day["T1"]'
    values = [m.coefficients().set_index(["Model", "Term"]).loc[("Enhanced MLR", triple), "Coefficient"] for m in (raw, centered)]
    assert values[0] == pytest.approx(values[1], abs=1e-9)


def test_coefficient_inference_matches_simple_regression():
    rng = np.random.default_rng(3)
    x = pd.DataFrame({"x": rng.normal(size=40)})
    y = 2 + 1.5 * x.x + rng.normal(size=40)
    from sklearn.linear_model import LinearRegression
    rows, df = ols_inference(x, y, LinearRegression().fit(x, y))
    reference = stats.linregress(x.x, y)
    assert df == 38
    assert rows[0]["Std. Error"] == pytest.approx(reference.intercept_stderr)
    assert rows[1]["Std. Error"] == pytest.approx(reference.stderr)
    assert rows[1]["p-value"] == pytest.approx(reference.pvalue)
    assert rows[1]["95% CI Lower"] < 1.5 < rows[1]["95% CI Upper"]


def test_vif_detects_collinearity():
    rng = np.random.default_rng(5)
    a = rng.normal(size=200)
    frame = pd.DataFrame({"a": a, "near_copy": a + rng.normal(scale=.1, size=200), "independent": rng.normal(size=200)})
    vif = {row["Term"]: row["VIF"] for row in variance_inflation(frame)}
    r = np.corrcoef(frame.a, frame.near_copy)[0, 1]
    assert vif["near_copy"] > 10 and vif["independent"] < 1.2
    assert vif["a"] == pytest.approx(1 / (1 - r ** 2), rel=.05)


def test_metrics_and_no_assumed_improvement():
    result = metrics([1, 2, 3], [2, 2, 1])
    assert result["MSE"] == pytest.approx(5 / 3)
    assert result["RMSE"] == pytest.approx(np.sqrt(5 / 3))
    assert result["MAE"] == pytest.approx(1)
    assert result["R2"] == pytest.approx(1 - 5 / 2)
    assert np.isnan(metrics([4], [4])["R2"])
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
