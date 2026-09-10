from pagemaker_core import Document, Rect
from phase20_text_frame_tools import TextFrameTools

class A:
    def __init__(self): self.document=Document()


def test_create_frame_from_drag():
    a=A(); p=a.document.add_page(); t=TextFrameTools(a)
    t.begin_create(300,200)
    f=t.finish_create(p,100,80,column=1)
    assert f.rect.x==100 and f.rect.y==80
    assert f.rect.width==200 and f.rect.height==120
    assert f.column==1


def test_threading_and_delete_reconnects_chain():
    a=A(); p=a.document.add_page(); t=TextFrameTools(a)
    x=a.document.add_text_frame(p,Rect(0,0,100,100)); y=a.document.add_text_frame(p,Rect(120,0,100,100)); z=a.document.add_text_frame(p,Rect(240,0,100,100))
    t.begin_thread(x.id); assert t.finish_thread(y.id)
    t.begin_thread(y.id); assert t.finish_thread(z.id)
    assert t.delete_frame(y.id)
    assert x.thread_next==z.id and z.thread_prev==x.id
