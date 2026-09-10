"""PageMaker Pro Phase-2B interaction layer.

Adds a dedicated Select tool, safe frame move/resize gestures, visual handles,
manual thread/unthread controls, and a real three-choice Ask Me overflow flow.
The text editor remains normal when the Text tool is active.
"""
import sys
import tkinter as tk
from tkinter import messagebox

from pagemaker_core import Document, Rect
from pagemaker_workspace import WorkspaceController
from story_runtime import StoryRuntime

_orig_tk_init = tk.Tk.__init__


def _mode(app):
    try:
        value = app.flow.get()
    except Exception:
        value = app.settings.get('flow_mode', 'next_column')
    if 'Same Column' in value or value == 'same_column': return 'same_column'
    if 'Ask Me' in value or value == 'ask': return 'ask'
    return 'next_column'


def _widget_order(app, mode=None):
    mode = mode or _mode(app)
    pages = list(app.pages)
    if mode == 'same_column':
        mc = max((len(getattr(p, 'texts', [])) for p in pages), default=0)
        return [p.texts[ci] for ci in range(mc) for p in pages if ci < len(p.texts)]
    return [t for p in pages for t in getattr(p, 'texts', [])]


def _sync_document(app, preserve_story=False):
    doc = Document()
    doc.pages.clear(); doc.stories.clear(); doc.frames.clear()
    doc.next_page_number = 1; doc._id_counter = 1
    for p in app.pages:
        mp = doc.add_page(); mp.number = p.number
        mp.width = float(app.settings.get('page_w', 794))
        mp.height = float(app.settings.get('page_h', 1123))
        mp.margin = float(app.settings.get('margin', 45))
        mp.columns = len(getattr(p, 'texts', [])) or int(app.settings.get('columns', 2))
        mp.column_gap = float(app.settings.get('gap', 24))
        total = mp.width - 2 * mp.margin; gap = mp.column_gap
        cw = max(1, (total - gap * (mp.columns - 1)) / mp.columns)
        top, bottom = 48, mp.height - 52
        for ci in range(mp.columns):
            x = mp.margin + ci * (cw + gap)
            doc.add_text_frame(mp, Rect(x, top, cw, max(1, bottom-top)), None, ci)
    old = getattr(app, 'document', None)
    old_story = next(iter(getattr(old, 'stories', {}).values()), None) if preserve_story else None
    widgets = _widget_order(app)
    widget_text = ''.join(t.get('1.0', 'end-1c') for t in widgets)
    story = doc.add_story(old_story.text if old_story and not widget_text else widget_text)
    app.document = doc
    app.story_runtime = StoryRuntime(doc)
    app.story_runtime.active_story_id = story.id
    app.story_runtime.attach_frames(story, _mode(app))
    for widget, fid in zip(widgets, story.frame_ids):
        doc.frames[fid].text = widget.get('1.0', 'end-1c')
    return story


def _sync_story_from_widgets(app):
    rt = getattr(app, 'story_runtime', None)
    if rt is None: return None
    story = rt.story() or rt.ensure_story('')
    mode = _mode(app)
    rt.attach_frames(story, mode)
    widgets = _widget_order(app, mode)
    parts = []
    for widget, fid in zip(widgets, story.frame_ids):
        text = widget.get('1.0', 'end-1c')
        parts.append(text)
        app.document.frames[fid].text = text
    story.text = ''.join(parts)
    return story


def _render_story(app, story):
    mode = _mode(app)
    app.story_runtime.attach_frames(story, mode)
    widgets = _widget_order(app, mode)
    app._pm_rendering = True
    try:
        for widget, fid in zip(widgets, story.frame_ids):
            value = app.document.frames[fid].text
            if widget.get('1.0', 'end-1c') != value:
                widget.delete('1.0', 'end'); widget.insert('1.0', value)
    finally:
        app._pm_rendering = False


def _ask_overflow(app):
    win = tk.Toplevel(app.root)
    win.title('Text Overflow')
    win.transient(app.root); win.grab_set(); win.resizable(False, False)
    tk.Label(win, text='The story has more text than the available frames.',
             font=('Segoe UI', 10, 'bold'), padx=22, pady=14).pack()
    tk.Label(win, text='Where should the overflow go?', padx=22, pady=2).pack()
    choice = {'value': None}
    box = tk.Frame(win); box.pack(padx=18, pady=14)
    def pick(value):
        choice['value'] = value; win.destroy()
    tk.Button(box, text='Next Page — Same Column', width=25,
              command=lambda: pick('same_column')).grid(row=0, column=0, padx=4, pady=4)
    tk.Button(box, text='Continue Next Column', width=25,
              command=lambda: pick('next_column')).grid(row=0, column=1, padx=4, pady=4)
    tk.Button(box, text='Stop Here', width=25,
              command=lambda: pick('stop')).grid(row=1, column=0, columnspan=2, pady=4)
    win.protocol('WM_DELETE_WINDOW', lambda: pick('stop'))
    app.root.wait_window(win)
    return choice['value'] or 'stop'


def _reflow_story(app):
    if getattr(app, '_pm_canonical_busy', False): return
    app._pm_canonical_busy = True
    try:
        app.root.update_idletasks()
        story = _sync_story_from_widgets(app)
        if story is None: return
        mode = _mode(app)
        if mode == 'ask':
            # First fill the currently available thread. Only ask when there is
            # genuine overflow; this keeps ordinary typing interruption-free.
            result, remaining = app.story_runtime.distribute(story, mode='next_column')
            _render_story(app, story)
            if not remaining:
                app.status.config(text='Story threaded — no overflow')
                return
            decision = _ask_overflow(app)
            if decision == 'stop':
                app.status.config(text='Overflow stopped by user')
                return
            original_add = getattr(app, '_pm_original_add_page', None)
            if original_add is None:
                app.status.config(text='Overflow: page creator unavailable')
                return
            # Preserve the unrendered remainder and add pages until it fits.
            story.text = remaining
            if decision == 'same_column':
                while True:
                    original_add(False)
                    story = _sync_document(app, False)
                    story.text = remaining
                    result, remaining = app.story_runtime.distribute(story, mode='same_column')
                    _render_story(app, story)
                    if not remaining: break
            else:
                original_add(False)
                story = _sync_document(app, False)
                story.text = remaining
                while True:
                    result, remaining = app.story_runtime.distribute(story, mode='next_column')
                    _render_story(app, story)
                    if not remaining: break
                    original_add(False)
                    story = _sync_document(app, False)
                    story.text = remaining
            _install_frame_tools(app)
            _refresh_nav(app)
            app.status.config(text='Overflow routed by user')
            return
        for _ in range(100):
            result, remaining = app.story_runtime.distribute(story, mode=mode)
            if not remaining:
                _render_story(app, story)
                app.status.config(text='Story threaded through all text frames')
                return
            original_add = getattr(app, '_pm_original_add_page', None)
            if original_add is None:
                app.status.config(text='Story overflow: no page creator'); return
            original_add(False)
            story = _sync_document(app, False)
            _sync_story_from_widgets(app)
        app.status.config(text='Story overflow: page limit reached')
    finally:
        app._pm_canonical_busy = False


def _frame_for_widget(app, widget):
    widgets = _widget_order(app, _mode(app))
    try: index = widgets.index(widget)
    except ValueError: return None
    story = app.story_runtime.story()
    if story and index < len(story.frame_ids):
        return app.document.frames.get(story.frame_ids[index])
    return None


def _select_frame(app, widget):
    frame = _frame_for_widget(app, widget)
    if frame is None: return
    old = getattr(app, '_pm_selected_widget', None)
    if old and old is not widget:
        try: old.configure(highlightthickness=0)
        except Exception: pass
    app._pm_selected_widget = widget; app._pm_selected_frame = frame.id
    widget.configure(highlightthickness=2, highlightbackground='#3973d4', highlightcolor='#3973d4')
    _draw_handles(app, widget)
    app.status.config(text=f'Selected Text Frame  |  {frame.rect.width:.0f} × {frame.rect.height:.0f}')


def _draw_handles(app, widget):
    _remove_handles(app)
    try:
        hs = max(5, min(9, int(float(app._zoom) * 9)))
        handles = []
        for x, y in ((0,0),(widget.winfo_width(),0),(0,widget.winfo_height()),
                     (widget.winfo_width(),widget.winfo_height())):
            h = tk.Frame(widget, width=hs, height=hs, bg='#3973d4', cursor='sizing')
            h.place(x=max(0,x-hs//2), y=max(0,y-hs//2)); handles.append(h)
        app._pm_handles = handles
    except Exception: pass


def _remove_handles(app):
    for h in getattr(app, '_pm_handles', []):
        try: h.destroy()
        except Exception: pass
    app._pm_handles = []


def _clear_selection(app):
    old = getattr(app, '_pm_selected_widget', None)
    if old:
        try: old.configure(highlightthickness=0)
        except Exception: pass
    _remove_handles(app)
    app._pm_selected_widget = None; app._pm_selected_frame = None


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
    if app.story_runtime.move_frame(frame.id, frame.rect.x+dx/z, frame.rect.y+dy/z):
        widget.place(x=widget.winfo_x()+dx, y=widget.winfo_y()+dy)
        _draw_handles(app, widget)
        app.changed(widget)


def _frame_drag_end(app, event, widget):
    if not getattr(app, '_pm_select_mode', True): return
    app._pm_drag = None
    frame = _frame_for_widget(app, widget)
    if frame: app.status.config(text=f'Frame moved  |  X {frame.rect.x:.0f}  Y {frame.rect.y:.0f}')


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
    if frame:
        z = max(.25, float(app._zoom))
        app.story_runtime.resize_frame(frame.id, nw/z, nh/z)
        widget.place(width=nw, height=nh)
        _draw_handles(app, widget)
        app.changed(widget)


def _frame_resize_end(app, event, widget):
    if not getattr(app, '_pm_select_mode', True): return
    app._pm_resize = None
    frame = _frame_for_widget(app, widget)
    if frame: app.status.config(text=f'Frame resized  |  {frame.rect.width:.0f} × {frame.rect.height:.0f}')


def _thread_next(app):
    widget = getattr(app, '_pm_selected_widget', None)
    if widget is None: return
    widgets = _widget_order(app, _mode(app))
    try: i = widgets.index(widget)
    except ValueError: return
    if i+1 >= len(widgets):
        app.status.config(text='No next Text Frame available'); return
    story = _sync_story_from_widgets(app)
    ids = story.frame_ids
    current = _frame_for_widget(app, widget)
    nxt = _frame_for_widget(app, widgets[i+1])
    if current and nxt:
        order = [current.id, nxt.id] + [x for x in ids if x not in (current.id, nxt.id)]
        story.frame_ids = order
        for fid in ids: app.document.frames[fid].story_id = story.id if fid in order else None
        app.status.config(text='Text Frame threaded to next frame')
        _render_story(app, story)


def _unthread(app):
    widget = getattr(app, '_pm_selected_widget', None)
    frame = _frame_for_widget(app, widget) if widget else None
    story = app.story_runtime.story() if getattr(app, 'story_runtime', None) else None
    if not frame or not story: return
    try: idx = story.frame_ids.index(frame.id)
    except ValueError: return
    if idx == len(story.frame_ids)-1:
        app.status.config(text='Selected frame is already the last frame'); return
    story.frame_ids = story.frame_ids[:idx+1]
    for fid, f in app.document.frames.items():
        if fid not in story.frame_ids: f.story_id = None
    app.status.config(text='Text Frame unthreaded after selected frame')


def _thread_menu(app, widget, event):
    _select_frame(app, widget)
    menu = tk.Menu(app.root, tearoff=False)
    menu.add_command(label='Thread to Next Text Frame', command=lambda:_thread_next(app))
    menu.add_command(label='Unthread After This Frame', command=lambda:_unthread(app))
    menu.add_separator(); menu.add_command(label='Clear Selection', command=lambda:_clear_selection(app))
    try: menu.tk_popup(event.x_root, event.y_root)
    finally: menu.grab_release()


def _install_frame_tools(app):
    for p in app.pages:
        for widget in p.texts:
            if getattr(widget, '_pm_2b_bound', False): continue
            widget._pm_2b_bound = True
            widget.bind('<Button-1>', lambda e,w=widget:_frame_drag_start(app,e,w), add='+')
            widget.bind('<B1-Motion>', lambda e,w=widget:_frame_drag_move(app,e,w), add='+')
            widget.bind('<ButtonRelease-1>', lambda e,w=widget:_frame_drag_end(app,e,w), add='+')
            widget.bind('<Alt-Button-1>', lambda e,w=widget:_frame_resize_start(app,e,w), add='+')
            widget.bind('<Alt-B1-Motion>', lambda e,w=widget:_frame_resize_move(app,e,w), add='+')
            widget.bind('<Alt-ButtonRelease-1>', lambda e,w=widget:_frame_resize_end(app,e,w), add='+')
            widget.bind('<Button-3>', lambda e,w=widget:_thread_menu(app,w,e), add='+')


def _select_tool(app):
    app._pm_select_mode = True
    app.status.config(text='Select tool: click/drag a frame to move; Alt+drag to resize')
    for p in app.pages:
        for w in p.texts:
            try: w.configure(cursor='arrow')
            except Exception: pass


def _text_tool(app):
    app._pm_select_mode = False
    app.status.config(text='Text tool: click inside text to edit')
    try: app.text_tool()
    except Exception: pass


def _patch_toolbar(app):
    # Replace the existing no-op Select button command without rebuilding the UI.
    try:
        for child in app.left.winfo_children():
            if isinstance(child, tk.Button) and 'Select' in child.cget('text'):
                child.configure(command=lambda:_select_tool(app))
            elif isinstance(child, tk.Button) and 'Text' in child.cget('text'):
                child.configure(command=lambda:_text_tool(app))
    except Exception: pass
    _select_tool(app)


def _install_page_wrapper(app):
    if getattr(app, '_pm_page_wrapper', False): return
    app._pm_page_wrapper = True
    original_add = app.add_page; original_remove = app.remove_page
    original_new = app.new; original_open = app.open
    app._pm_original_add_page = original_add
    def add_page(mark=True):
        p = original_add(mark); _sync_document(app, True); _show_page(app, len(app.pages)-1); _install_frame_tools(app); return p
    def remove_page():
        original_remove(); _sync_document(app, False)
        if app.pages: _show_page(app, min(app.workspace.view.active_page, len(app.pages)-1))
    def new_document():
        result = original_new(); _sync_document(app, False)
        if app.pages: _show_page(app, 0); _install_frame_tools(app)
        return result
    def open_document():
        result = original_open(); _sync_document(app, False)
        if app.pages: _show_page(app, 0); _install_frame_tools(app)
        return result
    app.add_page=add_page; app.remove_page=remove_page; app.new=new_document; app.open=open_document


def _install_edit_sync(app):
    if getattr(app, '_pm_edit_sync', False): return
    app._pm_edit_sync = True; original_changed = app.changed
    def changed(widget=None):
        if getattr(app, '_pm_rendering', False): return
        try: _sync_story_from_widgets(app)
        except Exception: pass
        original_changed(widget)
    app.changed = changed


def _show_page(app, index):
    if not getattr(app, 'pages', None): return
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
    if getattr(app, '_pm_enhanced', False): return
    app._pm_enhanced = True
    app.document=Document(); app.workspace=WorkspaceController(app.document); _sync_document(app,False)
    _install_page_wrapper(app); _install_edit_sync(app); _install_frame_tools(app)
    nav=tk.Frame(app.root,height=38,bd=1,relief='sunken'); nav.pack(side='bottom',fill='x')
    tk.Button(nav,text='◀',width=3,command=lambda:_show_page(app,app.workspace.previous_page())).pack(side='left',padx=3,pady=3)
    tk.Label(nav,text='Page',padx=7).pack(side='left'); buttons=tk.Frame(nav); buttons.pack(side='left',fill='x',expand=True)
    tk.Button(nav,text='▶',width=3,command=lambda:_show_page(app,app.workspace.next_page())).pack(side='right',padx=3,pady=3)
    app._pm_nav=nav; app._pm_page_buttons=buttons
    _patch_toolbar(app)
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
        app._pm_original_reflow=app.reflow; app.reflow=lambda *args,**kwargs:_reflow_story(app); app._pm_reflow_wrapped=True
    app.status.config(text='Phase 2B: Select tool active')


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
