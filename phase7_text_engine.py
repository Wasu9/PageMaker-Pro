"""PageMaker Pro Phase 7 — professional Unicode text/paragraph layer.

Adds paragraph alignment, spacing, indentation, tabs, line spacing and a
small formatting toolbar while leaving Tk's Unicode text engine intact.
"""
import tkinter as tk
from tkinter import ttk
import phase5_canvas as p5

ALIGN = ("Left", "Center", "Right", "Justify")


def _app_install(app):
    if getattr(app, "_pm7_installed", False):
        return
    app._pm7_installed = True
    app._pm7_tags = {}

    def widget():
        w = getattr(app, "active", None)
        if w is None:
            w = getattr(app, "active_text", None)
        return w

    def selected_range(w):
        try:
            return w.index("sel.first"), w.index("sel.last")
        except tk.TclError:
            return "1.0", "end-1c"

    def para_tag(w, option, value):
        if not w: return
        tag = f"pm7_{option}_{str(value).lower().replace(' ', '_')}"
        if option == "align":
            justify = {"left":"left", "center":"center", "right":"right", "justify":"left"}.get(str(value).lower(), "left")
            w.tag_configure(tag, justify=justify)
        elif option == "spacing1":
            w.tag_configure(tag, spacing1=max(0, int(value)))
        elif option == "spacing3":
            w.tag_configure(tag, spacing3=max(0, int(value)))
        elif option == "indent":
            w.tag_configure(tag, lmargin1=max(0, int(value)), lmargin2=max(0, int(value)))
        elif option == "first":
            w.tag_configure(tag, lmargin1=max(0, int(value)))
        elif option == "tabs":
            w.tag_configure(tag, tabs=(str(value),))
        w.tag_add(tag, *selected_range(w))
        app.dirty = True

    def apply_align(value):
        w=widget(); para_tag(w,"align",value) if w else None

    def apply_spacing():
        w=widget()
        if not w:return
        try: v=int(app._pm7_spacing.get())
        except Exception:return
        para_tag(w,"spacing1",v)

    def apply_after():
        w=widget()
        if not w:return
        try:v=int(app._pm7_after.get())
        except Exception:return
        para_tag(w,"spacing3",v)

    def apply_indent():
        w=widget()
        if not w:return
        try:v=int(app._pm7_indent.get())
        except Exception:return
        para_tag(w,"indent",v)

    def apply_first():
        w=widget()
        if not w:return
        try:v=int(app._pm7_first.get())
        except Exception:return
        para_tag(w,"first",v)

    def clear_paragraph():
        w=widget()
        if not w:return
        a,b=selected_range(w)
        for tag in w.tag_names():
            if str(tag).startswith("pm7_"): w.tag_remove(tag,a,b)
        app.dirty=True

    def font_size():
        w=widget()
        if not w:return
        try:size=int(app._pm7_size.get())
        except Exception:return
        tag=f"pm7_font_{size}"
        w.tag_configure(tag,font=(app.settings.get("font","Noto Sans"),max(6,size)))
        w.tag_add(tag,*selected_range(w));app.dirty=True

    def toggle_style(name):
        w=widget()
        if not w:return
        a,b=selected_range(w)
        tag=f"pm7_{name}"
        if tag not in w.tag_names():
            w.tag_configure(tag,font=(app.settings.get("font","Noto Sans"),int(app.settings.get("size",12)),name))
        w.tag_add(tag,a,b);app.dirty=True

    # Formatting bar — compact and deliberately paper-production focused.
    bar=tk.Frame(app.top, bd=0)
    bar.pack(side="left", padx=5)
    tk.Label(bar,text="¶").pack(side="left")
    for label in ALIGN:
        tk.Button(bar,text=label,relief="flat",padx=3,command=lambda x=label:apply_align(x)).pack(side="left")
    tk.Label(bar,text="Spacing").pack(side="left",padx=(6,1))
    app._pm7_spacing=tk.StringVar(value="0")
    ttk.Spinbox(bar,from_=0,to=100,width=3,textvariable=app._pm7_spacing,command=apply_spacing).pack(side="left")
    tk.Label(bar,text="After").pack(side="left",padx=(3,1))
    app._pm7_after=tk.StringVar(value="0")
    ttk.Spinbox(bar,from_=0,to=100,width=3,textvariable=app._pm7_after,command=apply_after).pack(side="left")
    tk.Label(bar,text="Indent").pack(side="left",padx=(3,1))
    app._pm7_indent=tk.StringVar(value="0")
    ttk.Spinbox(bar,from_=0,to=150,width=4,textvariable=app._pm7_indent,command=apply_indent).pack(side="left")
    tk.Label(bar,text="First").pack(side="left",padx=(3,1))
    app._pm7_first=tk.StringVar(value="0")
    ttk.Spinbox(bar,from_=-100,to=150,width=4,textvariable=app._pm7_first,command=apply_first).pack(side="left")
    app._pm7_size=tk.StringVar(value=str(app.settings.get("size",12)))
    ttk.Spinbox(bar,from_=6,to=96,width=4,textvariable=app._pm7_size,command=font_size).pack(side="left",padx=3)
    tk.Button(bar,text="B",font=("Segoe UI",9,"bold"),relief="flat",command=lambda:toggle_style("bold")).pack(side="left")
    tk.Button(bar,text="I",font=("Segoe UI",9,"italic"),relief="flat",command=lambda:toggle_style("italic")).pack(side="left")
    tk.Button(bar,text="Clear ¶",relief="flat",command=clear_paragraph).pack(side="left",padx=2)

    # Keyboard shortcuts useful for paper production.
    def key(event):
        ctrl=bool(event.state & 0x0004); shift=bool(event.state & 0x0001)
        if ctrl and event.keysym=="l": apply_align("Left")
        elif ctrl and event.keysym=="e": apply_align("Center")
        elif ctrl and event.keysym=="r": apply_align("Right")
        elif ctrl and event.keysym=="j": apply_align("Justify")
        else:return
        return "break"
    app.root.bind_all("<KeyPress>",key,add="+")

    # Expose a small API for future renderer/export phases.
    app.pm7_apply_alignment=apply_align
    app.pm7_apply_spacing=apply_spacing
    app.pm7_apply_after=apply_after
    app.pm7_apply_indent=apply_indent
    app.pm7_apply_first=apply_first
    app.pm7_clear_paragraph=clear_paragraph


def install(app):
    try:_app_install(app)
    except Exception:pass

_old=p5._install_app
if not getattr(_old,"_pm7_wrapped",False):
    def wrapped(app):
        _old(app);install(app)
    wrapped._pm7_wrapped=True
    p5._install_app=wrapped
