"""PageMaker Pro runtime integration.

This module is intentionally UI-light: it bridges the existing Tk editor to the
new document/workspace architecture while the renderer is being migrated.
"""
import sys
import tkinter as tk

from pagemaker_core import Document, Rect
from pagemaker_workspace import WorkspaceController

_orig_tk_init = tk.Tk.__init__


def _canvas_fix(root):
    def walk(w):
        yield w
        try:
            for c in w.winfo_children():
                yield from walk(c)
        except Exception:
            pass

    def refresh():
        try:
            for c in [w for w in walk(root) if isinstance(w, tk.Canvas)]:
                try:
                    children = c.winfo_children()
                    rw = max([x.winfo_reqwidth() for x in children] + [0])
                    rh = max([x.winfo_reqheight() for x in children] + [0])
                    c.configure(scrollregion=(0, 0,
                        max(c.winfo_width() + 2, rw + 30),
                        max(c.winfo_height() + 2, rh + 30)))
                except Exception:
                    pass
        except Exception:
            pass
        try:
            root.after(300, refresh)
        except Exception:
            pass

    root.after(250, refresh)


def _sync_document(app):
    """Mirror the legacy Tk pages into the new model without changing editing yet."""
    try:
        doc = Document()
        doc.pages.clear()
        doc.next_page_number = 1
        for p in app.pages:
            mp = doc.add_page()
            mp.number = p.number
            mp.width = float(app.settings.get('page_w', 794))
            mp.height = float(app.settings.get('page_h', 1123))
            mp.margin = float(app.settings.get('margin', 45))
            mp.columns = len(p.texts) or int(app.settings.get('columns', 2))
            mp.column_gap = float(app.settings.get('gap', 24))
            if p.texts:
                story = doc.add_story('\n'.join(t.get('1.0', 'end-1c') for t in p.texts))
                total = mp.width - 2 * mp.margin
                gap = mp.column_gap
                cw = max(1, (total - gap * (mp.columns - 1)) / mp.columns)
                top = 48
                bottom = mp.height - 52
                for ci in range(mp.columns):
                    x = mp.margin + ci * (cw + gap)
                    frame = doc.add_text_frame(mp,
                        Rect(x, top, cw, max(1, bottom - top)), story, ci)
                    frame.text = p.texts[ci].get('1.0', 'end-1c')
        app.document = doc
    except Exception:
        pass


def _show_page(app, index):
    """Show one physical page in the pasteboard, like classic PageMaker."""
    if not getattr(app, 'pages', None):
        return
    index = max(0, min(int(index), len(app.pages) - 1))
    app.workspace.goto_page(index)
    for p in app.pages:
        try:
            p.frame.pack_forget()
        except Exception:
            pass
    p = app.pages[index]
    try:
        p.frame.pack(side='top', padx=28, pady=28)
        app.root.update_idletasks()
        app._canvas_layout()
        app.canvas.yview_moveto(0.0)
        app.canvas.xview_moveto(0.0)
    except Exception:
        pass
    try:
        app.status.config(text=f'Page {p.number} of {len(app.pages)}')
    except Exception:
        pass
    try:
        _sync_document(app)
    except Exception:
        pass
    _refresh_nav(app)


def _refresh_nav(app):
    nav = getattr(app, '_pm_nav', None)
    if not nav:
        return
    try:
        buttons = app._pm_page_buttons
        for b in buttons.winfo_children():
            b.destroy()
        current = app.workspace.view.active_page
        for i, p in enumerate(app.pages):
            b = tk.Button(buttons, text=str(p.number), width=3,
                          relief='sunken' if i == current else 'raised',
                          command=lambda i=i: _show_page(app, i))
            b.pack(side='left', padx=2, pady=2)
    except Exception:
        pass


def _install_page_wrapper(app):
    if getattr(app, '_pm_page_wrapper', False):
        return
    app._pm_page_wrapper = True
    original_add_page = app.add_page
    original_remove_page = app.remove_page
    original_new = app.new
    original_open = app.open

    def add_page(mark=True):
        p = original_add_page(mark)
        _sync_document(app)
        _show_page(app, len(app.pages) - 1)
        return p

    def remove_page():
        original_remove_page()
        _sync_document(app)
        if app.pages:
            _show_page(app, min(app.workspace.view.active_page, len(app.pages) - 1))

    def new_document():
        result = original_new()
        _sync_document(app)
        if app.pages:
            _show_page(app, 0)
        return result

    def open_document():
        result = original_open()
        _sync_document(app)
        if app.pages:
            _show_page(app, 0)
        return result

    app.add_page = add_page
    app.remove_page = remove_page
    app.new = new_document
    app.open = open_document


def _enhance(app):
    if getattr(app, '_pm_enhanced', False):
        return
    app._pm_enhanced = True

    # New architecture objects. The legacy editor remains the editing surface
    # temporarily, while these become the canonical page/workspace state.
    app.document = Document()
    app.workspace = WorkspaceController(app.document)
    _sync_document(app)
    _install_page_wrapper(app)

    nav = tk.Frame(app.root, height=38, bd=1, relief='sunken')
    nav.pack(side='bottom', fill='x')
    tk.Button(nav, text='◀', width=3,
              command=lambda: _show_page(app, app.workspace.previous_page())).pack(side='left', padx=3, pady=3)
    tk.Label(nav, text='Page', padx=7).pack(side='left')
    buttons = tk.Frame(nav)
    buttons.pack(side='left', fill='x', expand=True)
    tk.Button(nav, text='▶', width=3,
              command=lambda: _show_page(app, app.workspace.next_page())).pack(side='right', padx=3, pady=3)
    app._pm_nav = nav
    app._pm_page_buttons = buttons

    def refresh():
        try:
            _refresh_nav(app)
        except Exception:
            pass
        try:
            app.root.after(700, refresh)
        except Exception:
            pass

    refresh()

    # Keyboard navigation is page navigation, not canvas scrolling.
    app.root.bind_all('<Next>', lambda e: (_show_page(app, app.workspace.next_page()), 'break')[1], add='+')
    app.root.bind_all('<Prior>', lambda e: (_show_page(app, app.workspace.previous_page()), 'break')[1], add='+')
    app.root.bind_all('<Control-Home>', lambda e: (_show_page(app, 0), 'break')[1], add='+')
    app.root.bind_all('<Control-End>', lambda e: (_show_page(app, len(app.pages) - 1), 'break')[1], add='+')

    # Replace the old horizontal multi-page presentation with one active page.
    if app.pages:
        _show_page(app, 0)

    # Unicode-first equation builder.
    def equation():
        if app.active is None:
            if app.pages and app.pages[0].texts:
                app.activate(app.pages[app.workspace.view.active_page].texts[0])
                app.active.focus_set()
            else:
                return
        w = tk.Toplevel(app.root)
        w.title('Math / Equation Builder')
        w.geometry('940x470')
        w.transient(app.root)
        tk.Label(w, text='Equation Builder', font=('Segoe UI', 12, 'bold')).pack(anchor='w', padx=12, pady=(10, 2))
        tk.Label(w, text='Unicode equations remain editable and copyable.').pack(anchor='w', padx=12)
        e = tk.Entry(w, font=('Cambria Math', 18))
        e.pack(fill='x', padx=12, pady=8)
        e.focus_set()
        symbols = 'α β γ δ θ λ μ π σ φ ω Ω Δ Σ √ ∛ ∞ ∑ ∏ ∫ ∂ ∇ ± × ÷ ≠ ≈ ≤ ≥ ∝ → ⇒ ⇔ ∴ ∵ ∠ ° · ½ ⅓ ¼ ¾'.split()
        bar = tk.Frame(w); bar.pack(fill='x', padx=12)
        for s in symbols:
            tk.Button(bar, text=s, width=3, command=lambda s=s: e.insert('insert', s)).pack(side='left', padx=1, pady=1)
        row = tk.Frame(w); row.pack(fill='x', padx=12, pady=8)

        def add(v):
            e.insert('insert', v); e.focus_set()
        def frac():
            q = tk.Toplevel(w); q.title('Insert Fraction'); q.resizable(False, False)
            tk.Label(q, text='Numerator').grid(row=0, column=0, padx=8, pady=6)
            n = tk.Entry(q, width=24); n.grid(row=0, column=1, padx=8, pady=6)
            tk.Label(q, text='Denominator').grid(row=1, column=0, padx=8, pady=6)
            d = tk.Entry(q, width=24); d.grid(row=1, column=1, padx=8, pady=6)
            def ok():
                add((n.get() or 'a') + '⁄' + (d.get() or 'b')); q.destroy()
            tk.Button(q, text='Insert', command=ok).grid(row=2, column=0, columnspan=2, pady=8)
            n.focus_set()
        for label, cmd in [('Fraction', frac), ('x²', lambda: add('²')), ('xₙ', lambda: add('ₙ')), ('xⁿ', lambda: add('ⁿ')), ('√( )', lambda: add('√()')), ('→', lambda: add('→')), ('±', lambda: add('±'))]:
            tk.Button(row, text=label, command=cmd, padx=10).pack(side='left', padx=2)
        tk.Label(w, text='Examples: v² = u² + 2as    Δx/Δt    F = ma    H₂SO₄    x₁ + x₂    a⁄b', font=('Consolas', 10)).pack(anchor='w', padx=12, pady=8)
        def insert():
            if e.get():
                app.active.insert('insert', e.get())
                app.changed()
                w.destroy()
        tk.Button(w, text='Insert Equation', command=insert).pack(pady=10)

    app.math = equation
    app.root.bind_all('<Control-Alt-m>', lambda e: (equation(), 'break')[1], add='+')


def _trace(frame, event, arg):
    if event == 'return' and frame.f_code.co_name == '__init__':
        obj = frame.f_locals.get('self')
        if obj is not None and obj.__class__.__name__ == 'App':
            try:
                _enhance(obj)
            except Exception:
                pass
            return None
    return _trace


def _tk_init(self, *args, **kwargs):
    _orig_tk_init(self, *args, **kwargs)
    _canvas_fix(self)


tk.Tk.__init__ = _tk_init
sys.settrace(_trace)
