from __future__ import annotations

import pytest

from server.assets import (
    ReusableAssetNotFoundError,
    ReusableAssetService,
    ReusableAssetValidationError,
    sanitize_template_name,
)
from server.database import Database
from server.models import UserRecord
from src.layout_dna import LayoutDNA

OWNER_ID = "00000000-0000-0000-0000-000000000020"
OTHER_ID = "00000000-0000-0000-0000-000000000021"


@pytest.fixture()
def assets(tmp_path):
    database = Database.from_url(f"sqlite:///{tmp_path / 'assets.db'}")
    with database.sessions.begin() as session:
        session.add_all(
            [
                UserRecord(
                    id=OWNER_ID,
                    email="owner@example.test",
                    password_hash="!test-account",
                ),
                UserRecord(
                    id=OTHER_ID,
                    email="other@example.test",
                    password_hash="!test-account",
                ),
            ]
        )
    try:
        yield ReusableAssetService(database.sessions)
    finally:
        database.close()


def test_sanitize_accepts_valid_names() -> None:
    assert sanitize_template_name("my-page") == "my-page"
    assert sanitize_template_name("  Landing_v2  ") == "Landing_v2"
    assert sanitize_template_name("my_page.html") == "my_page"


def test_sanitize_rejects_invalid_names() -> None:
    for bad in ("", "../evil", "a/b", "a\\b", "..", ".", "a b", "x" * 65):
        with pytest.raises(ReusableAssetValidationError):
            sanitize_template_name(bad)


def test_template_round_trip_update_and_delete(assets: ReusableAssetService) -> None:
    assert assets.save_template(OWNER_ID, "hero", "<section>one</section>") == "hero"
    assets.save_template(OWNER_ID, "hero.html", "<section>two</section>")

    assert assets.list_templates(OWNER_ID) == ["hero"]
    assert assets.load_template(OWNER_ID, "hero") == "<section>two</section>"
    assets.delete_template(OWNER_ID, "hero")
    assets.delete_template(OWNER_ID, "hero")
    assert assets.list_templates(OWNER_ID) == []


def test_templates_are_owner_scoped(assets: ReusableAssetService) -> None:
    assets.save_template(OWNER_ID, "private", "secret")

    assert assets.list_templates(OTHER_ID) == []
    with pytest.raises(ReusableAssetNotFoundError):
        assets.load_template(OTHER_ID, "private")
    assets.delete_template(OTHER_ID, "private")
    assert assets.load_template(OWNER_ID, "private") == "secret"


def test_layout_dna_names_are_unique_and_owner_scoped(
    assets: ReusableAssetService,
) -> None:
    dna = LayoutDNA(("header", "main", "footer"), script_statement_count=2)

    first = assets.save_dna(OWNER_ID, dna)
    second = assets.save_dna(OWNER_ID, dna)

    assert first["name"] == "header_main_footer"
    assert second["name"] == "header_main_footer-2"
    assert first["signature"] == "header/main/footer"
    assert "at most ~2 statements" in first["guidance"]
    assert len(assets.list_dnas(OWNER_ID)) == 2
    assert assets.list_dnas(OTHER_ID) == []


def test_duplicate_long_layout_dna_name_stays_within_storage_limit(
    assets: ReusableAssetService,
) -> None:
    dna = LayoutDNA(("section" * 20,))

    first = assets.save_dna(OWNER_ID, dna)
    second = assets.save_dna(OWNER_ID, dna)

    assert len(first["name"]) <= 80
    assert len(second["name"]) <= 80
    assert second["name"].endswith("-2")
