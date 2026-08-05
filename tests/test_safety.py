from src.safety import apply_output_safety_policy


def test_removes_disallowed_container_tags() -> None:
    raw = "<div>ok</div><iframe src='x'></iframe><object data='y'></object>"
    sanitized, alerts = apply_output_safety_policy(raw)

    assert "<iframe" not in sanitized.lower()
    assert "<object" not in sanitized.lower()
    assert alerts


def test_removes_external_script_tag() -> None:
    raw = "<script src='https://evil.example/app.js'></script><p>safe</p>"
    sanitized, alerts = apply_output_safety_policy(raw)

    assert "script src" not in sanitized.lower()
    assert "safe" in sanitized
    assert any("external script" in a.lower() for a in alerts)


def test_removes_inline_event_handlers() -> None:
    raw = "<button onclick=\"alert(1)\" onmouseover='x()'>Click</button>"
    sanitized, alerts = apply_output_safety_policy(raw)

    assert "onclick" not in sanitized.lower()
    assert "onmouseover" not in sanitized.lower()
    assert any("event handler" in a.lower() for a in alerts)


def test_neutralizes_dangerous_url_attributes() -> None:
    raw = "<a href=\"javascript:alert(1)\">x</a><img src='data:text/html;base64,AAAA'/>"
    sanitized, alerts = apply_output_safety_policy(raw)

    assert "javascript:" not in sanitized.lower()
    assert "data:text/html" not in sanitized.lower()
    assert 'href="#"' in sanitized or "href='#'" in sanitized
    assert any("neutralized" in a.lower() for a in alerts)


def test_removes_empty_inline_script_but_keeps_real_one() -> None:
    raw = (
        "<script>  </script><script>var a = 1;</script>"
        '<script type="application/ld+json">{"@context": "x"}</script>'
    )
    sanitized, alerts = apply_output_safety_policy(raw)

    assert "<script>  </script>" not in sanitized
    assert "var a = 1;" in sanitized
    assert "application/ld+json" in sanitized
    assert any("empty script" in a.lower() for a in alerts)


def test_keeps_safe_html_unchanged() -> None:
    raw = "<section><h1>Hello</h1><p>World</p></section>"
    sanitized, alerts = apply_output_safety_policy(raw)

    assert sanitized == raw
    assert alerts == []
