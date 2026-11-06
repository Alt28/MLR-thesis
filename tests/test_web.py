"""Temporary artificial fixtures verify the local HTTP workflow, never thesis results."""
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app


@pytest.fixture
def web(tmp_path):
    with TestClient(create_app(tmp_path / "web")) as client:
        yield client


def upload(web, data):
    result = web.post("/api/experiments", files={"file": ("ARTIFICIAL_TEST.csv", data.to_csv(index=False).encode(), "text/csv")})
    assert result.status_code == 201, result.text
    return result.json()


def wait_for_job(web, sid):
    for _ in range(150):
        result = web.get(f"/api/experiments/{sid}").json()
        if result["status"] != "running": return result
        time.sleep(.05)
    pytest.fail("Training job timed out")


def test_validation_and_templates(web, fixture_data):
    assert web.get("/api/health").json()["application"] == "transit-lab"
    assert web.get("/api/templates/xlsx").status_code == 200
    assert "Station ID" in web.get("/api/templates/csv").text
    bad = web.post("/api/experiments", files={"file": ("bad.csv", b"wrong\n123", "text/csv")})
    assert bad.status_code == 400 and "Missing required" in bad.text
    assert web.get("/api/not-a-real-route").status_code == 404
    assert web.post("/api/experiments", headers={"Origin": "https://external.example"}, files={"file": ("a.csv", b"x")}).status_code == 403
    assert web.post("/api/experiments", files={"file": ("corrupt.xlsx", b"not an Excel archive")}).status_code == 400


def test_deployment_allows_configured_frontend_origin(monkeypatch, tmp_path):
    monkeypatch.setenv("MLR_ALLOWED_ORIGINS", "https://mlr-sigma.vercel.app")
    with TestClient(create_app(tmp_path / "public")) as client:
        assert client.get("/api/experiments").status_code == 200
        assert client.post(
            "/api/experiments",
            headers={"Origin": "https://mlr-sigma.vercel.app"},
            files={"file": ("bad.csv", b"invalid\nvalue", "text/csv")},
        ).status_code == 400
        assert client.post(
            "/api/experiments",
            headers={"Origin": "https://other.example"},
            files={"file": ("bad.csv", b"invalid\nvalue", "text/csv")},
        ).status_code == 403


def test_complete_web_workflow(web, fixture_data):
    labeled = fixture_data.copy()
    labeled['Transport Mode'] = ['Bus', 'Train'] * (len(labeled) // 2)
    labeled['Station ID'] = ['ST-01', 'ST-02'] * (len(labeled) // 2)
    s = upload(web, labeled)
    base = f"/api/experiments/{s['id']}"
    assert s["metrics"] == [] and s["approved"] is False
    assert web.get(base + "/tables/dataset?limit=5").json()["total"] == 80
    assert web.post(base + "/train", json={"revision": 1, "selection": "enhanced"}).status_code == 409
    assert web.post(base + "/train", json={"revision": 1, "selection": "baseline"}).status_code == 202
    s = wait_for_job(web, s["id"])
    assert s["trained"] == ["Baseline MLR"]
    assert not s["export_ready"]
    config = s["config"]
    config["category_severity"] = {"Traffic Condition": {"A": 0, "B": 1, "C": 3}, "Weather Condition": {"W0": 0, "W1": 3}, "Time of Day": {"T0": 0, "T1": 3}}
    config["numerical_directions"]["Route Distance"] = "higher"
    config["vehicle_frequency_unit"] = "fixture vehicles/hour"
    s = web.put(base + "/config", json={"revision": 1, "config": config, "approve_interactions": True}).json()
    assert s["revision"] == 2 and s["trained"] == []
    assert web.post(base + "/train", json={"revision": 1}).status_code == 409
    assert web.post(base + "/train", json={"revision": 2}).status_code == 202
    s = wait_for_job(web, s["id"])
    assert s["status"] == "complete", s.get("error")
    assert len(s["metrics"]) == 2 and len(s["figures"]) == 8
    assert len(s["mode_metrics"]) == 4
    assert s["station_aggregation"]["available"] and s["station_aggregation"]["station_count"] == 2
    station_rows = web.get(base + "/tables/station_summary").json()
    assert station_rows["total"] == 2
    assert sum(row["Test Records"] for row in station_rows["rows"]) == s["test"]
    assert web.get(base + "/download/csv?table=mode_metrics").status_code == 200
    assert s["study_available"] and len(s["study_metrics"]) == 3
    bus = web.get(base + "/tables/predictions?transport_mode=bus").json()
    train = web.get(base + "/tables/predictions?transport_mode=train").json()
    assert bus["total"] == s["transport"]["test_counts"]["bus"]
    assert train["total"] == s["transport"]["test_counts"]["train"]
    assert bus["total"] + train["total"] == s["test"]
    assert all(row["Transport Mode"] == "Bus" for row in bus["rows"])
    assert all(row["Transport Mode"] == "Train" for row in train["rows"])
    assert web.get(base + "/tables/predictions?transport_mode=unspecified").json()["total"] == 0
    assert web.get(base + "/tables/predictions?transport_mode=ferry").status_code == 422
    assert web.get(base + "/tables/coefficients?transport_mode=bus").status_code == 400
    assert web.get(base).json()["metrics"] == s["metrics"]
    assert s["provenance"]["status"] == "undocumented"
    assert web.get(base + "/tables/study_predictions").json()["total"] == 16
    assert web.get(base + "/download/csv?table=study_comparisons").status_code == 200
    assert "Pending configuration" not in s["distribution"]
    for kind in ["excel", "bundle", "config", "reviews"]:
        assert web.get(base + "/download/" + kind).status_code == 200
    assert web.get(base + "/download/csv?table=predictions").status_code == 200
    assert web.get(base + "/figures/rmse").headers["content-type"] == "image/png"
    from PIL import Image
    from io import BytesIO
    dark_figure = web.get(base + "/figures/rmse?theme=dark")
    light_figure = web.get(base + "/figures/rmse")
    assert max(Image.open(BytesIO(dark_figure.content)).getpixel((0, 0))[:3]) < 60
    assert min(Image.open(BytesIO(light_figure.content)).getpixel((0, 0))[:3]) > 240
    assert web.get(base + "/download/csv?table=../../metadata").status_code == 404
    assert web.get(base + "/tables/classification").json()["total"] == 16
    target_free = labeled.drop(columns=["Actual Waiting Time"]).to_csv(index=False).encode()
    forecast = web.post(base + "/predict", files={"file": ("future.csv", target_free, "text/csv")})
    assert forecast.status_code == 200, forecast.text
    assert len(forecast.json()["rows"]) == len(labeled)
    assert "Enhanced Predicted Waiting Time" in forecast.json()["columns"]
    assert forecast.json()["station_aggregation"]["station_count"] == 2
    assert "Actual Waiting Time" not in forecast.json()["columns"]
    labeled_prediction = web.post(base + "/predict", files={"file": ("labeled.csv", labeled.to_csv(index=False).encode(), "text/csv")})
    assert labeled_prediction.status_code == 400 and "must omit" in labeled_prediction.text
    invalid_prediction = web.post(base + "/predict", files={"file": ("bad.csv", b"invalid\nvalue", "text/csv")})
    assert invalid_prediction.status_code == 400 and "Missing required" in invalid_prediction.text
    # Reload server-created state: persisted models/results retain their exact revision.
    web.app.state.store.sessions.clear()
    restored = web.get(base).json()
    assert restored["metrics"] == s["metrics"] and restored["export_ready"]
    assert restored["study_metrics"] == s["study_metrics"]
    assert len(web.get("/api/experiments").json()) == 1


def test_review_invalidates_and_persists(web, fixture_data):
    data = fixture_data.copy()
    data["Passenger Volume"] = 10.
    data.at[data.index[0], "Passenger Volume"] = 100000.
    s = upload(web, data)
    base = f"/api/experiments/{s['id']}"
    flags = web.get(base + "/tables/flags").json()["rows"]
    assert flags
    rid = flags[0]["Record ID"]
    record = web.get(base + "/records/" + rid).json()
    assert record["flagged"]
    response = web.put(base + "/reviews", json={"revision": 1, "record_id": rid, "action": "retain", "reason": "Verified artificial fixture"})
    assert response.status_code == 200
    assert response.json()["revision"] == 2
    assert web.get(base + "/tables/history").json()["total"] == 1
    web.app.state.store.sessions.clear()
    restored = web.get(base).json()
    assert restored["revision"] == 2 and restored["reviewed"] == 1
    assert web.put(base + "/reviews", json={"revision": 2, "record_id": "TEST_ONLY", "action": "exclude", "reason": "Invalid"}).status_code == 400


def test_single_action_analysis_preserves_reviews_and_requires_confirmation(web, fixture_data):
    data = fixture_data.copy()
    data["Passenger Volume"] = 10.
    data.loc[data.index[:4], "Passenger Volume"] = 100000.
    s = upload(web, data)
    base = f"/api/experiments/{s['id']}"
    assert s["flagged"] > 1
    assert web.post(base + "/analyze", json={"revision": 1}).status_code == 409
    assert web.post(base + "/analyze", json={"revision": 1, "approve_interactions": True}).status_code == 409
    assert web.post(base + "/analyze", json={"revision": 1, "approve_interactions": True, "retain_remaining": True}).status_code == 400
    unchanged = web.get(base).json()
    assert unchanged["revision"] == 1 and unchanged["approved"] is False and unchanged["reviewed"] == 0
    flag = web.get(base + "/tables/flags").json()["rows"][0]
    rid = flag["Record ID"]
    s = web.put(base + "/reviews", json={"revision": 1, "record_id": rid, "action": "exclude", "reason": "Artificial test of exclusion persistence"}).json()
    assert web.post(base + "/analyze", json={"revision": 1, "approve_interactions": True, "retain_remaining": True, "retain_reason": "Fixture"}).status_code == 409
    assert web.post(base + "/analyze", json={"revision": s["revision"], "approve_interactions": True, "retain_remaining": True, "retain_reason": "Retain artificial observations for software test"}).status_code == 202
    s = wait_for_job(web, s["id"])
    assert s["status"] == "complete" and s["reviewed"] == s["flagged"]
    assert s["reviewed_training"] == s["training"] - 1
    assert s["config"]["category_severity"] == unchanged["config"]["category_severity"]
    decisions = web.get(base + "/download/reviews").json()["decisions"]
    assert decisions[rid]["action"] == "exclude"
    assert all(v["action"] == "retain" and v["reason"].startswith("Retain artificial") for k, v in decisions.items() if k != rid)
    # JSON arrays and Python tuple defaults describe the same approved terms.
    documented = web.put(base + "/config", json={"revision": s["revision"], "config": {
        **s["config"], "research_notes": {"source_type": "simulated", "source_reference": "Artificial test fixture"}
    }}).json()
    assert documented["approved"] is True
    assert documented["reviewed"] == s["reviewed"]
    assert documented["provenance"]["status"] == "prototype"
    assert not documented["export_ready"]



@pytest.mark.parametrize("key,value", [("category_severity", []), ("category_severity", {"Traffic Condition": []}), ("numerical_directions", None), ("vehicle_frequency_unit", 100), ("random_state", -1)])
def test_invalid_web_settings_do_not_mutate_experiment(web, fixture_data, key, value):
    s = upload(web, fixture_data)
    config = {**s["config"], key: value}
    base = f"/api/experiments/{s['id']}"
    assert web.put(base + "/config", json={"revision": 1, "config": config}).status_code == 400
    assert web.get(base).json()["revision"] == 1


def test_legacy_classification_requires_rerun_without_overwriting_saved_results(web, fixture_data):
    s = upload(web, fixture_data)
    base = f"/api/experiments/{s['id']}"
    response = web.post(base + '/analyze', json={'revision': s['revision'], 'approve_interactions': True,
                                              'retain_remaining': True, 'retain_reason': 'Artificial fixture'})
    assert response.status_code == 202
    s = wait_for_job(web, s['id'])
    assert s['export_ready'] and not s['classification_stale']
    session = web.app.state.store.get(s['id'])
    old_export = session['export_dir']
    original_predictions = session['result'].predictions.copy(deep=True)
    del session['result'].classifier.method_version
    web.app.state.store.save(session)
    web.app.state.store.sessions.clear()
    stale = web.get(base).json()
    assert stale['classification_stale'] and not stale['export_ready']
    assert Path(old_export).exists()
    import pandas as pd
    pd.testing.assert_frame_equal(web.app.state.store.get(s['id'])['result'].predictions, original_predictions)
    assert web.post(base + '/analyze', json={'revision': stale['revision']}).status_code == 202
    fresh = wait_for_job(web, s['id'])
    assert fresh['export_ready'] and not fresh['classification_stale']
    assert fresh['classification_rules']['category_mappings']
    assert Path(old_export).exists()
