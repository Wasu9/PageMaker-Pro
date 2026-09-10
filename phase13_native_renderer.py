"""PageMaker Pro Phase 13 — native canvas text rendering foundation.

The Tk Text widgets remain the editing adapter, while this module renders the
canonical Story/TextFrame layout onto the page canvas. Rendering uses the same
DTPTextLayout geometry as Phase 12, preserving Unicode source text and making
visual output independent from the editor widget's scrolling/word wrapping.
"""
import tkinter as tk
from dtp_text_layout import DTPTextLayout
import phase5_canvas as p5


def _font(app, size=12, bold=False, italic=False):
    family = app.settings.get("font", "Noto Sans")
    weight = "bold" if bold else "normal"
    slant = "italic" if italic else "roman"
    return (family, max(6, int(size)), weight, slant)


def _install(app):
    if getattr(app, "_pm13_installed", False):
        return
    app._pm13_installed = True
    app._pm13_renderer = True

    def render_page(page):
        canvas = p5._page_canvas(page)
        doc_page = p5._doc_page(app, page)
        if canvas is None or doc_page is None:
            return
        z = p5._zoom(app)
        canvas.delete("pm13-text")
        story = getattr(getattr(app, "story_runtime", None), "story", lambda: None)()
        story_ids = set(getattr(story, "frame_ids", [])) if story else set()
        engine = DTPTextLayout(font_size=float(app.settings.get("size", 12)))
        for fid in getattr(doc_page, "frame_ids", []):
            frame = getattr(app.document, "frames", {}).get(fid)
            if not frame or fid not in story_ids or not frame.text:
                continue
            x = frame.rect.x * z
            y = frame.rect.y * z
            width = frame.rect.width * z
            layout = engine.layout_paragraph(frame.text, width / max(z, .001), y=frame.rect.y,
                                              align="left", line_height=engine.line_height)
            for line in layout.lines:
                # Keep newline/Unicode code points untouched. Tk Canvas performs
                # Unicode text rendering; Phase 12 determines line geometry.
                canvas.create_text((frame.rect.x + line.x) * z,
                                   line.y * z,
                                   anchor="nw",
                                   text=line.text,
                                   font=_font(app, engine.font_size),
                                   tags=("pm13-text", fid))

    def refresh():
        for page in getattr(app, "pages", []):
            try:
                render_page(page)
            except Exception:
                pass

    app.pm13_render_text = refresh
    app.pm13_render_page = render_page

    old_refresh = getattr(p5, "refresh_all", None)
    if old_refresh and not getattr(old_refresh, "_pm13_wrapped", False):
        def wrapped_refresh(app_, *args, **kwargs):
            result = old_refresh(app_, *args, **kwargs)
            try:
                refresh()
            except Exception:
                pass
            return result
        wrapped_refresh._pm13_wrapped = True
        p5.refresh_all = wrapped_refresh

    app.root.after(350, refresh)


def install(app):
    try:
        _install(app)
    except Exception:
        pass

_old = p5._install_app
if not getattr(_old, "_pm13_wrapped", False):
    def wrapped(app):
        _old(app)
        install(app)
    wrapped._pm13_wrapped = True
    p5._install_app = wrapped
