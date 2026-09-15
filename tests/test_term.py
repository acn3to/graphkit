from graphkit.term import safe

def test_safe_falls_back_to_ascii_on_a_narrow_encoding():
    assert safe("✓ ok — done…", encoding="cp1252") == "+ ok -- done..."

def test_safe_keeps_unicode_when_the_encoding_supports_it():
    assert safe("✓ ok", encoding="utf-8") == "✓ ok"

def test_safe_falls_back_on_an_unknown_encoding_name():
    assert safe("✗", encoding="not-a-real-codec") == "x"
