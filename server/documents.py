"""Validation boundary for the versioned visual-editor document format."""

from __future__ import annotations

import json
import re
from typing import Any

MAX_EDITOR_DOCUMENT_CHARS = 4_000_000
MAX_EDITOR_DOCUMENT_NODES = 50_000
MAX_EDITOR_DOCUMENT_DEPTH = 100
_NODE_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
_TAG_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9:-]{0,79}$")


class EditorDocumentValidationError(ValueError):
    pass


def _string_map(value: Any, label: str) -> None:
    if not isinstance(value, dict) or any(
        not isinstance(key, str) or not isinstance(item, str)
        for key, item in value.items()
    ):
        raise EditorDocumentValidationError(f"{label} must contain string values")


def validate_editor_document(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    if (
        not isinstance(value, dict)
        or type(value.get("schemaVersion")) is not int
        or value.get("schemaVersion") != 1
    ):
        raise EditorDocumentValidationError("Unsupported editor document schema")
    try:
        encoded = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise EditorDocumentValidationError(
            "Editor document must be valid JSON"
        ) from exc
    if len(encoded) > MAX_EDITOR_DOCUMENT_CHARS:
        raise EditorDocumentValidationError(
            f"Editor document must be at most {MAX_EDITOR_DOCUMENT_CHARS} characters"
        )

    for field in ("doctype", "headHtml", "css"):
        if not isinstance(value.get(field), str):
            raise EditorDocumentValidationError(f"{field} must be a string")
    _string_map(value.get("htmlAttributes"), "htmlAttributes")
    _string_map(value.get("bodyAttributes"), "bodyAttributes")
    scripts = value.get("bodyScripts")
    if not isinstance(scripts, list) or any(
        not isinstance(script, str) for script in scripts
    ):
        raise EditorDocumentValidationError("bodyScripts must be a list of strings")
    body = value.get("body")
    if not isinstance(body, list):
        raise EditorDocumentValidationError("body must be a list")

    used_ids: set[str] = set()
    node_count = 0
    pending = [(node, 1) for node in reversed(body)]
    while pending:
        node, depth = pending.pop()
        node_count += 1
        if node_count > MAX_EDITOR_DOCUMENT_NODES:
            raise EditorDocumentValidationError("Editor document has too many nodes")
        if depth > MAX_EDITOR_DOCUMENT_DEPTH:
            raise EditorDocumentValidationError("Editor document is nested too deeply")
        if not isinstance(node, dict):
            raise EditorDocumentValidationError("Document nodes must be objects")
        node_type = node.get("type")
        if node_type in {"text", "comment"}:
            if not isinstance(node.get("value"), str):
                raise EditorDocumentValidationError(
                    f"{node_type} node value must be a string"
                )
            continue
        if node_type != "element":
            raise EditorDocumentValidationError("Unsupported document node type")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not _NODE_ID.fullmatch(node_id):
            raise EditorDocumentValidationError("Element node ID is invalid")
        if node_id in used_ids:
            raise EditorDocumentValidationError("Element node IDs must be unique")
        used_ids.add(node_id)
        tag = node.get("tag")
        if not isinstance(tag, str) or not _TAG_NAME.fullmatch(tag):
            raise EditorDocumentValidationError("Element tag is invalid")
        _string_map(node.get("attributes"), "Element attributes")
        children = node.get("children")
        if not isinstance(children, list):
            raise EditorDocumentValidationError("Element children must be a list")
        pending.extend((child, depth + 1) for child in reversed(children))
    return value
