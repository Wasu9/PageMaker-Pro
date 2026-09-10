from pagemaker_core import Document, Rect
from phase18_text_frames import TextFrameController


def test_thread_and_unthread():
    d=Document(); p=d.add_page()
    a=d.add_text_frame(p,Rect(0,0,200,100),column=0)
    b=d.add_text_frame(p,Rect(210,0,200,100),column=1)
    c=TextFrameController(d)
    assert c.thread(a.id,b.id)
    assert a.thread_next==b.id and b.thread_prev==a.id
    assert c.thread_chain(a.id)==[a.id,b.id]
    c.unthread(b.id)
    assert a.thread_next is None and b.thread_prev is None


def test_thread_rejects_cycle():
    d=Document(); p=d.add_page()
    a=d.add_text_frame(p,Rect(0,0,100,100)); b=d.add_text_frame(p,Rect(110,0,100,100)); c=d.add_text_frame(p,Rect(220,0,100,100))
    x=TextFrameController(d); x.thread(a.id,b.id); x.thread(b.id,c.id)
    try: x.thread(c.id,a.id)
    except ValueError: pass
    else: raise AssertionError("cycle was accepted")
