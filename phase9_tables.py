"""PageMaker Pro Phase 9 — editable table objects for question papers."""
import tkinter as tk
from tkinter import simpledialog

import phase5_canvas as p5


def _install(app):
    if getattr(app, "_pm9_installed", False): return
    app._pm9_installed=True

    def current_table():
        oid=getattr(app,"_pm_selected_object",None)
        return getattr(app,"document",None).tables.get(oid) if getattr(app,"document",None) else None

    old_draw=p5._draw_page
    if not getattr(old_draw,"_pm9_wrapped",False):
        def draw(app_,page,_old=old_draw):
            _old(app_,page)
            p= p5._doc_page(app_,page); c=p5._page_canvas(page)
            if not p or c is None:return
            z=p5._zoom(app_)
            for oid in p.objects:
                t=getattr(app_.document,"tables",{}).get(oid)
                if not t: continue
                r=t.rect; x,y=r.x*z,r.y*z
                x2,y2=(r.x+r.width)*z,(r.y+r.height)*z
                selected=oid in getattr(app_,"_pm5_selected",set())
                c.create_rectangle(x,y,x2,y2,fill="white",outline="#3973d4" if selected else "#555",width=2 if selected else 1,tags=("pm5","table",oid))
                yy=y
                for ri,rh in enumerate(t.row_heights):
                    xx=x
                    for ci,cw in enumerate(t.col_widths):
                        c.create_rectangle(xx,yy,xx+cw*z,yy+rh*z,outline="#555" if t.border else "",tags=("pm5","table-cell",oid,f"cell-{ri}-{ci}"))
                        text=t.cells[ri][ci] if ri<len(t.cells) and ci<len(t.cells[ri]) else ""
                        if text: c.create_text(xx+t.cell_padding*z,yy+rh*z/2,anchor="w",text=text,fill="#111",tags=("pm5","table-text",oid))
                        xx+=cw*z
                    yy+=rh*z
        draw._pm9_wrapped=True; p5._draw_page=draw

    def insert():
        if not app.pages:return
        rows=simpledialog.askinteger("Insert Table","Rows:",initialvalue=3,minvalue=1,maxvalue=100,parent=app.root)
        if rows is None:return
        cols=simpledialog.askinteger("Insert Table","Columns:",initialvalue=2,minvalue=1,maxvalue=30,parent=app.root)
        if cols is None:return
        page=app.pages[max(0,min(len(app.pages)-1,getattr(app.workspace.view,"active_page",0)))]
        p=p5._doc_page(app,page)
        if not p:return
        w= min(600,p.width-2*p.margin); h=min(260,max(80,rows*32))
        t=app.document.add_table(p,p5.Rect(p.margin,p.margin,w,h),rows,cols)
        app._pm_selected_object=t.id; app._pm5_selected={t.id}; app.dirty=True; p5.refresh_all(app)
        app.status.config(text=f"Table {rows} × {cols} inserted — double-click a cell to edit")

    def edit_cell(event):
        page=event.widget._pm9_page
        c=event.widget
        z=p5._zoom(app); p=p5._doc_page(app,page)
        if not p:return
        px,py=event.x/z,event.y/z
        for oid in p.objects:
            t=getattr(app.document,"tables",{}).get(oid)
            if not t:continue
            if not(t.rect.x<=px<=t.rect.x+t.rect.width and t.rect.y<=py<=t.rect.y+t.rect.height):continue
            xx=t.rect.x
            for ci,cw in enumerate(t.col_widths):
                yy=t.rect.y
                if xx<=px<=xx+cw:
                    for ri,rh in enumerate(t.row_heights):
                        if yy<=py<=yy+rh:
                            old=t.cells[ri][ci]
                            value=simpledialog.askstring("Edit Cell",f"Row {ri+1}, Column {ci+1}:",initialvalue=old,parent=app.root)
                            if value is not None:
                                t.cells[ri][ci]=value; app._pm_selected_object=oid; app._pm5_selected={oid}; app.dirty=True; p5.refresh_all(app)
                            return
                        yy+=rh
                xx+=cw

    def select_table(event):
        page=event.widget._pm9_page; c=event.widget; z=p5._zoom(app); p=p5._doc_page(app,page)
        if not p:return
        px,py=event.x/z,event.y/z
        for oid in reversed(p.objects):
            t=getattr(app.document,"tables",{}).get(oid)
            if t and t.rect.x<=px<=t.rect.x+t.rect.width and t.rect.y<=py<=t.rect.y+t.rect.height:
                app._pm_selected_object=oid; app._pm5_selected={oid}; p5._draw_page(app,page); app.status.config(text=f"Selected Table | {t.rows} × {t.cols}"); return

    def late():
        for page in getattr(app,"pages",[]):
            c=p5._page_canvas(page)
            if c and not getattr(c,"_pm9_bound",False):
                c._pm9_bound=True; c._pm9_page=page
                c.bind("<Button-1>",select_table,add="+")
                c.bind("<Double-Button-1>",edit_cell,add="+")

    bar=tk.Frame(app.top,bd=0); bar.pack(side="left",padx=3)
    tk.Button(bar,text="Table",relief="flat",command=insert).pack(side="left")
    tk.Button(bar,text="Edit Cell",relief="flat",command=lambda:None).pack(side="left")
    app.pm9_insert_table=insert
    app.root.after(250,late)


def install(app):
    try:_install(app)
    except Exception:pass

_old=p5._install_app
if not getattr(_old,"_pm9_wrapped",False):
    def wrapped(app): _old(app); install(app)
    wrapped._pm9_wrapped=True; p5._install_app=wrapped
