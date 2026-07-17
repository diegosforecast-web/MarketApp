import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent)
)

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200


def test_root():
    r = client.get("/")
    assert r.status_code == 200


def test_compare_models_not_exposed_in_v1():
    r = client.get("/api/v1/compare_models/schema")
    assert r.status_code == 404
