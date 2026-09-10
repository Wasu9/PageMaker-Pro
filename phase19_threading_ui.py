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


def _rect_values(rect):
    """Return x, y, width, height for Rect objects and tuple/list rectangles."""
    if hasattr(rect, "x"):
        return rect.x, rect.y, rect.width, rect.height
    if isinstance(rect, (tuple, list)) and len(rect) == 4:
        return rect[0], rect[1], rect[2], rect[3]
    raise TypeError("frame.rect must be a Rect-like object or (x, y, width, height)")


def draw_thread_overlay(app):
    canvas=getattr(app,"canvas",None) or getattr(app,"page_canvas",None)
    if canvas is None or not hasattr(canvas,"create_line"): return
    for tag in ("pm19-thread","pm19-overflow"):
        canvas.delete(tag)
    frames=_frames(app)
    for fid,f in frames.items():
        if getattr(f,"thread_next",None) not in frames: continue
        n=frames[f.thread_next]
        x,y,w,h=_rect_values(f.rect)
        nx,ny,nw,nh=_rect_values(n.rect)
        x1=x+w; y1=y+h/2
        x2=nx; y2=ny+nh/2
        canvas.create_line(x1,y1,x2,y2,fill="#4477aa",width=1,arrow=tk.LAST,tags="pm19-thread")
    # Overflow is represented by a small red triangle at the lower-right edge.
    for fid,f in frames.items():
        if not getattr(f,"overflow",False): continue
        x,y,w,h=_rect_values(f.rect)
        px=x+w; py=y+h
        canvas.create_polygon(px-12,py,px,py,px,py-12,fill="#cc3333",outline="",tags="pm19-overflow")


def frame_ports(frame):
    x,y,w,h=_rect_values(frame.rect)
    return {
        "in":(x,y+h/2),
        "out":(x+w,y+h/2),
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
