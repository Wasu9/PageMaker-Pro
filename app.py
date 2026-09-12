import json, os, tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser

# IMPORTANT: the professional DTP interaction layer must be loaded explicitly
# in the frozen Windows application. PyInstaller's hidden-import list alone
# does not execute sitecustomize.py, so without this import the EXE falls back
# to the old multi-page prototype UI. sitecustomize installs the canonical DTP
# model, PageMaker-style workspace, page navigation and frame interaction.
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
        self.page.configure(highlightthickness=1 if border else 0,
            highlightbackground=self.app.border_color() if border else bg,
            highlightcolor=self.app.border_color() if border else bg)
        base_size = max(6, int(round(s['size'] * z)))
        label_size = max(7, int(round(max(8, s['size'] - 1) * z)))
        if header:
            tk.Label(self.page, text=header, bg=bg, fg=fg, font=(s['font'], label_size)).place(relx=.5, y=max(5, int(14*z)), anchor='n')
        if watermark:
            tk.Label(self.page, text=watermark, bg=bg, fg='#d0d0d0', font=('Segoe UI', max(12, int(34*z)), 'bold')).place(relx=.5, rely=.5, anchor='center')
        if footer:
            tk.Label(self.page, text=footer + '    Page ' + str(self.number), bg=bg, fg=fg, font=(s['font'], label_size)).place(relx=.5, y=ph-max(5, int(18*z)), anchor='s')
        top = max(35, int(48*z)); bottom = max(top + 40, ph - max(35, int(52*z))); th = max(40, bottom - top)
        for i in range(n):
            x = margin + i * (cw + gap)
            t = tk.Text(self.page, wrap='word', undo=True, font=(s['font'], base_size), bg=bg, fg=fg,
                        insertbackground=fg, relief='flat', bd=0, padx=max(2, int(3*z)), pady=max(1, int(2*z)), selectbackground='#4a78c2')
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
            if i >= len(self.texts): break
            if isinstance(data, str): self.texts[i].insert('1.0', data)
            elif isinstance(data, dict): self.texts[i].insert('1.0', data.get('text',''))
        self.saved = []

    def capture(self): return [t.get('1.0','end-1c') for t in self.texts]

class App:
    def __init__(self, root):
        self.root = root; self.settings = dict(DEFAULTS); self.theme = THEMES['light']; self.pages = []
        self.active = None; self.filename = None; self.dirty = False; self._reflow_busy = False; self._zoom = self.settings['zoom']
        root.title(APP_TITLE); root.geometry('1450x920'); root.minsize(1100,700); self.ui(); self.apply_theme('light',False); self.add_page(False)
        root.after(150,self.fit); root.protocol('WM_DELETE_WINDOW',self.close)
    def page_bg(self): return '#000000' if self.settings.get('theme') == 'invert' else self.settings.get('page_color','#fff')
    def page_fg(self): return '#ffffff' if self.settings.get('theme') == 'invert' else '#111111'
    def border_color(self): return '#dddddd' if self.settings.get('theme') == 'invert' else '#222222'
    def ui(self):
        self.root.option_add('*tearOff',False); m=tk.Menu(self.root); self.root.config(menu=m)
        menus={'File':[('New',self.new),('Open…',self.open),('Save',self.save),('Save As…',self.save_as),None,('Export PDF…',self.export_pdf),('Export DOCX…',self.export_docx),None,('Exit',self.close)],'Edit':[('Undo',self.undo),('Redo',self.redo),None,('Find & Replace',self.find_replace)],'Insert':[('Text Frame',self.text_tool),('Image…',self.image),('Math / Symbol…',self.math),('Table…',self.table)],'Layout':[('Page Settings…',self.page_settings),('A-Master…',self.master),('Add Page',lambda:self.add_page()),('Remove Page',self.remove_page)],'Type':[('Bold',lambda:self.tag('bold')),('Italic',lambda:self.tag('italic')),('Superscript',lambda:self.tag('sup')),('Subscript',lambda:self.tag('sub')),('Clear Formatting',self.clear_fmt)],'View':[('Fit Page',self.fit),('100% Zoom',lambda:self.zoom(1)),('Light',lambda:self.apply_theme('light')),('Gray',lambda:self.apply_theme('gray')),('Dark',lambda:self.apply_theme('dark')),('Dark Invert',lambda:self.apply_theme('invert'))]}
        for name,items in menus.items():
            q=tk.Menu(m)
            for item in items:
                if item is None:q.add_separator()
                else:q.add_command(label=item[0],command=item[1])
            m.add_cascade(label=name,menu=q)
        top=tk.Frame(self.root,height=44);top.pack(fill='x');self.top=top
        for label,cmd in [('New',self.new),('Open',self.open),('Save',self.save),('Add Page',self.add_page),('Master',self.master),('PDF',self.export_pdf)]:tk.Button(top,text=label,command=cmd,relief='flat',padx=9).pack(side='left',pady=5,padx=2)
        tk.Label(top,text='Font').pack(side='left',padx=5);self.font=ttk.Combobox(top,width=14,values=['Noto Sans','Arial','Times New Roman','Calibri','Mangal','Nirmala UI'],state='readonly');self.font.set('Noto Sans');self.font.pack(side='left');self.font.bind('<<ComboboxSelected>>',lambda e:self.font_apply())
        tk.Label(top,text='Size').pack(side='left',padx=4);self.sz=ttk.Spinbox(top,from_=7,to=72,width=4);self.sz.set(12);self.sz.pack(side='left');self.sz.bind('<Return>',lambda e:self.font_apply())
        tk.Label(top,text='Flow').pack(side='left',padx=6);self.flow=ttk.Combobox(top,width=24,values=['Column → Column → Next Page','Same Column → Next Page','Ask Me'],state='readonly');self.flow.set('Column → Column → Next Page');self.flow.pack(side='left');self.flow.bind('<<ComboboxSelected>>',lambda e:self.set_flow())
        tk.Label(top,text='Zoom').pack(side='left',padx=6);self.zoom_box=ttk.Combobox(top,width=10,values=['50%','60%','67%','72%','80%','90%','100%','Fit Page'],state='readonly');self.zoom_box.set('Fit Page');self.zoom_box.pack(side='left');self.zoom_box.bind('<<ComboboxSelected>>',lambda e:self.set_zoom(self.zoom_box.get()));tk.Label(top,text='Ctrl + Mouse Wheel = Zoom').pack(side='left',padx=12)
        left=tk.Frame(self.root,width=78);left.pack(side='left',fill='y');self.left=left
        for txt,cmd in [('↖\nSelect',lambda:None),('T\nText',self.text_tool),('▣\nImage',self.image),('∑\nMath',self.math),('▤\nTable',self.table),('M\nMaster',self.master),('＋\nPage',self.add_page)]:tk.Button(left,text=txt,command=cmd,relief='flat',padx=2,pady=8).pack(fill='x',padx=6,pady=2)
        work=tk.Frame(self.root);work.pack(side='left',fill='both',expand=True);self.ruler_corner=tk.Frame(work,width=24,height=22);self.ruler_corner.grid(row=0,column=0);self.hruler=tk.Canvas(work,height=22,highlightthickness=0);self.hruler.grid(row=0,column=1,sticky='ew');self.vruler=tk.Canvas(work,width=24,highlightthickness=0);self.vruler.grid(row=1,column=0,sticky='ns');self.canvas=tk.Canvas(work,highlightthickness=0);self.canvas.grid(row=1,column=1,sticky='nsew');work.grid_rowconfigure(1,weight=1);work.grid_columnconfigure(1,weight=1)
        vsb=ttk.Scrollbar(work,orient='vertical',command=self.canvas.yview);hsb=ttk.Scrollbar(work,orient='horizontal',command=self.canvas.xview);vsb.grid(row=1,column=2,sticky='ns');hsb.grid(row=2,column=1,sticky='ew');self.canvas.configure(yscrollcommand=vsb.set,xscrollcommand=hsb.set)
        self.root.bind_all('<MouseWheel>',self._global_wheel,add='+');self.root.bind_all('<Button-4>',lambda e:self._global_wheel(e,-1),add='+');self.root.bind_all('<Button-5>',lambda e:self._global_wheel(e,1),add='+');self.root.bind_all('<Next>',lambda e:self._workspace_page(1),add='+');self.root.bind_all('<Prior>',lambda e:self._workspace_page(-1),add='+');self.root.bind_all('<Home>',lambda e:self._workspace_home(),add='+');self.root.bind_all('<End>',lambda e:self._workspace_end(),add='+')
        self.host=tk.Frame(self.canvas);self.host_window=self.canvas.create_window((20,10),window=self.host,anchor='nw');self.host.bind('<Configure>',lambda e:self._canvas_layout());self.canvas.bind('<Configure>',lambda e:self._canvas_layout());self.status=tk.Label(self.root,text='Ready',anchor='w',padx=10);self.status.pack(side='bottom',fill='x')
    def _global_wheel(self,event,direction=None):
        ctrl=bool(getattr(event,'state',0)&0x0004)
        if ctrl:
            delta=getattr(event,'delta',0);step=1.10 if ((delta>0) if direction is None else direction<0) else 1/1.10;self.zoom(self._zoom*step);return 'break'
        if direction is None:
            delta=getattr(event,'delta',0)
            if not delta:return 'break'
            direction=-1 if delta>0 else 1;steps=max(1,min(6,int(abs(delta)/120)))
        else:steps=3
        try:self.canvas.yview_scroll(direction*steps,'units')
        except tk.TclError:pass
        return 'break'
    def _text_wheel(self,event,widget,direction=None):
        ctrl=bool(getattr(event,'state',0)&0x0004)
        if ctrl:
            delta=getattr(event,'delta',0);step=1.10 if ((delta>0) if direction is None else direction<0) else 1/1.10;self.zoom(self._zoom*step);return 'break'
        if direction is None:
            delta=getattr(event,'delta',0)
            if not delta:return 'break'
            direction=-1 if delta>0 else 1;steps=max(1,min(6,int(abs(delta)/120)))
        else:steps=3
        try:widget.yview_scroll(direction*steps,'units')
        except tk.TclError:pass
        return 'break'
    def _canvas_layout(self):
        try:self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        except Exception:pass
    def activate(self,w):self.active=w
    def changed(self,w=None):self.dirty=True;self.root.after(80,self.reflow)
    def paste(self,w=None):
        t=w or self.active
        if not t:return 'break'
        try:t.insert('insert',self.root.clipboard_get());self.changed(t);return 'break'
        except Exception:return None
    def tag(self,name):
        if not self.active:return
        try:self.active.tag_add(name,'sel.first','sel.last')
        except tk.TclError:self.active.tag_configure(name)
        self.changed()
    def clear_fmt(self):
        if self.active:
            for tag in ('bold','italic','sup','sub'):self.active.tag_remove(tag,'sel.first','sel.last')
            self.changed()
    def font_apply(self):self.changed()
    def set_flow(self):self.settings['flow_mode']={'Column → Column → Next Page':'next_column','Same Column → Next Page':'same_column','Ask Me':'ask'}.get(self.flow.get(),'next_column');self.changed()
    def text_tool(self):pass
    def math(self):pass
    def table(self):pass
    def image(self):pass
    def page_settings(self):pass
    def master(self):pass
    def add_page(self,mark=True):
        p=Page(self,len(self.pages)+1);p.frame.pack(side='left',padx=8,pady=8);self.pages.append(p);self.root.update_idletasks();self._canvas_layout()
        if mark:self.changed()
        return p
    def remove_page(self):
        if len(self.pages)>1:self.pages.pop().frame.destroy();self.renumber();self.changed();self._canvas_layout()
    def renumber(self):
        for i,p in enumerate(self.pages,1):p.number=i
    def rebuild_pages(self):
        for p in self.pages:p.saved=p.capture();p.rebuild()
        self.root.update_idletasks();self._canvas_layout();self.reflow()
    def capture(self):return [p.capture() for p in self.pages]
    def new(self):
        if self.dirty and not messagebox.askyesno('New','Discard unsaved changes?'):return
        for p in self.pages:p.frame.destroy()
        self.pages=[];self.settings=dict(DEFAULTS);self._zoom=self.settings['zoom'];self.filename=None;self.dirty=False;self.add_page(False);self.fit();self.status.config(text='New document')
    def save(self):
        if not self.filename:return self.save_as()
        with open(self.filename,'w',encoding='utf-8') as f:json.dump({'settings':self.settings,'pages':self.capture()},f,ensure_ascii=False,indent=2)
        self.dirty=False;self.status.config(text='Saved: '+os.path.basename(self.filename))
    def save_as(self):
        fn=filedialog.asksaveasfilename(defaultextension='.upm',filetypes=[('PageMaker Pro','*.upm'),('JSON','*.json')]);
        if fn:self.filename=fn;self.save()
    def open(self):
        fn=filedialog.askopenfilename(filetypes=[('PageMaker Pro','*.upm *.json'),('All files','*.*')]);
        if not fn:return
        try:
            with open(fn,'r',encoding='utf-8') as f:d=json.load(f)
            for p in self.pages:p.frame.destroy()
            self.pages=[];self.settings.update(d.get('settings',{}));self._zoom=float(self.settings.get('zoom',.72))
            for data in d.get('pages',[]):p=self.add_page(False);p.saved=data;p.rebuild()
            if not self.pages:self.add_page(False)
            self.filename=fn;self.dirty=False;self.status.config(text='Opened: '+os.path.basename(fn));self.sync_controls();self.fit()
        except Exception as e:messagebox.showerror('Open',str(e))
    def sync_controls(self):self.font.set(self.settings.get('font','Noto Sans'));self.sz.set(self.settings.get('size',12));self.flow.set({'next_column':'Column → Column → Next Page','same_column':'Same Column → Next Page','ask':'Ask Me'}.get(self.settings.get('flow_mode'),'Column → Column → Next Page'))
    def undo(self):
        if self.active:
            try:self.active.edit_undo()
            except tk.TclError:pass
    def redo(self):
        if self.active:
            try:self.active.edit_redo()
            except tk.TclError:pass
    def find_replace(self):pass
    def apply_theme(self,name,mark=True):
        if name not in THEMES:name='light'
        self.theme=THEMES[name];self.settings['theme']=name;self.root.configure(bg=self.theme[0]);self.top.configure(bg=self.theme[2]);self.left.configure(bg=self.theme[1]);self.status.configure(bg=self.theme[1],fg=self.theme[3]);self.canvas.configure(bg=self.theme[4]);self.host.configure(bg=self.theme[4]);self.draw_rulers();self.rebuild_pages()
        if mark:self.changed()
    def set_zoom(self,value):
        if value=='Fit Page':self.fit();return
        try:self.zoom(float(value.strip('%'))/100.0)
        except Exception:pass
    def zoom(self,z):
        old=self._zoom;z=max(.35,min(1.50,float(z)))
        if abs(z-old)<.001:return
        self._zoom=z;self.settings['zoom']=z;self.rebuild_pages();self.zoom_box.set(f'{round(z*100)}%') if hasattr(self,'zoom_box') else None;self.status.config(text=f'Zoom {round(z*100)}%')
    def fit(self):
        self.root.update_idletasks();aw=max(500,self.canvas.winfo_width()-70);ah=max(400,self.canvas.winfo_height()-55);z=min(aw/self.settings['page_w'],ah/self.settings['page_h'],1.0);self._zoom=max(.35,z);self.settings['zoom']=self._zoom
        if hasattr(self,'zoom_box'):self.zoom_box.set('Fit Page')
        self.rebuild_pages();self.status.config(text=f'Fit Page — {round(self._zoom*100)}%')
    def export_pdf(self):pass
    def export_docx(self):pass
    def hexrgb(self,h):h=h.lstrip('#');return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))
    def close(self):
        if self.dirty and not messagebox.askyesno('Exit','Exit without saving?'):return
        self.root.destroy()

# Phase 25: fix the editor interactions requested for NEET/JEE paper production.
try:
    import phase25_editor_fixes
    phase25_editor_fixes.install(App)
except Exception:
    phase25_editor_fixes = None

if __name__ == '__main__':
    root=tk.Tk();App(root);root.mainloop()
