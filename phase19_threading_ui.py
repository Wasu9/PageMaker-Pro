"""Phase 19 — visual text-frame threading and overflow indicators.

The module is intentionally defensive: it works as a Canvas overlay when the
host exposes page canvases, and remains a no-op for non-GUI/headless imports.
"""
import tkinter as tk


def _frames(app):
    doc=getattr(app,"document",None)
    return getattr(doc,"frames",{}) if doc else {}


def _page_for(app, fid):
    for pi,p in enumerate(getattr(app.document,"pages",[])):
        if fid in getattr(p,"frame_ids",[]): return pi,p
    return -1,None


def draw_thread_overlay(app):
    canvas=getattr(app,"canvas",None) or getattr(app,"page_canvas",None)
    if canvas is None or not hasattr(canvas,"create_line"): return
    for tag in ("pm19-thread","pm19-overflow"):
        canvas.delete(tag)
    frames=_frames(app)
    for fid,f in frames.items():
        if getattr(f,"thread_next",None) not in frames: continue
        n=frames[f.thread_next]
        x1=f.rect.x+f.rect.width; y1=f.rect.y+f.rect.height/2
        x2=n.rect.x; y2=n.rect.y+n.rect.height/2
        canvas.create_line(x1,y1,x2,y2,fill="#4477aa",width=1,arrow=tk.LAST,tags="pm19-thread")
    # Overflow is represented by a small red triangle at the lower-right edge.
    for fid,f in frames.items():
        if not getattr(f,"overflow",False): continue
        x=f.rect.x+f.rect.width; y=f.rect.y+f.rect.height
        canvas.create_polygon(x-12,y,x,y,x,y-12,fill="#cc3333",outline="",tags="pm19-overflow")


def frame_ports(frame):
    return {
        "in":(frame.rect.x,frame.rect.y+frame.rect.height/2),
        "out":(frame.rect.x+frame.rect.width,frame.rect.y+frame.rect.height/2),
    }


def connect(app, source_id, target_id):
    controller=getattr(app,"pm18_frames",None)
    if controller is None: return False
    ok=controller.thread(source_id,target_id)
    draw_thread_overlay(app)
    return ok


def disconnect(app, frame_id):
    controller=getattr(app,"pm18_frames",None)
    if controller is None: return None
    result=controller.unthread(frame_id)
    draw_thread_overlay(app)
    return result


def install(app):
    if getattr(app,"_pm19_installed",False): return
    app._pm19_installed=True
    if getattr(app,"document",None) is not None:
        app.pm19_draw_threads=lambda: draw_thread_overlay(app)
        app.pm19_connect=lambda a,b: connect(app,a,b)
        app.pm19_disconnect=lambda a: disconnect(app,a)
