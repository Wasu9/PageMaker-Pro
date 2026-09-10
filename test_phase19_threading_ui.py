from pagemaker_core import Document
from phase18_text_frames import TextFrameController
from phase19_threading_ui import frame_ports


def test_frame_ports():
    d=Document(); p=d.add_page(); f=d.add_text_frame(p,(10,20,100,80))
    ports=frame_ports(f)
    assert ports["in"]==(10,60)
    assert ports["out"]==(110,60)


def test_controller_connection():
    d=Document(); p=d.add_page(); a=d.add_text_frame(p,(0,0,100,100)); b=d.add_text_frame(p,(120,0,100,100))
    c=TextFrameController(d); assert c.thread(a.id,b.id)
    assert c.thread_chain(a.id)==[a.id,b.id]
