from src.js_analysis import audit_inline_scripts, extract_inline_scripts


def test_extract_inline_scripts_returns_bodies() -> None:
    html = "<script>var a = 1;</script><script>var b = 2;</script>"

    scripts = extract_inline_scripts(html)

    assert scripts == ["var a = 1;", "var b = 2;"]


def test_extract_inline_scripts_skips_external() -> None:
    html = "<script src='https://x/app.js'></script><script>var a = 1;</script>"

    assert extract_inline_scripts(html) == ["var a = 1;"]


def test_audit_clean_simple_script_returns_no_alerts() -> None:
    html = "<script>const n = 5; console.log(n);</script>"

    assert audit_inline_scripts(html) == []


def test_audit_flags_empty_script() -> None:
    assert any("empty" in a for a in audit_inline_scripts("<script>  </script>"))


def test_audit_flags_eval() -> None:
    alerts = audit_inline_scripts("<script>eval(code);</script>")

    assert any("eval()" in a for a in alerts)


def test_audit_flags_new_function() -> None:
    alerts = audit_inline_scripts("<script>new Function('return 1')();</script>")

    assert any("new Function" in a for a in alerts)


def test_audit_flags_document_write() -> None:
    alerts = audit_inline_scripts("<script>document.write('x');</script>")

    assert any("document.write" in a for a in alerts)


def test_audit_does_not_flag_document_writeln() -> None:
    html = "<script>document.writeln('x');</script>"

    assert not any("document.write" in a for a in audit_inline_scripts(html))


def test_audit_flags_complex_script() -> None:
    code = "<script>" + ";".join(f"f({i});" for i in range(100)) + "</script>"
    alerts = audit_inline_scripts(code)

    assert any("statements" in a for a in alerts)


def test_audit_does_not_count_semicolons_inside_strings() -> None:
    code = "<script>const s = 'a;b;c'; console.log(s);</script>"

    assert not any("statements" in a for a in audit_inline_scripts(code))


def test_audit_ignores_json_ld_data_script() -> None:
    html = "<script type=\"application/ld+json\">{'@context': 'x'}</script>"

    assert audit_inline_scripts(html) == []


def test_audit_returns_empty_for_no_scripts() -> None:
    assert audit_inline_scripts("<main>hello</main>") == []
