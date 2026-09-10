"""PageMaker Pro Phase 5 — DTP object/pasteboard canvas layer.

This layer adds a real page-level Canvas renderer underneath the editable Tk
Text widgets. The canonical Document/Story model remains authoritative.
It provides object outlines, selection, snapping, guides, z-order helpers and
page/pasteboard rendering without replacing the Unicode editor surface.
"""
import tkinter as tk

from pagemaker_core import Rect


def _find_app(root):
    for w in root.winfo_children():
        try:
            if hasattr(w, "pages") and hasattr(w, "settings") and hasattr(w, "canvas"):
                return w
        except Exception:
            pass
        found = _find_app(w)
        if found:
            return found
    return None


def _page_canvas(page):
    return getattr(page, "_pm5_canvas", None)


def _zoom(app):
    try:
        return max(.25, float(app._zoom))
    except Exception:
        return .72


def _doc_page(app, page):
    doc = getattr(app, "document", None)
    if not doc:
        return None
    try:
        return doc.pages[app.pages.index(page)]
    except Exception:
        return None


def _object_for_id(app, oid):
    doc = getattr(app, "document", None)
    if not doc:
        return None
    return doc.frames.get(oid) or doc.images.get(oid)


def _object_ids(app, page):
    p = _doc_page(app, page)
    return list(getattr(p, "objects", [])) if p else []


def _snap(value, grid=5.0):
    return round(float(value) / grid) * grid


def _draw_page(app, page):
    c = _page_canvas(page)
    p = _doc_page(app, page)
    if c is None or p is None:
        return
    z = _zoom(app)
    c.delete("pm5")
    pw, ph = p.width * z, p.height * z
    c.configure(width=max(1, int(pw)), height=max(1, int(ph)))

    # Page boundary and pasteboard-facing inner guides.
    c.create_rectangle(0, 0, pw, ph, outline="", tags="pm5")
    if getattr(app, "settings", {}).get("border", True):
        c.create_rectangle(0, 0, pw - 1, ph - 1, outline="#8a8d91", tags="pm5")

    margin = float(p.margin) * z
    c.create_rectangle(margin, margin, pw - margin, ph - margin,
                       outline="#b7bcc3", dash=(3, 4), tags="pm5")
    n = max(1, int(p.columns))
    gap = float(p.column_gap) * z
    total = p.width - 2 * p.margin
    cw = max(1, (total - gap * (n - 1)) / n)
    top, bottom = 48 * z, (p.height - 52) * z
    for i in range(n):
        x = (p.margin + i * (cw + p.column_gap)) * z
        c.create_rectangle(x, top, x + cw * z, bottom,
                           outline="#d5d9df", dash=(2, 5), tags="pm5")

    for oid in _object_ids(app, page):
        obj = _object_for_id(app, oid)
        if obj is None or not getattr(obj, "visible", True):
            continue
        r = obj.rect
        x1, y1 = r.x * z, r.y * z
        x2, y2 = (r.x + r.width) * z, (r.y + r.height) * z
        if oid in getattr(app, "_pm5_selected", set()):
            outline = "#3973d4"
            dash = None
        else:
            outline = "#aeb4bd"
            dash = (3, 3)
        c.create_rectangle(x1, y1, x2, y2, outline=outline,
                           width=2 if oid in getattr(app, "_pm5_selected", set()) else 1,
                           dash=dash, tags=("pm5", "obj", oid))
        if oid in getattr(app, "document", None).images if getattr(app, "document", None) else False:
            c.create_text(x1 + 5, y1 + 5, anchor="nw", text="IMAGE",
                          fill="#737982", tags=("pm5", oid))

    # Selection handles are deliberately drawn on the Canvas, not as child
    # widgets, so they remain stable while the editor is rebuilt.
    for oid in getattr(app, "_pm5_selected", set()):
        obj = _object_for_id(app, oid)
        if not obj:
            continue
        r = obj.rect
        x1, y1, x2, y2 = r.x*z, r.y*z, (r.x+r.width)*z, (r.y+r.height)*z
        hs = max(5, min(9, int(8*z)))
        for x, y in ((x1,y1),(x2,y1),(x1,y2),(x2,y2)):
            c.create_rectangle(x-hs/2, y-hs/2, x+hs/2, y+hs/2,
                               fill="#3973d4", outline="#ffffff",
                               tags=("pm5", "handle", oid))


def _select(app, page, oid, additive=False):
    if not additive:
        app._pm5_selected = set()
    if oid:
        app._pm5_selected.add(oid)
        app._pm_selected_object = oid
    else:
        app._pm_selected_object = None
    _draw_page(app, page)
    obj = _object_for_id(app, oid) if oid else None
    if obj:
        app.status.config(text=f"Selected object  |  {oid}  |  {obj.rect.width:.0f} × {obj.rect.height:.0f}")


def _canvas_press(app, page, event):
    c = _page_canvas(page)
    if c is None:
        return
    hits = c.find_overlapping(event.x, event.y, event.x, event.y)
    oid = None
    for item in reversed(hits):
        tags = c.gettags(item)
        for tag in tags:
            if tag.startswith("frame-") or tag.startswith("image-"):
                oid = tag
                break
        if oid:
            break
    if not oid:
        _select(app, page, None)
        return
    _select(app, page, oid, bool(getattr(event, "state", 0) & 0x0001))
    app._pm5_drag = (page, oid, event.x, event.y, _object_for_id(app, oid).rect.x,
                     _object_for_id(app, oid).rect.y)


def _canvas_drag(app, page, event):
    drag = getattr(app, "_pm5_drag", None)
    if not drag or drag[0] is not page:
        return
    _, oid, sx, sy, ox, oy = drag
    obj = _object_for_id(app, oid)
    if not obj or getattr(obj, "locked", False):
        return
    z = _zoom(app)
    nx = ox + (event.x - sx) / z
    ny = oy + (event.y - sy) / z
    if not (getattr(event, "state", 0) & 0x0004):
        nx, ny = _snap(nx), _snap(ny)
    doc = app.document
    if oid in doc.frames:
        doc.move_frame(oid, nx, ny)
    else:
        doc.move_image(oid, nx, ny)
    _draw_page(app, page)


def _canvas_release(app, page, event):
    if getattr(app, "_pm5_drag", None):
        app._pm5_drag = None
        try:
            app.dirty = True
        except Exception:
            pass


def _patch_page_rebuild():
    # Import-time patch: pagemaker_workspace imports this module before App is
    # instantiated, while app.py is already loaded as the main module.
    try:
        import __main__ as main
        Page = getattr(main, "Page", None)
        if Page is None or getattr(Page, "_pm5_patched", False):
            return
        original = Page.rebuild

        def rebuild(self, *args, **kwargs):
            original(self, *args, **kwargs)
            app = getattr(self, "app", None)
            if app is None:
                return
            p = _doc_page(app, self)
            if p is None:
                return
            old = getattr(self, "_pm5_canvas", None)
            if old is not None:
                try: old.destroy()
                except Exception: pass
            z = _zoom(app)
            self._pm5_canvas = tk.Canvas(self.page, highlightthickness=0,
                                         bd=0, bg=app.page_bg())
            self._pm5_canvas.place(x=0, y=0, width=max(1, int(p.width*z)),
                                   height=max(1, int(p.height*z)))
            self._pm5_canvas.lower()
            self._pm5_canvas.bind("<Button-1>", lambda e,p=self:self._press(p,e), add="+")
            self._pm5_canvas.bind("<B1-Motion>", lambda e,p=self:self._drag(p,e), add="+")
            self._pm5_canvas.bind("<ButtonRelease-1>", lambda e,p=self:self._release(p,e), add="+")
            _draw_page(app, self)

        Page.rebuild = rebuild
        Page._pm5_patched = True

        def _press(self, page, event):
            _canvas_press(self.app, page, event)
        def _drag(self, page, event):
            _canvas_drag(self.app, page, event)
        def _release(self, page, event):
            _canvas_release(self.app, page, event)
        Page._press, Page._drag, Page._release = _press, _drag, _release
    except Exception:
        pass


def refresh_all(app):
    for page in getattr(app, "pages", []):
        _draw_page(app, page)


def selected_object(app):
    oid = getattr(app, "_pm_selected_object", None)
    return _object_for_id(app, oid) if oid else None


def _nudge(app, dx, dy):
    obj = selected_object(app)
    if not obj or getattr(obj, "locked", False):
        return
    step = 10 if getattr(app, "_pm5_shift", False) else 1
    nx, ny = obj.rect.x + dx*step, obj.rect.y + dy*step
    if obj.id in app.document.frames:
        app.document.move_frame(obj.id, nx, ny)
    else:
        app.document.move_image(obj.id, nx, ny)
    refresh_all(app)
    app.dirty = True


def _z_order(app, direction):
    oid = getattr(app, "_pm_selected_object", None)
    if not oid:
        return
    for p in app.document.pages:
        if oid in p.objects:
            i = p.objects.index(oid)
            j = i + direction
            if 0 <= j < len(p.objects):
                p.objects[i], p.objects[j] = p.objects[j], p.objects[i]
            refresh_all(app)
            app.dirty = True
            return


def _toggle_guides(app):
    app._pm5_guides = not getattr(app, "_pm5_guides", True)
    for p in getattr(app, "pages", []):
        _draw_page(app, p)


def _install_app(app):
    if getattr(app, "_pm5_installed", False):
        return
    app._pm5_installed = True
    app._pm5_selected = set()
    app._pm5_guides = True
    app._pm5_shift = False

    original_changed = getattr(app, "changed", None)
    if original_changed:
        def changed(widget=None, _orig=original_changed):
            result = _orig(widget)
            app.root.after(80, lambda: refresh_all(app))
            return result
        app.changed = changed

    def keypress(event):
        key = event.keysym
        app._pm5_shift = bool(event.state & 0x0001)
        if key == "Left": _nudge(app, -1, 0)
        elif key == "Right": _nudge(app, 1, 0)
        elif key == "Up": _nudge(app, 0, -1)
        elif key == "Down": _nudge(app, 0, 1)
        elif key in ("bracketleft", "Prior") and (event.state & 0x0004): _z_order(app, -1)
        elif key in ("bracketright", "Next") and (event.state & 0x0004): _z_order(app, 1)
        elif key == "semicolon" and (event.state & 0x0004): _toggle_guides(app)
        else: return
        return "break"
    app.root.bind_all("<KeyPress>", keypress, add="+")

    # Re-render after geometry-changing operations from Phase 2C/4.
    old_draw = getattr(app, "_canvas_layout", None)
    if old_draw:
        def layout(*args, _old=old_draw):
            result = _old(*args)
            refresh_all(app)
            return result
        app._canvas_layout = layout


def _patch_tk():
    # Use Tk's class hook so the layer is ready before PageMaker's App exists.
    old_init = tk.Tk.__init__
    if getattr(old_init, "_pm5_wrapped", False):
        return
    def init(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        self.after(120, lambda: _late_install(self))
    init._pm5_wrapped = True
    tk.Tk.__init__ = init


def _late_install(root):
    try:
        app = _find_app(root)
        if app:
            _install_app(app)
            refresh_all(app)
    except Exception:
        pass


_patch_page_rebuild()
_patch_tk()
