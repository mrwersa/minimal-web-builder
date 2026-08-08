"""Shared validation rules for persisted and generated page documents."""

MAX_DOCUMENT_CHARS = 2_000_000


class DocumentValidationError(ValueError):
    pass


def validate_document(html: str) -> str:
    if len(html) > MAX_DOCUMENT_CHARS:
        raise DocumentValidationError(
            f"Document must be at most {MAX_DOCUMENT_CHARS} characters"
        )
    return html
