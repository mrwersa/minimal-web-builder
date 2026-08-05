from src.config import load_config


def test_load_config_reads_overrides(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "k-test")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("GEMINI_TEMPERATURE", "0.35")
    monkeypatch.setenv("GEMINI_MAX_OUTPUT_TOKENS", "2048")
    monkeypatch.setenv("GEMINI_MAX_PROMPT_CHARS", "900")

    cfg = load_config()

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

    cfg = load_config()

    assert cfg.temperature == 0.2
    assert cfg.max_output_tokens == 1500
    assert cfg.max_prompt_chars == 1200


def test_load_config_analytics_file_from_env(monkeypatch) -> None:
    monkeypatch.setenv("ANALYTICS_FILE", "data/events.jsonl")

    assert load_config().analytics_file == "data/events.jsonl"


def test_load_config_analytics_file_defaults_none(monkeypatch) -> None:
    monkeypatch.delenv("ANALYTICS_FILE", raising=False)

    assert load_config().analytics_file is None
