from src.sections import extract_first_top_level, extract_sections, replace_section

SAMPLE_HTML = """<header>
  <h1>Acme</h1>
</header>
<main>
  <p>Hello world</p>
</main>
<footer>Bye</footer>"""


def test_extract_sections_returns_top_level_sections() -> None:
    sections = extract_sections(SAMPLE_HTML)

    assert [s.tag for s in sections] == ["header", "main", "footer"]
    assert sections[0].index == 0
    assert sections[1].index == 1
    assert sections[2].index == 2


def test_extract_sections_html_is_exact_slice() -> None:
    sections = extract_sections(SAMPLE_HTML)

    for section in sections:
        assert section.html == SAMPLE_HTML[section.start : section.end]


def test_extract_sections_snippet_captures_text() -> None:
    sections = extract_sections(SAMPLE_HTML)

    assert "Acme" in sections[0].snippet
    assert "Hello world" in sections[1].snippet
    assert "Bye" in sections[2].snippet


def test_replace_section_splices_by_offsets() -> None:
    sections = extract_sections(SAMPLE_HTML)
    replacement = "<main><p>Updated</p></main>"

    updated = replace_section(SAMPLE_HTML, sections[1], replacement)

    assert "<p>Hello world</p>" not in updated
    assert "<p>Updated</p>" in updated
    assert "<header>" in updated and "<footer>" in updated


def test_replace_section_first_section() -> None:
    sections = extract_sections(SAMPLE_HTML)
    updated = replace_section(SAMPLE_HTML, sections[0], "<header>New</header>")
    assert updated.startswith("<header>New</header>")


def test_extract_sections_single_line_html() -> None:
    html = "<section>a</section><section>b</section>"
    sections = extract_sections(html)
    assert [s.tag for s in sections] == ["section", "section"]
    assert sections[0].html == "<section>a</section>"
    assert sections[1].html == "<section>b</section>"


def test_extract_sections_handles_self_closing_inside_section() -> None:
    html = "<main><img src='x'/>text</main><footer>f</footer>"
    sections = extract_sections(html)
    assert [s.tag for s in sections] == ["main", "footer"]
    assert sections[0].html == "<main><img src='x'/>text</main>"


def test_extract_first_top_level_skips_wrappers() -> None:
    html = "<html><body><section>one</section><footer>two</footer></body></html>"
    assert extract_first_top_level(html) == "<section>one</section>"


def test_extract_first_top_level_without_wrappers() -> None:
    assert extract_first_top_level("<section>one</section>") == "<section>one</section>"


def test_extract_first_top_level_empty() -> None:
    assert extract_first_top_level("") is None
    assert extract_first_top_level("just text") is None
