from __future__ import annotations

import time
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from server.assets import ReusableAssetService
from server.auth import AuthService
from server.controls import RequestControlService
from server.database import Database
from server.main import app
from server.orchestrator import GenerationOrchestrator
from server.projects import ProjectService
from server.runtime import GenerationClient
from src.config import AppConfig
from tests.editor_document import editor_document


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
    app.state.orchestrator = GenerationOrchestrator(database.sessions)
    app.state.controls = RequestControlService(database.sessions)
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


TERMINAL = {"succeeded", "failed", "cancelled"}


def run_generation(
    client: TestClient, path: str, payload: dict, timeout: float = 10.0
) -> dict:
    """Submit a generation and wait for the background job to settle."""
    response = client.post(path, json=payload)
    assert response.status_code == 202, response.text
    job_id = response.json()["job_id"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/generation-jobs/{job_id}").json()
        if job["status"] in TERMINAL:
            return job
        time.sleep(0.01)
    raise AssertionError(f"job {job_id} never settled")


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
    ):
        assert key in j
    assert j["custom_profile_id"] == "custom"
    assert any(t["key"] == "minimal" for t in j["tones"])


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
    job = run_generation(
        client,
        "/api/generate",
        {"prompt": "a coffee shop landing page", "thread_id": "generate-thread"},
    )
    assert job["status"] == "succeeded"
    result = job["result"]
    assert "<h1>Hi</h1>" in result["html"]
    assert result["settings"]["tone"] == "minimal"
    checkpoint = client.get("/api/conversations/generate-thread").json()
    assert checkpoint["current_code"] == result["html"]
    jobs = client.get("/api/generation-jobs").json()["jobs"]
    assert jobs[0]["operation"] == "generate"


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
    job = run_generation(
        client,
        "/api/generate",
        {
            "constraints": {
                "sections": ["hero", "footer"],
                "color_limit": "single-accent",
                "density": "balanced",
            }
        },
    )
    assert "Constrained" in job["result"]["html"]


def test_generate_propagates_api_errors(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("server.main.generate", lambda *a, **k: "API error: boom")

    job = run_generation(client, "/api/generate", {"prompt": "x"})

    # The provider failure is now reported on the job rather than as the status
    # of the submission, which succeeded.
    assert job["status"] == "failed"
    assert job["failure_kind"] == "provider"
    assert job["error"] == "API error: boom"


def test_generation_job_stats_report_outcomes_and_latency(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "server.main.generate",
        lambda *a, **k: "<!doctype html><html><body><h1>Hi</h1></body></html>",
    )
    run_generation(client, "/api/generate", {"prompt": "a landing page"})
    monkeypatch.setattr("server.main.generate", lambda *a, **k: "API error: boom")
    run_generation(client, "/api/generate", {"prompt": "another page"})

    stats = client.get("/api/generation-jobs/stats").json()

    assert stats["totals"]["total"] == 2
    assert stats["totals"]["succeeded"] == 1
    assert stats["totals"]["failed"] == 1
    assert stats["totals"]["success_rate"] == 0.5
    assert stats["totals"]["p95_ms"] is not None
    assert stats["failure_kinds"] == {"provider": 1}
    assert [item["operation"] for item in stats["operations"]] == ["generate"]


def test_generation_job_stats_require_authentication(client: TestClient) -> None:
    client.post("/api/auth/logout")
    assert client.get("/api/generation-jobs/stats").status_code == 401


def test_generate_section_replaces_section(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    code = "<body><header>OLD</header><main>m</main></body>"
    monkeypatch.setattr(
        "server.main.regenerate_section",
        lambda *a, **k: "<header>NEW</header>",
    )
    job = run_generation(
        client,
        "/api/generate-section",
        {"code": code, "section_index": 0, "instructions": "make it new"},
    )
    assert "<header>NEW</header>" in job["result"]["html"]
    assert "OLD" not in job["result"]["html"]


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


def test_chat_checkpoint_and_job_are_durable(client: TestClient) -> None:
    job = run_generation(
        client, "/api/chat", {"message": "hello", "thread_id": "conversation-1"}
    )

    assert job["status"] == "succeeded"
    assert job["result"]["intent"] == "answer"
    draft = client.put(
        "/api/conversations/conversation-1/document",
        json={
            "code": "<main>manually edited</main>",
            "document": editor_document(),
        },
    )
    assert draft.status_code == 200
    app.state.orchestrator = GenerationOrchestrator(app.state.database.sessions)
    checkpoint = client.get("/api/conversations/conversation-1")
    assert checkpoint.status_code == 200
    assert checkpoint.json()["thread_id"] == "conversation-1"
    assert checkpoint.json()["current_code"] == "<main>manually edited</main>"
    assert checkpoint.json()["document"] == editor_document()
    assert [item["role"] for item in checkpoint.json()["messages"]] == [
        "user",
        "assistant",
    ]
    jobs = client.get("/api/generation-jobs").json()["jobs"]
    assert jobs[0]["operation"] == "chat"
    assert jobs[0]["status"] == "succeeded"


def test_chat_rejects_a_missing_scoped_editor_node(client: TestClient) -> None:
    response = client.post(
        "/api/chat",
        json={
            "message": "make it warmer",
            "current_code": '<main data-mwb-id="present">Old</main>',
            "target_node_id": "missing",
        },
    )

    assert response.status_code == 400
    assert "Selected element" in response.json()["detail"]


def test_project_revision_api_round_trip(client: TestClient) -> None:
    created_response = client.post(
        "/api/projects",
        json={
            "name": "Product",
            "html": "<main>v1</main>",
            "document": editor_document("project-v1"),
        },
    )
    assert created_response.status_code == 201
    created = created_response.json()
    page = created["pages"][0]
    assert page["document"] == editor_document("project-v1")

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

    checkpoint = client.post(
        f"/api/pages/{page['id']}/checkpoints",
        json={"name": "Before launch", "expected_version": 2},
    )
    assert checkpoint.status_code == 201
    assert checkpoint.json()["version"] == 3
    checkpoint_revision = client.get(f"/api/pages/{page['id']}/revisions").json()[
        "revisions"
    ][0]
    assert checkpoint_revision["name"] == "Before launch"
    revision_copy = client.post(
        f"/api/pages/{page['id']}/revisions/{revisions[1]['id']}/duplicate",
        json={"name": "Historical copy"},
    )
    assert revision_copy.status_code == 201
    assert revision_copy.json()["pages"][0]["html"] == "<main>v1</main>"

    restored = client.post(
        f"/api/pages/{page['id']}/revisions/{revisions[1]['id']}/restore",
        json={"expected_version": 3},
    )
    assert restored.status_code == 200
    assert restored.json()["html"] == "<main>v1</main>"
    assert restored.json()["version"] == 4

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


def test_project_api_rejects_invalid_structured_document(client: TestClient) -> None:
    response = client.post(
        "/api/projects",
        json={"name": "Invalid", "html": "", "document": {"schemaVersion": 99}},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported editor document schema"


def test_project_create_replays_idempotent_response(client: TestClient) -> None:
    headers = {"Idempotency-Key": "create-project-1"}
    payload = {"name": "Only once", "html": "<main>one</main>"}

    first = client.post("/api/projects", json=payload, headers=headers)
    replay = client.post("/api/projects", json=payload, headers=headers)

    assert first.status_code == replay.status_code == 201
    assert first.json()["id"] == replay.json()["id"]
    assert len(client.get("/api/projects").json()["projects"]) == 1
    conflict = client.post(
        "/api/projects",
        json={"name": "Different", "html": ""},
        headers=headers,
    )
    assert conflict.status_code == 409


def test_mutations_create_owner_scoped_audit_events(client: TestClient) -> None:
    response = client.post("/api/projects", json={"name": "Audited", "html": ""})
    assert response.status_code == 201

    events = client.get("/api/audit-events").json()["events"]

    assert events[0]["action"] == "POST /api/projects"
    assert events[0]["status_code"] == 201


def test_project_api_requires_authentication(client: TestClient) -> None:
    client.cookies.clear()

    response = client.get("/api/projects")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_authenticated_request_reuses_middleware_principal(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    authenticate = app.state.auth.authenticate
    calls = 0

    def counted_authenticate(token):
        nonlocal calls
        calls += 1
        return authenticate(token)

    monkeypatch.setattr(app.state.auth, "authenticate", counted_authenticate)

    assert client.get("/api/projects").status_code == 200
    assert calls == 1


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


def test_auth_rate_limit_returns_retry_after(client: TestClient) -> None:
    app.state.client.config = replace(
        app.state.client.config, auth_rate_limit_per_minute=1
    )

    response = client.post(
        "/api/auth/login",
        json={"email": "owner@example.test", "password": "correct horse battery"},
    )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"


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


def test_conversations_and_jobs_are_isolated_between_users(client: TestClient) -> None:
    run_generation(
        client, "/api/chat", {"message": "hello", "thread_id": "private-thread"}
    )
    client.post("/api/auth/logout")
    client.post(
        "/api/auth/register",
        json={"email": "second@example.test", "password": "another secure password"},
    )

    assert client.get("/api/conversations/private-thread").status_code == 404
    assert client.get("/api/generation-jobs").json()["jobs"] == []
