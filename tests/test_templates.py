from pathlib import Path

import pytest

from src.templates import (
    delete_template,
    list_templates,
    load_template,
    sanitize_template_name,
    save_template,
)


def test_sanitize_accepts_valid_names() -> None:
    assert sanitize_template_name("my-page") == "my-page"
    assert sanitize_template_name("  Landing_v2  ") == "Landing_v2"
    assert sanitize_template_name("my_page.html") == "my_page"


def test_sanitize_rejects_empty() -> None:
    with pytest.raises(ValueError, match="empty"):
        sanitize_template_name("   ")


def test_sanitize_rejects_path_separators_and_spaces() -> None:
    for bad in ("../evil", "a/b", "a\\b", "..", ".", "a b"):
        with pytest.raises(ValueError, match="may only contain"):
            sanitize_template_name(bad)


def test_sanitize_rejects_too_long() -> None:
    with pytest.raises(ValueError, match="at most"):
        sanitize_template_name("x" * 65)


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    path = save_template(tmp_path, "hero", "<section>hi</section>")

    assert path.name == "hero.html"
    assert path.exists()
    assert load_template(tmp_path, "hero") == "<section>hi</section>"


def test_save_creates_directory(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "templates"
    save_template(target, "page", "<p>x</p>")

    assert (target / "page.html").exists()


def test_list_templates_returns_sorted_stems(tmp_path: Path) -> None:
    save_template(tmp_path, "beta", "<p>1</p>")
    save_template(tmp_path, "alpha", "<p>2</p>")
    (tmp_path / "notes.txt").write_text("not a template", encoding="utf-8")

    assert list_templates(tmp_path) == ["alpha", "beta"]


def test_list_templates_missing_dir_returns_empty(tmp_path: Path) -> None:
    assert list_templates(tmp_path / "does-not-exist") == []


def test_load_missing_template_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_template(tmp_path, "missing")


def test_delete_template_removes_file(tmp_path: Path) -> None:
    save_template(tmp_path, "page", "<p>x</p>")
    delete_template(tmp_path, "page")

    assert not (tmp_path / "page.html").exists()
    assert list_templates(tmp_path) == []


def test_delete_template_is_idempotent(tmp_path: Path) -> None:
    delete_template(tmp_path, "never-existed")
