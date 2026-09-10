"""Phase 18 — professional text-frame/threading interaction layer.

Provides a UI-neutral controller for selecting frames, creating explicit
threads, breaking threads, and reporting overflow.  It keeps the canonical
Document/Story model authoritative and is safe to use from the Tk adapter.
"""
from dataclasses import dataclass


@dataclass
class FrameStatus:
    frame_id: str
    page_index: int
    column_index: int
    overflow: bool = False
    threaded_to: str | None = None
    threaded_from: str | None = None


class TextFrameController:
    def __init__(self, document):
        self.document=document
        self.selected=None

    def frames(self):
        return list(self.document.frames.values())

    def select(self, frame_id):
        if frame_id not in self.document.frames:
            raise KeyError(frame_id)
        self.selected=frame_id
        return self.document.frames[frame_id]

    def thread(self, source_id, target_id):
        if source_id==target_id: raise ValueError("A frame cannot thread to itself")
        source=self.document.frames[source_id]; target=self.document.frames[target_id]
        # Prevent a cycle before changing either endpoint.
        seen={source_id}; cur=target
        while cur.thread_next:
            if cur.thread_next in seen: raise ValueError("Thread cycle detected")
            seen.add(cur.thread_next); cur=self.document.frames[cur.thread_next]
        if target.thread_prev and target.thread_prev!=source_id:
            raise ValueError("Target frame is already threaded from another frame")
        if source.thread_next and source.thread_next!=target_id:
            raise ValueError("Source frame is already threaded to another frame")
        source.thread_next=target_id
        target.thread_prev=source_id
        return True

    def unthread(self, frame_id):
        frame=self.document.frames[frame_id]
        prev_id, next_id=frame.thread_prev, frame.thread_next
        if prev_id and prev_id in self.document.frames:
            self.document.frames[prev_id].thread_next=next_id
        if next_id and next_id in self.document.frames:
            self.document.frames[next_id].thread_prev=prev_id
        frame.thread_prev=None; frame.thread_next=None
        return prev_id,next_id

    def status(self, frame_id, overflow=False):
        f=self.document.frames[frame_id]
        page_index=next((i for i,p in enumerate(self.document.pages) if f.id in p.frame_ids),-1)
        column_index=next((i for i,x in enumerate(self.document.pages[page_index].frame_ids) if x==f.id),-1) if page_index>=0 else -1
        return FrameStatus(f.id,page_index,column_index,bool(overflow),f.thread_next,f.thread_prev)

    def thread_chain(self, start_id):
        out=[]; seen=set(); cur=start_id
        while cur:
            if cur in seen: raise ValueError("Thread cycle detected")
            seen.add(cur); out.append(cur)
            cur=self.document.frames[cur].thread_next
        return out


def install(app):
    if getattr(app,"_pm18_installed",False): return
    app._pm18_installed=True
    if getattr(app,"document",None) is not None:
        app.pm18_frames=TextFrameController(app.document)
