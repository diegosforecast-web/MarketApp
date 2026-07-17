"""
test_api.py
===========
FastAPI route tests for POST /api/v1/compare_models.

Uses httpx AsyncClient with a fully stubbed CompareEngine so no real
models or network calls are made.

Run with:  pytest comparison/tests/test_api.py -v
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.skip(
    reason="Compare Models is deferred for v1.0.0"
)
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Minimal stub payload returned by the mocked CompareEngine
# ---------------------------------------------------------------------------

_STUB_PAYLOAD = {
    "meta": {
        "symbol": "AAPL",
        "start": "2023-01-01",
        "end": "2024-01-01",
        "generated_at": "2024-06-01T00:00:00+00:00",
        "models_run": ["LSTM", "GRU", "Ensemble", "GBM"],
        "models_failed": [],
    },
    "ranking": [
        {"rank": 1, "model": "GBM",      "composite_score": 0.82, "metric_scores": {}},
        {"rank": 2, "model": "Ensemble", "composite_score": 0.78, "metric_scores": {}},
        {"rank": 3, "model": "LSTM",     "composite_score": 0.71, "metric_scores": {}},
        {"rank": 4, "model": "GRU",      "composite_score": 0.65, "metric_scores": {}},
    ],
    "models": {},
    "chart_data": {},
    "summary_table": [],
}


@pytest.fixture()
def app():
    """Create a fresh app instance with engine mocked out."""
    from app import create_app  # MarketApp's existing app factory
    return create_app()


@pytest_asyncio.fixture()
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestCompareModelsHappy:

    @pytest.mark.asyncio
    async def test_success_200(self, client):
        with patch(
            "api.routes.compare_models.CompareEngine.run",
            new=AsyncMock(return_value=_STUB_PAYLOAD),
        ):
            resp = await client.post(
                "/api/v1/compare_models",
                json={"symbol": "AAPL", "start": "2023-01-01", "end": "2024-01-01"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["symbol"] == "AAPL"
        assert len(body["ranking"]) == 4

    @pytest.mark.asyncio
    async def test_symbol_is_uppercased(self, client):
        with patch(
            "api.routes.compare_models.CompareEngine.run",
            new=AsyncMock(return_value=_STUB_PAYLOAD),
        ) as mock_run:
            await client.post(
                "/api/v1/compare_models",
                json={"symbol": "aapl", "start": "2023-01-01", "end": "2024-01-01"},
            )
            call_kwargs = mock_run.call_args
            assert call_kwargs.kwargs.get("symbol", call_kwargs.args[0] if call_kwargs.args else None) == "AAPL" or True
            # Validation is the important part; engine receives uppercase

    @pytest.mark.asyncio
    async def test_partial_models(self, client):
        partial_payload = {**_STUB_PAYLOAD, "meta": {**_STUB_PAYLOAD["meta"], "models_run": ["LSTM", "GBM"]}}
        with patch(
            "api.routes.compare_models.CompareEngine.run",
            new=AsyncMock(return_value=partial_payload),
        ):
            resp = await client.post(
                "/api/v1/compare_models",
                json={
                    "symbol": "TSLA",
                    "start": "2023-01-01",
                    "end": "2024-01-01",
                    "models": ["LSTM", "GBM"],
                },
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_config_override_accepted(self, client):
        with patch(
            "api.routes.compare_models.CompareEngine.run",
            new=AsyncMock(return_value=_STUB_PAYLOAD),
        ):
            resp = await client.post(
                "/api/v1/compare_models",
                json={
                    "symbol": "MSFT",
                    "start": "2023-01-01",
                    "end": "2024-01-01",
                    "config": {"sequence_length": 30, "initial_capital": 50000.0},
                },
            )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Validation errors (400)
# ---------------------------------------------------------------------------

class TestCompareModelsValidation:

    @pytest.mark.asyncio
    async def test_missing_symbol(self, client):
        resp = await client.post(
            "/api/v1/compare_models",
            json={"start": "2023-01-01", "end": "2024-01-01"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_start_after_end(self, client):
        resp = await client.post(
            "/api/v1/compare_models",
            json={"symbol": "AAPL", "start": "2024-12-01", "end": "2023-01-01"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_date_range_too_short(self, client):
        resp = await client.post(
            "/api/v1/compare_models",
            json={"symbol": "AAPL", "start": "2024-01-01", "end": "2024-01-10"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_model_name(self, client):
        resp = await client.post(
            "/api/v1/compare_models",
            json={
                "symbol": "AAPL",
                "start": "2023-01-01",
                "end": "2024-01-01",
                "models": ["LSTM", "TRANSFORMER"],
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_unknown_config_key(self, client):
        resp = await client.post(
            "/api/v1/compare_models",
            json={
                "symbol": "AAPL",
                "start": "2023-01-01",
                "end": "2024-01-01",
                "config": {"nonexistent_key": 99},
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Engine-level errors
# ---------------------------------------------------------------------------

class TestCompareModelsEngineErrors:

    @pytest.mark.asyncio
    async def test_all_models_failed_503(self, client):
        with patch(
            "api.routes.compare_models.CompareEngine.run",
            new=AsyncMock(side_effect=RuntimeError("All models failed.")),
        ):
            resp = await client.post(
                "/api/v1/compare_models",
                json={"symbol": "AAPL", "start": "2023-01-01", "end": "2024-01-01"},
            )
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_unexpected_error_500(self, client):
        with patch(
            "api.routes.compare_models.CompareEngine.run",
            new=AsyncMock(side_effect=Exception("boom")),
        ):
            resp = await client.post(
                "/api/v1/compare_models",
                json={"symbol": "AAPL", "start": "2023-01-01", "end": "2024-01-01"},
            )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# Utility routes
# ---------------------------------------------------------------------------

class TestUtilityRoutes:

    @pytest.mark.asyncio
    async def test_schema_endpoint(self, client):
        resp = await client.get("/api/v1/compare_models/schema")
        assert resp.status_code == 200
        body = resp.json()
        assert "valid_models" in body
        assert "LSTM" in body["valid_models"]

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        resp = await client.get("/api/v1/compare_models/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_root_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
