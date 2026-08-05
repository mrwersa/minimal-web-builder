from src.export import SplitDocument, split_document

SAMPLE = """<!DOCTYPE html>
<html>
<head>
  <style>h1 { color: #222; }</style>
</head>
<body>
  <h1>Hello</h1>
  <script>console.log('hi');</script>
</body>
</html>"""


def test_split_extracts_style_and_script() -> None:
    split = split_document(SAMPLE)

    assert "h1 { color: #222; }" in split.styles_css
    assert "console.log('hi');" in split.app_js
    assert 'href="styles.css"' in split.index_html
    assert 'src="app.js"' in split.index_html


def test_split_removes_inline_blocks_from_index() -> None:
    split = split_document(SAMPLE)

    assert "<style>" not in split.index_html
    assert "<script>console.log" not in split.index_html


def test_split_merges_multiple_blocks() -> None:
    html = (
        "<style>a{}</style><p>x</p><style>b{}</style>"
        "<script>one()</script><script>two()</script>"
    )
    split = split_document(html)

    assert "a{}" in split.styles_css and "b{}" in split.styles_css
    assert "one()" in split.app_js and "two()" in split.app_js
    assert split.index_html.count('href="styles.css"') == 1
    assert split.index_html.count('src="app.js"') == 1


def test_split_no_assets() -> None:
    split = split_document("<h1>bare</h1>")

    assert split.index_html == "<h1>bare</h1>"
    assert split.styles_css == ""
    assert split.app_js == ""


def test_split_keeps_external_script_src() -> None:
    html = '<script src="https://example.com/x.js"></script><p>hi</p>'
    split = split_document(html)

    assert "https://example.com/x.js" in split.index_html
    assert split.app_js == ""
    assert 'src="app.js"' not in split.index_html


def test_split_preserves_non_asset_content() -> None:
    html = "<main><p>keep me</p></main><style>h1{}</style>"
    split = split_document(html)

    assert "<p>keep me</p>" in split.index_html


def test_split_style_with_attributes() -> None:
    html = '<style type="text/css">h1 { color: red; }</style><p>x</p>'
    split = split_document(html)

    assert "h1 { color: red; }" in split.styles_css
    assert 'href="styles.css"' in split.index_html


def test_split_ignores_style_inside_script_data() -> None:
    html = "<script>var css = '<style>p{}</style>';</script><p>hi</p>"
    split = split_document(html)

    assert split.app_js == "var css = '<style>p{}</style>';"
    assert split.styles_css == ""


def test_split_empty_style_block_is_skipped() -> None:
    html = "<style>  </style><p>hi</p>"
    split = split_document(html)

    assert split.styles_css == ""
    assert 'href="styles.css"' not in split.index_html


def test_split_returns_dataclass() -> None:
    split = split_document(SAMPLE)
    assert isinstance(split, SplitDocument)
