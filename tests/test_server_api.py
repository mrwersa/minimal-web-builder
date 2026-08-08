from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.assets import ReusableAssetService
from server.auth import AuthService
from server.database import Database
from server.main import app
from server.projects import ProjectService
from server.runtime import GenerationClient
from src.config import AppConfig


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path):
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
        database_url=f"sqlite:///{tmp_path / 'projects.db'}",
    )
    generation_client = GenerationClient(
        config=cfg, model="google/gemini-2.5-flash", genai=None
    )
    app.state.client = generation_client
    app.state.profiles = []
    database = Database.from_url(cfg.database_url)
    app.state.database = database
    app.state.auth = AuthService(database.sessions, session_hours=cfg.session_hours)
    app.state.projects = ProjectService(database.sessions)
    app.state.assets = ReusableAssetService(database.sessions)
    test_client = TestClient(app)
    response = test_client.post(
        "/api/auth/register",
        json={"email": "owner@example.test", "password": "correct horse battery"},
    )
    assert response.status_code == 201
    try:
        yield test_client
    finally:
        test_client.close()
        database.close()


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
    r = client.post(
        "/api/sections",
        json={"code": "<body><header>h</header><main>m</main></body>"},
    )
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


def test_generate_accepts_constraints_without_prompt(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "server.main.generate",
        lambda *a, **k: "<!doctype html><html><body><h1>Constrained</h1></body></html>",
    )
    r = client.post(
        "/api/generate",
        json={
            "constraints": {
                "sections": ["hero", "footer"],
                "color_limit": "single-accent",
                "density": "balanced",
            }
        },
    )
    assert r.status_code == 200
    assert "Constrained" in r.json()["html"]


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


def test_templates_round_trip(client: TestClient) -> None:
    r = client.post("/api/templates", json={"name": "my-page", "html": "<html></html>"})
    assert r.status_code == 200
    assert r.json()["saved"] == "my-page"
    r = client.get("/api/templates")
    assert r.json()["templates"] == ["my-page"]
    r = client.get("/api/templates/my-page")
    assert r.status_code == 200
    assert r.json() == {"name": "my-page", "html": "<html></html>"}
    r = client.delete("/api/templates/my-page")
    assert r.status_code == 200
    assert client.get("/api/templates").json()["templates"] == []


def test_template_load_missing_returns_404(client: TestClient) -> None:
    r = client.get("/api/templates/missing")
    assert r.status_code == 404


def test_layout_dna_round_trip(client: TestClient) -> None:
    html = "<body><header>Top</header><main>Body</main><footer>End</footer></body>"

    saved = client.post("/api/layout-dnas", json={"html": html})

    assert saved.status_code == 200
    assert saved.json()["name"] == "header_main_footer"
    listed = client.get("/api/layout-dnas")
    assert listed.status_code == 200
    assert listed.json()["dnas"][0]["signature"] == "header/main/footer"


def test_project_revision_api_round_trip(client: TestClient) -> None:
    created_response = client.post(
        "/api/projects", json={"name": "Product", "html": "<main>v1</main>"}
    )
    assert created_response.status_code == 201
    created = created_response.json()
    page = created["pages"][0]

    assert client.get("/api/projects").json()["projects"][0]["id"] == created["id"]
    saved_response = client.put(
        f"/api/pages/{page['id']}/document",
        json={
            "html": "<main>v2</main>",
            "expected_version": 1,
            "source": "autosave",
        },
    )
    assert saved_response.status_code == 200
    assert saved_response.json()["version"] == 2

    conflict = client.put(
        f"/api/pages/{page['id']}/document",
        json={"html": "stale", "expected_version": 1},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["current_version"] == 2

    revisions = client.get(f"/api/pages/{page['id']}/revisions").json()["revisions"]
    assert [revision["sequence"] for revision in revisions] == [2, 1]

    restored = client.post(
        f"/api/pages/{page['id']}/revisions/{revisions[1]['id']}/restore",
        json={"expected_version": 2},
    )
    assert restored.status_code == 200
    assert restored.json()["html"] == "<main>v1</main>"
    assert restored.json()["version"] == 3

    renamed = client.patch(
        f"/api/projects/{created['id']}", json={"name": "Renamed Product"}
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Renamed Product"

    duplicate = client.post(
        f"/api/projects/{created['id']}/duplicate", json={"name": None}
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["name"] == "Renamed Product Copy"
    assert duplicate.json()["pages"][0]["html"] == "<main>v1</main>"

    search = client.get("/api/projects", params={"search": "renamed product copy"})
    assert [item["id"] for item in search.json()["projects"]] == [
        duplicate.json()["id"]
    ]

    archived = client.delete(f"/api/projects/{created['id']}")
    assert archived.status_code == 200
    project_ids = [
        item["id"] for item in client.get("/api/projects").json()["projects"]
    ]
    assert created["id"] not in project_ids


def test_project_api_requires_authentication(client: TestClient) -> None:
    client.cookies.clear()

    response = client.get("/api/projects")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_authentication_round_trip(client: TestClient) -> None:
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "owner@example.test"

    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401

    invalid = client.post(
        "/api/auth/login",
        json={"email": "owner@example.test", "password": "wrong password value"},
    )
    assert invalid.status_code == 401

    login = client.post(
        "/api/auth/login",
        json={"email": "OWNER@example.test", "password": "correct horse battery"},
    )
    assert login.status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_duplicate_registration_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "OWNER@example.test", "password": "another secure password"},
    )

    assert response.status_code == 409


def test_project_api_does_not_expose_another_users_project(client: TestClient) -> None:
    project = client.post(
        "/api/projects", json={"name": "Private", "html": "secret"}
    ).json()
    assert client.post("/api/auth/logout").status_code == 204
    second_user = client.post(
        "/api/auth/register",
        json={"email": "second@example.test", "password": "another secure password"},
    )
    assert second_user.status_code == 201

    assert client.get("/api/projects").json()["projects"] == []
    assert client.get(f"/api/projects/{project['id']}").status_code == 404
    assert client.get(f"/api/pages/{project['pages'][0]['id']}").status_code == 404


def test_reusable_assets_are_isolated_between_users(client: TestClient) -> None:
    client.post(
        "/api/templates", json={"name": "private", "html": "<main>secret</main>"}
    )
    client.post("/api/layout-dnas", json={"html": "<body><header>x</header></body>"})
    client.post("/api/auth/logout")
    client.post(
        "/api/auth/register",
        json={"email": "second@example.test", "password": "another secure password"},
    )

    assert client.get("/api/templates").json()["templates"] == []
    assert client.get("/api/templates/private").status_code == 404
    assert client.get("/api/layout-dnas").json()["dnas"] == []
