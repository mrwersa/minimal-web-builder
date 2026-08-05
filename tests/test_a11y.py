from src.a11y import audit_generated_html


def test_flags_img_without_alt() -> None:
    alerts = audit_generated_html('<img src="data:image/svg+xml;base64,AAA">')
    assert any("alt" in a for a in alerts)


def test_allows_img_with_alt() -> None:
    alerts = audit_generated_html(
        '<img src="data:image/svg+xml;base64,AAA" alt="Logo">'
    )
    assert alerts == []


def test_flags_multiple_h1() -> None:
    alerts = audit_generated_html("<h1>One</h1><p>x</p><h1>Two</h1>")
    assert any("single <h1>" in a for a in alerts)


def test_allows_single_h1() -> None:
    alerts = audit_generated_html("<h1>One</h1><h2>Two</h2>")
    assert alerts == []


def test_flags_unlabelled_form_control() -> None:
    alerts = audit_generated_html('<input type="text">')
    assert any("<input> control" in a for a in alerts)


def test_allows_aria_label_form_control() -> None:
    alerts = audit_generated_html('<input type="text" aria-label="Name">')
    assert alerts == []


def test_allows_wrapping_label() -> None:
    alerts = audit_generated_html("<label>Name <input type='text'></label>")
    assert alerts == []


def test_allows_label_for_reference() -> None:
    html = '<label for="email">Email</label><input type="email" id="email">'
    assert audit_generated_html(html) == []


def test_allows_label_for_after_control() -> None:
    html = '<input type="email" id="email"><label for="email">Email</label>'
    assert audit_generated_html(html) == []


def test_flags_positive_tabindex() -> None:
    alerts = audit_generated_html('<input tabindex="5">')
    assert any("tabindex > 0" in a for a in alerts)


def test_allows_neutral_or_negative_tabindex() -> None:
    assert audit_generated_html('<button tabindex="0">Ok</button>') == []
    assert audit_generated_html('<button tabindex="-1">Skip</button>') == []


def test_self_closing_img_is_checked() -> None:
    alerts = audit_generated_html("<img src='x'/>")
    assert any("alt" in a for a in alerts)
