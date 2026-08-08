"""Owner-scoped persistence for reusable templates and layout DNA."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from server.content import validate_document
from server.models import LayoutDNARecord, TemplateRecord, utcnow
from src.layout_dna import (
    MAX_DNA_NAME_CHARS,
    LayoutDNA,
    from_dict,
    grammar_signature,
    suggest_dna_name,
    to_dict,
    to_guidance,
)

MAX_TEMPLATE_NAME_CHARS = 64
_TEMPLATE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ReusableAssetNotFoundError(LookupError):
    pass


class ReusableAssetValidationError(ValueError):
    pass


def sanitize_template_name(name: str) -> str:
    cleaned = name.strip()
    if cleaned.lower().endswith(".html"):
        cleaned = cleaned[: -len(".html")].rstrip()
    if not cleaned:
        raise ReusableAssetValidationError("Template name cannot be empty.")
    if len(cleaned) > MAX_TEMPLATE_NAME_CHARS:
        raise ReusableAssetValidationError(
            f"Template name must be at most {MAX_TEMPLATE_NAME_CHARS} characters."
        )
    if cleaned in (".", "..") or not _TEMPLATE_NAME_RE.fullmatch(cleaned):
        raise ReusableAssetValidationError(
            "Template name may only contain letters, digits, dots, dashes, and underscores."
        )
    return cleaned


class ReusableAssetService:
    def __init__(self, sessions: sessionmaker[Session]):
        self._sessions = sessions

    def list_templates(self, owner_id: str) -> list[str]:
        with self._sessions() as session:
            return list(
                session.scalars(
                    select(TemplateRecord.name)
                    .where(TemplateRecord.owner_id == owner_id)
                    .order_by(TemplateRecord.name)
                )
            )

    def save_template(self, owner_id: str, name: str, html: str) -> str:
        clean_name = sanitize_template_name(name)
        clean_html = validate_document(html)
        try:
            with self._sessions.begin() as session:
                record = session.scalar(
                    select(TemplateRecord).where(
                        TemplateRecord.owner_id == owner_id,
                        TemplateRecord.name == clean_name,
                    )
                )
                if record is None:
                    session.add(
                        TemplateRecord(
                            owner_id=owner_id, name=clean_name, html=clean_html
                        )
                    )
                else:
                    record.html = clean_html
                    record.updated_at = utcnow()
        except IntegrityError:
            # A concurrent first save won the unique(owner, name) race; update it.
            with self._sessions.begin() as session:
                record = session.scalar(
                    select(TemplateRecord).where(
                        TemplateRecord.owner_id == owner_id,
                        TemplateRecord.name == clean_name,
                    )
                )
                if record is None:  # pragma: no cover - defensive database anomaly
                    raise
                record.html = clean_html
                record.updated_at = utcnow()
        return clean_name

    def load_template(self, owner_id: str, name: str) -> str:
        clean_name = sanitize_template_name(name)
        with self._sessions() as session:
            html = session.scalar(
                select(TemplateRecord.html).where(
                    TemplateRecord.owner_id == owner_id,
                    TemplateRecord.name == clean_name,
                )
            )
            if html is None:
                raise ReusableAssetNotFoundError("Template not found")
            return html

    def delete_template(self, owner_id: str, name: str) -> None:
        clean_name = sanitize_template_name(name)
        with self._sessions.begin() as session:
            session.execute(
                delete(TemplateRecord).where(
                    TemplateRecord.owner_id == owner_id,
                    TemplateRecord.name == clean_name,
                )
            )

    def list_dnas(self, owner_id: str) -> list[dict[str, Any]]:
        with self._sessions() as session:
            records = session.scalars(
                select(LayoutDNARecord)
                .where(LayoutDNARecord.owner_id == owner_id)
                .order_by(LayoutDNARecord.name)
            )
            return [self._dna_snapshot(record) for record in records]

    def save_dna(self, owner_id: str, dna: LayoutDNA) -> dict[str, Any]:
        stem = suggest_dna_name(dna)
        for _attempt in range(5):
            try:
                with self._sessions.begin() as session:
                    existing = set(
                        session.scalars(
                            select(LayoutDNARecord.name).where(
                                LayoutDNARecord.owner_id == owner_id
                            )
                        )
                    )
                    name = stem
                    counter = 2
                    while name in existing:
                        suffix = f"-{counter}"
                        name = (
                            f"{stem[: MAX_DNA_NAME_CHARS - len(suffix)].rstrip('_-')}"
                            f"{suffix}"
                        )
                        counter += 1
                    record = LayoutDNARecord(
                        owner_id=owner_id,
                        name=name,
                        definition=to_dict(dna),
                    )
                    session.add(record)
                    session.flush()
                    return self._dna_snapshot(record)
            except IntegrityError:
                continue
        raise RuntimeError("Could not allocate a unique Layout DNA name")

    @staticmethod
    def _dna_snapshot(record: LayoutDNARecord) -> dict[str, Any]:
        dna = from_dict(record.definition)
        return {
            "name": record.name,
            "signature": grammar_signature(dna),
            "guidance": to_guidance(dna),
        }
