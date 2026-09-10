"""PageMaker Pro Phase 10 — master pages, headers, footers and page numbering.

Keeps master metadata in Document.masters and renders non-editable repeating
items on the page canvas. Page numbers support the common "Page X" form.
"""
import tkinter as tk
from tkinter import ttk

import phase5_canvas as p5


def _install(app):
    if getattr(app, "_pm10_installed", False):
        return
    app._pm10_installed = True

    def master():
        doc = getattr(app, "document", None)
        return doc.masters.get("A-Master") if doc else None

    def refresh():
        m = master()
        if not m:
            return
        m.header = app._pm10_header.get()
        m.footer = app._pm10_footer.get()
        m.watermark = app._pm10_watermark.get()
        m.border = bool(app._pm10_border.get())
        try:
            m.margin = float(app._pm10_margin.get())
        except Exception:
            pass
        app.dirty = True
        p5.refresh_all(app)
        app.status.config(text="A-Master updated")

    def page_text(c, x, y, text, anchor="center", font=("Noto Sans", 9), tags=("pm10",)):
        if text:
            c.create_text(x, y, text=text, anchor=anchor, font=font, fill="#777b82", tags=tags)

    old_draw = p5._draw_page
    if not getattr(old_draw, "_pm10_wrapped", False):
        def draw(app_, page, _old=old_draw):
            _old(app_, page)
            c = p5._page_canvas(page)
            p = p5._doc_page(app_, page)
            if c is None or p is None:
                return
            m = app_.document.masters.get(getattr(p, "master", "A-Master"))
            if not m:
                return
            z = p5._zoom(app_)
            if getattr(m, "border", True):
                c.create_rectangle(1, 1, p.width*z-2, p.height*z-2,
                                   outline="#777b82", tags="pm10")
            page_text(c, p.width*z/2, 22*z, getattr(m, "header", ""), font=("Noto Sans", 9), tags=("pm10", "header"))
            page_text(c, p.width*z/2, (p.height-20)*z, getattr(m, "footer", ""), font=("Noto Sans", 9), tags=("pm10", "footer"))
            wm = getattr(m, "watermark", "")
            if wm:
                c.create_text(p.width*z/2, p.height*z/2, text=wm, angle=45,
                              font=("Noto Sans", 28), fill="#d0d2d6", tags=("pm10", "watermark"))
            c.create_text(p.width*z/2, (p.height-7)*z, text=f"Page {p.number}",
                          anchor="center", font=("Noto Sans", 8), fill="#8a8d91", tags=("pm10", "page-number"))
        draw._pm10_wrapped = True
        p5._draw_page = draw

    m = master()
    bar = tk.Frame(app.top, bd=0)
    bar.pack(side="left", padx=4)
    tk.Button(bar, text="Master", relief="flat", command=lambda: app.status.config(text="A-Master active")).pack(side="left")
    tk.Label(bar, text="H").pack(side="left", padx=(4, 1))
    app._pm10_header = tk.StringVar(value=getattr(m, "header", "") if m else "")
    ttk.Entry(bar, textvariable=app._pm10_header, width=12).pack(side="left")
    tk.Label(bar, text="F").pack(side="left", padx=(3, 1))
    app._pm10_footer = tk.StringVar(value=getattr(m, "footer", "") if m else "")
    ttk.Entry(bar, textvariable=app._pm10_footer, width=12).pack(side="left")
    tk.Label(bar, text="WM").pack(side="left", padx=(3, 1))
    app._pm10_watermark = tk.StringVar(value=getattr(m, "watermark", "") if m else "")
    ttk.Entry(bar, textvariable=app._pm10_watermark, width=10).pack(side="left")
    app._pm10_margin = tk.StringVar(value=str(getattr(m, "margin", 45) if m else 45))
    ttk.Spinbox(bar, from_=0, to=300, width=4, textvariable=app._pm10_margin, command=refresh).pack(side="left", padx=3)
    app._pm10_border = tk.BooleanVar(value=bool(getattr(m, "border", True) if m else True))
    ttk.Checkbutton(bar, text="Border", variable=app._pm10_border, command=refresh).pack(side="left")
    tk.Button(bar, text="Apply Master", relief="flat", command=refresh).pack(side="left", padx=2)

    app.pm10_refresh_master = refresh


def install(app):
    try:
        _install(app)
    except Exception:
        pass

_old = p5._install_app
if not getattr(_old, "_pm10_wrapped", False):
    def wrapped(app):
        _old(app)
        install(app)
    wrapped._pm10_wrapped = True
    p5._install_app = wrapped
