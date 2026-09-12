import tkinter as tk
import sitecustomize_base as _base

globals().update({k:v for k,v in _base.__dict__.items() if k not in {'__name__','__loader__','__package__','__spec__'}})

try:
    import phase25_editor_fixes as _p25
    _orig_tk_init = tk.Tk.__init__
    def _find_app(root):
        stack=list(root.winfo_children())
        while stack:
            w=stack.pop()
            owner=getattr(w,'app',None)
            if owner is not None and hasattr(owner,'pages') and hasattr(owner,'settings'):
                return owner
            try: stack.extend(w.winfo_children())
            except Exception: pass
        return None
    def _late_install(root):
        app=_find_app(root)
        if app is None:
            try: root.after(100,_late_install,root)
            except Exception: pass
            return
        try:
            _p25._lock_columns(app)
            app.image=lambda:_base._import_image(app)
            app.math=lambda:_p25.math_dialog(app)
            app.table=lambda:_p25.table_dialog(app,False)
            app.match_table=lambda:_p25.table_dialog(app,True)
            root.bind_all('<Control-Shift-M>',lambda e:_p25.table_dialog(app,True),add='+')
            root.bind_all('<Control-Shift-=>',lambda e:_p25.style_selection(app,'sup'),add='+')
            root.bind_all('<Control-Shift-->',lambda e:_p25.style_selection(app,'sub'),add='+')
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
                        sub=menu.nametowidget(menu.entrycget(i,'menu'))
                        sub.add_separator(); sub.add_command(label='Match Columns Table…',command=app.match_table); break
                except Exception: pass
            app.status.config(text='Phase 25: columns locked • Ctrl+A selects full column')
            app._pm25_active=True
        except Exception:
            try: root.after(100,_late_install,root)
            except Exception: pass
    def _tk_init(self,*a,**k):
        _orig_tk_init(self,*a,**k)
        try: self.after_idle(_late_install,self)
        except Exception: pass
    tk.Tk.__init__ = _tk_init
except Exception:
    pass
