"""Phase 4 visual/workspace interaction layer.

Keeps the document model separate from the screen while adding PageMaker-style
pasteboard navigation, zoom shortcuts, and precise keyboard object controls.
"""
import tkinter as tk

_ORIGINAL_TK_INIT = tk.Tk.__init__
_INSTALLED = False


def _find_app(root):
    """Find the owning PageMaker App without global state."""
    direct = getattr(root, "_pagemaker_app", None)
    if direct is not None:
        return direct
    stack = list(root.winfo_children())
    while stack:
        widget = stack.pop()
        owner = getattr(widget, "app", None)
        if owner is not None and hasattr(owner, "pages") and hasattr(owner, "zoom"):
            root._pagemaker_app = owner
            return owner
        stack.extend(widget.winfo_children())
    return None


def _zoom_step(root, direction):
    app = _find_app(root)
    if app is None or not hasattr(app, "zoom"):
        return
    z = max(.25, float(getattr(app, "_zoom", .72)))
    app.zoom(z * (1.10 if direction > 0 else 1 / 1.10))
    return "break"


def _fit(root):
    app = _find_app(root)
    if app is not None and hasattr(app, "fit"):
        app.fit()
    return "break"


def _page(root, direction):
    app = _find_app(root)
    if app is None:
        return
    ws = getattr(app, "workspace", None)
    if ws is not None:
        ws.goto_page(ws.view.active_page + direction)
    try:
        from sitecustomize import _show_page
        _show_page(app, getattr(ws.view, "active_page", 0))
    except Exception:
        pass
    return "break"


def _selected_frame(app):
    widget = getattr(app, "_pm_selected_widget", None)
    if widget is None:
        return None, None
    try:
        from sitecustomize import _frame_for_widget
        return widget, _frame_for_widget(app, widget)
    except Exception:
        return widget, None


def _key_object(root, event):
    app = _find_app(root)
    if app is None:
        return
    widget, frame = _selected_frame(app)
    if frame is None or not getattr(app, "_pm_select_mode", True):
        return
    if isinstance(event.widget, tk.Text):
        return
    step = 1.0 / max(.25, float(getattr(app, "_zoom", .72)))
    if event.state & 0x0001:
        step *= 10
    dx = dy = 0
    if event.keysym == "Left": dx = -step
    elif event.keysym == "Right": dx = step
    elif event.keysym == "Up": dy = -step
    elif event.keysym == "Down": dy = step
    if not (dx or dy):
        return
    if event.state & 0x0004:
        if dx:
            app.story_runtime.resize_frame(frame.id, frame.rect.width + dx, frame.rect.height)
        else:
            app.story_runtime.resize_frame(frame.id, frame.rect.width, frame.rect.height + dy)
    else:
        app.story_runtime.move_frame(frame.id, frame.rect.x + dx, frame.rect.y + dy)
    try:
        z = float(app._zoom)
        widget.place(x=int(frame.rect.x * z), y=int(frame.rect.y * z),
                     width=int(frame.rect.width * z), height=int(frame.rect.height * z))
        key = sitecustomize._frame_key(app, widget)
        app._pm_frame_geometry[key] = (frame.rect.x, frame.rect.y,
                                       frame.rect.width, frame.rect.height)
        sitecustomize._draw_handles(app, widget)
    except Exception:
        pass
    return "break"


def _set_100(root):
    app = _find_app(root)
    if app is not None and hasattr(app, "zoom"):
        app.zoom(1.0)
    return "break"


def _clear(root):
    app = _find_app(root)
    if app is None:
        return
    try:
        from sitecustomize import _clear_selection
        _clear_selection(app)
    except Exception:
        pass
    return "break"


def _bind(root):
    if getattr(root, "_pm_phase4_bound", False):
        return
    root._pm_phase4_bound = True
    root.bind_all("<Control-MouseWheel>", lambda e: _zoom_step(root, 1 if e.delta > 0 else -1), add="+")
    root.bind_all("<Control-Button-4>", lambda e: _zoom_step(root, 1), add="+")
    root.bind_all("<Control-Button-5>", lambda e: _zoom_step(root, -1), add="+")
    root.bind_all("<Control-KeyPress-plus>", lambda e: _zoom_step(root, 1), add="+")
    root.bind_all("<Control-KeyPress-equal>", lambda e: _zoom_step(root, 1), add="+")
    root.bind_all("<Control-KeyPress-minus>", lambda e: _zoom_step(root, -1), add="+")
    root.bind_all("<Control-KeyPress-0>", lambda e: _fit(root), add="+")
    root.bind_all("<Control-KeyPress-1>", lambda e: _set_100(root), add="+")
    root.bind_all("<PageDown>", lambda e: _page(root, 1), add="+")
    root.bind_all("<PageUp>", lambda e: _page(root, -1), add="+")
    root.bind_all("<Escape>", lambda e: _clear(root), add="+")
    for key in ("Left", "Right", "Up", "Down"):
        root.bind_all("<KeyPress-%s>" % key, lambda e: _key_object(root, e), add="+")


def _tk_init(self, *args, **kwargs):
    _ORIGINAL_TK_INIT(self, *args, **kwargs)
    _bind(self)


if not _INSTALLED:
    tk.Tk.__init__ = _tk_init
    _INSTALLED = True
