from __future__ import annotations

import re
from typing import List, Tuple


DANGEROUS_CONTAINER_TAGS = ("iframe", "frame", "frameset", "object", "embed")
URL_ATTRS = ("href", "src", "action", "formaction", "xlink:href")


def _remove_dangerous_container_tags(html: str) -> Tuple[str, bool]:
    updated = html
    changed = False
    for tag in DANGEROUS_CONTAINER_TAGS:
        block_pattern = re.compile(rf"<{tag}\b[^>]*>.*?</{tag}\s*>", re.IGNORECASE | re.DOTALL)
        single_pattern = re.compile(rf"<{tag}\b[^>]*?/?>", re.IGNORECASE | re.DOTALL)

        updated_next, n1 = block_pattern.subn("", updated)
        updated_next, n2 = single_pattern.subn("", updated_next)
        updated = updated_next
        changed = changed or (n1 + n2 > 0)
    return updated, changed


def _remove_external_script_tags(html: str) -> Tuple[str, bool]:
    script_src_pattern = re.compile(
        r"<script\b(?=[^>]*\bsrc\s*=)[^>]*>.*?</script\s*>",
        re.IGNORECASE | re.DOTALL,
    )
    updated, count = script_src_pattern.subn("", html)
    return updated, count > 0


def _remove_event_handler_attributes(html: str) -> Tuple[str, bool]:
    event_attr_pattern = re.compile(
        r"\s+on[a-zA-Z0-9_:-]+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)",
        re.IGNORECASE,
    )
    updated, count = event_attr_pattern.subn("", html)
    return updated, count > 0


def _neutralize_dangerous_url_attributes(html: str) -> Tuple[str, bool]:
    updated = html
    changed = False
    for attr in URL_ATTRS:
        quoted_pattern = re.compile(
            rf"({attr}\s*=\s*)([\"'])\s*(javascript:|data:text/html)[^\"']*\2",
            re.IGNORECASE,
        )
        unquoted_pattern = re.compile(
            rf"({attr}\s*=\s*)(javascript:|data:text/html)[^\s>]*",
            re.IGNORECASE,
        )

        updated_next, n1 = quoted_pattern.subn(r"\1\2#\2", updated)
        updated_next, n2 = unquoted_pattern.subn(r"\1#", updated_next)
        updated = updated_next
        changed = changed or (n1 + n2 > 0)
    return updated, changed


def apply_output_safety_policy(generated_html: str) -> Tuple[str, List[str]]:
    sanitized = generated_html
    alerts: List[str] = []

    sanitized, removed_containers = _remove_dangerous_container_tags(sanitized)
    if removed_containers:
        alerts.append("Removed disallowed container tags (iframe/frame/object/embed).")

    sanitized, removed_external_scripts = _remove_external_script_tags(sanitized)
    if removed_external_scripts:
        alerts.append("Removed external script tags (script src=...).")

    sanitized, removed_events = _remove_event_handler_attributes(sanitized)
    if removed_events:
        alerts.append("Removed inline event handler attributes (on*).")

    sanitized, neutralized_urls = _neutralize_dangerous_url_attributes(sanitized)
    if neutralized_urls:
        alerts.append("Neutralized dangerous javascript:/data:text/html URL attributes.")

    return sanitized, alerts
