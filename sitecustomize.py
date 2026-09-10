"""PageMaker Pro runtime integration.

Phase 1: one canonical Story owns the document text and TextFrames define its
thread. Tk Text widgets remain the editing surface and are synchronized into
the model before every reflow.
"""
import sys
import tkinter as tk

from pagemaker_core import Document, Rect
from pagemaker_workspace import WorkspaceController
from story_runtime import StoryRuntime

_orig_tk_init = tk.Tk.__init__


def _canvas_fix(root):
    def refresh():
        try:
            stack = [root]
            while stack:
                w = stack.pop()
                if isinstance(w, tk.Canvas):
                    try:
                        bbox = w.bbox('all')
                        if bbox:
                            x1, y1, x2, y2 = bbox
                            w.configure(scrollregion=(min(0, x1), min(0, y1),
                                                       max(x2, w.winfo_width()),
                                                       max(y2, w.winfo_height())))
                    except Exception:
                        pass
                try:
                    stack.extend(w.winfo_children())
                except Exception:
                    pass
        except Exception:
            pass
        try:
            root.after(300, refresh)
        except Exception:
            pass
    root.after(250, refresh)


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
        max_cols = max((len(getattr(p, 'texts', [])) for p in pages), default=0)
        return [p.texts[ci] for ci in range(max_cols) for p in pages
                if ci < len(p.texts)]
    return [t for p in pages for t in getattr(p, 'texts', [])]


def _sync_document(app, preserve_story=False):
    """Build physical pages and exactly one Story with all text frames."""
    doc = Document()
    doc.pages.clear(); doc.stories.clear(); doc.frames.clear()
    doc.next_page_number = 1; doc._id_counter = 1

    for p in app.pages:
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
            doc.add_text_frame(mp, Rect(x, top, cw, max(1, bottom - top)), None, ci)

    old = getattr(app, 'document', None)
    old_story = next(iter(getattr(old, 'stories', {}).values()), None) if preserve_story else None
    widgets = _widget_order(app)
    widget_text = '\n'.join(t.get('1.0', 'end-1c') for t in widgets)
    story = doc.add_story(old_story.text if old_story and not widget_text else widget_text)
    app.document = doc
    app.story_runtime = StoryRuntime(doc)
    app.story_runtime.active_story_id = story.id
    app.story_runtime.attach_frames(story, _mode(app))
    for widget, fid in zip(widgets, story.frame_ids):
        doc.frames[fid].text = widget.get('1.0', 'end-1c')
    return story


def _sync_story_from_widgets(app):
    """Live-sync every editable Text widget into the canonical Story."""
    runtime = getattr(app, 'story_runtime', None)
    if runtime is None:
        return None
    story = runtime.story() or runtime.ensure_story('')
    mode = _mode(app)
    runtime.attach_frames(story, mode)
    widgets = _widget_order(app, mode)
    parts = []
    for widget, fid in zip(widgets, story.frame_ids):
        text = widget.get('1.0', 'end-1c')
        parts.append(text)
        app.document.frames[fid].text = text
    story.text = '\n'.join(parts)
    return story


def _render_story(app, story):
    """Render canonical frame text back into the legacy Text widgets."""
    mode = _mode(app)
    app.story_runtime.attach_frames(story, mode)
    widgets = _widget_order(app, mode)
    app._pm_rendering = True
    try:
        for widget, fid in zip(widgets, story.frame_ids):
            value = app.document.frames[fid].text
            if widget.get('1.0', 'end-1c') != value:
                widget.delete('1.0', 'end')
                widget.insert('1.0', value)
    finally:
        app._pm_rendering = False


def _reflow_story(app):
    """Phase-1 canonical reflow with automatic page creation."""
    if getattr(app, '_pm_canonical_busy', False):
        return
    app._pm_canonical_busy = True
    try:
        app.root.update_idletasks()
        story = _sync_story_from_widgets(app)
        if story is None:
            return
        mode = _mode(app)
        if mode == 'ask':
            app.status.config(text='Story synced — Ask Me mode does not auto-route overflow')
            return

        for _ in range(100):
            result, remaining = app.story_runtime.distribute(story, mode=mode)
            if not remaining:
                _render_story(app, story)
                app._canvas_layout()
                app.status.config(text='Story threaded through all text frames')
                return
            _render_story(app, story)
            original_add = getattr(app, '_pm_original_add_page', None)
            if original_add is None:
                app.status.config(text='Story overflow: no page creator available')
                return
            original_add(False)
            story = _sync_document(app, preserve_story=False)
            # Reconstruct the same canonical text from the now-rendered frames.
            _sync_story_from_widgets(app)

        _render_story(app, story)
        app.status.config(text='Story overflow: automatic page limit reached')
    finally:
        app._pm_canonical_busy = False


def _show_page(app, index):
    if not getattr(app, 'pages', None):
        return
    index = max(0, min(int(index), len(app.pages) - 1))
    app.workspace.goto_page(index)
    for p in app.pages:
        try: p.frame.pack_forget()
        except Exception: pass
    p = app.pages[index]
    try:
        p.frame.pack(side='top', padx=28, pady=28)
        app.root.update_idletasks(); app._canvas_layout()
        app.canvas.yview_moveto(0.0); app.canvas.xview_moveto(0.0)
    except Exception:
        pass
    try: app.status.config(text=f'Page {p.number} of {len(app.pages)}')
    except Exception: pass
    _refresh_nav(app)


def _refresh_nav(app):
    nav = getattr(app, '_pm_nav', None)
    if not nav: return
    try:
        buttons = app._pm_page_buttons
        for b in buttons.winfo_children(): b.destroy()
        current = app.workspace.view.active_page
        for i, p in enumerate(app.pages):
            tk.Button(buttons, text=str(p.number), width=3,
                      relief='sunken' if i == current else 'raised',
                      command=lambda i=i: _show_page(app, i)).pack(side='left', padx=2, pady=2)
    except Exception:
        pass


def _install_page_wrapper(app):
    if getattr(app, '_pm_page_wrapper', False): return
    app._pm_page_wrapper = True
    original_add = app.add_page
    original_remove = app.remove_page
    original_new = app.new
    original_open = app.open
    app._pm_original_add_page = original_add

    def add_page(mark=True):
        p = original_add(mark)
        _sync_document(app, preserve_story=True)
        _show_page(app, len(app.pages) - 1)
        return p
    def remove_page():
        original_remove(); _sync_document(app, preserve_story=False)
        if app.pages: _show_page(app, min(app.workspace.view.active_page, len(app.pages)-1))
    def new_document():
        result = original_new(); _sync_document(app, preserve_story=False)
        if app.pages: _show_page(app, 0)
        return result
    def open_document():
        result = original_open(); _sync_document(app, preserve_story=False)
        if app.pages: _show_page(app, 0)
        return result
    app.add_page = add_page; app.remove_page = remove_page
    app.new = new_document; app.open = open_document


def _install_edit_sync(app):
    if getattr(app, '_pm_edit_sync', False): return
    app._pm_edit_sync = True
    original_changed = app.changed
    def changed(widget=None):
        if getattr(app, '_pm_rendering', False): return
        try: _sync_story_from_widgets(app)
        except Exception: pass
        original_changed(widget)
    app.changed = changed


def _enhance(app):
    if getattr(app, '_pm_enhanced', False): return
    app._pm_enhanced = True
    app.document = Document()
    app.workspace = WorkspaceController(app.document)
    _sync_document(app, preserve_story=False)
    _install_page_wrapper(app)
    _install_edit_sync(app)

    nav = tk.Frame(app.root, height=38, bd=1, relief='sunken'); nav.pack(side='bottom', fill='x')
    tk.Button(nav, text='◀', width=3, command=lambda:_show_page(app, app.workspace.previous_page())).pack(side='left', padx=3, pady=3)
    tk.Label(nav, text='Page', padx=7).pack(side='left')
    buttons = tk.Frame(nav); buttons.pack(side='left', fill='x', expand=True)
    tk.Button(nav, text='▶', width=3, command=lambda:_show_page(app, app.workspace.next_page())).pack(side='right', padx=3, pady=3)
    app._pm_nav = nav; app._pm_page_buttons = buttons

    def refresh():
        try: _refresh_nav(app)
        except Exception: pass
        try: app.root.after(700, refresh)
        except Exception: pass
    refresh()
    app.root.bind_all('<Next>', lambda e:(_show_page(app,app.workspace.next_page()),'break')[1], add='+')
    app.root.bind_all('<Prior>', lambda e:(_show_page(app,app.workspace.previous_page()),'break')[1], add='+')
    app.root.bind_all('<Control-Home>', lambda e:(_show_page(app,0),'break')[1], add='+')
    app.root.bind_all('<Control-End>', lambda e:(_show_page(app,len(app.pages)-1),'break')[1], add='+')
    if app.pages: _show_page(app, 0)

    if not getattr(app, '_pm_reflow_wrapped', False):
        app._pm_original_reflow = app.reflow
        app.reflow = lambda *args, **kwargs: _reflow_story(app)
        app._pm_reflow_wrapped = True

    def equation():
        target = app.active
        if target is None and app.pages and app.pages[app.workspace.view.active_page].texts:
            target = app.pages[app.workspace.view.active_page].texts[0]; app.activate(target)
        if target is None: return
        w = tk.Toplevel(app.root); w.title('Math / Equation Builder'); w.geometry('900x390'); w.transient(app.root)
        tk.Label(w,text='Equation Builder',font=('Segoe UI',12,'bold')).pack(anchor='w',padx=12,pady=(10,2))
        tk.Label(w,text='Unicode equations remain editable and copyable.').pack(anchor='w',padx=12)
        e=tk.Entry(w,font=('Cambria Math',18)); e.pack(fill='x',padx=12,pady=8); e.focus_set()
        symbols='α β γ δ θ λ μ π σ φ ω Ω Δ Σ √ ∛ ∞ ∑ ∏ ∫ ∂ ∇ ± × ÷ ≠ ≈ ≤ ≥ ∝ → ⇒ ⇔ ∴ ∠ ° · ½ ⅓ ¼ ¾'.split()
        bar=tk.Frame(w); bar.pack(fill='x',padx=12)
        for s in symbols: tk.Button(bar,text=s,width=3,command=lambda s=s:e.insert('insert',s)).pack(side='left',padx=1,pady=1)
        row=tk.Frame(w); row.pack(fill='x',padx=12,pady=8)
        for label,value in [('x²','²'),('xₙ','ₙ'),('xⁿ','ⁿ'),('√( )','√()'),('→','→'),('±','±')]:
            tk.Button(row,text=label,command=lambda v=value:e.insert('insert',v),padx=10).pack(side='left',padx=2)
        def insert():
            if e.get(): target.insert('insert',e.get()); app.changed(target); w.destroy()
        tk.Button(w,text='Insert Equation',command=insert).pack(pady=10)
    app.math = equation
    app.root.bind_all('<Control-Alt-m>', lambda e:(equation(),'break')[1], add='+')


def _trace(frame, event, arg):
    if event == 'return' and frame.f_code.co_name == '__init__':
        obj = frame.f_locals.get('self')
        if obj is not None and obj.__class__.__name__ == 'App':
            try: _enhance(obj)
            except Exception: pass
            return None
    return _trace


def _tk_init(self, *args, **kwargs):
    _orig_tk_init(self, *args, **kwargs)
    _canvas_fix(self)


tk.Tk.__init__ = _tk_init
sys.settrace(_trace)
