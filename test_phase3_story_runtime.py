from pagemaker_core import Document, Rect
from story_runtime import StoryRuntime


def make_runtime():
    doc = Document()
    page = doc.add_page()
    a = doc.add_text_frame(page, Rect(0, 0, 200, 80), column=0)
    b = doc.add_text_frame(page, Rect(220, 0, 200, 80), column=1)
    story = doc.add_story("")
    rt = StoryRuntime(doc)
    rt.active_story_id = story.id
    return doc, rt, story, a, b


def test_live_edit_uses_story_as_source():
    doc, rt, story, a, b = make_runtime()
    rt.thread_frames(story, [a.id, b.id])
    story, result, remaining = rt.live_edit("A" * 200, frame_ids=[a.id, b.id])
    assert story.text == "A" * 200
    assert a.text
    assert b.text
    assert remaining == ""


def test_manual_thread_survives_reflow():
    doc, rt, story, a, b = make_runtime()
    rt.thread_frames(story, [b.id, a.id])
    rt.reflow(story, frame_ids=[b.id, a.id])
    assert story.frame_ids == [b.id, a.id]


def test_unthread_after_selected_frame():
    doc, rt, story, a, b = make_runtime()
    rt.thread_frames(story, [a.id, b.id])
    rt.unthread_after(story, a.id)
    assert story.frame_ids == [a.id]
