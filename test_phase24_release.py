from pathlib import Path
from tempfile import TemporaryDirectory

from pagemaker_core import Document, Rect
from phase23_document_system import save_document, load_document
from phase24_release_qa import check_document


def test_pmp_roundtrip_unicode_and_threads():
    d = Document(); p = d.add_page()
    a = d.add_text_frame(p, Rect(45, 48, 300, 300), column=0)
    b = d.add_text_frame(p, Rect(369, 48, 300, 300), column=1)
    s = d.add_story('प्रश्न 1: H₂O + α ≤ β — English')
    a.story_id = b.story_id = s.id
    s.frame_ids = [a.id, b.id]
    a.thread_next = b.id; b.thread_prev = a.id
    a.text = s.text[:12]; b.text = s.text[12:]
    with TemporaryDirectory() as td:
        path = save_document(d, Path(td) / 'paper')
        loaded = load_document(path)
    assert loaded.stories[s.id].text == s.text
    assert loaded.frames[a.id].thread_next == b.id
    assert loaded.frames[b.id].thread_prev == a.id
    assert ''.join(loaded.frames[x].text for x in s.frame_ids) == s.text


def test_release_document_checks():
    d = Document(); p = d.add_page(); d.add_text_frame(p, Rect(0, 0, 100, 100))
    assert check_document(d) == []
