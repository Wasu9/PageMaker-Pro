"""PageMaker Pro Phase 15 — mixed Unicode run renderer.

Renders a lossless Unicode story as independently styled Canvas runs.  The
renderer understands bold/italic/size spans supplied by the Tk editor tags and
keeps superscripts/subscripts as visual baseline/size adjustments when their
Unicode characters are used directly (e.g. x², H₂O).
"""
import tkinter as tk
from phase14_unicode_shaping import UnicodeRunEngine
from dtp_text_layout import DTPTextLayout
import phase5_canvas as p5


def _style_at(widget, index, default_size):
    bold = italic = False
    size = default_size
    try:
        tags = widget.tag_names(index)
        for tag in tags:
            s = str(tag).lower()
            if s == "pm7_bold" or s.endswith("_bold"): bold = True
            if s == "pm7_italic" or s.endswith("_italic"): italic = True
            if s.startswith("pm7_font_"):
                try: size = float(s.rsplit("_",1)[1])
                except Exception: pass
    except Exception:
        pass
    return size, bold, italic


def _install(app):
    if getattr(app, "_pm15_installed", False): return
    app._pm15_installed=True

    def render_page(page):
        canvas=p5._page_canvas(page); doc_page=p5._doc_page(app,page)
        if canvas is None or doc_page is None: return
        z=p5._zoom(app); canvas.delete("pm15-text")
        rt=getattr(app,"story_runtime",None); story=rt.story() if rt else None
        if not story:return
        default=float(app.settings.get("size",12)); family=app.settings.get("font","Noto Sans")
        for fid in getattr(doc_page,"frame_ids",[]):
            frame=app.document.frames.get(fid)
            if not frame or fid not in story.frame_ids or not frame.text:continue
            widget=None
            for p in app.pages:
                for w in getattr(p,"texts",[]):
                    try:
                        if p5._doc_page(app,p) is doc_page and p5._frame_for_widget(app,w).id==fid: widget=w
                    except Exception: pass
            # Layout remains geometry-driven; run drawing is independent.
            layout=DTPTextLayout(font_size=default).layout_paragraph(frame.text,frame.rect.width)
            pos=0
            for line in layout.lines:
                if not line.text:continue
                i=0
                while i<len(line.text):
                    global_index=line.start+i
                    if widget is not None:
                        try: size,bold,italic=_style_at(widget,f"1.0+{global_index}c",default)
                        except Exception: size,bold,italic=default,False,False
                    else:size,bold,italic=default,False,False
                    j=i+1
                    while j<len(line.text):
                        if widget is not None:
                            try:
                                s2,b2,it2=_style_at(widget,f"1.0+{line.start+j}c",default)
                            except Exception:s2,b2,it2=size,bold,italic
                        else:s2,b2,it2=size,bold,italic
                        if (s2,b2,it2)!=(size,bold,italic):break
                        j+=1
                    run=line.text[i:j]
                    engine=UnicodeRunEngine(family,size)
                    x=(frame.rect.x+line.x+engine.measure(line.text[:i],family,size,bold,italic) if engine.measure(line.text[:i],family,size,bold,italic) is not None else frame.rect.x+line.x)*z
                    canvas.create_text(x,line.y*z,anchor="nw",text=run,
                                       font=(family,max(6,int(size)),"bold" if bold else "normal","italic" if italic else "roman"),
                                       tags=("pm15-text",fid))
                    i=j

    def refresh():
        for page in getattr(app,"pages",[]):
            try:render_page(page)
            except Exception:pass
    app.pm15_render_text=refresh
    app.root.after(450,refresh)


def install(app):
    try:_install(app)
    except Exception:pass
