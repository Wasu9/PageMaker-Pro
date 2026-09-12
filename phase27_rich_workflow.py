"""Phase 27 — production paste workflow for question-paper authoring."""
import base64, ctypes, os, re, tempfile, urllib.parse
from html.parser import HTMLParser

_SUP = str.maketrans({'0':'\u2070','1':'\u00b9','2':'\u00b2','3':'\u00b3','4':'\u2074','5':'\u2075','6':'\u2076','7':'\u2078','8':'\u2079','9':'\u2079','+':'\u207a','-':'\u207b','=':'\u207c','(':'\u207d',')':'\u207e','n':'\u207f','i':'\u2071'})
_SUB = str.maketrans({'0':'\u2080','1':'\u2081','2':'\u2082','3':'\u2083','4':'\u2084','5':'\u2085','6':'\u2086','7':'\u2087','8':'\u2088','9':'\u2089','+':'\u208a','-':'\u208b','=':'\u208c','(':'\u208d',')':'\u208e','a':'\u2090','e':'\u2091','h':'\u2095','i':'\u1d62','j':'\u2c7c','k':'\u2096','l':'\u2097','m':'\u2098','n':'\u2099','o':'\u2092','p':'\u209a','r':'\u1d63','s':'\u209b','t':'\u209c','u':'\u1d64','v':'\u1d65','x':'\u2093'})
_BLOCK={'p','div','section','article','li','h1','h2','h3','h4','h5','h6','pre','blockquote'}

def _cf_html():
    if os.name!='nt': return ''
    u=ctypes.windll.user32; k=ctypes.windll.kernel32; fmt=u.RegisterClipboardFormatW('HTML Format')
    if not fmt or not u.OpenClipboard(None): return ''
    try:
        if not u.IsClipboardFormatAvailable(fmt): return ''
        h=u.GetClipboardData(fmt)
        if not h:return ''
        p=k.GlobalLock(h)
        if not p:return ''
        try: raw=ctypes.string_at(p,int(k.GlobalSize(h))).split(b'\0',1)[0]
        finally:k.GlobalUnlock(h)
        s=raw.decode('utf-8','replace'); vals={}
        for key,val in re.findall(r'(?im)^([A-Za-z]+):([0-9]+)\\s*$',s): vals[key.lower()]=int(val)
        a,b=vals.get('startfragment'),vals.get('endfragment')
        if a is not None and b is not None and 0<=a<b<=len(raw): return raw[a:b].decode('utf-8','replace')
        m=re.search(r'<!--StartFragment-->(.*?)<!--EndFragment-->',s,re.I|re.S)
        return m.group(1) if m else s
    finally:u.CloseClipboard()

class _PaperHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.parts=[]; self.ranges=[]; self.images=[]; self.bold=self.italic=self.sup=self.sub=0; self.pre=0; self.table=0; self.cell_count=0; self.last_nl=False
    def pos(self):return sum(len(x[0]) for x in self.parts)
    def emit(self,t):
        if not t:return
        t=t.replace('\r\n','\n').replace('\r','\n')
        if self.sup:t=t.translate(_SUP)
        elif self.sub:t=t.translate(_SUB)
        a=self.pos(); self.parts.append((t,self.bold>0,self.italic>0,self.sup>0,self.sub>0)); self.ranges.append((a,a+len(t),self.bold>0,self.italic>0,self.sup>0,self.sub>0)); self.last_nl=t.endswith('\n')
    def nl(self):
        if self.parts and not self.last_nl:self.emit('\n')
    def handle_starttag(self,tag,attrs):
        tag=tag.lower(); attrs=dict(attrs)
        if tag in _BLOCK:self.nl()
        if tag=='br':self.nl();return
        if tag in ('b','strong'):self.bold+=1
        elif tag in ('i','em'):self.italic+=1
        elif tag=='sup':self.sup+=1
        elif tag=='sub':self.sub+=1
        elif tag=='pre':self.pre+=1
        elif tag=='table':self.table+=1;self.nl()
        elif tag=='tr':self.cell_count=0
        elif tag in ('td','th') and self.table:
            if self.cell_count:self.emit('\t')
            self.cell_count+=1
        elif tag=='img':
            src=attrs.get('src',''); alt=attrs.get('alt','')
            if src:self.images.append((src,alt))
            if alt:self.emit(alt)
    def handle_endtag(self,tag):
        tag=tag.lower()
        if tag in ('b','strong'):self.bold=max(0,self.bold-1)
        elif tag in ('i','em'):self.italic=max(0,self.italic-1)
        elif tag=='sup':self.sup=max(0,self.sup-1)
        elif tag=='sub':self.sub=max(0,self.sub-1)
        elif tag=='pre':self.pre=max(0,self.pre-1);self.nl()
        elif tag=='tr' and self.table:self.nl()
        elif tag=='table':self.table=max(0,self.table-1);self.nl()
        elif tag in _BLOCK:self.nl()
    def handle_data(self,data):
        if not self.pre:data=re.sub(r'[ \t\f\v]+',' ',data)
        self.emit(data)
    def result(self):
        text=''.join(x[0] for x in self.parts); text=re.sub(r'\n{3,}','\n\n',text).strip('\n'); return text,self.ranges,self.images

def parse_html(source):
    p=_PaperHTML();p.feed(source);return p.result()

def _insert_text(w,text,ranges):
    try:a,b=w.index('sel.first'),w.index('sel.last');w.delete(a,b)
    except Exception:a='insert'
    start=w.index(a);w.insert(a,text)
    for s,e,bold,italic,sup,sub in ranges:
        try:
            aa=f'{start}+{s}c';bb=f'{start}+{e}c'
            if bold:w.tag_add('bold',aa,bb)
            if italic:w.tag_add('italic',aa,bb)
            if sup:w.tag_add('sup',aa,bb)
            if sub:w.tag_add('sub',aa,bb)
        except Exception:pass
    try:w.mark_set('insert',f'{start}+{len(text)}c');w.see('insert')
    except Exception:pass

def _apply_runs(app,ranges):
    try:
        from sitecustomize import _widget_order
        widgets=_widget_order(app)
    except Exception:return
    offset=0
    for w in widgets:
        try:n=len(w.get('1.0','end-1c'))
        except Exception:n=0
        for s,e,bold,italic,sup,sub in ranges:
            a=max(s,offset);b=min(e,offset+n)
            if a>=b:continue
            aa=f'1.0+{a-offset}c';bb=f'1.0+{b-offset}c'
            try:
                if bold:w.tag_add('bold',aa,bb)
                if italic:w.tag_add('italic',aa,bb)
                if sup:w.tag_add('sup',aa,bb)
                if sub:w.tag_add('sub',aa,bb)
            except Exception:pass
        offset+=n

def _paste_image_near_cursor(app,w):
    try:
        from PIL import ImageGrab,ImageTk
        im=ImageGrab.grabclipboard()
        if im is None or not hasattr(im,'save'):return False
        pi=next(i for i,p in enumerate(app.pages) if w in getattr(p,'texts',[])); page=app.pages[pi].page
        bb=w.bbox('insert'); x=w.winfo_x()+(bb[0] if bb else 0); y=w.winfo_y()+(bb[1] if bb else 0)
        im=im.convert('RGBA'); im.thumbnail((max(120,int(w.winfo_width()*.85)),220));
        root=os.path.join(tempfile.gettempdir(),'PageMakerPro_clipboard');os.makedirs(root,exist_ok=True);path=os.path.join(root,'clipboard_%d.png'%id(im));im.save(path,'PNG')
        ph=ImageTk.PhotoImage(im); label=__import__('tkinter').Label(page,image=ph,bd=1,relief='solid'); label.place(x=x,y=y,width=im.width,height=im.height)
        app._pm_image_refs=getattr(app,'_pm_image_refs',[])+[ph]
        obj=app.document.add_image(app.document.pages[pi],__import__('pagemaker_core').Rect(60,70,im.width,im.height),path)
        app._pm_image_widgets=getattr(app,'_pm_image_widgets',{});app._pm_image_widgets[obj.id]=label
        try:
            import phase26_image_resize as r;r.bind_image(app,obj.id,label)
        except Exception:pass
        app._pm_selected_image=obj.id;app.dirty=True
        app.status.config(text='Image pasted at insertion point — drag/resize handles')
        return True
    except Exception:return False

def paste_rich(app,w=None):
    w=w or getattr(app,'active',None)
    if w is None:return 'break'
    source=_cf_html()
    if source:
        try:
            text,ranges,images=parse_html(source)
            if text:
                _insert_text(w,text,ranges);app._pm27_pending_runs=ranges;app.changed(w)
                try:app.root.after(280,lambda:_apply_runs(app,ranges))
                except Exception:pass
            # If the clipboard also carries a bitmap, preserve it rather than
            # silently dropping the graphic component of a rich paste.
            if images or _paste_image_near_cursor(app,w):
                pass
            app.status.config(text='Rich paste: bulk text + Unicode math + sup/sub + basic formatting preserved')
            return 'break'
        except Exception:pass
    try:
        text=app.root.clipboard_get();_insert_text(w,text,[(0,len(text),False,False,False,False)]);app.changed(w);return 'break'
    except Exception:pass
    if _paste_image_near_cursor(app,w):return 'break'
    return None

def install(app):
    try:
        import phase25_editor_fixes as p25
        p25.paste=lambda a,w=None:paste_rich(a,w)
        app.paste=lambda w=None:paste_rich(app,w);app._pm27_rich_paste=True
    except Exception:pass

def install_once(app):
    if getattr(app,'_pm27_installed',False):return
    install(app);app._pm27_installed=True
