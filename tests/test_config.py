from src.config import (
    DEFAULT_OPENROUTER_MODEL,
    GEMINI_PROVIDER,
    OPENROUTER_PROVIDER,
    load_config,
)

_NO_DOTENV = "does-not-exist.env"


def test_load_config_reads_overrides(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "k-test")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("GEMINI_TEMPERATURE", "0.35")
    monkeypatch.setenv("GEMINI_MAX_OUTPUT_TOKENS", "2048")
    monkeypatch.setenv("GEMINI_MAX_PROMPT_CHARS", "900")

    cfg = load_config(dotenv_path=_NO_DOTENV)

    assert cfg.api_key == "k-test"
    assert cfg.model == "gemini-2.5-flash"
    assert cfg.temperature == 0.35
    assert cfg.max_output_tokens == 2048
    assert cfg.max_prompt_chars == 900


def test_load_config_falls_back_on_invalid_numeric(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "k-test")
    monkeypatch.setenv("GEMINI_TEMPERATURE", "not-a-float")
    monkeypatch.setenv("GEMINI_MAX_OUTPUT_TOKENS", "not-an-int")
    monkeypatch.setenv("GEMINI_MAX_PROMPT_CHARS", "not-an-int")

    cfg = load_config(dotenv_path=_NO_DOTENV)

    assert cfg.temperature == 0.2
    assert cfg.max_output_tokens == 8192
    assert cfg.max_prompt_chars == 1200


def test_load_config_analytics_file_from_env(monkeypatch) -> None:
    monkeypatch.setenv("ANALYTICS_FILE", "data/events.jsonl")

    assert load_config(dotenv_path=_NO_DOTENV).analytics_file == "data/events.jsonl"


def test_load_config_analytics_file_defaults_none(monkeypatch) -> None:
    monkeypatch.delenv("ANALYTICS_FILE", raising=False)

    assert load_config(dotenv_path=_NO_DOTENV).analytics_file is None


def test_load_config_defaults_to_gemini_provider(monkeypatch) -> None:
    monkeypatch.delenv("GENERATION_PROVIDER", raising=False)

    cfg = load_config(dotenv_path=_NO_DOTENV)

    assert cfg.provider == GEMINI_PROVIDER
    assert cfg.openrouter_api_key is None


def test_load_config_reads_openrouter_settings(monkeypatch) -> None:
    monkeypatch.setenv("GENERATION_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    monkeypatch.setenv("OPENROUTER_MODEL", "anthropic/claude-3.5-haiku")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://proxy.example/v1")

    cfg = load_config(dotenv_path=_NO_DOTENV)

    assert cfg.provider == OPENROUTER_PROVIDER
    assert cfg.openrouter_api_key == "or-test"
    assert cfg.openrouter_model == "anthropic/claude-3.5-haiku"
    assert cfg.openrouter_base_url == "https://proxy.example/v1"


def test_load_config_openrouter_defaults(monkeypatch) -> None:
    monkeypatch.setenv("GENERATION_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")

    cfg = load_config(dotenv_path=_NO_DOTENV)

    assert cfg.openrouter_model == DEFAULT_OPENROUTER_MODEL
    assert cfg.openrouter_base_url == "https://openrouter.ai/api/v1"


def test_load_config_case_insensitive_provider(monkeypatch) -> None:
    monkeypatch.setenv("GENERATION_PROVIDER", "OpenRouter")

    assert load_config(dotenv_path=_NO_DOTENV).provider == OPENROUTER_PROVIDER


def test_load_config_rejects_unknown_provider(monkeypatch) -> None:
    monkeypatch.setenv("GENERATION_PROVIDER", "watson")

    assert load_config(dotenv_path=_NO_DOTENV).provider == GEMINI_PROVIDER


def test_load_config_reads_values_from_dotenv_path(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GENERATION_PROVIDER=openrouter\n"
        "OPENROUTER_API_KEY=or-file\n"
        "GEMINI_TEMPERATURE=0.5\n",
        encoding="utf-8",
    )

    cfg = load_config(dotenv_path=env_file)

    assert cfg.provider == OPENROUTER_PROVIDER
    assert cfg.openrouter_api_key == "or-file"
    assert cfg.temperature == 0.5
