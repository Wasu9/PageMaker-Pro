"""PageMaker Pro Phase 6 — object editing and manipulation layer.

Adds professional object selection, 8-point resize handles, snapping,
keyboard nudging, duplicate/delete, lock state, z-order, and a safe
Ctrl+drag text-frame creation gesture. The Unicode Tk text surface remains
editable; this layer only adds DTP manipulation around the canonical model.
"""
import tkinter as tk

import phase5_canvas as p5


def _app_install(app):
    if getattr(app, "_pm6_installed", False):
        return
    app._pm6_installed = True
    app._pm6_handles = []
    app._pm6_resize = None
    app._pm6_drag = None
    app._pm6_create = None

    def clear_handles():
        for h in getattr(app, "_pm6_handles", []):
            try: h.destroy()
            except Exception: pass
        app._pm6_handles = []

    def obj_for_widget(w):
        try:
            return p5._frame_for_widget(app, w)
        except Exception:
            return None

    def select_widget(w):
        obj = obj_for_widget(w)
        if not obj: return
        app._pm_selected_widget = w
        app._pm_selected_frame = obj.id
        app._pm_selected_object = obj.id
        app._pm5_selected = {obj.id}
        try:
            w.configure(highlightthickness=2, highlightbackground="#3973d4",
                        highlightcolor="#3973d4")
        except Exception: pass
        clear_handles()
        hs = max(6, min(10, int(9 * max(.25, float(app._zoom)))))
        positions = {
            "nw": (0,0), "n": (.5,0), "ne": (1,0),
            "w": (0,.5), "e": (1,.5),
            "sw": (0,1), "s": (.5,1), "se": (1,1)
        }
        for name, (rx, ry) in positions.items():
            h = tk.Frame(w, width=hs, height=hs, bg="#3973d4",
                         cursor="sizing")
            h.place(relx=rx, rely=ry, anchor="center")
            h.bind("<Button-1>", lambda e, n=name, ww=w: resize_start(e,n,ww))
            h.bind("<B1-Motion>", lambda e, n=name, ww=w: resize_move(e,n,ww))
            h.bind("<ButtonRelease-1>", lambda e: resize_end())
            app._pm6_handles.append(h)
        app.status.config(text=f"Selected Text Frame | {obj.rect.width:.0f} × {obj.rect.height:.0f}")

    def resize_start(event, handle, w):
        obj = obj_for_widget(w)
        if not obj or obj.locked: return
        app._pm6_resize = (handle, w, event.x, event.y,
                           w.winfo_x(), w.winfo_y(), w.winfo_width(), w.winfo_height())

    def resize_move(event, handle, w):
        state = getattr(app, "_pm6_resize", None)
        obj = obj_for_widget(w)
        if not state or not obj or obj.locked: return
        _, _, sx, sy, ox, oy, ow, oh = state
        dx, dy = event.x-sx, event.y-sy
        z = max(.25, float(app._zoom))
        left, top, right, bottom = ox, oy, ox+ow, oy+oh
        if "w" in handle: left = ox + dx
        if "e" in handle: right = ox + ow + dx
        if "n" in handle: top = oy + dy
        if "s" in handle: bottom = oy + oh + dy
        minw, minh = 60, 40
        if right-left < minw:
            if "w" in handle: left = right-minw
            else: right = left+minw
        if bottom-top < minh:
            if "n" in handle: top = bottom-minh
            else: bottom = top+minh
        # Shift keeps aspect ratio; Alt resizes from the center.
        if getattr(event, "state", 0) & 0x0001:
            nw, nh = right-left, bottom-top
            ratio = ow/max(1,oh)
            if abs(dx) >= abs(dy): nh = nw/max(.01,ratio)
            else: nw = nh*ratio
            if "w" in handle: left = right-nw
            else: right = left+nw
            if "n" in handle: top = bottom-nh
            else: bottom = top+nh
        if getattr(event, "state", 0) & 0x0008:
            cx, cy = ox+ow/2, oy+oh/2
            hw, hh = (right-left)/2, (bottom-top)/2
            left, right, top, bottom = cx-hw, cx+hw, cy-hh, cy+hh
        app.document.move_frame(obj.id, left/z, top/z)
        app.document.resize_frame(obj.id, (right-left)/z, (bottom-top)/z)
        w.place(x=int(left), y=int(top), width=int(right-left), height=int(bottom-top))
        select_widget(w)
        app.dirty = True

    def resize_end():
        app._pm6_resize = None

    def bind_widget(w):
        if getattr(w, "_pm6_bound", False): return
        w._pm6_bound = True
        w.bind("<Button-1>", lambda e, ww=w: select_widget(ww), add="+")
        w.bind("<Alt-Button-1>", lambda e, ww=w: start_move(e,ww), add="+")
        w.bind("<Alt-B1-Motion>", lambda e, ww=w: move_widget(e,ww), add="+")
        w.bind("<Alt-ButtonRelease-1>", lambda e: end_move(), add="+")

    def start_move(event,w):
        obj = obj_for_widget(w)
        if not obj or obj.locked: return
        select_widget(w)
        app._pm6_drag = (w,event.x,event.y,w.winfo_x(),w.winfo_y())

    def move_widget(event,w):
        state = getattr(app,"_pm6_drag",None)
        obj = obj_for_widget(w)
        if not state or not obj: return
        _,sx,sy,ox,oy = state
        z=max(.25,float(app._zoom))
        nx,ny=ox+event.x-sx,oy+event.y-sy
        if not (event.state & 0x0004):
            nx,ny=p5._snap(nx/z),p5._snap(ny/z)
            nx,ny=nx*z,ny*z
        w.place(x=int(nx),y=int(ny))
        app.document.move_frame(obj.id,nx/z,ny/z)
        p5.refresh_all(app)
        select_widget(w)
        app.dirty=True

    def end_move(): app._pm6_drag=None

    def key(event):
        oid=getattr(app,"_pm_selected_object",None)
        if not oid: return
        obj=p5._object_for_id(app,oid)
        if not obj or obj.locked: return
        step=10 if event.state & 0x0001 else 1
        dx,dy=0,0
        if event.keysym=="Left": dx=-step
        elif event.keysym=="Right": dx=step
        elif event.keysym=="Up": dy=-step
        elif event.keysym=="Down": dy=step
        elif event.keysym in ("Delete","BackSpace"):
            for pg in app.document.pages:
                if oid in pg.objects:
                    pg.objects.remove(oid); pg.frame_ids=[x for x in pg.frame_ids if x!=oid]
            app.document.frames.pop(oid,None); app._pm5_selected=set(); app._pm_selected_object=None
            p5.refresh_all(app); app.dirty=True; return "break"
        elif event.keysym=="d" and event.state & 0x0004:
            if oid in app.document.frames:
                src=app.document.frames[oid]
                for pg in app.document.pages:
                    if oid in pg.objects:
                        dup=app.document.add_text_frame(pg,p5.Rect(src.rect.x+12,src.rect.y+12,src.rect.width,src.rect.height),None,src.column)
                        dup.text=src.text; app._pm_selected_object=dup.id; app._pm5_selected={dup.id}; p5.refresh_all(app); app.dirty=True; return "break"
        elif event.keysym=="l" and event.state & 0x0004:
            obj.locked=not obj.locked; app.status.config(text=("Locked" if obj.locked else "Unlocked")+f" | {oid}"); return "break"
        else: return
        if dx or dy:
            if oid in app.document.frames: app.document.move_frame(oid,obj.rect.x+dx,obj.rect.y+dy)
            else: app.document.move_image(oid,obj.rect.x+dx,obj.rect.y+dy)
            p5.refresh_all(app); app.dirty=True; return "break"

    def late():
        for pg in getattr(app,"pages",[]):
            for w in getattr(pg,"texts",[]): bind_widget(w)
            p5._draw_page(app,pg)
        app.root.bind_all("<KeyPress>",key,add="+")

    original_changed=getattr(app,"changed",None)
    if original_changed:
        def changed(widget=None,_orig=original_changed):
            result=_orig(widget)
            app.root.after(120,late)
            return result
        app.changed=changed
    late()


def install(app):
    try: _app_install(app)
    except Exception: pass


# Phase 5 installs itself late; wrap its installer so Phase 6 is attached too.
_old_install = getattr(p5, "_install_app", None)
if _old_install and not getattr(_old_install, "_pm6_wrapped", False):
    def _install_with_phase6(app):
        _old_install(app)
        install(app)
    _install_with_phase6._pm6_wrapped=True
    p5._install_app=_install_with_phase6
