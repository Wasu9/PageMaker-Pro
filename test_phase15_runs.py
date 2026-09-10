"""Headless regression tests for Phase 15 mixed-run behavior."""
from phase14_unicode_shaping import UnicodeRunEngine


def test_unicode_runs_preserve_source():
    text="प्रश्न H₂O + α = β — English"
    runs=UnicodeRunEngine().runs(text)
    assert "".join(r.text for r in runs)==text
    assert any(r.script=="Devanagari" for r in runs)
    assert any(r.script=="Greek" for r in runs)


def test_combining_marks_stay_with_script_run():
    text="क्‍ष e\u0301"
    runs=UnicodeRunEngine().runs(text)
    assert "".join(r.text for r in runs)==text
