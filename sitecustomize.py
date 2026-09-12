import tkinter as tk
import sitecustomize_base as _base

# Phase 26 image resize module is intentionally separate so image interaction
# can evolve without touching the canonical document/flow implementation.
try:
    import phase26_image_resize as _p26img
except Exception:
    _p26img = None

globals().update({k:v for k,v in _base.__dict__.items() if k not in {'__name__','__loader__','__package__','__spec__'}})

try:
    import phase25_editor_fixes as _p25
    _orig_tk_init = tk.Tk.__init__

    def _guard_fixed(app, w, event):
        state = int(getattr(event, 'state', 0)); key = str(getattr(event, 'keysym', '')).lower(); ctrl = bool(state & 0x0004)
        if ctrl and key == 'a': return _p25.select_column(app, w)
        if ctrl and key == 'c' and getattr(app, '_pm25_column_widgets', None): return _p25.copy_column(app, event)
        if ctrl and key == 'v': return _p25.paste(app, w)
        if getattr(app, '_pm_select_mode', True): return 'break'
        return None
    _p25._guard = _guard_fixed

    def _lock_columns_fixed(app):
        for p in getattr(app, 'pages', []):
            for w in getattr(p, 'texts', []):
                try: w.tag_configure('pm25_column_selection', background='#4a78c2', foreground='#ffffff')
                except Exception: pass
                tag = 'PM26_' + str(id(w)); tags = list(w.bindtags())
                if tag in tags: continue
                w.bindtags((tag,) + tuple(tags))
                w.bind_class(tag, '<Button-1>', lambda e,w=w:_guard_fixed(app,w,e))
                w.bind_class(tag, '<B1-Motion>', lambda e,w=w:_guard_fixed(app,w,e))
                w.bind_class(tag, '<ButtonRelease-1>', lambda e,w=w:_guard_fixed(app,w,e))
                w.bind_class(tag, '<Control-KeyPress-a>', lambda e,w=w:_p25.select_column(app,w))
                w.bind_class(tag, '<Control-KeyPress-A>', lambda e,w=w:_p25.select_column(app,w))
                w.bind_class(tag, '<Control-KeyPress-c>', lambda e:_p25.copy_column(app,e))
                w.bind_class(tag, '<Control-KeyPress-C>', lambda e:_p25.copy_column(app,e))
                w.bind_class(tag, '<Control-KeyPress-v>', lambda e,w=w:_p25.paste(app,w))
                w.bind_class(tag, '<Control-KeyPress-V>', lambda e,w=w:_p25.paste(app,w))
        app._pm25_lock_columns=True; app._pm26_columns_bound=True
        if _p26img: _p26img.install(app)

    _p25._lock_columns = _lock_columns_fixed

    def _find_app(root):
        stack=list(root.winfo_children())
        while stack:
            w=stack.pop(); owner=getattr(w,'app',None)
            if owner is not None and hasattr(owner,'pages') and hasattr(owner,'settings'): return owner
            try: stack.extend(w.winfo_children())
            except Exception: pass
        return None

    def _make_professional_nav(app):
        old=getattr(app,'_pm_nav',None)
        if old is not None and getattr(app,'_pm26_nav',False): _refresh_professional_nav(app); return
        if old is not None:
            try: old.destroy()
            except Exception: pass
        nav=tk.Frame(app.root,height=46,bd=0,highlightthickness=1,highlightbackground='#c7cbd1'); nav.pack(side='bottom',fill='x'); nav.pack_propagate(False)
        prev=tk.Button(nav,text='  ◀  ',width=5,relief='flat',command=lambda:_show_page(app,app.workspace.previous_page())); prev.pack(side='left',padx=(6,2),pady=5)
        page_label=tk.Label(nav,text='Page 1 / 1',width=12,font=('Segoe UI',9,'bold'),anchor='center'); page_label.pack(side='left',padx=2)
        first=tk.Button(nav,text='|◀',width=4,relief='flat',command=lambda:_show_page(app,0)); first.pack(side='left',padx=2,pady=5)
        rail=tk.Frame(nav,bd=0); rail.pack(side='left',fill='both',expand=True,padx=6,pady=3)
        rail_canvas=tk.Canvas(rail,height=36,highlightthickness=0,bd=0); rail_canvas.pack(side='top',fill='both',expand=True)
        rail_inner=tk.Frame(rail_canvas,bd=0); rail_window=rail_canvas.create_window((0,18),window=rail_inner,anchor='w')
        rail_inner.bind('<Configure>',lambda e:rail_canvas.configure(scrollregion=rail_canvas.bbox('all')))
        rail_canvas.bind('<Configure>',lambda e:rail_canvas.itemconfigure(rail_window,height=max(30,e.height-2)))
        last=tk.Button(nav,text='▶|',width=4,relief='flat',command=lambda:_show_page(app,len(app.pages)-1)); last.pack(side='right',padx=2,pady=5)
        nxt=tk.Button(nav,text='  ▶  ',width=5,relief='flat',command=lambda:_show_page(app,app.workspace.next_page())); nxt.pack(side='right',padx=(2,6),pady=5)
        app._pm_nav=nav; app._pm_page_buttons=rail_inner; app._pm26_nav_canvas=rail_canvas; app._pm26_nav_label=page_label; app._pm26_nav_prev=prev; app._pm26_nav_next=nxt; app._pm26_nav_first=first; app._pm26_nav_last=last; app._pm26_nav=True
        _refresh_professional_nav(app)

    def _refresh_professional_nav(app):
        nav=getattr(app,'_pm_nav',None); buttons=getattr(app,'_pm_page_buttons',None)
        if nav is None or buttons is None:return
        try:
            current=int(app.workspace.view.active_page); total=len(app.pages); app._pm26_nav_label.config(text=f'Page {current+1} / {total}')
            for child in buttons.winfo_children(): child.destroy()
            bg=app.page_bg() if hasattr(app,'page_bg') else '#ffffff'; active_bg='#3973d4'
            for i,p in enumerate(app.pages):
                active=i==current
                b=tk.Button(buttons,text=str(p.number),width=4,relief='sunken' if active else 'flat',bd=1,font=('Segoe UI',9,'bold' if active else 'normal'),bg=active_bg if active else bg,fg='#ffffff' if active else '#202124',activebackground=active_bg,activeforeground='#ffffff',cursor='hand2',command=lambda i=i:_show_page(app,i))
                b.pack(side='left',padx=2,pady=4)
                if active:b.configure(state='disabled')
            app._pm26_nav_prev.config(state='disabled' if current<=0 else 'normal'); app._pm26_nav_next.config(state='disabled' if current>=total-1 else 'normal'); app._pm26_nav_first.config(state='disabled' if current<=0 else 'normal'); app._pm26_nav_last.config(state='disabled' if current>=total-1 else 'normal')
            app._pm26_nav_canvas.update_idletasks(); children=buttons.winfo_children()
            if children and current<len(children):
                target=children[current]; x1=target.winfo_x(); width=max(1,app._pm26_nav_canvas.winfo_width()); bbox=app._pm26_nav_canvas.bbox('all')
                if bbox and bbox[2]>width: app._pm26_nav_canvas.xview_moveto(max(0,min(1,(x1-width/3)/max(1,bbox[2]-width))))
        except Exception: pass
    _base._refresh_nav=_refresh_professional_nav

    def _late_install(root):
        app=_find_app(root)
        if app is None:
            try: root.after(100,_late_install,root)
            except Exception: pass
            return
        try:
            _p25._lock_columns(app)
            app.image=lambda:_base._import_image(app); app.math=lambda:_p25.math_dialog(app); app.table=lambda:_p25.table_dialog(app,False); app.match_table=lambda:_p25.table_dialog(app,True)
            root.bind_all('<Control-Shift-M>',lambda e:_p25.table_dialog(app,True),add='+'); root.bind_all('<Control-Shift-=>',lambda e:_p25.style_selection(app,'sup'),add='+'); root.bind_all('<Control-Shift-->',lambda e:_p25.style_selection(app,'sub'),add='+')
            for child in app.left.winfo_children():
                try:
                    label=child.cget('text')
                    if isinstance(child,tk.Button) and 'Image' in label: child.configure(command=app.image)
                    elif isinstance(child,tk.Button) and 'Math' in label: child.configure(command=app.math)
                    elif isinstance(child,tk.Button) and 'Table' in label: child.configure(command=app.table)
                except Exception: pass
            menu=root.nametowidget(root['menu'])
            for i in range(menu.index('end')+1):
                try:
                    if menu.entrycget(i,'label')=='Insert':
                        sub=menu.nametowidget(menu.entrycget(i,'menu')); sub.add_separator(); sub.add_command(label='Match Columns Table...',command=app.match_table); break
                except Exception: pass
            _make_professional_nav(app); app.status.config(text='Professional workspace ready | Ctrl+A = full column | Ctrl+V = image/text')
            app._pm25_active=True
            def maintain():
                try:
                    _p25._lock_columns(app)
                    if _p26img: _p26img.install(app)
                    _refresh_professional_nav(app); root.after(350,maintain)
                except Exception: pass
            if not getattr(app,'_pm26_maintain',False): app._pm26_maintain=True; root.after(350,maintain)
        except Exception:
            try: root.after(150,_late_install,root)
            except Exception: pass

    def _tk_init(self,*a,**k):
        _orig_tk_init(self,*a,**k)
        try: self.after_idle(_late_install,self)
        except Exception: pass
    tk.Tk.__init__=_tk_init
except Exception:
    pass
