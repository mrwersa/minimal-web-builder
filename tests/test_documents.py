from __future__ import annotations

import pytest

from server.documents import EditorDocumentValidationError, validate_editor_document
from tests.editor_document import editor_document


def test_accepts_versioned_editor_document() -> None:
    document = editor_document()

    assert validate_editor_document(document) is document


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value.update(schemaVersion=2), "Unsupported"),
        (lambda value: value.update(schemaVersion=True), "Unsupported"),
        (lambda value: value["body"][0].update(id="bad id"), "ID is invalid"),
        (lambda value: value["body"][0].update(tag="<script>"), "tag is invalid"),
        (
            lambda value: value["body"].append(value["body"][0].copy()),
            "IDs must be unique",
        ),
    ],
)
def test_rejects_invalid_editor_documents(mutate, message: str) -> None:
    document = editor_document()
    mutate(document)

    with pytest.raises(EditorDocumentValidationError, match=message):
        validate_editor_document(document)


def test_validates_responsive_style_references() -> None:
    document = editor_document()
    document["responsiveStyles"] = {
        "hero": {"mobile": {"display": "none", "padding": "12px"}}
    }
    assert validate_editor_document(document) is document

    document["responsiveStyles"] = {"missing": {"watch": {"display": "none"}}}
    with pytest.raises(EditorDocumentValidationError, match="existing element"):
        validate_editor_document(document)
