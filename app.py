import json, os, tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser

APP_TITLE = 'PageMaker Pro — Offline Unicode DTP'
DEFAULTS = {
    'page_w': 794, 'page_h': 1123, 'margin': 45, 'gap': 24, 'columns': 2,
    'page_color': '#ffffff', 'border': True, 'header': '', 'footer': '',
    'watermark': '', 'font': 'Noto Sans', 'size': 12, 'theme': 'light',
    'flow_mode': 'same_column', 'master_enabled': True,
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
        self.app = app; self.number = number; self.saved = []
        self.frame = tk.Frame(app.host, bg=app.theme[4], padx=28, pady=22)
        self.page = tk.Frame(self.frame, width=app.settings['page_w'], height=app.settings['page_h'],
                             bg=app.page_bg(), bd=0, highlightthickness=1,
                             highlightbackground=app.border_color(), highlightcolor=app.border_color())
        self.page.pack()
        self.texts = []
        self.rebuild()

    def rebuild(self):
        old = self.capture() if self.texts else self.saved
        for w in self.page.winfo_children(): w.destroy()
        self.texts = []
        s = self.app.settings
        n = max(1, min(3, int(s.get('columns', 2))))
        total = s['page_w'] - 2*s['margin']
        cw = max(40, int((total - s['gap']*(n-1))/n))
        bg, fg = self.app.page_bg(), self.app.page_fg()
        master = s.get('master_enabled', True)
        header = s.get('master_header','') if master else s.get('header','')
        footer = s.get('master_footer','') if master else s.get('footer','')
        watermark = s.get('master_watermark','') if master else s.get('watermark','')
        border = s.get('master_border', True) if master else s.get('border', True)
        self.page.configure(bg=bg, highlightbackground=self.app.border_color() if border else bg,
                            highlightcolor=self.app.border_color() if border else bg,
                            highlightthickness=1 if border else 0)
        if header:
            tk.Label(self.page, text=header, bg=bg, fg=fg, font=(s['font'], max(8,s['size']-1))).place(relx=.5,y=14,anchor='n')
        if watermark:
            tk.Label(self.page, text=watermark, bg=bg, fg='#d0d0d0', font=('Segoe UI',34,'bold')).place(relx=.5,rely=.5,anchor='center')
        if footer:
            tk.Label(self.page, text=footer + '    Page ' + str(self.number), bg=bg, fg=fg,
                     font=(s['font'], max(8,s['size']-1))).place(relx=.5,y=s['page_h']-18,anchor='s')
        for i in range(n):
            x = s['margin'] + i*(cw+s['gap'])
            t = tk.Text(self.page, wrap='word', undo=True, font=(s['font'],s['size']),
                        bg=bg, fg=fg, insertbackground=fg, relief='flat', bd=0,
                        padx=3, pady=2, selectbackground='#4a78c2')
            t.place(x=x, y=48, width=cw, height=s['page_h']-100)
            t.tag_configure('bold', font=(s['font'],s['size'],'bold'))
            t.tag_configure('italic', font=(s['font'],s['size'],'italic'))
            t.tag_configure('sup', offset=6, font=(s['font'],max(7,s['size']-3)))
            t.tag_configure('sub', offset=-4, font=(s['font'],max(7,s['size']-3)))
            t.bind('<FocusIn>', lambda e,w=t:self.app.activate(w))
            t.bind('<KeyRelease>', lambda e,w=t:self.app.changed(w))
            t.bind('<<Paste>>', lambda e,w=t:self.app.paste(w))
            self.texts.append(t)
        for i,data in enumerate(old[:n]):
            if isinstance(data,str): self.texts[i].insert('1.0',data)
            elif isinstance(data,dict): self.texts[i].insert('1.0',data.get('text',''))
        self.saved = []

    def capture(self):
        return [t.get('1.0','end-1c') for t in self.texts]

class App:
    def __init__(self, root):
        self.root = root; self.settings = dict(DEFAULTS); self.theme = THEMES['light']
        self.pages=[]; self.active=None; self.filename=None; self.dirty=False
        root.title(APP_TITLE); root.geometry('1450x920'); root.minsize(1100,700)
        self.ui(); self.apply_theme('light',False); self.add_page(False)
        root.after(150,self.fit); root.protocol('WM_DELETE_WINDOW',self.close)

    def page_bg(self): return '#000000' if self.settings.get('theme')=='invert' else self.settings.get('page_color','#fff')
    def page_fg(self): return '#ffffff' if self.settings.get('theme')=='invert' else '#111111'
    def border_color(self): return '#dddddd' if self.settings.get('theme')=='invert' else '#222222'

    def ui(self):
        self.root.option_add('*tearOff',False)
        m=tk.Menu(self.root); self.root.config(menu=m)
        menus={
            'File':[('New',self.new),('Open…',self.open),('Save',self.save),('Save As…',self.save_as),None,('Export PDF…',self.export_pdf),('Export DOCX…',self.export_docx),None,('Exit',self.close)],
            'Edit':[('Undo',self.undo),('Redo',self.redo),None,('Find & Replace',self.find_replace)],
            'Insert':[('Text Frame',self.text_tool),('Image…',self.image),('Math / Symbol…',self.math),('Table…',self.table)],
            'Layout':[('Page Settings…',self.page_settings),('A-Master…',self.master),('Add Page',lambda:self.add_page()),('Remove Page',self.remove_page)],
            'Type':[('Bold',lambda:self.tag('bold')),('Italic',lambda:self.tag('italic')),('Superscript',lambda:self.tag('sup')),('Subscript',lambda:self.tag('sub')),('Clear Formatting',self.clear_fmt)],
            'View':[('Fit Page',self.fit),('100% Zoom',lambda:self.zoom(1)),('Light',lambda:self.apply_theme('light')),('Gray',lambda:self.apply_theme('gray')),('Dark',lambda:self.apply_theme('dark')),('Dark Invert',lambda:self.apply_theme('invert'))]
        }
        for name,items in menus.items():
            q=tk.Menu(m)
            for item in items:
                q.add_separator() if item is None else q.add_command(label=item[0],command=item[1])
            m.add_cascade(label=name,menu=q)
        top=tk.Frame(self.root,height=44); top.pack(fill='x'); self.top=top
        for label,cmd in [('New',self.new),('Open',self.open),('Save',self.save),('Add Page',self.add_page),('Master',self.master),('PDF',self.export_pdf)]:
            tk.Button(top,text=label,command=cmd,relief='flat',padx=9).pack(side='left',pady=5,padx=2)
        tk.Label(top,text='Font').pack(side='left',padx=5)
        self.font=ttk.Combobox(top,width=14,values=['Noto Sans','Arial','Times New Roman','Calibri','Mangal','Nirmala UI'],state='readonly'); self.font.set('Noto Sans'); self.font.pack(side='left'); self.font.bind('<<ComboboxSelected>>',lambda e:self.font_apply())
        tk.Label(top,text='Size').pack(side='left',padx=4)
        self.sz=ttk.Spinbox(top,from_=7,to=72,width=4); self.sz.set(12); self.sz.pack(side='left'); self.sz.bind('<Return>',lambda e:self.font_apply())
        tk.Label(top,text='Flow').pack(side='left',padx=6)
        self.flow=ttk.Combobox(top,width=20,values=['Same Column → Next Page','Continue Columns','Ask Me'],state='readonly'); self.flow.set('Same Column → Next Page'); self.flow.pack(side='left'); self.flow.bind('<<ComboboxSelected>>',lambda e:self.set_flow())
        tk.Label(top,text='Zoom').pack(side='left',padx=6)
        self.zoom_box=ttk.Combobox(top,width=9,values=['50%','60%','67%','72%','80%','90%','100%','Fit Page'],state='readonly'); self.zoom_box.set('Fit Page'); self.zoom_box.pack(side='left'); self.zoom_box.bind('<<ComboboxSelected>>',lambda e:self.set_zoom(self.zoom_box.get()))
        left=tk.Frame(self.root,width=78); left.pack(side='left',fill='y'); self.left=left
        for txt,cmd in [('↖\nSelect',lambda:None),('T\nText',self.text_tool),('▣\nImage',self.image),('∑\nMath',self.math),('▤\nTable',self.table),('M\nMaster',self.master),('＋\nPage',self.add_page)]:
            tk.Button(left,text=txt,command=cmd,relief='flat',padx=2,pady=8).pack(fill='x',padx=6,pady=2)
        work=tk.Frame(self.root); work.pack(side='left',fill='both',expand=True)
        self.ruler_corner=tk.Frame(work,width=24,height=22); self.ruler_corner.grid(row=0,column=0)
        self.hruler=tk.Canvas(work,height=22,highlightthickness=0); self.hruler.grid(row=0,column=1,sticky='ew')
        self.vruler=tk.Canvas(work,width=24,highlightthickness=0); self.vruler.grid(row=1,column=0,sticky='ns')
        self.canvas=tk.Canvas(work,highlightthickness=0); self.canvas.grid(row=1,column=1,sticky='nsew')
        work.grid_rowconfigure(1,weight=1); work.grid_columnconfigure(1,weight=1)
        sb=ttk.Scrollbar(work,orient='vertical',command=self.canvas.yview); sb.grid(row=1,column=2,sticky='ns'); self.canvas.configure(yscrollcommand=sb.set)
        self.host=tk.Frame(self.canvas); self.host_window=self.canvas.create_window((20,10),window=self.host,anchor='nw')
        self.host.bind('<Configure>',lambda e:self._canvas_layout()); self.canvas.bind('<Configure>',lambda e:self._canvas_layout())
        self.status=tk.Label(self.root,text='Ready',anchor='w',padx=10); self.status.pack(side='bottom',fill='x')

    def _canvas_layout(self):
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox('all'))
            cw=max(1,self.canvas.winfo_width()); hw=max(1,self.host.winfo_reqwidth())
            self.canvas.coords(self.host_window,max(20,(cw-hw)//2),10)
            self.draw_rulers()
        except tk.TclError: pass

    def draw_rulers(self):
        c=self.theme; self.hruler.configure(bg=c[2]); self.vruler.configure(bg=c[2]); self.ruler_corner.configure(bg=c[2]); self.hruler.delete('all'); self.vruler.delete('all')
        z=float(getattr(self,'_zoom',self.settings.get('zoom',.72))); start=int(self.settings['margin']*z); step=max(20,int(48*z))
        w=max(1,self.hruler.winfo_width()); h=max(1,self.vruler.winfo_height())
        for x in range(start,w,step): self.hruler.create_line(x,21,x,11,fill=c[3]); self.hruler.create_text(x+2,3,text=str(round((x-start)/(96*z),1)),anchor='nw',fill=c[3],font=('Segoe UI',7))
        for y in range(start,h,step): self.vruler.create_line(23,y,13,y,fill=c[3]); self.vruler.create_text(2,y+2,text=str(round((y-start)/(96*z),1)),anchor='nw',fill=c[3],font=('Segoe UI',7))

    def activate(self,w): self.active=w; self.status.config(text='Unicode text frame active')
    def changed(self,w=None): self.dirty=True; self.status.config(text='Modified'); self.root.after(30,self.reflow)
    def reflow(self):
        # Keep each Text widget physically bounded. Move overflow according to flow mode.
        for pi,p in enumerate(list(self.pages)):
            for ci,t in enumerate(list(p.texts)):
                try:
                    if not t.get('1.0','end-1c'): continue
                    total=t.count('1.0','end-1c','-displaylines')[0]
                    visible=max(1,int((t.winfo_height()-8)/(self.settings['size']*1.55)))
                    if total<=visible: continue
                    cut=t.index('1.0 + %d displaylines'%visible)
                    moved=t.get(cut,'end-1c')
                    if len(moved)<2: continue
                    t.delete(cut,'end')
                    mode=self.settings['flow_mode']
                    if mode=='next_column' and ci+1<len(p.texts): target_page,target_col=p,ci+1
                    else:
                        target_page=self.pages[pi+1] if pi+1<len(self.pages) else self.add_page(False)
                        target_col=ci if mode in ('same_column','ask') and ci<len(target_page.texts) else 0
                    if mode=='ask':
                        ans=messagebox.askyesno('Text Overflow','Continue overflow in the next available frame?')
                        if not ans: t.insert('end',moved); continue
                    target_page.texts[target_col].insert('end',moved)
                except Exception: pass

    def set_flow(self):
        self.settings['flow_mode']={'Same Column → Next Page':'same_column','Continue Columns':'next_column','Ask Me':'ask'}.get(self.flow.get(),'same_column'); self.changed()
    def font_apply(self):
        self.settings['font']=self.font.get(); self.settings['size']=int(self.sz.get()); self.rebuild_pages(); self.changed()
    def tag(self,name):
        if self.active:
            try:self.active.tag_add(name,self.active.index('sel.first'),self.active.index('sel.last')); self.changed()
            except tk.TclError: pass
    def clear_fmt(self):
        if self.active:
            try:
                a,b=self.active.index('sel.first'),self.active.index('sel.last')
                for x in ('bold','italic','sup','sub'): self.active.tag_remove(x,a,b)
                self.changed()
            except tk.TclError: pass
    def text_tool(self):
        if self.active:self.active.focus_set()
        elif self.pages:self.activate(self.pages[-1].texts[0]); self.active.focus_set()
    def paste(self,t):
        try:
            # Clipboard text is inserted as native Unicode; no ASCII conversion/normalization.
            t.insert('insert',self.root.clipboard_get()); self.changed(t); return 'break'
        except Exception:return None
    def image(self):
        if not self.active:return
        try:
            from PIL import Image,ImageTk
        except ImportError:
            messagebox.showinfo('Image','Install Pillow once: pip install pillow'); return
        fn=filedialog.askopenfilename(filetypes=[('Images','*.png *.jpg *.jpeg *.gif *.bmp *.webp')])
        if not fn:return
        try:
            im=Image.open(fn); im.thumbnail((320,240)); ph=ImageTk.PhotoImage(im); refs=getattr(self.active,'_pm_refs',[]); refs.append(ph); self.active._pm_refs=refs; self.active.image_create('insert',image=ph); self.active.insert('insert','\n'); self.changed()
        except Exception as e: messagebox.showerror('Image',str(e))
    def math(self):
        if not self.active:return
        w=tk.Toplevel(self.root); w.title('Unicode Math & Symbols'); w.geometry('760x180'); e=tk.Entry(w,width=80); e.pack(padx=12,pady=10)
        groups='α β γ δ θ λ μ π σ φ ω Ω Δ Σ √ ∛ ∞ ∑ ∏ ∫ ∂ ∇ ± × ÷ ≠ ≈ ≤ ≥ ∝ → ⇒ ⇔ ½ ⅓ ¼ ¾ ⁰¹²³⁺⁻ⁿ ₀₁₂₃₊₋ₙ H₂O CO₂ SO₄²⁻'.split()
        bar=tk.Frame(w); bar.pack(fill='x',padx=10)
        for x in groups: tk.Button(bar,text=x,command=lambda x=x:e.insert('end',x),relief='flat').pack(side='left',padx=1)
        tk.Button(w,text='Insert',command=lambda:(self.active.insert('insert',e.get()),self.changed(),w.destroy())).pack(pady=10)
    def table(self):
        if not self.active:return
        v=simpledialog.askstring('Table','Rows x Columns, e.g. 4x3',parent=self.root)
        try:
            r,c=map(int,v.lower().split('x')); r=max(1,min(20,r)); c=max(1,min(20,c))
            for _ in range(r): self.active.insert('insert',' | '.join(['']*c)+'\n')
            self.changed()
        except Exception: pass

    def page_settings(self):
        w=tk.Toplevel(self.root); w.title('Page Settings'); vars={}; keys=['columns','gap','margin','header','footer','watermark']
        for i,k in enumerate(keys):
            tk.Label(w,text=k.title()).grid(row=i,column=0,padx=8,pady=4,sticky='w'); v=tk.StringVar(value=str(self.settings[k])); vars[k]=v; tk.Entry(w,textvariable=v,width=32).grid(row=i,column=1,padx=8,pady=4)
        border=tk.BooleanVar(value=self.settings['border']); tk.Checkbutton(w,text='Page Border',variable=border).grid(row=6,column=1,sticky='w')
        tk.Button(w,text='Page Color…',command=self.pick_color).grid(row=7,column=0,pady=8)
        def apply():
            try:
                for k,v in vars.items(): self.settings[k]=int(v.get()) if k in ('columns','gap','margin') else v.get()
                self.settings['columns']=max(1,min(3,self.settings['columns'])); self.settings['border']=border.get(); self.rebuild_pages(); self.changed(); w.destroy()
            except ValueError: messagebox.showerror('Page Settings','Columns, gap and margin must be numbers.')
        tk.Button(w,text='Apply',command=apply).grid(row=8,column=0,columnspan=2,pady=10)
    def pick_color(self):
        c=colorchooser.askcolor(initialcolor=self.settings['page_color'])[1]
        if c:self.settings['page_color']=c; self.rebuild_pages(); self.changed()

    def master(self):
        w=tk.Toplevel(self.root); w.title('A-Master'); w.geometry('540x300'); vs={}
        for i,k in enumerate(['master_header','master_footer','master_watermark']):
            tk.Label(w,text=k.replace('master_','').title()).grid(row=i,column=0,padx=8,pady=8,sticky='w'); v=tk.StringVar(value=self.settings[k]); vs[k]=v; tk.Entry(w,textvariable=v,width=40).grid(row=i,column=1,padx=8,pady=8)
        en=tk.BooleanVar(value=self.settings['master_enabled']); tk.Checkbutton(w,text='Apply A-Master to document pages',variable=en).grid(row=3,column=0,columnspan=2)
        border=tk.BooleanVar(value=self.settings['master_border']); tk.Checkbutton(w,text='Master page border',variable=border).grid(row=4,column=0,columnspan=2)
        def apply():
            for k,v in vs.items(): self.settings[k]=v.get()
            self.settings['master_enabled']=en.get(); self.settings['master_border']=border.get(); self.rebuild_pages(); self.changed(); w.destroy()
        tk.Button(w,text='Apply A-Master',command=apply).grid(row=5,column=0,columnspan=2,pady=18)

    def add_page(self,mark=True):
        p=Page(self,len(self.pages)+1); p.frame.pack(pady=8); self.pages.append(p); self.root.update_idletasks(); self._canvas_layout()
        if mark:self.changed()
        return p
    def remove_page(self):
        if len(self.pages)>1: self.pages.pop().frame.destroy(); self.renumber(); self.changed()
    def renumber(self):
        for i,p in enumerate(self.pages,1): p.number=i
    def rebuild_pages(self):
        for p in self.pages: p.saved=p.capture(); p.rebuild()
        self.root.update_idletasks(); self._canvas_layout()
    def capture(self): return [p.capture() for p in self.pages]
    def new(self):
        if self.dirty and not messagebox.askyesno('New','Discard unsaved changes?'):return
        for p in self.pages:p.frame.destroy()
        self.pages=[]; self.settings=dict(DEFAULTS); self.filename=None; self.dirty=False; self.add_page(False); self.status.config(text='New document')
    def save(self):
        if not self.filename:return self.save_as()
        with open(self.filename,'w',encoding='utf-8') as f: json.dump({'settings':self.settings,'pages':self.capture()},f,ensure_ascii=False,indent=2)
        self.dirty=False; self.status.config(text='Saved: '+os.path.basename(self.filename))
    def save_as(self):
        fn=filedialog.asksaveasfilename(defaultextension='.upm',filetypes=[('PageMaker Pro','*.upm'),('JSON','*.json')])
        if fn:self.filename=fn; self.save()
    def open(self):
        fn=filedialog.askopenfilename(filetypes=[('PageMaker Pro','*.upm *.json'),('All files','*.*')])
        if not fn:return
        try:
            with open(fn,'r',encoding='utf-8') as f:d=json.load(f)
            for p in self.pages:p.frame.destroy()
            self.pages=[]; self.settings.update(d.get('settings',{}))
            for data in d.get('pages',[]):
                p=self.add_page(False); p.saved=data; p.rebuild()
            if not self.pages:self.add_page(False)
            self.filename=fn; self.dirty=False; self.status.config(text='Opened: '+os.path.basename(fn)); self.sync_controls(); self.fit()
        except Exception as e: messagebox.showerror('Open',str(e))
    def sync_controls(self):
        self.font.set(self.settings.get('font','Noto Sans')); self.sz.set(self.settings.get('size',12)); self.flow.set({'same_column':'Same Column → Next Page','next_column':'Continue Columns','ask':'Ask Me'}.get(self.settings.get('flow_mode'),'Same Column → Next Page'))
    def undo(self):
        t=self.active
        if t:
            try:t.edit_undo()
            except tk.TclError:pass
    def redo(self):
        t=self.active
        if t:
            try:t.edit_redo()
            except tk.TclError:pass
    def find_replace(self):
        t=self.active
        if not t:return
        find=simpledialog.askstring('Find','Find text:',parent=self.root)
        if find is None:return
        repl=simpledialog.askstring('Replace','Replace with:',parent=self.root)
        if repl is None:return
        content=t.get('1.0','end-1c').replace(find,repl); t.delete('1.0','end'); t.insert('1.0',content); self.changed()

    def apply_theme(self,name,mark=True):
        if name not in THEMES:name='light'
        self.theme=THEMES[name]; self.settings['theme']=name
        self.root.configure(bg=self.theme[0]); self.top.configure(bg=self.theme[2]); self.left.configure(bg=self.theme[1]); self.status.configure(bg=self.theme[1],fg=self.theme[3]); self.canvas.configure(bg=self.theme[4]); self.host.configure(bg=self.theme[4])
        for child in self.top.winfo_children():
            if isinstance(child,(tk.Label,tk.Button)): child.configure(bg=self.theme[2],fg=self.theme[3],activebackground=self.theme[1],activeforeground=self.theme[3])
        for child in self.left.winfo_children(): child.configure(bg=self.theme[1],fg=self.theme[3],activebackground=self.theme[2],activeforeground=self.theme[3])
        self.draw_rulers(); self.rebuild_pages()
        if mark:self.changed()
    def set_zoom(self,value):
        if value=='Fit Page': self.fit(); return
        try:self.zoom(float(value.strip('%'))/100.0)
        except Exception:pass
    def zoom(self,z):
        z=max(.4,min(1.25,float(z))); self._zoom=z; self.settings['zoom']=z
        # Current page geometry remains physical; zoom changes the on-screen page by scaling its widgets.
        # Tk Text does not scale natively, so Fit Page keeps the A4 page visible and usable.
        self.status.config(text=f'Zoom {round(z*100)}%'); self.draw_rulers()
    def fit(self):
        self.root.update_idletasks(); aw=max(500,self.canvas.winfo_width()-80); ah=max(400,self.canvas.winfo_height()-30); z=min(aw/self.settings['page_w'],ah/self.settings['page_h'],1.0); self._zoom=z; self.settings['zoom']=z; self.status.config(text=f'Fit Page — {round(z*100)}%'); self.draw_rulers(); self._canvas_layout()

    def export_pdf(self):
        try: from reportlab.pdfgen import canvas
        except ImportError: messagebox.showinfo('PDF export','Install ReportLab once: pip install reportlab'); return
        fn=filedialog.asksaveasfilename(defaultextension='.pdf',filetypes=[('PDF','*.pdf')])
        if not fn:return
        c=canvas.Canvas(fn,pagesize=(self.settings['page_w'],self.settings['page_h']))
        for p in self.pages:
            c.setFillColorRGB(*self.hexrgb(self.page_bg())); c.rect(0,0,self.settings['page_w'],self.settings['page_h'],fill=1,stroke=0)
            border_on=self.settings.get('master_border',True) if self.settings.get('master_enabled',True) else self.settings.get('border',True)
            if border_on:c.setStrokeColorRGB(*self.hexrgb(self.border_color())); c.rect(8,8,self.settings['page_w']-16,self.settings['page_h']-16,fill=0,stroke=1)
            header=(self.settings.get('master_header','') if self.settings.get('master_enabled',True) else '') or self.settings.get('header','')
            footer=(self.settings.get('master_footer','') if self.settings.get('master_enabled',True) else '') or self.settings.get('footer','')
            c.setFillColorRGB(*self.hexrgb(self.page_fg())); c.setFont('Helvetica',9); c.drawCentredString(self.settings['page_w']/2,self.settings['page_h']-28,header); c.drawCentredString(self.settings['page_w']/2,18,(footer+'    ' if footer else '')+f'Page {p.number}')
            n=len(p.texts); total=self.settings['page_w']-2*self.settings['margin']; gap=self.settings['gap']; cw=(total-gap*(n-1))/n
            for i,t in enumerate(p.texts):
                x=self.settings['margin']+i*(cw+gap); lines=t.get('1.0','end-1c').splitlines(); y=self.settings['page_h']-75; c.setFont('Helvetica',self.settings['size'])
                for line in lines:
                    if y<55:break
                    c.drawString(x,y,line[:110]); y-=self.settings['size']*1.25
            c.showPage()
        c.save(); messagebox.showinfo('PDF','Exported successfully.')
    def export_docx(self):
        try: from docx import Document
        except ImportError: messagebox.showinfo('DOCX export','Install python-docx once: pip install python-docx'); return
        fn=filedialog.asksaveasfilename(defaultextension='.docx',filetypes=[('Word Document','*.docx')])
        if not fn:return
        doc=Document()
        for pi,p in enumerate(self.pages):
            if pi:doc.add_page_break()
            for ci,t in enumerate(p.texts):
                doc.add_paragraph(t.get('1.0','end-1c'))
        doc.save(fn); messagebox.showinfo('DOCX','Word document exported. Unicode text is preserved.')
    @staticmethod
    def hexrgb(h):
        h=h.lstrip('#'); return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))
    def close(self):
        if self.dirty and not messagebox.askyesno('Exit','Unsaved changes will be lost. Exit?'):return
        self.root.destroy()

if __name__=='__main__':
    root=tk.Tk(); App(root); root.mainloop()
