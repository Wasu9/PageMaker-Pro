"""Phase 25 editor fixes: locked columns, column-wide selection, clipboard images,
Unicode math/superscript/subscript, and inline question tables."""
import os, tempfile, tkinter as tk
from tkinter import messagebox
from pagemaker_core import Rect

_SUP = str.maketrans({'0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹','+':'⁺','-':'⁻','=','⁼','(':'⁽',')':'⁾','n':'ⁿ','i':'ⁱ','a':'ᵃ','e':'ᵉ','o':'ᵒ','x':'ˣ','A':'ᴬ','B':'ᴮ','D':'ᴰ','E':'ᴱ','G':'ᴳ','H':'ᴴ','I':'ᴵ','J':'ᴶ','K':'ᴷ','L':'ᴸ','M':'ᴹ','N':'ᴺ','O':'ᴼ','P':'ᴾ','R':'ᴿ','T':'ᵀ','U':'ᵁ','V':'ⱽ','W':'ᵂ'})
_SUB = str.maketrans({'0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅','6':'₆','7':'₇','8':'₈','9':'₉','+':'₊','-':'₋','=':'₌','(':'₍',')':'₎','a':'ₐ','e':'ₑ','h':'ₕ','i':'ᵢ','j':'ⱼ','k':'ₖ','l':'ₗ','m':'ₘ','n':'ₙ','o':'ₒ','p':'ₚ','r':'ᵣ','s':'ₛ','t':'ₜ','u':'ᵤ','v':'ᵥ','x':'ₓ','β':'ᵦ','γ':'ᵧ','ρ':'ᵨ','φ':'ᵩ','χ':'ᵪ'})
MATH_GROUPS = ['α β γ δ θ λ μ π ρ σ φ ω Ω Δ Σ Φ Ψ √ ∛ ∜ ∞ ∑ ∏ ∫ ∬ ∂ ∇ ± × ÷ ≠ ≈ ≤ ≥ < > ∝ ∴ ∵ → ← ↔ ⇒ ⇔ ↦ ∈ ∉ ∩ ∪ ∅ ∀ ∃','½ ⅓ ⅔ ¼ ¾ ⅕ ⅖ ⅗ ⅘ ⅙ ⅚ ⅛ ⅜ ⅝ ⅞','⁰¹²³⁴⁵⁶⁷⁸⁹ ⁺⁻⁼⁽⁾ ⁿ ⁱ','₀₁₂₃₄₅₆₇₈₉ ₊₋₌₍₎ ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ','H₂O CO₂ SO₄²⁻ NH₄⁺ Ca²⁺ Al³⁺ x² y² a₁ b₂']

def _active(app): return getattr(app,'active',None)
def _frame_key(app,w):
    for pi,p in enumerate(app.pages):
        for ci,x in enumerate(getattr(p,'texts',[])):
            if x is w:return (pi,ci)
    return None

def _clear_col_tags(app):
    for p in app.pages:
        for w in getattr(p,'texts',[]):
            try:w.tag_remove('pm25_column_selection','1.0','end')
            except Exception:pass

def select_column(app,w=None):
    w=w or _active(app); key=_frame_key(app,w) if w else None
    if key is None:return 'break'
    _,ci=key; _clear_col_tags(app)
    widgets=[]
    for p in app.pages:
        if ci<len(getattr(p,'texts',[])):
            x=p.texts[ci]; widgets.append(x); x.tag_add('pm25_column_selection','1.0','end')
    app._pm25_selected_column=ci; app._pm25_column_widgets=widgets
    try:app.status.config(text=f'Column {ci+1} selected across {len(widgets)} page(s)')
    except Exception:pass
    return 'break'

def copy_column(app,event=None):
    widgets=getattr(app,'_pm25_column_widgets',None)
    if not widgets:return None
    text='\n'.join(w.get('1.0','end-1c') for w in widgets)
    try:app.root.clipboard_clear();app.root.clipboard_append(text);app.root.update();app.status.config(text=f'Copied complete column ({len(text)} characters)')
    except Exception:pass
    return 'break'

def _paste_clipboard_image(app,w):
    try:
        from PIL import ImageGrab,ImageTk
        im=ImageGrab.grabclipboard()
    except Exception:return False
    if im is None or not hasattr(im,'save'):return False
    try:
        root_dir=os.path.join(tempfile.gettempdir(),'PageMakerPro_clipboard');os.makedirs(root_dir,exist_ok=True)
        path=os.path.join(root_dir,'clipboard_%d.png'%id(im));im.convert('RGBA').save(path,'PNG')
        pi,ci=_frame_key(app,w); page=app.document.pages[pi]
        im2=im.convert('RGBA');im2.thumbnail((300,220));ph=ImageTk.PhotoImage(im2)
        label=tk.Label(app.pages[pi].page,image=ph,bd=1,relief='solid');label.place(x=60*app._zoom,y=70*app._zoom,width=max(20,int(im2.width*app._zoom)),height=max(20,int(im2.height*app._zoom)))
        refs=getattr(app,'_pm_image_refs',[]);refs.append(ph);app._pm_image_refs=refs
        image=app.document.add_image(page,Rect(60,70,im2.width,im2.height),path)
        store=getattr(app,'_pm_image_widgets',{});store[image.id]=label;app._pm_image_widgets=store
        state={'last':None}
        def down(e):
            if not getattr(app,'_pm_select_mode',True):return
            state['last']=(e.x,e.y);app._pm_selected_image=image.id
        def move(e):
            if not state.get('last'):return
            dx,dy=e.x-state['last'][0],e.y-state['last'][1];state['last']=(e.x,e.y);z=max(.25,float(app._zoom));app.document.move_image(image.id,image.rect.x+dx/z,image.rect.y+dy/z);label.place(x=label.winfo_x()+dx,y=label.winfo_y()+dy)
        label.bind('<Button-1>',down,add='+');label.bind('<B1-Motion>',move,add='+')
        app.status.config(text='Clipboard image pasted — Select tool: drag to move');return True
    except Exception as exc:
        try:messagebox.showerror('Paste Image',str(exc))
        except Exception:pass
        return False

def paste(app,w=None):
    w=w or _active(app)
    if w is None:return 'break'
    if _paste_clipboard_image(app,w):return 'break'
    try:w.insert('insert',app.root.clipboard_get());app.changed(w);return 'break'
    except Exception:return None

def _replace_selection(w,text,tag=None):
    try:a,b=w.index('sel.first'),w.index('sel.last')
    except tk.TclError:w.insert('insert',text);return
    w.delete(a,b);w.insert(a,text);w.mark_set('insert',f'{a}+{len(text)}c')
    if tag:w.tag_add(tag,a,f'{a}+{len(text)}c')

def style_selection(app,kind):
    w=_active(app)
    if not w:return 'break'
    try:src=w.get('sel.first','sel.last')
    except tk.TclError:src=''
    out=src.translate(_SUP if kind=='sup' else _SUB) if src else ('²' if kind=='sup' else '₂')
    _replace_selection(w,out,kind);app.changed(w);return 'break'

def math_dialog(app):
    w=_active(app)
    if not w:return
    win=tk.Toplevel(app.root);win.title('Math / Equation / Unicode Symbols');win.geometry('900x360');win.transient(app.root)
    entry=tk.Entry(win,font=('Segoe UI',14));entry.pack(fill='x',padx=12,pady=10)
    tk.Label(win,text='Unicode-safe equation text — type directly or click symbols').pack(anchor='w',padx=12)
    for line in MATH_GROUPS:
        bar=tk.Frame(win);bar.pack(fill='x',padx=10,pady=3)
        for ch in line.split():tk.Button(bar,text=ch,command=lambda ch=ch:entry.insert('end',ch),relief='flat',padx=4).pack(side='left')
    def ins():_replace_selection(w,entry.get());app.changed(w);win.destroy()
    tk.Button(win,text='Insert Equation',command=ins).pack(pady=12);entry.focus_set()

def table_dialog(app,match=False):
    w=_active(app)
    if not w:return
    win=tk.Toplevel(app.root);win.title('Match Columns Table' if match else 'Insert Table');win.geometry('700x470');win.transient(app.root)
    top=tk.Frame(win);top.pack(fill='x',padx=10,pady=8)
    tk.Label(top,text='Rows').pack(side='left');rv=tk.Spinbox(top,from_=1,to=30,width=4);rv.set(4);rv.pack(side='left',padx=5)
    tk.Label(top,text='Columns').pack(side='left');cv=tk.Spinbox(top,from_=1,to=8,width=4);cv.set(2 if match else 3);cv.pack(side='left',padx=5)
    grid=tk.Frame(win);grid.pack(fill='both',expand=True,padx=10,pady=5);entries=[]
    def build():
        for c in grid.winfo_children():c.destroy()
        entries.clear();r,c=int(rv.get()),int(cv.get())
        for i in range(r):
            row=[]
            for j in range(c):
                e=tk.Entry(grid,width=22);e.grid(row=i,column=j,padx=2,pady=2,sticky='ew');row.append(e)
            entries.append(row)
    build()
    def insert_table():
        text='\n'.join('\t'.join(e.get() for e in row) for row in entries)+'\n';_replace_selection(w,text);app.changed(w);win.destroy()
    tk.Button(top,text='Rebuild',command=build).pack(side='left',padx=10);tk.Button(win,text='Insert into Question Flow',command=insert_table).pack(pady=10)

def _guard(app,w,event):
    # Built-in columns never move in Select mode. Text mode keeps normal editing.
    if getattr(app,'_pm_select_mode',True):return 'break'
    if event.state & 0x0004 and event.keysym.lower()=='a':return select_column(app,w)
    if event.state & 0x0004 and event.keysym.lower()=='c' and getattr(app,'_pm25_column_widgets',None):return copy_column(app,event)
    if event.state & 0x0004 and event.keysym.lower()=='v':return paste(app,w)
    return None

def _lock_columns(app):
    for p in app.pages:
        for w in getattr(p,'texts',[]):
            try:w.tag_configure('pm25_column_selection',background='#4a78c2',foreground='#ffffff')
            except Exception:pass
            tags=list(w.bindtags())
            tag='PM25_'+str(id(w))
            if tag not in tags:
                w.bindtags((tag,)+tuple(tags));w.bind_class(tag,'<Button-1>',lambda e,w=w:_guard(app,w,e));w.bind_class(tag,'<B1-Motion>',lambda e,w=w:_guard(app,w,e));w.bind_class(tag,'<ButtonRelease-1>',lambda e,w=w:_guard(app,w,e));w.bind_class(tag,'<Control-KeyPress-a>',lambda e,w=w:select_column(app,w));w.bind_class(tag,'<Control-KeyPress-A>',lambda e,w=w:select_column(app,w));w.bind_class(tag,'<Control-KeyPress-c>',lambda e:copy_column(app,e));w.bind_class(tag,'<Control-KeyPress-C>',lambda e:copy_column(app,e));w.bind_class(tag,'<Control-KeyPress-v>',lambda e,w=w:paste(app,w));w.bind_class(tag,'<Control-KeyPress-V>',lambda e,w=w:paste(app,w))
    app._pm25_lock_columns=True

def install(app_cls):
    if getattr(app_cls,'_pm25_installed',False):return
    app_cls._pm25_installed=True;orig=app_cls.__init__
    def init(self,*a,**k):
        orig(self,*a,**k);_lock_columns(self)
        self.image=lambda:self._pm25_insert_image();self.math=lambda:math_dialog(self);self.table=lambda:table_dialog(self,False);self.match_table=lambda:table_dialog(self,True)
        try:
            self.root.bind_all('<Control-Shift-M>',lambda e:table_dialog(self,True),add='+')
            self.root.bind_all('<Control-Shift-=>',lambda e:style_selection(self,'sup'),add='+')
            self.root.bind_all('<Control-Shift-->',lambda e:style_selection(self,'sub'),add='+')
            for child in self.left.winfo_children():
                if isinstance(child,tk.Button) and 'Image' in child.cget('text'):child.configure(command=self.image)
                elif isinstance(child,tk.Button) and 'Math' in child.cget('text'):child.configure(command=self.math)
                elif isinstance(child,tk.Button) and 'Table' in child.cget('text'):child.configure(command=self.table)
            menu=self.root.nametowidget(self.root['menu'])
            for i in range(menu.index('end')+1):
                try:
                    if menu.entrycget(i,'label')=='Insert':
                        sub=menu.nametowidget(menu.entrycget(i,'menu'));sub.add_separator();sub.add_command(label='Match Columns Table…',command=self.match_table);break
                except Exception:pass
        except Exception:pass
    app_cls.__init__=init
    def insert_image(self):
        try:
            from sitecustomize import _import_image;_import_image(self)
        except Exception:pass
    app_cls._pm25_insert_image=insert_image
