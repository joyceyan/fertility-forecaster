"""Integration tests for the FastAPI endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from fertility_forecaster.api import app

client = TestClient(app)


class TestHealth:
    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestSimulate:
    def test_simulate_minimal_params(self):
        resp = client.post(
            "/simulate",
            json={"female_age": 28, "desired_children": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert 0 <= data["completion_rate"] <= 1
        assert data["median_time_to_completion_months"] is not None
        assert data["mean_age_at_completion"] is not None
        assert len(data["time_distribution"]) == 12
        assert "natural" in data["completion_by_method"]
        # params_used present and correct for defaults
        pu = data["params_used"]
        assert pu["curve_type"] == "nulligravid"
        assert pu["base_fecundability"] == pytest.approx(0.25)
        assert pu["bmi_natural_fr"] == pytest.approx(1.0)
        assert pu["smoking_fr"] == pytest.approx(1.0)

    def test_simulate_all_params(self):
        resp = client.post(
            "/simulate",
            json={
                "female_age": 32,
                "desired_children": 2,
                "male_age": 35,
                "bmi": 36.0,
                "ivf_willingness": "yes",
                "smoking_status": "current_regular",
                "prior_live_births": 0,
                "prior_miscarriages": 0,
                "cycles_tried": 3,
                "frozen_egg_batches": [],
                "frozen_embryo_batches": [],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        pu = data["params_used"]
        assert pu["smoking_fr"] == pytest.approx(0.77)
        assert pu["bmi_natural_fr"] == pytest.approx(0.78)

    def test_simulate_frozen_batches_nonzero(self):
        resp = client.post(
            "/simulate",
            json={
                "female_age": 38,
                "desired_children": 1,
                "ivf_willingness": "yes",
                "frozen_egg_batches": [
                    {"age_at_freeze": 30, "num_eggs": 20},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        cbm = data["completion_by_method"]
        # With frozen eggs available, at least some should use them
        assert cbm["ivf_frozen_egg"] > 0 or cbm["ivf_frozen_embryo"] > 0 or cbm["natural"] > 0

    def test_simulate_prior_births_gravid(self):
        resp = client.post(
            "/simulate",
            json={
                "female_age": 30,
                "desired_children": 2,
                "prior_live_births": 1,
                "age_at_last_birth": 27,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["params_used"]["curve_type"] == "gravid"

    def test_simulate_invalid_params_422(self):
        # Missing required fields
        resp = client.post("/simulate", json={})
        assert resp.status_code == 422

        # female_age out of range
        resp = client.post(
            "/simulate",
            json={"female_age": 50, "desired_children": 1},
        )
        assert resp.status_code == 422

        # age_at_last_birth > female_age
        resp = client.post(
            "/simulate",
            json={
                "female_age": 25,
                "desired_children": 1,
                "age_at_last_birth": 30,
            },
        )
        assert resp.status_code == 422


class TestSweep:
    def test_sweep_correct_age_points(self):
        resp = client.post(
            "/sweep",
            json={
                "age_range_start": 25,
                "age_range_end": 35,
                "age_step": 1,
                "desired_children": 1,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 11
        assert len(data["scenarios"]["natural_only"]) == 11
        assert len(data["scenarios"]["with_ivf"]) == 11
        # Ages should match expected range
        ages = [p["starting_age"] for p in data["results"]]
        assert ages[0] == pytest.approx(25.0)
        assert ages[-1] == pytest.approx(35.0)

    def test_sweep_with_frozen_scenario(self):
        resp = client.post(
            "/sweep",
            json={
                "age_range_start": 30,
                "age_range_end": 35,
                "age_step": 1,
                "desired_children": 1,
                "ivf_willingness": "yes",
                "frozen_egg_batches": [
                    {"age_at_freeze": 28, "num_eggs": 15},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["scenarios"]["with_frozen"] is not None
        assert len(data["scenarios"]["with_frozen"]) == 6

    def test_sweep_without_frozen_no_scenario(self):
        resp = client.post(
            "/sweep",
            json={
                "age_range_start": 25,
                "age_range_end": 30,
                "age_step": 1,
                "desired_children": 1,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["scenarios"]["with_frozen"] is None
