"""PageMaker Pro runtime fix: keep embedded DTP canvases scrollable on Windows.
This is loaded automatically by normal Python startup when running app.py from the repo.
"""
import tkinter as _tk

_orig_tk_init = _tk.Tk.__init__


def _pm_fix_canvas_scrolling(root):
    def walk(widget):
        yield widget
        try:
            for child in widget.winfo_children():
                yield from walk(child)
        except Exception:
            return

    def refresh():
        try:
            canvases = [w for w in walk(root) if isinstance(w, _tk.Canvas)]
            for c in canvases:
                try:
                    # The DTP pages are embedded in a Frame window inside the Canvas.
                    # Use the embedded frame's requested height rather than relying only
                    # on bbox('all'), which can remain stale with Tk window items.
                    children = c.winfo_children()
                    req_h = max([ch.winfo_reqheight() for ch in children] + [0])
                    req_w = max([ch.winfo_reqwidth() for ch in children] + [0])
                    cur_h = c.winfo_height()
                    cur_w = c.winfo_width()
                    h = max(cur_h + 2, req_h + 24)
                    w = max(cur_w + 2, req_w + 24)
                    c.configure(scrollregion=(0, 0, w, h))

                    def wheel(event, canvas=c):
                        delta = getattr(event, 'delta', 0)
                        if delta:
                            steps = max(1, min(6, int(abs(delta) / 120)))
                            canvas.yview_scroll((-steps if delta > 0 else steps), 'units')
                        return 'break'

                    c.bind('<MouseWheel>', wheel, add='+')
                    c.bind('<Button-4>', lambda e, canvas=c: (canvas.yview_scroll(-3, 'units'), 'break')[-1], add='+')
                    c.bind('<Button-5>', lambda e, canvas=c: (canvas.yview_scroll(3, 'units'), 'break')[-1], add='+')
                except Exception:
                    pass
        except Exception:
            pass
        try:
            root.after(150, refresh)
        except Exception:
            pass

    root.after(250, refresh)


def _patched_tk_init(self, *args, **kwargs):
    _orig_tk_init(self, *args, **kwargs)
    _pm_fix_canvas_scrolling(self)


_tk.Tk.__init__ = _patched_tk_init
