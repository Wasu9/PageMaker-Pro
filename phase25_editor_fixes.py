"""Phase 25 editor fixes: locked columns, column-wide selection, clipboard images,
Unicode math/superscript/subscript, and inline question tables."""
import os, tempfile, tkinter as tk
from tkinter import messagebox
from pagemaker_core import Rect

_SUP = str.maketrans({
    '0':'\u2070','1':'\u00b9','2':'\u00b2','3':'\u00b3','4':'\u2074','5':'\u2075','6':'\u2076','7':'\u2077','8':'\u2078','9':'\u2079',
    '+':'\u207a','-':'\u207b','=':'\u207c','(':'\u207d',')':'\u207e','n':'\u207f','i':'\u2071','a':'\u1d43','e':'\u1d49','o':'\u1d52','x':'\u02e3',
    'A':'\u1d2c','B':'\u1d2e','D':'\u1d30','E':'\u1d31','G':'\u1d33','H':'\u1d34','I':'\u1d35','J':'\u1d36','K':'\u1d37','L':'\u1d38','M':'\u1d39','N':'\u1d3a','O':'\u1d3c','P':'\u1d3e','R':'\u1d3f','T':'\u1d40','U':'\u1d41','V':'\u2c7d','W':'\u1d42'})
_SUB = str.maketrans({
    '0':'\u2080','1':'\u2081','2':'\u2082','3':'\u2083','4':'\u2084','5':'\u2085','6':'\u2086','7':'\u2087','8':'\u2088','9':'\u2089',
    '+':'\u208a','-':'\u208b','=':'\u208c','(':'\u208d',')':'\u208e','a':'\u2090','e':'\u2091','h':'\u2095','i':'\u1d62','j':'\u2c7c','k':'\u2096','l':'\u2097','m':'\u2098','n':'\u2099','o':'\u2092','p':'\u209a','r':'\u1d63','s':'\u209b','t':'\u209c','u':'\u1d64','v':'\u1d65','x':'\u2093','\u03b2':'\u1d66','\u03b3':'\u1d67','\u03c1':'\u1d68','\u03c6':'\u1d69','\u03c7':'\u1d6a'})
MATH_GROUPS = [
    '\u03b1 \u03b2 \u03b3 \u03b4 \u03b8 \u03bb \u03bc \u03c0 \u03c1 \u03c3 \u03c6 \u03c9 \u03a9 \u0394 \u03a3 \u03a6 \u03a8 \u221a \u221b \u221c \u221e \u2211 \u220f \u222b \u222c \u2202 \u2207 \u00b1 \u00d7 \u00f7 \u2260 \u2248 \u2264 \u2265 < > \u221d \u2234 \u2235 \u2192 \u2190 \u2194 \u21d2 \u21d4 \u21a6 \u2208 \u2209 \u2229 \u222a \u2205 \u2200 \u2203',
    '\u00bd \u2153 \u2154 \u00bc \u00be \u2155 \u2156 \u2157 \u2158 \u2159 \u215a \u215b \u215c \u215d \u215e',
    '\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079 \u207a\u207b\u207c\u207d\u207e \u207f \u2071',
    '\u2080\u2081\u2082\u2083\u2084\u2085\u2086\u2087\u2088\u2089 \u208a\u208b\u208c\u208d\u208e \u2090\u2091\u2095\u1d62\u2c7c\u2096\u2097\u2098\u2099\u2092\u209a\u1d63\u209b\u209c\u1d64\u1d65\u2093',
    'H\u2082O CO\u2082 SO\u2084\u00b2\u207b NH\u2084\u207a Ca\u00b2\u207a Al\u00b3\u207a x\u00b2 y\u00b2 a\u2081 b\u2082'
]

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
    out=src.translate(_SUP if kind=='sup' else _SUB) if src else ('\u00b2' if kind=='sup' else '\u2082')
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
            tags=list(w.bindtags());tag='PM25_'+str(id(w))
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
                        sub=menu.nametowidget(menu.entrycget(i,'menu'));sub.add_separator();sub.add_command(label='Match Columns Table...',command=self.match_table);break
                except Exception:pass
        except Exception:pass
    app_cls.__init__=init
    def insert_image(self):
        try:
            from sitecustomize import _import_image;_import_image(self)
        except Exception:pass
    app_cls._pm25_insert_image=insert_image
