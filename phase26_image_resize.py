"""Phase 26 image resize interaction for PageMaker Pro.

Adds direct corner/edge resize handles to image widgets created by the
clipboard-image layer. Shift keeps the original aspect ratio. The canonical
Document ImageObject rect is updated together with the visible widget.
"""
import os
import tkinter as tk


def _resize_model(app, oid, x, y, w, h):
    doc = getattr(app, 'document', None)
    if not doc or not oid:
        return
    try:
        obj = doc.images.get(oid)
        if obj is None:
            return
        if hasattr(doc, 'resize_image'):
            doc.resize_image(oid, w, h)
        else:
            obj.rect.w = max(20, float(w))
            obj.rect.h = max(20, float(h))
            obj.rect.x = float(x)
            obj.rect.y = float(y)
    except Exception:
        pass


def bind_image(app, oid, widget):
    if getattr(widget, '_pm26_resize_bound', False):
        return
    widget._pm26_resize_bound = True
    widget._pm26_image_id = oid
    widget.configure(cursor='hand2')

    state = {'start': None, 'rect': None, 'handle': None, 'ratio': 1.0}
    handles = {}
    size = 8

    def make_handles():
        for h in list(handles.values()):
            try: h.destroy()
            except Exception: pass
        handles.clear()
        if not widget.winfo_exists():
            return
        for name, cursor in (
            ('nw','size_nw_se'),('n','size_ns'),('ne','size_ne_sw'),
            ('w','size_we'),('e','size_we'),
            ('sw','size_ne_sw'),('s','size_ns'),('se','size_nw_se')):
            h = tk.Frame(widget.master, width=size, height=size,
                         bd=1, relief='solid', cursor=cursor)
            h.configure(bg='#3973d4')
            h._pm26_handle = name
            h.bind('<Button-1>', lambda e, n=name: start(e, n), add='+')
            h.bind('<B1-Motion>', drag, add='+')
            h.bind('<ButtonRelease-1>', end, add='+')
            handles[name] = h
        place_handles()

    def place_handles():
        if not widget.winfo_exists():
            return
        x, y = widget.winfo_x(), widget.winfo_y()
        w, h = max(20, widget.winfo_width()), max(20, widget.winfo_height())
        pts = {'nw':(x,y),'n':(x+w//2,y),'ne':(x+w,y),
               'w':(x,y+h//2),'e':(x+w,y+h//2),
               'sw':(x,y+h),'s':(x+w//2,y+h),'se':(x+w,y+h)}
        for n, (px,py) in pts.items():
            q = handles.get(n)
            if q is not None:
                q.place(x=px-size//2,y=py-size//2,width=size,height=size)
                q.lift()

    def start(e, name):
        if not getattr(app, '_pm_select_mode', True):
            return 'break'
        oid2 = getattr(widget, '_pm26_image_id', oid)
        obj = getattr(app, 'document', None).images.get(oid2) if getattr(app, 'document', None) else None
        if obj is None:
            return 'break'
        state['start'] = (e.x_root, e.y_root)
        state['rect'] = (widget.winfo_x(), widget.winfo_y(), widget.winfo_width(), widget.winfo_height())
        state['handle'] = name
        state['ratio'] = max(0.01, state['rect'][2] / max(1, state['rect'][3]))
        app._pm26_selected_image = oid2
        return 'break'

    def drag(e):
        if not state.get('start'):
            return 'break'
        sx, sy = state['start']; ox, oy, ow, oh = state['rect']; dx = e.x_root-sx; dy = e.y_root-sy
        n = state['handle']
        nw, nh = ow, oh; nx, ny = ox, oy
        if 'e' in n: nw = ow + dx
        if 'w' in n: nw = ow - dx; nx = ox + dx
        if 's' in n: nh = oh + dy
        if 'n' in n: nh = oh - dy; ny = oy + dy
        nw, nh = max(24, nw), max(24, nh)
        if e.state & 0x0001:  # Shift = proportional resize
            ratio = state['ratio']
            if n in ('e','w'): nh = nw/ratio
            elif n in ('n','s'): nw = nh*ratio
            else:
                if abs(dx) >= abs(dy): nh = nw/ratio
                else: nw = nh*ratio
            if 'n' in n: ny = oy + oh - nh
            if 'w' in n: nx = ox + ow - nw
        widget.place(x=int(nx), y=int(ny), width=int(nw), height=int(nh))
        place_handles()
        return 'break'

    def end(e):
        if not state.get('start'):
            return 'break'
        z = max(0.25, float(getattr(app, '_zoom', 1.0)))
        x = widget.winfo_x()/z; y = widget.winfo_y()/z
        w = widget.winfo_width()/z; h = widget.winfo_height()/z
        _resize_model(app, oid, x, y, w, h)
        try: app.dirty = True
        except Exception: pass
        try: app.status.config(text='Image resized — drag a corner/edge handle; Shift = keep ratio')
        except Exception: pass
        state['start'] = None
        place_handles()
        return 'break'

    widget.bind('<Configure>', lambda e: place_handles(), add='+')
    make_handles()


def install(app):
    """Bind resize handles to clipboard image widgets discovered on the app."""
    try:
        for oid, widget in getattr(app, '_pm_image_widgets', {}).items():
            bind_image(app, oid, widget)
    except Exception:
        pass
