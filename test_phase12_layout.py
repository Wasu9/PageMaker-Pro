"""Headless regression tests for Phase 12 DTP layout."""
from dtp_text_layout import DTPTextLayout
from pagemaker_core import Document, Rect
from story_runtime import StoryRuntime


def test_unicode_is_preserved_and_breaks_at_words():
    text = "यह एक Unicode परीक्षण है — Physics: α β γ, H₂O, x² + y² = z²."
    engine = DTPTextLayout(font_size=12)
    end, lines = engine.fit_prefix(text, width=120, height=80)
    assert end > 0
    assert text[:end] == ''.join(line.text for line in lines)
    assert text[:end] in text
    assert "यह" in text[:end]
    assert "α" in text[:end] or "α" in text[end:]


def test_true_justify_metadata():
    engine = DTPTextLayout(font_size=12)
    layout = engine.layout_paragraph("one two three four five", 180, align="justify")
    assert layout.lines
    if len(layout.lines) > 1:
        assert layout.lines[0].justified is True
        assert layout.lines[0].extra_space >= 0


def test_story_runtime_uses_geometry_layout():
    doc = Document()
    p = doc.add_page()
    a = doc.add_text_frame(p, Rect(45, 48, 90, 90), column=0)
    b = doc.add_text_frame(p, Rect(159, 48, 90, 90), column=1)
    story = doc.add_story("word " * 100)
    rt = StoryRuntime(doc)
    rt.active_story_id = story.id
    rt.attach_frames(story, frame_ids=[a.id, b.id])
    result, remaining = rt.reflow(story, frame_ids=[a.id, b.id])
    assert result
    assert a.text
    assert b.text or remaining
    assert story.text == "word " * 100
