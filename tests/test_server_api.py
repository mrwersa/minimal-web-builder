from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.main import app
from server.runtime import GenerationClient
from src.config import AppConfig


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Avoid real provider/gemini setup; supply a minimal client with a real config.
    cfg = AppConfig(
        api_key="",
        model="g",
        temperature=0.7,
        max_output_tokens=100,
        max_prompt_chars=1200,
        analytics_file=None,
        provider="openrouter",
        openrouter_api_key="k",
        openrouter_model="google/gemini-2.5-flash",
        openrouter_base_url="https://openrouter.ai/api/v1",
    )
    app.state.client = GenerationClient(
        config=cfg, model="google/gemini-2.5-flash", genai=None
    )
    app.state.profiles = []
    return TestClient(app)


def test_health(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True
    assert j["provider"] == "openrouter"
    assert j["has_key"] is True


def test_options_shape(client: TestClient) -> None:
    r = client.get("/api/options")
    assert r.status_code == 200
    j = r.json()
    for key in (
        "profiles",
        "tones",
        "complexities",
        "refine_aspects",
        "sections",
        "color_limits",
        "tokens",
    ):
        assert key in j
    assert j["custom_profile_id"] == "custom"
    assert any(t["key"] == "minimal" for t in j["tones"])
    assert "accent" in j["tokens"]


def test_sections_listing(client: TestClient) -> None:
    r = client.get("/api/sections?code=<body><header>h</header><main>m</main></body>")
    assert r.status_code == 200
    tags = [s["tag"] for s in r.json()["sections"]]
    assert tags == ["header", "main"]


def test_generate_uses_mocked_output(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "server.main.generate",
        lambda *a, **k: "<!doctype html><html><body><h1>Hi</h1></body></html>",
    )
    r = client.post("/api/generate", json={"prompt": "a coffee shop landing page"})
    assert r.status_code == 200
    j = r.json()
    assert "<h1>Hi</h1>" in j["html"]
    assert j["settings"]["tone"] == "minimal"


def test_generate_rejects_empty_prompt(client: TestClient) -> None:
    r = client.post("/api/generate", json={"prompt": "   "})
    assert r.status_code == 400
    assert "detail" in r.json()


def test_generate_propagates_api_errors(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("server.main.generate", lambda *a, **k: "API error: boom")
    r = client.post("/api/generate", json={"prompt": "x"})
    assert r.status_code == 502
    assert "boom" in r.json()["detail"]


def test_generate_section_replaces_section(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    code = "<body><header>OLD</header><main>m</main></body>"
    monkeypatch.setattr(
        "server.main.regenerate_section",
        lambda *a, **k: "<header>NEW</header>",
    )
    r = client.post(
        "/api/generate-section",
        json={"code": code, "section_index": 0, "instructions": "make it new"},
    )
    assert r.status_code == 200
    assert "<header>NEW</header>" in r.json()["html"]
    assert "OLD" not in r.json()["html"]


def test_generate_section_bad_index(client: TestClient) -> None:
    r = client.post(
        "/api/generate-section",
        json={"code": "<body><header>x</header></body>", "section_index": 9},
    )
    assert r.status_code == 400


def test_export_single_and_split(client: TestClient) -> None:
    html = "<!doctype html><html><head><style>h1{color:red}</style></head><body><h1>Hi</h1></body></html>"
    r = client.post("/api/export", json={"html": html, "mode": "single"})
    assert r.status_code == 200
    assert r.json()["files"]["index.html"] == html
    r = client.post("/api/export", json={"html": html, "mode": "split"})
    j = r.json()
    assert set(j["files"]) == {"index.html", "styles.css", "app.js"}
    assert "color:red" in j["files"]["styles.css"]


def test_preview_doc_endpoint(client: TestClient) -> None:
    r = client.get("/api/preview-doc?html=<h1>Hi</h1>&editing=true")
    assert r.status_code == 200
    doc = r.json()["doc"]
    assert "<!doctype html>" in doc
    assert "Content-Security-Policy" in doc


def test_templates_round_trip(
    client: TestClient, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import server.main as m

    monkeypatch.setattr(m, "TEMPLATES_DIR", tmp_path)
    r = client.post("/api/templates", json={"name": "my-page", "html": "<html></html>"})
    assert r.status_code == 200
    assert r.json()["saved"] == "my-page"
    r = client.get("/api/templates")
    assert r.json()["templates"] == ["my-page"]
    r = client.delete("/api/templates/my-page")
    assert r.status_code == 200
    assert client.get("/api/templates").json()["templates"] == []
