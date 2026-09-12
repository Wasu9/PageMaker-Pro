"""PageMaker Pro Phase-2C interaction layer.

Keeps the existing Tk editor surface, while making the canonical DTP model
persistent across rebuilds. Adds movable/resizable text frames, persistent
manual threading, Ask-Me overflow routing, and imported image objects.
"""
import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox

from pagemaker_core import Document, Rect
from pagemaker_workspace import WorkspaceController
from story_runtime import StoryRuntime

_orig_tk_init = tk.Tk.__init__


def _mode(app):
    try:
        value = app.flow.get()
    except Exception:
        value = app.settings.get('flow_mode', 'next_column')
    if 'Same Column' in value or value == 'same_column':
        return 'same_column'
    if 'Ask Me' in value or value == 'ask':
        return 'ask'
    return 'next_column'


def _widget_order(app, mode=None):
    mode = mode or _mode(app)
    pages = list(app.pages)
    if mode == 'same_column':
        mc = max((len(getattr(p, 'texts', [])) for p in pages), default=0)
        return [p.texts[ci] for ci in range(mc)
                for p in pages if ci < len(p.texts)]
    return [t for p in pages for t in getattr(p, 'texts', [])]


def _frame_key(app, widget):
    for pi, p in enumerate(app.pages):
        for ci, w in enumerate(getattr(p, 'texts', [])):
            if w is widget:
                return (pi, ci)
    return None


def _capture_geometry(app):
    result = {}
    for pi, p in enumerate(app.pages):
        for ci, w in enumerate(getattr(p, 'texts', [])):
            try:
                z = max(.25, float(getattr(app, '_zoom', .72)))
                result[(pi, ci)] = (
                    w.winfo_x() / z, w.winfo_y() / z,
                    w.winfo_width() / z, w.winfo_height() / z)
            except Exception:
                pass
    return result


def _thread_keys(app):
    return list(getattr(app, '_pm_thread_keys', []))


def _sync_document(app, preserve_story=False):
    old = getattr(app, 'document', None)
    old_story = next(iter(getattr(old, 'stories', {}).values()), None)
    old_geom = getattr(app, '_pm_frame_geometry', {}) or {}
    old_keys = _thread_keys(app)
    if not old_geom:
        old_geom = _capture_geometry(app)

    doc = Document()
    widgets = _widget_order(app, _mode(app))
    for pi, p in enumerate(app.pages):
        mp = doc.add_page()
        mp.number = p.number
        mp.width = float(app.settings.get('page_w', 794))
        mp.height = float(app.settings.get('page_h', 1123))
        mp.margin = float(app.settings.get('margin', 45))
        mp.columns = len(getattr(p, 'texts', [])) or int(app.settings.get('columns', 2))
        mp.column_gap = float(app.settings.get('gap', 24))
        total = mp.width - 2 * mp.margin
        gap = mp.column_gap
        cw = max(1, (total - gap * (mp.columns - 1)) / mp.columns)
        top, bottom = 48, mp.height - 52
        for ci in range(mp.columns):
            x = mp.margin + ci * (cw + gap)
            rect = old_geom.get((pi, ci), (x, top, cw, max(1, bottom-top)))
            doc.add_text_frame(mp, Rect(*rect), None, ci)

    widget_text = ''.join(w.get('1.0', 'end-1c') for w in widgets)
    initial = old_story.text if preserve_story and old_story and not widget_text else widget_text
    story = doc.add_story(initial)
    app.document = doc
    app.story_runtime = StoryRuntime(doc)
    app.story_runtime.active_story_id = story.id

    default_ids = [f.id for p in doc.pages for f in doc.frame_order(p)]
    key_to_id = {}
    for pi, p in enumerate(app.pages):
        for ci, w in enumerate(getattr(p, 'texts', [])):
            key_to_id[(pi, ci)] = doc.pages[pi].frame_ids[ci]
    manual_ids = [key_to_id[k] for k in old_keys if k in key_to_id]
    if manual_ids:
        manual_ids += [fid for fid in default_ids if fid not in manual_ids]
        app.story_runtime.attach_frames(story, frame_ids=manual_ids)
    else:
        app.story_runtime.attach_frames(story, _mode(app))
    for widget, fid in zip(widgets, story.frame_ids):
        doc.frames[fid].text = widget.get('1.0', 'end-1c')
    app._pm_frame_geometry = {key: old_geom[key] for key in old_geom if key in key_to_id}
    if manual_ids:
        app._pm_thread_keys = [k for k in old_keys if k in key_to_id]
        app._pm_thread_keys += [k for k in key_to_id if k not in app._pm_thread_keys]
    else:
        app._pm_thread_keys = [(pi, ci) for pi, p in enumerate(app.pages)
                                for ci, _ in enumerate(getattr(p, 'texts', []))]
    return story


def _sync_story_from_widgets(app):
    rt = getattr(app, 'story_runtime', None)
    if rt is None:
        return None
    story = rt.story() or rt.ensure_story('')
    widgets = _widget_order(app, _mode(app))
    ids = list(story.frame_ids)
    if not ids:
        rt.attach_frames(story, _mode(app))
        ids = list(story.frame_ids)
    parts = []
    for widget, fid in zip(widgets, ids):
        text = widget.get('1.0', 'end-1c')
        parts.append(text)
        if fid in app.document.frames:
            app.document.frames[fid].text = text
    story.text = ''.join(parts)
    return story


def _render_story(app, story):
    widgets = _widget_order(app, _mode(app))
    app._pm_rendering = True
    try:
        for widget, fid in zip(widgets, story.frame_ids):
            if fid not in app.document.frames:
                continue
            value = app.document.frames[fid].text
            if widget.get('1.0', 'end-1c') != value:
                widget.delete('1.0', 'end')
                widget.insert('1.0', value)
    finally:
        app._pm_rendering = False


def _ask_overflow(app):
    win = tk.Toplevel(app.root)
    win.title('Text Overflow')
    win.transient(app.root)
    win.grab_set()
    tk.Label(win, text='The story has overflow text.',
             font=('Segoe UI', 10, 'bold'), padx=22, pady=14).pack()
    tk.Label(win, text='Where should the overflow go?', padx=22).pack()
    choice = {'value': 'stop'}
    box = tk.Frame(win); box.pack(padx=18, pady=14)
    def pick(value):
        choice['value'] = value
        win.destroy()
    tk.Button(box, text='Next Page — Same Column', width=25,
              command=lambda: pick('same_column')).grid(row=0, column=0, padx=4, pady=4)
    tk.Button(box, text='Continue Next Column', width=25,
              command=lambda: pick('next_column')).grid(row=0, column=1, padx=4, pady=4)
    tk.Button(box, text='Stop Here', width=25,
              command=lambda: pick('stop')).grid(row=1, column=0, columnspan=2, pady=4)
    win.protocol('WM_DELETE_WINDOW', lambda: pick('stop'))
    app.root.wait_window(win)
    return choice['value']


def _add_page_raw(app):
    fn = getattr(app, '_pm_original_add_page', None)
    return fn(False) if fn else None


def _route_remainder(app, remaining, mode):
    if not remaining:
        return
    # Existing rendered content remains untouched. New pages are appended and
    # only the remainder is distributed into a fresh frame sequence.
    if mode == 'same_column':
        target = len(app.pages)
        _add_page_raw(app)
        story = _sync_document(app, False)
        story.text = remaining
        ids = [fid for fid in story.frame_ids
               if fid in app.document.frames]
        # Start at the first frame of the newly created page, same column.
        if target < len(app.pages):
            first = app.pages[target].texts[0]
            key = (target, 0)
            id_map = {}
            for fid, w in zip(story.frame_ids, _widget_order(app, 'same_column')):
                k = _frame_key(app, w)
                id_map[k] = fid
            start = id_map.get(key)
            if start in ids:
                ids = ids[ids.index(start):]
        story.frame_ids = ids
        app.story_runtime.attach_frames(story, frame_ids=ids)
        while remaining:
            _, remaining = app.story_runtime.distribute(story, mode='same_column', frame_ids=story.frame_ids)
            _render_story(app, story)
            if remaining:
                _add_page_raw(app)
                story = _sync_document(app, False)
                story.text = remaining
                story.frame_ids = [fid for fid in story.frame_ids]
                app.story_runtime.attach_frames(story, frame_ids=story.frame_ids)
    else:
        while remaining:
            _add_page_raw(app)
            story = _sync_document(app, False)
            story.text = remaining
            _, remaining = app.story_runtime.distribute(story, mode='next_column', frame_ids=story.frame_ids)
            _render_story(app, story)


def _reflow_story(app):
    if getattr(app, '_pm_canonical_busy', False):
        return
    app._pm_canonical_busy = True
    try:
        app.root.update_idletasks()
        app._pm_frame_geometry = _capture_geometry(app)
        story = _sync_story_from_widgets(app)
        if story is None:
            return
        mode = _mode(app)
        _, remaining = app.story_runtime.distribute(story, mode='next_column' if mode == 'ask' else mode,
                                                     frame_ids=story.frame_ids)
        _render_story(app, story)
        if not remaining:
            app.status.config(text='Story threaded — no overflow')
            return
        if mode == 'ask':
            decision = _ask_overflow(app)
            if decision == 'stop':
                app.status.config(text='Overflow stopped here')
                return
            _route_remainder(app, remaining, decision)
        else:
            _route_remainder(app, remaining, mode)
        app._pm_frame_geometry = _capture_geometry(app)
        _refresh_nav(app)
        _install_frame_tools(app)
        app.status.config(text='Story reflow complete')
    finally:
        app._pm_canonical_busy = False


def _frame_for_widget(app, widget):
    key = _frame_key(app, widget)
    if key is None:
        return None
    pi, ci = key
    try:
        fid = app.document.pages[pi].frame_ids[ci]
        return app.document.frames.get(fid)
    except Exception:
        return None


def _select_frame(app, widget):
    frame = _frame_for_widget(app, widget)
    if frame is None:
        return
    old = getattr(app, '_pm_selected_widget', None)
    if old and old is not widget:
        try: old.configure(highlightthickness=0)
        except Exception: pass
    app._pm_selected_widget = widget
    app._pm_selected_frame = frame.id
    try:
        widget.configure(highlightthickness=2, highlightbackground='#3973d4', highlightcolor='#3973d4')
    except Exception: pass
    _draw_handles(app, widget)
    app.status.config(text=f'Selected Text Frame  |  {frame.rect.width:.0f} × {frame.rect.height:.0f}')


def _remove_handles(app):
    for h in getattr(app, '_pm_handles', []):
        try: h.destroy()
        except Exception: pass
    app._pm_handles = []


def _draw_handles(app, widget):
    _remove_handles(app)
    try:
        hs = max(5, min(9, int(float(app._zoom) * 9)))
        app._pm_handles = []
        for x, y in ((0, 0), (widget.winfo_width(), 0),
                     (0, widget.winfo_height()),
                     (widget.winfo_width(), widget.winfo_height())):
            h = tk.Frame(widget, width=hs, height=hs, bg='#3973d4', cursor='sizing')
            h.place(x=max(0, x-hs//2), y=max(0, y-hs//2))
            app._pm_handles.append(h)
    except Exception: pass


def _frame_drag_start(app, event, widget):
    if not getattr(app, '_pm_select_mode', True): return
    _select_frame(app, widget)
    app._pm_drag = (event.x, event.y)


def _frame_drag_move(app, event, widget):
    if not getattr(app, '_pm_select_mode', True): return
    if getattr(app, '_pm_selected_widget', None) is not widget or not getattr(app, '_pm_drag', None): return
    dx, dy = event.x-app._pm_drag[0], event.y-app._pm_drag[1]
    app._pm_drag = (event.x, event.y)
    frame = _frame_for_widget(app, widget)
    if not frame: return
    z = max(.25, float(app._zoom))
    app.story_runtime.move_frame(frame.id, frame.rect.x+dx/z, frame.rect.y+dy/z)
    widget.place(x=widget.winfo_x()+dx, y=widget.winfo_y()+dy)
    app._pm_frame_geometry[_frame_key(app, widget)] = (frame.rect.x, frame.rect.y, frame.rect.width, frame.rect.height)
    _draw_handles(app, widget)


def _frame_resize_start(app, event, widget):
    if not getattr(app, '_pm_select_mode', True): return
    _select_frame(app, widget)
    app._pm_resize = (event.x, event.y, widget.winfo_width(), widget.winfo_height())


def _frame_resize_move(app, event, widget):
    if not getattr(app, '_pm_select_mode', True): return
    if getattr(app, '_pm_selected_widget', None) is not widget or not getattr(app, '_pm_resize', None): return
    sx, sy, sw, sh = app._pm_resize
    nw, nh = max(60, sw+(event.x-sx)), max(40, sh+(event.y-sy))
    frame = _frame_for_widget(app, widget)
    if not frame: return
    z = max(.25, float(app._zoom))
    app.story_runtime.resize_frame(frame.id, nw/z, nh/z)
    widget.place(width=nw, height=nh)
    app._pm_frame_geometry[_frame_key(app, widget)] = (frame.rect.x, frame.rect.y, frame.rect.width, frame.rect.height)
    _draw_handles(app, widget)


def _frame_end(app, event, widget):
    app._pm_drag = None
    app._pm_resize = None
    frame = _frame_for_widget(app, widget)
    if frame:
        app.status.config(text=f'Frame: X {frame.rect.x:.0f} Y {frame.rect.y:.0f}  |  {frame.rect.width:.0f} × {frame.rect.height:.0f}')


def _thread_next(app):
    widget = getattr(app, '_pm_selected_widget', None)
    if widget is None: return
    key = _frame_key(app, widget)
    if key is None: return
    keys = _thread_keys(app)
    if key not in keys: keys.append(key)
    i = keys.index(key)
    widgets = _widget_order(app, _mode(app))
    candidates = [_frame_key(app, w) for w in widgets]
    if i + 1 >= len(keys):
        next_key = next((k for k in candidates if k not in keys), None)
        if next_key is None:
            app.status.config(text='No next Text Frame available'); return
        keys.insert(i+1, next_key)
    else:
        next_key = keys[i+1]
    app._pm_thread_keys = keys
    story = _sync_document(app, True)
    app.status.config(text='Text Frame threaded — custom order saved')
    _install_frame_tools(app)


def _unthread(app):
    widget = getattr(app, '_pm_selected_widget', None)
    key = _frame_key(app, widget) if widget else None
    keys = _thread_keys(app)
    if key not in keys: return
    i = keys.index(key)
    if i == len(keys)-1:
        app.status.config(text='Selected frame is already last')
        return
    app._pm_thread_keys = keys[:i+1]
    _sync_document(app, True)
    app.status.config(text='Text Frame unthreaded after selected frame')


def _thread_menu(app, widget, event):
    _select_frame(app, widget)
    menu = tk.Menu(app.root, tearoff=False)
    menu.add_command(label='Thread to Next Text Frame', command=lambda: _thread_next(app))
    menu.add_command(label='Unthread After This Frame', command=lambda: _unthread(app))
    menu.add_separator(); menu.add_command(label='Clear Selection', command=lambda: _clear_selection(app))
    try: menu.tk_popup(event.x_root, event.y_root)
    finally: menu.grab_release()


def _clear_selection(app):
    old = getattr(app, '_pm_selected_widget', None)
    if old:
        try: old.configure(highlightthickness=0)
        except Exception: pass
    _remove_handles(app)
    app._pm_selected_widget = None
    app._pm_selected_frame = None


def _install_frame_tools(app):
    for p in app.pages:
        for widget in getattr(p, 'texts', []):
            if getattr(widget, '_pm_2c_bound', False): continue
            widget._pm_2c_bound = True
            widget.bind('<Button-1>', lambda e,w=widget:_frame_drag_start(app,e,w), add='+')
            widget.bind('<B1-Motion>', lambda e,w=widget:_frame_drag_move(app,e,w), add='+')
            widget.bind('<ButtonRelease-1>', lambda e,w=widget:_frame_end(app,e,w), add='+')
            widget.bind('<Alt-Button-1>', lambda e,w=widget:_frame_resize_start(app,e,w), add='+')
            widget.bind('<Alt-B1-Motion>', lambda e,w=widget:_frame_resize_move(app,e,w), add='+')
            widget.bind('<Alt-ButtonRelease-1>', lambda e,w=widget:_frame_end(app,e,w), add='+')
            widget.bind('<Button-3>', lambda e,w=widget:_thread_menu(app,w,e), add='+')


def _select_tool(app):
    app._pm_select_mode = True
    app.status.config(text='Select: drag frame to move • Alt+drag to resize')


def _text_tool(app):
    app._pm_select_mode = False
    app.status.config(text='Text: click inside a frame to edit')
    try: app.text_tool()
    except Exception: pass


def _patch_toolbar(app):
    try:
        for child in app.left.winfo_children():
            if isinstance(child, tk.Button) and 'Select' in child.cget('text'):
                child.configure(command=lambda:_select_tool(app))
            elif isinstance(child, tk.Button) and 'Text' in child.cget('text'):
                child.configure(command=lambda:_text_tool(app))
    except Exception: pass
    _select_tool(app)


def _import_image(app):
    try:
        from PIL import Image, ImageTk
    except ImportError:
        messagebox.showinfo('Image', 'Install Pillow once: pip install pillow')
        return
    fn = filedialog.askopenfilename(parent=app.root,
        filetypes=[('Images','*.png *.jpg *.jpeg *.gif *.bmp *.webp'),('All files','*.*')])
    if not fn or not app.pages: return
    try:
        pi = app.workspace.view.active_page
    except Exception:
        pi = 0
    pi = max(0, min(pi, len(app.pages)-1))
    p = app.pages[pi]
    im = Image.open(fn).convert('RGBA')
    maxw, maxh = 280, 220
    im.thumbnail((maxw, maxh), Image.LANCZOS)
    ph = ImageTk.PhotoImage(im)
    x, y = 60, 70
    label = tk.Label(p.page, image=ph, bd=1, relief='solid', cursor='arrow')
    label.place(x=int(x*app._zoom), y=int(y*app._zoom),
                width=max(20,int(im.width*app._zoom)), height=max(20,int(im.height*app._zoom)))
    refs = getattr(app, '_pm_image_refs', [])
    refs.append(ph); app._pm_image_refs = refs
    image = app.document.add_image(p and app.document.pages[pi],
                                   Rect(x, y, im.width, im.height), fn)
    store = getattr(app, '_pm_image_widgets', {})
    store[image.id] = label; app._pm_image_widgets = store
    state = {'last': (0,0), 'start': None}
    label._pm_image_state = state
    def select(event=None):
        app._pm_selected_image = image.id
        try: label.configure(highlightthickness=2, highlightbackground='#3973d4')
        except Exception: pass
        app.status.config(text=f'Image selected  |  {os.path.basename(fn)}  |  {image.rect.width:.0f} × {image.rect.height:.0f}')
    def drag_start(event):
        if not getattr(app, '_pm_select_mode', True): return
        select(event); state['last']=(event.x,event.y)
    def drag_move(event):
        if not getattr(app, '_pm_select_mode', True) or not state.get('last'): return
        dx,dy=event.x-state['last'][0],event.y-state['last'][1]; state['last']=(event.x,event.y)
        z=max(.25,float(app._zoom)); app.document.move_image(image.id,image.rect.x+dx/z,image.rect.y+dy/z)
        label.place(x=label.winfo_x()+dx,y=label.winfo_y()+dy)
    def resize_start(event):
        if not getattr(app, '_pm_select_mode', True): return
        select(event); state['start']=(event.x,event.y,label.winfo_width(),label.winfo_height())
    def resize_move(event):
        if not getattr(app, '_pm_select_mode', True) or not state.get('start'): return
        sx,sy,sw,sh=state['start']; nw=max(30,sw+event.x-sx); nh=max(30,sh+event.y-sy)
        z=max(.25,float(app._zoom)); app.document.resize_image(image.id,nw/z,nh/z); label.place(width=nw,height=nh)
    label.bind('<Button-1>', drag_start, add='+'); label.bind('<B1-Motion>', drag_move, add='+')
    label.bind('<Alt-Button-1>', resize_start, add='+'); label.bind('<Alt-B1-Motion>', resize_move, add='+')
    app.status.config(text='Image imported — Select tool: drag to move, Alt+drag to resize')


def _install_page_wrapper(app):
    if getattr(app, '_pm_page_wrapper', False): return
    app._pm_page_wrapper = True
    original_add, original_remove = app.add_page, app.remove_page
    original_new, original_open = app.new, app.open
    app._pm_original_add_page = original_add
    def add_page(mark=True):
        p = original_add(mark)
        _sync_document(app, True); _show_page(app, len(app.pages)-1); _install_frame_tools(app)
        return p
    def remove_page():
        original_remove(); _sync_document(app, False)
        if app.pages: _show_page(app, min(app.workspace.view.active_page, len(app.pages)-1))
    def new_document():
        result=original_new(); app._pm_thread_keys=[]; app._pm_frame_geometry={}; _sync_document(app,False)
        if app.pages: _show_page(app,0); _install_frame_tools(app)
        return result
    def open_document():
        result=original_open(); app._pm_thread_keys=[]; app._pm_frame_geometry={}; _sync_document(app,False)
        if app.pages: _show_page(app,0); _install_frame_tools(app)
        return result
    app.add_page, app.remove_page, app.new, app.open = add_page, remove_page, new_document, open_document


def _install_edit_sync(app):
    if getattr(app, '_pm_edit_sync', False): return
    app._pm_edit_sync=True; original=app.changed
    def changed(widget=None):
        if getattr(app, '_pm_rendering', False): return
        try: _sync_story_from_widgets(app)
        except Exception: pass
        original(widget)
    app.changed=changed


def _show_page(app,index):
    if not getattr(app,'pages',None): return
    index=max(0,min(int(index),len(app.pages)-1)); app.workspace.goto_page(index)
    for p in app.pages:
        try:p.frame.pack_forget()
        except Exception:pass
    p=app.pages[index]
    try:
        p.frame.pack(side='top',padx=28,pady=28); app.root.update_idletasks(); app._canvas_layout(); app.canvas.yview_moveto(0); app.canvas.xview_moveto(0)
    except Exception:pass
    try:app.status.config(text=f'Page {p.number} of {len(app.pages)}')
    except Exception:pass
    _refresh_nav(app)


def _refresh_nav(app):
    nav=getattr(app,'_pm_nav',None)
    if not nav:return
    try:
        buttons=app._pm_page_buttons
        for b in buttons.winfo_children():b.destroy()
        current=app.workspace.view.active_page
        for i,p in enumerate(app.pages):
            tk.Button(buttons,text=str(p.number),width=3,relief='sunken' if i==current else 'raised',command=lambda i=i:_show_page(app,i)).pack(side='left',padx=2,pady=2)
    except Exception:pass


def _enhance(app):
    if getattr(app,'_pm_enhanced',False): return
    app._pm_enhanced=True
    app._pm_thread_keys=[]; app._pm_frame_geometry={}; app._pm_image_widgets={}; app._pm_image_refs=[]
    app.document=Document(); app.workspace=WorkspaceController(app.document); _sync_document(app,False)
    _install_page_wrapper(app); _install_edit_sync(app); _install_frame_tools(app)
    nav=tk.Frame(app.root,height=38,bd=1,relief='sunken'); nav.pack(side='bottom',fill='x')
    tk.Button(nav,text='◀',width=3,command=lambda:_show_page(app,app.workspace.previous_page())).pack(side='left',padx=3,pady=3)
    tk.Label(nav,text='Page',padx=7).pack(side='left'); buttons=tk.Frame(nav); buttons.pack(side='left',fill='x',expand=True)
    tk.Button(nav,text='▶',width=3,command=lambda:_show_page(app,app.workspace.next_page())).pack(side='right',padx=3,pady=3)
    app._pm_nav=nav; app._pm_page_buttons=buttons
    _patch_toolbar(app)
    # Replace the prototype image insertion with a real page object.
    app.image = lambda:_import_image(app)
    def refresh():
        try:_refresh_nav(app)
        except Exception:pass
        try:app.root.after(700,refresh)
        except Exception:pass
    refresh()
    app.root.bind_all('<Next>',lambda e:(_show_page(app,app.workspace.next_page()),'break')[1],add='+')
    app.root.bind_all('<Prior>',lambda e:(_show_page(app,app.workspace.previous_page()),'break')[1],add='+')
    app.root.bind_all('<Control-Home>',lambda e:(_show_page(app,0),'break')[1],add='+')
    app.root.bind_all('<Control-End>',lambda e:(_show_page(app,len(app.pages)-1),'break')[1],add='+')
    if app.pages:_show_page(app,0)
    if not getattr(app,'_pm_reflow_wrapped',False):
        app._pm_original_reflow=app.reflow; app.reflow=lambda *a,**k:_reflow_story(app); app._pm_reflow_wrapped=True
    app.status.config(text='Phase 2C: Select tool active')


def _trace(frame,event,arg):
    if event=='return' and frame.f_code.co_name=='__init__':
        obj=frame.f_locals.get('self')
        if obj is not None and obj.__class__.__name__=='App':
            try:_enhance(obj)
            except Exception:pass
            return None
    return _trace


def _tk_init(self,*args,**kwargs):
    _orig_tk_init(self,*args,**kwargs)


tk.Tk.__init__=_tk_init
sys.settrace(_trace)
