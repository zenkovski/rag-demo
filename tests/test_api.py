# -*- coding: utf-8 -*-
"""REST API (tools/api.py): úspěch, špatný vstup, chybějící klíč, výpadek a pomalý poskytovatel. Bez sítě, z cache."""
import sys
import time
from pathlib import Path
from urllib.parse import quote

import pytest
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

import api  # noqa: E402
import datasets  # noqa: E402
import rag  # noqa: E402
import service  # noqa: E402

KEY = {"X-API-Key": "test-key"}
Q4 = next(q["q"] for q in datasets.questions() if q["id"] == 4)
client = TestClient(api.app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def api_keys(monkeypatch):
    monkeypatch.setenv("RAG_API_KEYS", "other-key, test-key")


def assert_error(r, status, code):
    assert r.status_code == status, r.text
    body = r.json()["error"]
    assert body["code"] == code and body["message"] and body["request_id"] == r.headers["X-Request-ID"]


# ---------- úspěch ----------
def test_health_without_key():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["passages"] == 2475


def test_search_ok():
    r = client.post("/api/v1/search", headers=KEY, json={"query": Q4, "k": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "fast" and len(body["passages"]) == 3
    assert body["passages"][0]["id"] == "ZP § 51 odst. 2" and body["passages"][0]["source_url"].startswith("https://")


def test_search_full_mode_same_as_service():
    r = client.post("/api/v1/search", headers=KEY, json={"query": Q4, "mode": "full"})
    assert [p["id"] for p in r.json()["passages"]] == [p.id for p in service.search(Q4, mode="full").passages]


def test_ask_ok_with_citations():
    r = client.post("/api/v1/ask", headers=KEY, json={"question": Q4})
    assert r.status_code == 200
    body = r.json()
    assert body["evidence_status"] == "sufficient" and body["citations"]
    assert {"marker", "id", "excerpt", "source_url"} <= set(body["citations"][0])


def test_document_ok_url_encoded():
    r = client.get("/api/v1/documents/" + quote("ZP § 51 odst. 2"), headers=KEY)
    assert r.status_code == 200 and r.json()["law_number"] == "262/2006 Sb."


def test_request_id_is_echoed():
    r = client.post("/api/v1/search", headers={**KEY, "X-Request-ID": "abc-123"}, json={"query": Q4})
    assert r.headers["X-Request-ID"] == "abc-123"


def test_openapi_lists_endpoints():
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/api/v1/search", "/api/v1/ask", "/api/v1/documents/{doc_id}", "/health"} <= set(paths)


# ---------- klíč ----------
@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong"}, {"X-API-Key": ""}])
def test_unauthorized(headers):
    assert_error(client.post("/api/v1/search", headers=headers, json={"query": Q4}), 401, "unauthorized")


def test_no_keys_configured_rejects_everyone(monkeypatch):
    monkeypatch.setenv("RAG_API_KEYS", "")
    assert_error(client.get("/api/v1/documents/x", headers=KEY), 401, "unauthorized")


# ---------- špatný vstup ----------
@pytest.mark.parametrize("body", [{}, {"query": "ab"}, {"query": "x" * 501}, {"query": Q4, "k": 0}, {"query": Q4, "k": 99},
                                  {"query": Q4, "mode": "slow"}, {"query": Q4, "laws": ["GDPR"]}, {"query": 42}])
def test_invalid_input(body):
    assert_error(client.post("/api/v1/search", headers=KEY, json=body), 422, "invalid_input")


def test_unknown_document_404_with_suggestions():
    r = client.get("/api/v1/documents/" + quote("ZP § 51"), headers=KEY)
    assert_error(r, 404, "not_found")
    assert "ZP § 51 odst. 1" in r.json()["error"]["details"]["suggestions"]


def test_body_too_large():
    r = client.post("/api/v1/search", headers={**KEY, "Content-Type": "application/json"}, content=b'{"query": "' + b"x" * 20000 + b'"}')
    assert_error(r, 413, "payload_too_large")


def test_unknown_route_has_same_error_format():
    assert_error(client.get("/api/v2/nothing"), 404, "not_found")


# ---------- poskytovatel modelů ----------
def test_provider_unavailable_503(monkeypatch):
    def down(*a, **kw):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(rag, "search", down)
    assert_error(client.post("/api/v1/ask", headers=KEY, json={"question": Q4}), 503, "provider_unavailable")


def test_provider_timeout_504(monkeypatch):
    monkeypatch.setattr(rag, "search", lambda *a, **kw: time.sleep(1))
    monkeypatch.setattr(service, "TIMEOUT_S", 0.05)
    assert_error(client.post("/api/v1/search", headers=KEY, json={"query": Q4}), 504, "provider_timeout")


def test_offline_cache_miss_503():
    r = client.post("/api/v1/search", headers=KEY, json={"query": "Otázka, která v cache určitě není: kolik stojí rohlík?"})
    assert_error(r, 503, "provider_unavailable")


def test_unexpected_error_hides_details(monkeypatch):
    def boom(*a, **kw):
        raise ZeroDivisionError("secret internals")
    monkeypatch.setattr(rag, "search", boom)
    r = client.post("/api/v1/search", headers=KEY, json={"query": Q4})
    assert_error(r, 500, "internal_error")
    assert "secret" not in r.text
