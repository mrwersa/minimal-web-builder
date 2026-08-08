import pytest

from src.layout_dna import (
    LayoutDNA,
    combine_guidance,
    extract_layout_dna,
    from_dict,
    grammar_signature,
    suggest_dna_name,
    to_dict,
    to_guidance,
)

FULL_PAGE = """<!doctype html>
<html>
<head><title>Hi</title><script>var a = 1;</script></head>
<body>
<header>Top</header>
<main><section>Hero</section></main>
<footer>Bottom</footer>
<script>var b = 2; var c = 3;</script>
</body>
</html>
"""


def test_extract_layout_dna_skips_head_and_wrappers() -> None:
    dna = extract_layout_dna(FULL_PAGE)

    assert dna.section_tags == ("header", "main", "footer")


def test_extract_layout_dna_counts_inline_scripts_only() -> None:
    dna = extract_layout_dna(FULL_PAGE)

    assert dna.script_statement_count == 3


def test_extract_layout_dna_empty_html() -> None:
    dna = extract_layout_dna("<html></html>")

    assert dna.section_tags == ()
    assert dna.script_statement_count == 0


def test_section_count_property() -> None:
    assert LayoutDNA(("header", "main", "footer")).section_count == 3


def test_grammar_signature_joins_tags() -> None:
    dna = LayoutDNA(("header", "hero", "features"))

    assert grammar_signature(dna) == "header/hero/features"


def test_grammar_signature_empty() -> None:
    assert grammar_signature(LayoutDNA(())) == "empty"


def test_to_guidance_includes_grammar_and_js_note() -> None:
    guidance = to_guidance(LayoutDNA(("header", "footer"), script_statement_count=4))

    assert "header/footer" in guidance
    assert "at most ~4 statements" in guidance


def test_to_guidance_without_js_forbids_scripts() -> None:
    guidance = to_guidance(LayoutDNA(("header", "footer")))

    assert "Do not add any JavaScript." in guidance


def test_combine_guidance_skips_blank_parts() -> None:
    assert combine_guidance("a", "", "   ", "b") == "a\n\nb"
    assert combine_guidance("", "  ") == ""


def test_to_dict_from_dict_roundtrip() -> None:
    dna = LayoutDNA(("main", "footer"), script_statement_count=2)

    assert from_dict(to_dict(dna)) == dna


def test_suggest_dna_name_uses_normalized_grammar() -> None:
    dna = LayoutDNA(("header", "hero", "footer"), script_statement_count=2)

    assert suggest_dna_name(dna) == "header_hero_footer"
    assert suggest_dna_name(LayoutDNA(())) == "empty"


def test_from_dict_rejects_bad_data() -> None:
    with pytest.raises((TypeError, ValueError)):
        from_dict({"section_tags": 5})
