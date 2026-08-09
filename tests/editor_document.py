def editor_document(node_id: str = "hero") -> dict:
    return {
        "schemaVersion": 1,
        "doctype": "<!DOCTYPE html>",
        "htmlAttributes": {"lang": "en"},
        "headHtml": '<meta charset="utf-8">',
        "bodyAttributes": {"class": "page"},
        "body": [
            {
                "type": "element",
                "id": node_id,
                "tag": "main",
                "attributes": {"class": "hero"},
                "children": [{"type": "text", "value": "Hello"}],
            }
        ],
        "css": ".hero { display: grid; }",
        "bodyScripts": ["<script>window.ready = true;</script>"],
        "responsiveStyles": {},
        "designTokens": {},
    }
