"""PageMaker Pro runtime UX fixes and classic PageMaker-style page navigation."""
import sys
import tkinter as tk

_orig_tk_init = tk.Tk.__init__


def _canvas_fix(root):
    def walk(w):
        yield w
        try:
            for c in w.winfo_children(): yield from walk(c)
        except Exception: pass
    def refresh():
        try:
            for c in [w for w in walk(root) if isinstance(w, tk.Canvas)]:
                try:
                    children=c.winfo_children(); rw=max([x.winfo_reqwidth() for x in children]+[0]); rh=max([x.winfo_reqheight() for x in children]+[0])
                    c.configure(scrollregion=(0,0,max(c.winfo_width()+2,rw+30),max(c.winfo_height()+2,rh+30)))
                    def wheel(e,canvas=c):
                        d=getattr(e,'delta',0)
                        if d: canvas.yview_scroll((-max(1,min(6,int(abs(d)/120))) if d>0 else max(1,min(6,int(abs(d)/120)))),'units')
                        return 'break'
                    c.bind('<MouseWheel>',wheel,add='+'); c.bind('<Button-4>',lambda e,canvas=c:(canvas.yview_scroll(-3,'units'),'break')[-1],add='+'); c.bind('<Button-5>',lambda e,canvas=c:(canvas.yview_scroll(3,'units'),'break')[-1],add='+')
                except Exception: pass
        except Exception: pass
        try: root.after(200,refresh)
        except Exception: pass
    root.after(250,refresh)


def _enhance(app):
    root=app.root
    if getattr(app,'_pm_enhanced',False): return
    app._pm_enhanced=True
    nav=tk.Frame(root,height=34,bd=1,relief='sunken'); nav.pack(side='bottom',fill='x')
    tk.Button(nav,text='◀',width=3,command=lambda:_jump_relative(app,-1)).pack(side='left',padx=2,pady=2)
    tk.Label(nav,text=' Pages ',padx=4).pack(side='left')
    buttons=tk.Frame(nav); buttons.pack(side='left',fill='x',expand=True)
    tk.Button(nav,text='▶',width=3,command=lambda:_jump_relative(app,1)).pack(side='right',padx=2,pady=2)
    app._pm_nav=nav
    def refresh():
        try:
            for b in buttons.winfo_children(): b.destroy()
            for i,p in enumerate(app.pages,1): tk.Button(buttons,text=str(i),width=3,command=lambda p=p:_jump_page(app,p)).pack(side='left',padx=2,pady=2)
        except Exception: pass
        try: root.after(600,refresh)
        except Exception: pass
    refresh()
    def equation():
        if app.active is None:
            if app.pages and app.pages[0].texts: app.activate(app.pages[0].texts[0]); app.active.focus_set()
            else: return
        w=tk.Toplevel(root); w.title('Math / Equation Builder'); w.geometry('940x470'); w.transient(root)
        tk.Label(w,text='Equation Builder',font=('Segoe UI',12,'bold')).pack(anchor='w',padx=12,pady=(10,2))
        tk.Label(w,text='Unicode equations remain editable and copyable.').pack(anchor='w',padx=12)
        e=tk.Entry(w,font=('Cambria Math',18)); e.pack(fill='x',padx=12,pady=8); e.focus_set()
        symbols='α β γ δ θ λ μ π σ φ ω Ω Δ Σ √ ∛ ∞ ∑ ∏ ∫ ∂ ∇ ± × ÷ ≠ ≈ ≤ ≥ ∝ → ⇒ ⇔ ∴ ∵ ∠ ° · ½ ⅓ ¼ ¾'.split()
        bar=tk.Frame(w); bar.pack(fill='x',padx=12)
        for s in symbols: tk.Button(bar,text=s,width=3,command=lambda s=s:e.insert('insert',s)).pack(side='left',padx=1,pady=1)
        row=tk.Frame(w); row.pack(fill='x',padx=12,pady=8)
        def add(v): e.insert('insert',v); e.focus_set()
        def frac():
            q=tk.Toplevel(w); q.title('Insert Fraction'); q.resizable(False,False)
            tk.Label(q,text='Numerator').grid(row=0,column=0,padx=8,pady=6); n=tk.Entry(q,width=24); n.grid(row=0,column=1,padx=8,pady=6)
            tk.Label(q,text='Denominator').grid(row=1,column=0,padx=8,pady=6); d=tk.Entry(q,width=24); d.grid(row=1,column=1,padx=8,pady=6)
            def ok(): add((n.get() or 'a')+'⁄'+(d.get() or 'b')); q.destroy()
            tk.Button(q,text='Insert',command=ok).grid(row=2,column=0,columnspan=2,pady=8); n.focus_set()
        for label,cmd in [('Fraction',frac),('x²',lambda:add('²')),('xₙ',lambda:add('ₙ')),('xⁿ',lambda:add('ⁿ')),('√( )',lambda:add('√()')),('→',lambda:add('→')),('±',lambda:add('±'))]: tk.Button(row,text=label,command=cmd,padx=10).pack(side='left',padx=2)
        tk.Label(w,text='Examples: v² = u² + 2as    Δx/Δt    F = ma    H₂SO₄    x₁ + x₂    a⁄b',font=('Consolas',10)).pack(anchor='w',padx=12,pady=8)
        def insert():
            if e.get(): app.active.insert('insert',e.get()); app.changed(); w.destroy()
        tk.Button(w,text='Insert Equation',command=insert).pack(pady=10)
    app.math=equation
    root.bind_all('<Control-Alt-m>',lambda e:(equation(),'break'),add='+')


def _jump_page(app,p):
    try:
        app.root.update_idletasks(); x=p.frame.winfo_x(); total=max(1,app.host.winfo_reqwidth()-app.canvas.winfo_width()); app.canvas.xview_moveto(max(0,min(1,x/total))); app.status.config(text='Page '+str(p.number))
    except Exception: pass

def _jump_relative(app,d):
    try:
        cur=app.canvas.canvasx(0); pages=app.pages; target=pages[0]
        for p in pages:
            if p.frame.winfo_x()>cur+20: target=p; break
        idx=pages.index(target)+d; idx=max(0,min(len(pages)-1,idx)); _jump_page(app,pages[idx])
    except Exception: pass


def _trace(frame,event,arg):
    if event=='return' and frame.f_code.co_name=='__init__' and frame.f_locals.get('self',None).__class__.__name__=='App':
        try: _enhance(frame.f_locals['self'])
        except Exception: pass
        return None
    return _trace


def _tk_init(self,*args,**kwargs):
    _orig_tk_init(self,*args,**kwargs); _canvas_fix(self)


tk.Tk.__init__=_tk_init
sys.settrace(_trace)
