"""Headless regression tests for Phase 16."""
from phase16_paragraph_engine import ParagraphEngine, ParagraphStyle


def test_paragraph_slices_preserve_unicode():
    text="प्रश्न 1: H₂O + α\nउत्तर English"
    parts=ParagraphEngine().split(text)
    assert "".join(p[2] for p in parts)==text


def test_paragraph_style_geometry():
    style=ParagraphStyle(align="center",left_indent=12,right_indent=8,first_line_indent=6,space_after=4)
    result=ParagraphEngine(12).layout("Hindi English α β",300,200,style)
    assert result
    assert result[0][2].lines
    assert result[0][2].keep_with_next is False


def test_keep_widow_orphan_metadata():
    style=ParagraphStyle(keep_with_next=True,widow_lines=3,orphan_lines=3)
    pl=ParagraphEngine(12).layout("A short paragraph",300,200,style)[0][2]
    assert pl.keep_with_next is True
    assert pl.widow_lines==3
    assert pl.orphan_lines==3
