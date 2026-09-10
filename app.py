import json, os, tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser

APP_TITLE='PageMaker Pro — Offline Unicode DTP'
DEFAULTS={'page_w':794,'page_h':1123,'margin':45,'gap':24,'columns':2,'page_color':'#ffffff','border':True,'header':'','footer':'','watermark':'','font':'Noto Sans','size':12,'theme':'light','flow_mode':'same_column','master_enabled':True,'master_header':'','master_footer':'','master_watermark':'','master_border':True}
THEMES={'light':('#eef0f3','#f7f8fa','#fff','#202124','#d3d6da'),'gray':('#d5d7da','#e8e9eb','#ececee','#242628','#bfc2c6'),'dark':('#202225','#292c30','#292c30','#e8eaed','#15171a'),'invert':('#181a1d','#24272b','#24272b','#f5f6f7','#101113')}

class Page:
    def __init__(self,app,num):
        self.app,self.number=app,num; self.frame=tk.Frame(app.host,bg=app.theme[4],padx=28,pady=22); self.page=tk.Frame(self.frame,width=app.settings['page_w'],height=app.settings['page_h'],bg=app.page_bg(),highlightthickness=1); self.page.pack(); self.texts=[]; self.rebuild()
    def rebuild(self):
        for w in self.page.winfo_children(): w.destroy()
        self.texts=[]; s=self.app.settings; n=max(1,min(3,int(s['columns']))); total=s['page_w']-2*s['margin']; cw=int((total-s['gap']*(n-1))/n); fg=self.app.page_fg(); bg=self.app.page_bg()
        if s.get('master_enabled',True): header=s.get('master_header',''); footer=s.get('master_footer',''); wm=s.get('master_watermark',''); border=s.get('master_border',True)
        else: header=s.get('header',''); footer=s.get('footer',''); wm=s.get('watermark',''); border=s.get('border',True)
        if header: tk.Label(self.page,text=header,bg=bg,fg=fg).place(relx=.5,y=12,anchor='n')
        if wm: tk.Label(self.page,text=wm,bg=bg,fg='#d0d0d0',font=('Segoe UI',34,'bold')).place(relx=.5,rely=.5,anchor='center')
        if footer: tk.Label(self.page,text=footer,bg=bg,fg=fg).place(relx=.5,y=s['page_h']-18,anchor='s')
        if border: tk.Frame(self.page,bg=self.app.border_color()).place(x=7,y=7,width=s['page_w']-14,height=s['page_h']-14)
        for i in range(n):
            x=s['margin']+i*(cw+s['gap']); t=tk.Text(self.page,wrap='word',undo=True,font=(s['font'],s['size']),bg=bg,fg=fg,insertbackground=fg,relief='flat',bd=0,padx=3,pady=2)
            t.place(x=x,y=48,width=cw,height=s['page_h']-100); t.tag_configure('bold',font=(s['font'],s['size'],'bold')); t.tag_configure('italic',font=(s['font'],s['size'],'italic')); t.tag_configure('sup',offset=6,font=(s['font'],max(7,s['size']-3))); t.tag_configure('sub',offset=-4,font=(s['font'],max(7,s['size']-3))); t.bind('<FocusIn>',lambda e,w=t: self.app.activate(w)); t.bind('<KeyRelease>',lambda e,w=t:self.app.changed(w)); t.bind('<<Paste>>',lambda e,w=t:self.app.paste(w)); self.texts.append(t)
        old=getattr(self,'saved',[])
        for i,data in enumerate(old[:n]):
            if isinstance(data,str): self.texts[i].insert('1.0',data)
            elif isinstance(data,dict): self.texts[i].insert('1.0',data.get('text',''))
        self.saved=[]
    def capture(self): return [t.get('1.0','end-1c') for t in self.texts]

class App:
    def __init__(self,root):
        self.root=root; self.settings=dict(DEFAULTS); self.theme=THEMES['light']; self.pages=[]; self.active=None; self.filename=None; self.dirty=False; root.title(APP_TITLE); root.geometry('1450x920'); root.minsize(1100,700); self.ui(); self.apply_theme('light',False); self.add_page(False); root.after(100,self.fit)
    def page_bg(self): return '#000' if self.settings['theme']=='invert' else self.settings['page_color']
    def page_fg(self): return '#fff' if self.settings['theme']=='invert' else '#111'
    def border_color(self): return '#ddd' if self.settings['theme']=='invert' else '#222'
    def ui(self):
        self.root.option_add('*tearOff',False); m=tk.Menu(self.root); self.root.config(menu=m)
        menus={'File':[('New',self.new),('Open…',self.open),('Save',self.save),('Save As…',self.save_as),None,('Export PDF…',self.export_pdf),('Export DOCX…',self.export_docx),None,('Exit',self.close)],'Edit':[('Undo',self.undo),('Redo',self.redo),None,('Find & Replace',self.find_replace)],'Insert':[('Text Frame',self.text_tool),('Image…',self.image),('Math / Symbol…',self.math),('Table…',self.table)],'Layout':[('Page Settings…',self.page_settings),('A-Master…',self.master),('Add Page',lambda:self.add_page()),('Remove Page',self.remove_page)],'Type':[('Bold',lambda:self.tag('bold')),('Italic',lambda:self.tag('italic')),('Superscript',lambda:self.tag('sup')),('Subscript',lambda:self.tag('sub')),('Clear Formatting',self.clear_fmt)],'View':[('Fit Page',self.fit),('100% Zoom',lambda:self.zoom(1)),('Light',lambda:self.apply_theme('light')),('Gray',lambda:self.apply_theme('gray')),('Dark',lambda:self.apply_theme('dark')),('Dark Invert',lambda:self.apply_theme('invert'))]}
        for name,items in menus.items():
            q=tk.Menu(m); [q.add_separator() if x is None else q.add_command(label=x[0],command=x[1]) for x in items]; m.add_cascade(label=name,menu=q)
        top=tk.Frame(self.root,height=44); top.pack(fill='x'); self.top=top
        for label,cmd in [('New',self.new),('Open',self.open),('Save',self.save),('Add Page',self.add_page),('Master',self.master),('PDF',self.export_pdf)]: tk.Button(top,text=label,command=cmd,relief='flat',padx=9).pack(side='left',pady=5,padx=2)
        tk.Label(top,text='Font').pack(side='left',padx=5); self.font=ttk.Combobox(top,width=14,values=['Noto Sans','Arial','Times New Roman','Calibri','Mangal','Nirmala UI'],state='readonly'); self.font.set('Noto Sans'); self.font.pack(side='left'); self.font.bind('<<ComboboxSelected>>',lambda e:self.font_apply())
        tk.Label(top,text='Size').pack(side='left',padx=4); self.sz=ttk.Spinbox(top,from_=7,to=72,width=4); self.sz.set(12); self.sz.pack(side='left'); self.sz.bind('<Return>',lambda e:self.font_apply())
        tk.Label(top,text='Flow').pack(side='left',padx=6); self.flow=ttk.Combobox(top,width=20,values=['Same Column → Next Page','Continue Columns','Ask Me'],state='readonly'); self.flow.set('Same Column → Next Page'); self.flow.pack(side='left'); self.flow.bind('<<ComboboxSelected>>',lambda e:self.set_flow())
        left=tk.Frame(self.root,width=78); left.pack(side='left',fill='y'); self.left=left
        for txt,cmd in [('↖\nSelect',lambda:None),('T\nText',self.text_tool),('▣\nImage',self.image),('∑\nMath',self.math),('▤\nTable',self.table),('M\nMaster',self.master),('＋\nPage',self.add_page)]: tk.Button(left,text=txt,command=cmd,relief='flat',padx=2,pady=8).pack(fill='x',padx=6,pady=2)
        self.canvas=tk.Canvas(self.root,highlightthickness=0); self.canvas.pack(side='left',fill='both',expand=True); sb=ttk.Scrollbar(self.root,orient='vertical',command=self.canvas.yview); sb.pack(side='right',fill='y'); self.canvas.configure(yscrollcommand=sb.set); self.host=tk.Frame(self.canvas); self.canvas.create_window((20,10),window=self.host,anchor='nw'); self.host.bind('<Configure>',lambda e:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.status=tk.Label(self.root,text='Ready',anchor='w',padx=10); self.status.pack(side='bottom',fill='x')
    def activate(self,w): self.active=w; self.status.config(text='Unicode text frame active')
    def changed(self,w=None): self.dirty=True; self.status.config(text='Modified'); self.root.after(20,self.reflow)
    def reflow(self):
        # Physical frames are bounded; selected flow mode determines the next destination.
        for pi,p in enumerate(self.pages):
            for ci,t in enumerate(p.texts):
                if t.winfo_height()<=0: continue
                try:
                    if t.count('1.0','end-1c','-ypixels')[0] <= t.winfo_height(): continue
                    idx=t.index(f'@2,{t.winfo_height()-8}'); moved=t.get(idx,'end-1c')
                    if len(moved)<5: continue
                    t.delete(idx,'end'); mode=self.settings['flow_mode']; ni=ci+1 if mode=='next_column' and ci+1<len(p.texts) else ci; np=p if mode=='next_column' and ci+1<len(p.texts) else (self.add_page(False) if pi+1>=len(self.pages) else self.pages[pi+1])
                    if mode=='ask':
                        if not messagebox.askyesno('Text Overflow','Continue overflow in the next available frame?'): t.insert('end',moved); continue
                    np.texts[ni].insert('end',moved)
                except Exception: pass
    def reflow_pages(self):
        for p in self.pages: p.rebuild()
    def set_flow(self): self.settings['flow_mode']={'Same Column → Next Page':'same_column','Continue Columns':'next_column','Ask Me':'ask'}[self.flow.get()]; self.changed()
    def font_apply(self):
        self.settings['font']=self.font.get(); self.settings['size']=int(self.sz.get()); self.reflow_pages(); self.changed()
    def tag(self,name):
        if self.active:
            try:self.active.tag_add(name,self.active.index('sel.first'),self.active.index('sel.last')); self.changed()
            except tk.TclError: pass
    def clear_fmt(self):
        if self.active:
            try:
                a,b=self.active.index('sel.first'),self.active.index('sel.last'); [self.active.tag_remove(x,a,b) for x in ('bold','italic','sup','sub')]; self.changed()
            except tk.TclError: pass
    def text_tool(self):
        if self.active:self.active.focus_set()
        elif self.pages:self.activate(self.pages[-1].texts[0]); self.active.focus_set()
    def paste(self,t):
        try:t.insert('insert',self.root.clipboard_get()); self.changed(t); return 'break'
        except Exception:return None
    def image(self):
        if not self.active: return
        try:
            from PIL import Image,ImageTk
            fn=filedialog.askopenfilename(filetypes=[('Images','*.png *.jpg *.jpeg *.gif *.bmp *.webp')]);
            if not fn:return
            im=Image.open(fn); im.thumbnail((320,240)); ph=ImageTk.PhotoImage(im); refs=getattr(self.active,'_pm_refs',[]); refs.append(ph); self.active._pm_refs=refs; self.active.image_create('insert',image=ph); self.active.insert('insert','\n'); self.changed()
        except ImportError: messagebox.showinfo('Image','Install Pillow: pip install pillow')
    def math(self):
        if not self.active:return
        w=tk.Toplevel(self.root); w.title('Unicode Math & Symbols'); e=tk.Entry(w,width=70); e.pack(padx=12,pady=10); groups='α β γ δ θ λ μ π σ φ ω Ω Δ Σ √ ∛ ∞ ∑ ∏ ∫ ∂ ∇ ± × ÷ ≠ ≈ ≤ ≥ ∝ → ⇒ ⇔ ½ ⅓ ¼ ¾ ⁰¹²³⁺⁻ⁿ ₀₁₂₃₊₋ₙ H₂O CO₂ SO₄²⁻'.split(); [tk.Button(w,text=x,command=lambda x=x:e.insert('end',x),relief='flat').pack(side='left') for x in groups]; tk.Button(w,text='Insert',command=lambda:(self.active.insert('insert',e.get()),self.changed(),w.destroy())).pack(pady=10)
    def table(self):
        if not self.active:return
        v=simpledialog.askstring('Table','Rows x Columns, e.g. 4x3');
        try:r,c=map(int,v.lower().split('x')); [self.active.insert('insert',' | '.join(['']*c)+'\n') for _ in range(r)]; self.changed()
        except Exception: pass
    def page_settings(self):
        w=tk.Toplevel(self.root); w.title('Page Settings'); vars={}; keys=['columns','gap','margin','header','footer','watermark']
        for i,k in enumerate(keys): tk.Label(w,text=k.title()).grid(row=i,column=0,padx=8,pady=4); v=tk.StringVar(value=str(self.settings[k])); vars[k]=v; tk.Entry(w,textvariable=v,width=32).grid(row=i,column=1,padx=8,pady=4)
        def apply():
            for k,v in vars.items(): self.settings[k]=int(v.get()) if k in ('columns','gap','margin') else v.get()
            self.settings['columns']=max(1,min(3,self.settings['columns'])); self.reflow_pages(); self.changed(); w.destroy()
        tk.Button(w,text='Page Color…',command=self.pick_color).grid(row=7,column=0,pady=8); tk.Button(w,text='Apply',command=apply).grid(row=8,column=0,columnspan=2,pady=10)
    def pick_color(self):
        c=colorchooser.askcolor(initialcolor=self.settings['page_color'])[1]
        if c:self.settings['page_color']=c; self.reflow_pages(); self.changed()
    def master(self):
        w=tk.Toplevel(self.root); w.title('A-Master'); w.geometry('520x300'); vs={}
        for i,k in enumerate(['master_header','master_footer','master_watermark']): tk.Label(w,text=k.replace('master_','').title()).grid(row=i,column=0,padx=8,pady=8); v=tk.StringVar(value=self.settings[k]); vs[k]=v; tk.Entry(w,textvariable=v,width=38).grid(row=i,column=1)
        en=tk.BooleanVar(value=self.settings['master_enabled']); tk.Checkbutton(w,text='Apply A-Master to document pages',variable=en).grid(row=3,column=0,columnspan=2)
        def apply():
            [self.settings.__setitem__(k,v.get()) for k,v in vs.items()]; self.settings['master_enabled']=en.get(); self.reflow_pages(); self.changed(); w.destroy()
        tk.Button(w,text='Apply A-Master',command=apply).grid(row=4,column=0,columnspan=2,pady=20)
    def add_page(self,mark=True): self.pages.append(Page(self,len(self.pages)+1)); self.host.update_idletasks(); self.canvas.configure(scrollregion=self.canvas.bbox('all')); mark and self.changed(); return self.pages[-1]
    def remove_page(self):
        if len(self.pages)>1:self.pages.pop().frame.destroy(); self.changed()
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
        fn=filedialog.asksaveasfilename(defaultextension='.upm',filetypes=[('PageMaker Pro','*.upm')]);
        if fn:self.filename=fn; self.save()
    def open(self):
        fn=filedialog.askopenfilename(filetypes=[('PageMaker Pro','*.upm *.json')]);
        if not fn:return
        try:
            d=json.load(open(fn,encoding='utf-8')); self.settings.update(d.get('settings',{})); [p.frame.destroy() for p in self.pages]; self.pages=[]
            for cols in d.get('pages',[['']]): p=self.add_page(False); p.saved=cols; p.rebuild()
            self.filename=fn; self.dirty=False; self.status.config(text='Opened: '+os.path.basename(fn))
        except Exception as e: messagebox.showerror('Open failed',str(e))
    def undo(self):
        try:self.active.edit_undo()
        except Exception:pass
    def redo(self):
        try:self.active.edit_redo()
        except Exception:pass
    def find_replace(self):
        if not self.active:return
        f=simpledialog.askstring('Find','Find text'); r=simpledialog.askstring('Replace','Replace with')
        if f is not None:self.active.delete('1.0','end'); self.active.insert('1.0',self.active.get('1.0','end-1c').replace(f,r or '')); self.changed()
    def apply_theme(self,name,mark=True): self.settings['theme']=name; self.theme=THEMES[name]; self.root.configure(bg=self.theme[0]); self.reflow_pages(); mark and self.changed()
    def fit(self):
        self.root.update_idletasks(); h=max(500,self.canvas.winfo_height()-30); self.zoom(min(.95,h/self.settings['page_h']))
    def zoom(self,z):
        self.settings['zoom']=z
        for p in self.pages:p.frame.destroy()
        old=self.pages; self.pages=[]
        for oldp in old:
            p=self.add_page(False); p.saved=oldp.capture(); p.rebuild(); p.frame.pack(pady=8)
    def export_pdf(self):
        try: from reportlab.pdfgen import canvas
        except ImportError: messagebox.showinfo('PDF','Install reportlab: pip install reportlab'); return
        fn=filedialog.asksaveasfilename(defaultextension='.pdf',filetypes=[('PDF','*.pdf')]);
        if not fn:return
        c=canvas.Canvas(fn,pagesize=(self.settings['page_w'],self.settings['page_h']))
        for p in self.pages:
            c.setFillColorRGB(*self.rgb(self.page_bg())); c.rect(0,0,self.settings['page_w'],self.settings['page_h'],fill=1,stroke=0); c.setFillColorRGB(*self.rgb(self.page_fg())); c.setFont('Helvetica',9); c.drawCentredString(self.settings['page_w']/2,self.settings['page_h']-28,self.settings.get('master_header','') if self.settings.get('master_enabled',True) else self.settings.get('header','')); c.drawCentredString(self.settings['page_w']/2,18,f"Page {p.number}")
            for i,t in enumerate(p.texts):
                x=self.settings['margin']+i*((self.settings['page_w']-2*self.settings['margin']-self.settings['gap']*(len(p.texts)-1))/len(p.texts)+self.settings['gap']); y=self.settings['page_h']-70; c.setFont('Helvetica',self.settings['size'])
                for line in t.get('1.0','end-1c').splitlines():
                    if y<45:break
                    c.drawString(x,y,line[:120]); y-=self.settings['size']*1.25
            c.showPage()
        c.save(); messagebox.showinfo('PDF','Exported successfully')
    def export_docx(self):
        try: from docx import Document
        except ImportError: messagebox.showinfo('DOCX','Install python-docx: pip install python-docx'); return
        fn=filedialog.asksaveasfilename(defaultextension='.docx',filetypes=[('Word','*.docx')]);
        if not fn:return
        d=Document()
        for pi,p in enumerate(self.pages):
            if pi:d.add_page_break()
            for t in p.texts:d.add_paragraph(t.get('1.0','end-1c'))
        d.save(fn); messagebox.showinfo('DOCX','Exported successfully')
    @staticmethod
    def rgb(h): h=h.lstrip('#'); return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))
    def close(self):
        if not self.dirty or messagebox.askyesno('Exit','Unsaved changes will be lost. Exit?'): self.root.destroy()

if __name__=='__main__':
    root=tk.Tk(); App(root); root.mainloop()
