"""Phase 5 late bootstrap.

The application classes live in the __main__ module, so they may not exist
when sitecustomize imports the workspace modules. This bootstrap installs the
page canvas patch after Tk has created the PageMaker App.
"""
import tkinter as tk
import __main__ as main
import phase5_canvas as p5


def _install_page_patch(app):
    Page = getattr(main, "Page", None)
    if Page is None or getattr(Page, "_pm5_patched", False):
        return
    original = Page.rebuild

    def rebuild(self, *args, **kwargs):
        original(self, *args, **kwargs)
        app = getattr(self, "app", None)
        if app is None:
            return
        p = p5._doc_page(app, self)
        if p is None:
            return
        old = getattr(self, "_pm5_canvas", None)
        if old is not None:
            try:
                old.destroy()
            except Exception:
                pass
        z = p5._zoom(app)
        c = tk.Canvas(self.page, highlightthickness=0, bd=0, bg=app.page_bg())
        c.place(x=0, y=0, width=max(1, int(p.width*z)), height=max(1, int(p.height*z)))
        c.lower()
        self._pm5_canvas = c
        c.bind("<Button-1>", lambda e, pg=self: p5._canvas_press(app, pg, e), add="+")
        c.bind("<B1-Motion>", lambda e, pg=self: p5._canvas_drag(app, pg, e), add="+")
        c.bind("<ButtonRelease-1>", lambda e, pg=self: p5._canvas_release(app, pg, e), add="+")
        p5._draw_page(app, self)

    Page.rebuild = rebuild
    Page._pm5_patched = True


def install(root):
    try:
        app = p5._find_app(root)
        if app:
            _install_page_patch(app)
            p5._install_app(app)
            p5.refresh_all(app)
    except Exception:
        pass
