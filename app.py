import json, os, tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser

# IMPORTANT: the professional DTP interaction layer must be loaded explicitly
# in the frozen Windows application. PyInstaller's hidden-import list alone
# does not execute sitecustomize.py, so without this import the EXE falls back
# to the old multi-page prototype UI. sitecustomize installs the canonical
# document model, single-page pasteboard workspace, page navigation, frame
# selection/threading and object interaction layer immediately after App init.
try:
    import sitecustomize  # noqa: F401
except Exception:
    sitecustomize = None

APP_TITLE = 'PageMaker Pro — Offline Unicode DTP'
DEFAULTS = {
    'page_w': 794, 'page_h': 1123, 'margin': 45, 'gap': 24, 'columns': 2,
    'page_color': '#ffffff', 'border': True, 'header': '', 'footer': '',
    'watermark': '', 'font': 'Noto Sans', 'size': 12, 'theme': 'light',
    'flow_mode': 'next_column', 'master_enabled': True,
    'master_header': '', 'master_footer': '', 'master_watermark': '',
    'master_border': True, 'zoom': 0.72
}
THEMES = {
    'light': ('#eef0f3','#f7f8fa','#ffffff','#202124','#d3d6da'),
    'gray': ('#d5d7da','#e8e9eb','#ececee','#242628','#bfc2c6'),
    'dark': ('#202225','#292c30','#292c30','#e8eaed','#15171a'),
    'invert': ('#181a1d','#24272b','#000000','#ffffff','#101113')
}

class Page:
    def __init__(self, app, number):
        self.app = app
        self.number = number
        self.saved = []
        self.frame = tk.Frame(app.host, bg=app.theme[4], padx=22, pady=22)
        self.page = tk.Frame(self.frame, bg=app.page_bg(), bd=0)
        self.page.pack()
        self.texts = []
        self.rebuild()

    def rebuild(self):
        old = self.capture() if self.texts else self.saved
        for w in self.page.winfo_children():
            w.destroy()
        self.texts = []
        s = self.app.settings
        z = max(0.25, float(getattr(self.app, '_zoom', s.get('zoom', .72))))
        pw = max(80, int(s['page_w'] * z))
        ph = max(100, int(s['page_h'] * z))
        self.frame.configure(width=pw + 44, height=ph + 44)
        self.page.configure(width=pw, height=ph, bg=self.app.page_bg())
        self.page.pack_propagate(False)

        n = max(1, min(3, int(s.get('columns', 2))))
        margin = int(s['margin'] * z)
        gap = int(s['gap'] * z)
        total = pw - 2 * margin
        cw = max(30, int((total - gap * (n - 1)) / n))
        bg, fg = self.app.page_bg(), self.app.page_fg()
        master = s.get('master_enabled', True)
        header = s.get('master_header','') if master else s.get('header','')
        footer = s.get('master_footer','') if master else s.get('footer','')
        watermark = s.get('master_watermark','') if master else s.get('watermark','')
        border = s.get('master_border', True) if master else s.get('border', True)

        self.page.configure(
            highlightthickness=1 if border else 0,
            highlightbackground=self.app.border_color() if border else bg,
            highlightcolor=self.app.border_color() if border else bg
        )
        base_size = max(6, int(round(s['size'] * z)))
        label_size = max(7, int(round(max(8, s['size'] - 1) * z)))
        if header:
            tk.Label(self.page, text=header, bg=bg, fg=fg,
                     font=(s['font'], label_size)).place(relx=.5, y=max(5, int(14*z)), anchor='n')
        if watermark:
            tk.Label(self.page, text=watermark, bg=bg, fg='#d0d0d0',
                     font=('Segoe UI', max(12, int(34*z)), 'bold')).place(relx=.5, rely=.5, anchor='center')
        if footer:
            tk.Label(self.page, text=footer + '    Page ' + str(self.number), bg=bg, fg=fg,
                     font=(s['font'], label_size)).place(relx=.5, y=ph-max(5, int(18*z)), anchor='s')

        top = max(35, int(48*z))
        bottom = max(top + 40, ph - max(35, int(52*z)))
        th = max(40, bottom - top)
        for i in range(n):
            x = margin + i * (cw + gap)
            t = tk.Text(self.page, wrap='word', undo=True,
                        font=(s['font'], base_size), bg=bg, fg=fg,
                        insertbackground=fg, relief='flat', bd=0,
                        padx=max(2, int(3*z)), pady=max(1, int(2*z)),
                        selectbackground='#4a78c2')
            t.place(x=x, y=top, width=cw, height=th)
            t.tag_configure('bold', font=(s['font'], base_size, 'bold'))
            t.tag_configure('italic', font=(s['font'], base_size, 'italic'))
            t.tag_configure('sup', offset=max(2, int(6*z)), font=(s['font'], max(5, base_size-3)))
            t.tag_configure('sub', offset=-max(2, int(4*z)), font=(s['font'], max(5, base_size-3)))
            t.bind('<FocusIn>', lambda e,w=t:self.app.activate(w))
            t.bind('<KeyRelease>', lambda e,w=t:self.app.changed(w))
            t.bind('<<Paste>>', lambda e,w=t:self.app.paste(w))
            t.bind('<MouseWheel>', lambda e,w=t:self.app._text_wheel(e,w), add='+')
            t.bind('<Button-4>', lambda e,w=t:self.app._text_wheel(e,w,-1), add='+')
            t.bind('<Button-5>', lambda e,w=t:self.app._text_wheel(e,w,1), add='+')
            self.texts.append(t)

        for i, data in enumerate(old[:n]):
            if i >= len(self.texts):
                break
            if isinstance(data, str):
                self.texts[i].insert('1.0', data)
            elif isinstance(data, dict):
                self.texts[i].insert('1.0', data.get('text',''))
        self.saved = []

    def capture(self):
        return [t.get('1.0','end-1c') for t in self.texts]

class App:
    def __init__(self, root):
        self.root = root
        self.settings = dict(DEFAULTS)
        self.theme = THEMES['light']
        self.pages = []
        self.active = None
        self.filename = None
        self.dirty = False
        self._reflow_busy = False
        self._zoom = self.settings['zoom']
        root.title(APP_TITLE)
        root.geometry('1450x920')
        root.minsize(1100, 700)
        self.ui()
        self.apply_theme('light', False)
        self.add_page(False)
        root.after(150, self.fit)
        root.protocol('WM_DELETE_WINDOW', self.close)

    def page_bg(self):
        return '#000000' if self.settings.get('theme') == 'invert' else self.settings.get('page_color','#fff')
    def page_fg(self):
        return '#ffffff' if self.settings.get('theme') == 'invert' else '#111111'
    def border_color(self):
        return '#dddddd' if self.settings.get('theme') == 'invert' else '#222222'

    def ui(self):
        self.root.option_add('*tearOff', False)
        m = tk.Menu(self.root)
        self.root.config(menu=m)
        menus = {
            'File':[('New',self.new),('Open…',self.open),('Save',self.save),('Save As…',self.save_as),None,('Export PDF…',self.export_pdf),('Export DOCX…',self.export_docx),None,('Exit',self.close)],
            'Edit':[('Undo',self.undo),('Redo',self.redo),None,('Find & Replace',self.find_replace)],
            'Insert':[('Text Frame',self.text_tool),('Image…',self.image),('Math / Symbol…',self.math),('Table…',self.table)],
            'Layout':[('Page Settings…',self.page_settings),('A-Master…',self.master),('Add Page',lambda:self.add_page()),('Remove Page',self.remove_page)],
            'Type':[('Bold',lambda:self.tag('bold')),('Italic',lambda:self.tag('italic')),('Superscript',lambda:self.tag('sup')),('Subscript',lambda:self.tag('sub')),('Clear Formatting',self.clear_fmt)],
            'View':[('Fit Page',self.fit),('100% Zoom',lambda:self.zoom(1)),('Light',lambda:self.apply_theme('light')),('Gray',lambda:self.apply_theme('gray')),('Dark',lambda:self.apply_theme('dark')),('Dark Invert',lambda:self.apply_theme('invert'))]
        }
        for name, items in menus.items():
            q = tk.Menu(m)
            for item in items:
                if item is None: q.add_separator()
                else: q.add_command(label=item[0], command=item[1])
            m.add_cascade(label=name, menu=q)

        top = tk.Frame(self.root, height=44)
        top.pack(fill='x')
        self.top = top
        for label, cmd in [('New',self.new),('Open',self.open),('Save',self.save),('Add Page',self.add_page),('Master',self.master),('PDF',self.export_pdf)]:
            tk.Button(top, text=label, command=cmd, relief='flat', padx=9).pack(side='left', pady=5, padx=2)
        tk.Label(top, text='Font').pack(side='left', padx=5)
        self.font = ttk.Combobox(top, width=14, values=['Noto Sans','Arial','Times New Roman','Calibri','Mangal','Nirmala UI'], state='readonly')
        self.font.set('Noto Sans'); self.font.pack(side='left')
        self.font.bind('<<ComboboxSelected>>', lambda e:self.font_apply())
        tk.Label(top, text='Size').pack(side='left', padx=4)
        self.sz = ttk.Spinbox(top, from_=7, to=72, width=4)
        self.sz.set(12); self.sz.pack(side='left'); self.sz.bind('<Return>', lambda e:self.font_apply())
        tk.Label(top, text='Flow').pack(side='left', padx=6)
        self.flow = ttk.Combobox(top, width=24, values=['Column → Column → Next Page','Same Column → Next Page','Ask Me'], state='readonly')
        self.flow.set('Column → Column → Next Page'); self.flow.pack(side='left'); self.flow.bind('<<ComboboxSelected>>', lambda e:self.set_flow())
        tk.Label(top, text='Zoom').pack(side='left', padx=6)
        self.zoom_box = ttk.Combobox(top, width=10, values=['50%','60%','67%','72%','80%','90%','100%','Fit Page'], state='readonly')
        self.zoom_box.set('Fit Page'); self.zoom_box.pack(side='left'); self.zoom_box.bind('<<ComboboxSelected>>', lambda e:self.set_zoom(self.zoom_box.get()))
        tk.Label(top, text='Ctrl + Mouse Wheel = Zoom').pack(side='left', padx=12)

        left = tk.Frame(self.root, width=78)
        left.pack(side='left', fill='y')
        self.left = left
        for txt, cmd in [('↖\nSelect',lambda:None),('T\nText',self.text_tool),('▣\nImage',self.image),('∑\nMath',self.math),('▤\nTable',self.table),('M\nMaster',self.master),('＋\nPage',self.add_page)]:
            tk.Button(left, text=txt, command=cmd, relief='flat', padx=2, pady=8).pack(fill='x', padx=6, pady=2)

        work = tk.Frame(self.root)
        work.pack(side='left', fill='both', expand=True)
        self.ruler_corner = tk.Frame(work, width=24, height=22)
        self.ruler_corner.grid(row=0, column=0)
        self.hruler = tk.Canvas(work, height=22, highlightthickness=0)
        self.hruler.grid(row=0, column=1, sticky='ew')
        self.vruler = tk.Canvas(work, width=24, highlightthickness=0)
        self.vruler.grid(row=1, column=0, sticky='ns')
        self.canvas = tk.Canvas(work, highlightthickness=0)
        self.canvas.grid(row=1, column=1, sticky='nsew')
        work.grid_rowconfigure(1, weight=1)
        work.grid_columnconfigure(1, weight=1)
        vsb = ttk.Scrollbar(work, orient='vertical', command=self.canvas.yview)
        hsb = ttk.Scrollbar(work, orient='horizontal', command=self.canvas.xview)
        vsb.grid(row=1, column=2, sticky='ns')
        hsb.grid(row=2, column=1, sticky='ew')
        self.canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.root.bind_all('<MouseWheel>', self._global_wheel, add='+')
        self.root.bind_all('<Button-4>', lambda e:self._global_wheel(e,-1), add='+')
        self.root.bind_all('<Button-5>', lambda e:self._global_wheel(e,1), add='+')
        self.root.bind_all('<Next>', lambda e:self._workspace_page(1), add='+')
        self.root.bind_all('<Prior>', lambda e:self._workspace_page(-1), add='+')
        self.root.bind_all('<Home>', lambda e:self._workspace_home(), add='+')
        self.root.bind_all('<End>', lambda e:self._workspace_end(), add='+')

        self.host = tk.Frame(self.canvas)
        self.host_window = self.canvas.create_window((20,10), window=self.host, anchor='nw')
        self.host.bind('<Configure>', lambda e:self._canvas_layout())
        self.canvas.bind('<Configure>', lambda e:self._canvas_layout())
        self.status = tk.Label(self.root, text='Ready', anchor='w', padx=10)
        self.status.pack(side='bottom', fill='x')

    def _global_wheel(self, event, direction=None):
        ctrl = bool(getattr(event, 'state', 0) & 0x0004)
        if ctrl:
            delta = getattr(event, 'delta', 0)
            if direction is not None:
                step = 1.10 if direction < 0 else 1/1.10
            else:
                step = 1.10 if delta > 0 else 1/1.10
            self.zoom(self._zoom * step)
            return 'break'
        if direction is None:
            delta = getattr(event, 'delta', 0)
            if not delta: return 'break'
            direction = -1 if delta > 0 else 1
            steps = max(1, min(6, int(abs(delta) / 120)))
        else:
            steps = 3
        try: self.canvas.yview_scroll(direction * steps, 'units')
        except tk.TclError: pass
        return 'break'

    def _text_wheel(self, event, widget, direction=None):
        ctrl = bool(getattr(event, 'state', 0) & 0x0004)
        if ctrl:
            delta = getattr(event, 'delta', 0)
            step = 1.10 if ((delta > 0) if direction is None else direction < 0) else 1/1.10
            self.zoom(self._zoom * step)
            return 'break'
        if direction is None:
            delta = getattr(event, 'delta', 0)
            if not delta: return 'break'
            direction = -1 if delta > 0 else 1
            steps = max(1, min(6, int(abs(delta) / 120)))
        else:
            steps = 3
        try: self.canvas.yview_scroll(direction * steps, 'units')
        except tk.TclError: pass
        return 'break'

    def _workspace_page(self, direction):
        try: self.canvas.yview_scroll(direction * max(1, int(self.canvas.winfo_height() * .85)), 'units')
        except tk.TclError: pass
        return 'break'
    def _workspace_home(self):
        self.canvas.yview_moveto(0.0); self.canvas.xview_moveto(0.0); return 'break'
    def _workspace_end(self):
        self.canvas.yview_moveto(1.0); self.canvas.xview_moveto(1.0); return 'break'

    def _canvas_layout(self):
        try:
            self.host.update_idletasks()
            bbox = self.canvas.bbox('all')
            if bbox:
                x1,y1,x2,y2 = bbox
                self.canvas.configure(scrollregion=(min(0,x1), min(0,y1), max(x2, self.canvas.winfo_width()), max(y2, self.canvas.winfo_height())))
            cw = max(1, self.canvas.winfo_width())
            hw = max(1, self.host.winfo_reqwidth())
            if hw < cw:
                self.canvas.coords(self.host_window, (cw-hw)//2, 10)
            else:
                self.canvas.coords(self.host_window, 20, 10)
            self.draw_rulers()
        except tk.TclError:
            pass

    def draw_rulers(self):
        c = self.theme
        self.hruler.configure(bg=c[2]); self.vruler.configure(bg=c[2]); self.ruler_corner.configure(bg=c[2])
        self.hruler.delete('all'); self.vruler.delete('all')
        z = max(.1, float(self._zoom))
        start = int(self.settings['margin'] * z)
        step = max(20, int(48*z))
        w = max(1, self.hruler.winfo_width()); h = max(1, self.vruler.winfo_height())
        for x in range(start, w, step):
            self.hruler.create_line(x,21,x,11,fill=c[3])
            self.hruler.create_text(x+2,3,text=str(round((x-start)/(96*z),1)),anchor='nw',fill=c[3],font=('Segoe UI',7))
        for y in range(start, h, step):
            self.vruler.create_line(23,y,13,y,fill=c[3])
            self.vruler.create_text(2,y+2,text=str(round((y-start)/(96*z),1)),anchor='nw',fill=c[3],font=('Segoe UI',7))

    def activate(self,w):
        self.active = w
        self.status.config(text='Unicode text frame active')
    def changed(self,w=None):
        self.dirty = True
        self.status.config(text='Modified')
        if not self._reflow_busy:
            self.root.after(80, self.reflow)

    def _displayline_count(self, t):
        try: return int(t.count('1.0','end-1c','displaylines')[0])
        except Exception: return 0

    def _overflow(self, t):
        total = self._displayline_count(t)
        if total <= 0: return None
        try:
            first = t.dlineinfo('1.0')
            if not first: return None
            line_h = max(1, int(first[3]))
            visible = max(1, int((t.winfo_height()-6) / line_h))
            if total <= visible: return None
            cut = t.index('1.0 + %d displaylines' % visible)
            moved = t.get(cut,'end-1c')
            if len(moved) < 1: return None
            return cut, moved
        except Exception:
            return None

    def reflow(self):
        if self._reflow_busy: return
        self._reflow_busy = True
        try:
            self.root.update_idletasks()
            mode = self.settings.get('flow_mode','next_column')
            changed_any = False
            for pi, p in enumerate(list(self.pages)):
                for ci, t in enumerate(list(p.texts)):
                    while True:
                        ov = self._overflow(t)
                        if not ov: break
                        cut, moved = ov
                        if mode == 'ask':
                            ans = messagebox.askyesnocancel('Text Overflow', 'Continue overflow into the next column/frame?')
                            if ans is None or not ans:
                                break
                        t.delete(cut,'end')
                        target_page, target_col = self._next_target(pi, ci, mode)
                        target_page.texts[target_col].insert('end', moved)
                        changed_any = True
                        if mode == 'ask': break
            if changed_any:
                self._canvas_layout()
        finally:
            self._reflow_busy = False

    def _next_target(self, pi, ci, mode):
        if mode == 'next_column' and ci + 1 < len(self.pages[pi].texts):
            return self.pages[pi], ci + 1
        if pi + 1 >= len(self.pages):
            p = self.add_page(False)
        else:
            p = self.pages[pi + 1]
        if mode == 'same_column' and ci < len(p.texts):
            return p, ci
        return p, 0

    def set_flow(self):
        self.settings['flow_mode'] = {
            'Column → Column → Next Page':'next_column',
            'Same Column → Next Page':'same_column',
            'Ask Me':'ask'
        }.get(self.flow.get(),'next_column')
        self.changed()

    def font_apply(self):
        try: self.settings['font'] = self.font.get(); self.settings['size'] = int(self.sz.get())
        except ValueError: return
        self.rebuild_pages(); self.changed()
    def tag(self,name):
        if self.active:
            try: self.active.tag_add(name,self.active.index('sel.first'),self.active.index('sel.last')); self.changed()
            except tk.TclError: pass
    def clear_fmt(self):
        if self.active:
            try:
                a,b=self.active.index('sel.first'),self.active.index('sel.last')
                for x in ('bold','italic','sup','sub'): self.active.tag_remove(x,a,b)
                self.changed()
            except tk.TclError: pass
    def text_tool(self):
        if self.active: self.active.focus_set()
        elif self.pages: self.activate(self.pages[0].texts[0]); self.active.focus_set()

    def paste(self,t):
        try:
            t.insert('insert', self.root.clipboard_get())
            self.changed(t)
            return 'break'
        except Exception:
            return None

    def image(self):
        if not self.active: return
        try:
            from PIL import Image, ImageTk
        except ImportError:
            messagebox.showinfo('Image','Install Pillow once: pip install pillow'); return
        fn=filedialog.askopenfilename(filetypes=[('Images','*.png *.jpg *.jpeg *.gif *.bmp *.webp')])
        if not fn: return
        try:
            im=Image.open(fn); im.thumbnail((320,240)); ph=ImageTk.PhotoImage(im)
            refs=getattr(self.active,'_pm_refs',[]); refs.append(ph); self.active._pm_refs=refs
            self.active.image_create('insert',image=ph); self.active.insert('insert','\n'); self.changed()
        except Exception as e: messagebox.showerror('Image',str(e))

    def math(self):
        if not self.active: return
        w=tk.Toplevel(self.root); w.title('Unicode Math & Symbols'); w.geometry('760x180')
        e=tk.Entry(w,width=80); e.pack(padx=12,pady=10)
        groups='α β γ δ θ λ μ π σ φ ω Ω Δ Σ √ ∛ ∞ ∑ ∏ ∫ ∂ ∇ ± × ÷ ≠ ≈ ≤ ≥ ∝ → ⇒ ⇔ ½ ⅓ ¼ ¾ ⁰¹²³⁺⁻ⁿ ₀₁₂₃₊₋ₙ H₂O CO₂ SO₄²⁻'.split()
        bar=tk.Frame(w); bar.pack(fill='x',padx=10)
        for x in groups: tk.Button(bar,text=x,command=lambda x=x:e.insert('end',x),relief='flat').pack(side='left',padx=1)
        tk.Button(w,text='Insert',command=lambda:(self.active.insert('insert',e.get()),self.changed(),w.destroy())).pack(pady=10)

    def table(self):
        if not self.active: return
        v=simpledialog.askstring('Table','Rows x Columns, e.g. 4x3',parent=self.root)
        try:
            r,c=map(int,v.lower().split('x')); r=max(1,min(20,r)); c=max(1,min(20,c))
            for _ in range(r): self.active.insert('insert',' | '.join(['']*c)+'\n')
            self.changed()
        except Exception: pass

    def page_settings(self):
        w=tk.Toplevel(self.root); w.title('Page Settings'); vars={}
        keys=['columns','gap','margin','header','footer','watermark']
        for i,k in enumerate(keys):
            tk.Label(w,text=k.title()).grid(row=i,column=0,padx=8,pady=4,sticky='w')
            v=tk.StringVar(value=str(self.settings[k])); vars[k]=v
            tk.Entry(w,textvariable=v,width=32).grid(row=i,column=1,padx=8,pady=4)
        border=tk.BooleanVar(value=self.settings['border'])
        tk.Checkbutton(w,text='Page Border',variable=border).grid(row=6,column=1,sticky='w')
        tk.Button(w,text='Page Color…',command=self.pick_color).grid(row=7,column=0,pady=8)
        def apply():
            try:
                for k,v in vars.items(): self.settings[k]=int(v.get()) if k in ('columns','gap','margin') else v.get()
                self.settings['columns']=max(1,min(3,self.settings['columns']))
                self.settings['border']=border.get(); self.rebuild_pages(); self.changed(); w.destroy()
            except ValueError:
                messagebox.showerror('Page Settings','Columns, gap and margin must be numbers.')
        tk.Button(w,text='Apply',command=apply).grid(row=8,column=0,columnspan=2,pady=10)

    def pick_color(self):
        c=colorchooser.askcolor(initialcolor=self.settings['page_color'])[1]
        if c: self.settings['page_color']=c; self.rebuild_pages(); self.changed()

    def master(self):
        w=tk.Toplevel(self.root); w.title('A-Master'); w.geometry('540x300'); vs={}
        for i,k in enumerate(['master_header','master_footer','master_watermark']):
            tk.Label(w,text=k.replace('master_','').title()).grid(row=i,column=0,padx=8,pady=8,sticky='w')
            v=tk.StringVar(value=self.settings[k]); vs[k]=v; tk.Entry(w,textvariable=v,width=40).grid(row=i,column=1,padx=8,pady=8)
        en=tk.BooleanVar(value=self.settings['master_enabled'])
        tk.Checkbutton(w,text='Apply A-Master to document pages',variable=en).grid(row=3,column=0,columnspan=2)
        border=tk.BooleanVar(value=self.settings['master_border'])
        tk.Checkbutton(w,text='Master page border',variable=border).grid(row=4,column=0,columnspan=2)
        def apply():
            for k,v in vs.items(): self.settings[k]=v.get()
            self.settings['master_enabled']=en.get(); self.settings['master_border']=border.get(); self.rebuild_pages(); self.changed(); w.destroy()
        tk.Button(w,text='Apply A-Master',command=apply).grid(row=5,column=0,columnspan=2,pady=18)

    def add_page(self,mark=True):
        p=Page(self,len(self.pages)+1)
        p.frame.pack(side='left', padx=8, pady=8)
        self.pages.append(p)
        self.root.update_idletasks(); self._canvas_layout()
        if mark: self.changed()
        return p
    def remove_page(self):
        if len(self.pages)>1:
            self.pages.pop().frame.destroy(); self.renumber(); self.changed(); self._canvas_layout()
    def renumber(self):
        for i,p in enumerate(self.pages,1): p.number=i
    def rebuild_pages(self):
        for p in self.pages:
            p.saved=p.capture(); p.rebuild()
        self.root.update_idletasks(); self._canvas_layout(); self.reflow()

    def capture(self): return [p.capture() for p in self.pages]
    def new(self):
        if self.dirty and not messagebox.askyesno('New','Discard unsaved changes?'): return
        for p in self.pages: p.frame.destroy()
        self.pages=[]; self.settings=dict(DEFAULTS); self._zoom=self.settings['zoom']; self.filename=None; self.dirty=False
        self.add_page(False); self.fit(); self.status.config(text='New document')
    def save(self):
        if not self.filename: return self.save_as()
        with open(self.filename,'w',encoding='utf-8') as f: json.dump({'settings':self.settings,'pages':self.capture()},f,ensure_ascii=False,indent=2)
        self.dirty=False; self.status.config(text='Saved: '+os.path.basename(self.filename))
    def save_as(self):
        fn=filedialog.asksaveasfilename(defaultextension='.upm',filetypes=[('PageMaker Pro','*.upm'),('JSON','*.json')])
        if fn: self.filename=fn; self.save()
    def open(self):
        fn=filedialog.askopenfilename(filetypes=[('PageMaker Pro','*.upm *.json'),('All files','*.*')])
        if not fn: return
        try:
            with open(fn,'r',encoding='utf-8') as f: d=json.load(f)
            for p in self.pages: p.frame.destroy()
            self.pages=[]; self.settings.update(d.get('settings',{})); self._zoom=float(self.settings.get('zoom',.72))
            for data in d.get('pages',[]):
                p=self.add_page(False); p.saved=data; p.rebuild()
            if not self.pages: self.add_page(False)
            self.filename=fn; self.dirty=False; self.status.config(text='Opened: '+os.path.basename(fn)); self.sync_controls(); self.fit()
        except Exception as e: messagebox.showerror('Open',str(e))
    def sync_controls(self):
        self.font.set(self.settings.get('font','Noto Sans')); self.sz.set(self.settings.get('size',12))
        self.flow.set({'next_column':'Column → Column → Next Page','same_column':'Same Column → Next Page','ask':'Ask Me'}.get(self.settings.get('flow_mode'),'Column → Column → Next Page'))

    def undo(self):
        if self.active:
            try: self.active.edit_undo()
            except tk.TclError: pass
    def redo(self):
        if self.active:
            try: self.active.edit_redo()
            except tk.TclError: pass
    def find_replace(self):
        t=self.active
        if not t: return
        find=simpledialog.askstring('Find','Find text:',parent=self.root)
        if find is None: return
        repl=simpledialog.askstring('Replace','Replace with:',parent=self.root)
        if repl is None: return
        content=t.get('1.0','end-1c').replace(find,repl); t.delete('1.0','end'); t.insert('1.0',content); self.changed()

    def apply_theme(self,name,mark=True):
        if name not in THEMES: name='light'
        self.theme=THEMES[name]; self.settings['theme']=name
        self.root.configure(bg=self.theme[0]); self.top.configure(bg=self.theme[2]); self.left.configure(bg=self.theme[1]); self.status.configure(bg=self.theme[1],fg=self.theme[3]); self.canvas.configure(bg=self.theme[4]); self.host.configure(bg=self.theme[4])
        for child in self.top.winfo_children():
            if isinstance(child,(tk.Label,tk.Button)): child.configure(bg=self.theme[2],fg=self.theme[3],activebackground=self.theme[1],activeforeground=self.theme[3])
        for child in self.left.winfo_children(): child.configure(bg=self.theme[1],fg=self.theme[3],activebackground=self.theme[2],activeforeground=self.theme[3])
        self.draw_rulers(); self.rebuild_pages()
        if mark: self.changed()

    def set_zoom(self,value):
        if value == 'Fit Page': self.fit(); return
        try: self.zoom(float(value.strip('%'))/100.0)
        except Exception: pass
    def zoom(self,z):
        old=self._zoom
        z=max(.35,min(1.50,float(z)))
        if abs(z-old)<.001: return
        self._zoom=z; self.settings['zoom']=z
        self.rebuild_pages()
        self.zoom_box.set(f'{round(z*100)}%') if hasattr(self,'zoom_box') else None
        self.status.config(text=f'Zoom {round(z*100)}%')

    def fit(self):
        self.root.update_idletasks()
        aw=max(500,self.canvas.winfo_width()-70)
        ah=max(400,self.canvas.winfo_height()-55)
        z=min(aw/self.settings['page_w'], ah/self.settings['page_h'], 1.0)
        self._zoom=max(.35,z); self.settings['zoom']=self._zoom
        if hasattr(self,'zoom_box'): self.zoom_box.set('Fit Page')
        self.rebuild_pages()
        self.status.config(text=f'Fit Page — {round(self._zoom*100)}%')

    def export_pdf(self):
        try: from reportlab.pdfgen import canvas
        except ImportError: messagebox.showinfo('PDF export','Install ReportLab once: pip install reportlab'); return
        fn=filedialog.asksaveasfilename(defaultextension='.pdf',filetypes=[('PDF','*.pdf')])
        if not fn: return
        c=canvas.Canvas(fn,pagesize=(self.settings['page_w'],self.settings['page_h']))
        for p in self.pages:
            c.setFillColorRGB(*self.hexrgb(self.page_bg())); c.rect(0,0,self.settings['page_w'],self.settings['page_h'],fill=1,stroke=0)
            border_on=self.settings.get('master_border',True) if self.settings.get('master_enabled',True) else self.settings.get('border',True)
            if border_on:
                c.setStrokeColorRGB(*self.hexrgb(self.border_color())); c.rect(8,8,self.settings['page_w']-16,self.settings['page_h']-16,fill=0,stroke=1)
            header=(self.settings.get('master_header','') if self.settings.get('master_enabled',True) else self.settings.get('header',''))
            footer=(self.settings.get('master_footer','') if self.settings.get('master_enabled',True) else self.settings.get('footer',''))
            c.setFillColorRGB(*self.hexrgb(self.page_fg())); c.setFont('Helvetica',9)
            if header: c.drawCentredString(self.settings['page_w']/2,self.settings['page_h']-28,header)
            c.drawCentredString(self.settings['page_w']/2,18,(footer+'    ' if footer else '')+f'Page {p.number}')
            n=len(p.texts); total=self.settings['page_w']-2*self.settings['margin']; gap=self.settings['gap']; cw=(total-gap*(n-1))/n
            for i,t in enumerate(p.texts):
                x=self.settings['margin']+i*(cw+gap); lines=t.get('1.0','end-1c').splitlines(); y=self.settings['page_h']-75
                c.setFont('Helvetica',self.settings['size'])
                for line in lines:
                    if y < 35: break
                    c.drawString(x,y,line[:120]); y-=self.settings['size']*1.35
        c.save(); self.status.config(text='PDF exported')

    def export_docx(self):
        try:
            from docx import Document
        except ImportError:
            messagebox.showinfo('DOCX export','Install python-docx once: pip install python-docx'); return
        fn=filedialog.asksaveasfilename(defaultextension='.docx',filetypes=[('Word document','*.docx')])
        if not fn:return
        d=Document()
        for pi,p in enumerate(self.pages):
            if pi: d.add_page_break()
            for t in p.texts:
                txt=t.get('1.0','end-1c')
                if txt: d.add_paragraph(txt)
        d.save(fn); self.status.config(text='DOCX exported')

    def hexrgb(self,h):
        h=h.lstrip('#'); return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))
    def close(self):
        if self.dirty and not messagebox.askyesno('Exit','Exit without saving?'): return
        self.root.destroy()

if __name__ == '__main__':
    root=tk.Tk()
    App(root)
    root.mainloop()
