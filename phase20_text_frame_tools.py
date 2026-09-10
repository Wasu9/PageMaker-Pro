"""Phase 20 — real text-frame creation and mouse threading tools."""
from pagemaker_core import Rect
from phase18_text_frames import TextFrameController

MIN_SIZE=24.0

class TextFrameTools:
    def __init__(self,app):
        self.app=app
        self.start=None
        self.creating=False
        self.thread_source=None
        self.controller=TextFrameController(app.document)

    def begin_create(self,x,y):
        self.start=(float(x),float(y)); self.creating=True
        return self.start

    def finish_create(self,page,x,y,column=0,story=None):
        if not self.creating or self.start is None: return None
        x1,y1=self.start; x2,y2=float(x),float(y)
        left,right=sorted((x1,x2)); top,bottom=sorted((y1,y2))
        width=max(MIN_SIZE,right-left); height=max(MIN_SIZE,bottom-top)
        self.creating=False; self.start=None
        return self.app.document.add_text_frame(page,Rect(left,top,width,height),story=story,column=column)

    def cancel_create(self):
        self.creating=False; self.start=None

    def begin_thread(self,source_id):
        self.controller.select(source_id); self.thread_source=source_id
        return source_id

    def finish_thread(self,target_id):
        if not self.thread_source: return False
        source=self.thread_source
        self.thread_source=None
        return self.controller.thread(source,target_id)

    def cancel_thread(self): self.thread_source=None

    def delete_frame(self,frame_id):
        f=self.app.document.frames.get(frame_id)
        if not f or f.locked: return False
        prev,nxt=f.thread_prev,f.thread_next
        if prev in self.app.document.frames: self.app.document.frames[prev].thread_next=nxt
        if nxt in self.app.document.frames: self.app.document.frames[nxt].thread_prev=prev
        self.app.document.frames.pop(frame_id,None)
        for p in self.app.document.pages:
            p.frame_ids=[x for x in p.frame_ids if x!=frame_id]
            p.objects=[x for x in p.objects if x!=frame_id]
        for s in self.app.document.stories.values():
            s.frame_ids=[x for x in s.frame_ids if x!=frame_id]
        return True


def install(app):
    if getattr(app,"_pm20_installed",False): return
    app._pm20_installed=True
    if getattr(app,"document",None) is not None:
        app.pm20_tools=TextFrameTools(app)
