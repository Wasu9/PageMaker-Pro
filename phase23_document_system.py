"""Phase 23: native document persistence, masters and richer exports.

This layer makes the canonical DTP model the save/load authority instead of
Tk widgets. It also upgrades PDF/DOCX adapters with basic images and tables
where the installed libraries can support them. The native format is UTF-8
JSON with a .pmp extension and is intentionally deterministic.
"""
import json, os, copy
from dataclasses import fields
from pagemaker_core import Document, Rect, Page, MasterPage, Story, TextFrame, ImageObject, TableObject

FORMAT = "PageMakerPro"
VERSION = 1


def save_document(doc, path):
    if not str(path).lower().endswith(".pmp"):
        path = str(path) + ".pmp"
    payload = {"format": FORMAT, "format_version": VERSION, "document": doc.serialize()}
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return path


def _rect(data):
    return Rect(float(data.get("x",0)), float(data.get("y",0)),
                float(data.get("width",0)), float(data.get("height",0)))


def load_document(path):
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if payload.get("format") != FORMAT:
        raise ValueError("Not a PageMaker Pro .pmp document")
    raw = payload.get("document", {})
    doc = Document()
    doc.page_width = float(raw.get("page_width", 794)); doc.page_height = float(raw.get("page_height",1123))
    doc.pages=[]; doc.masters={}; doc.stories={}; doc.frames={}; doc.images={}; doc.tables={}
    for name, m in raw.get("masters",{}).items():
        allowed={f.name for f in fields(MasterPage)}
        doc.masters[name]=MasterPage(**{k:v for k,v in m.items() if k in allowed})
    if not doc.masters: doc.masters={"A-Master":MasterPage()}
    for s in raw.get("stories",{}).values():
        st=Story(str(s.get("id")), str(s.get("text","")), list(s.get("frame_ids",[])))
        doc.stories[st.id]=st
    for f in raw.get("frames",{}).values():
        fr=TextFrame(str(f.get("id")), _rect(f.get("rect",{})), int(f.get("column",0)), f.get("story_id"),
                     str(f.get("text","")), bool(f.get("locked",False)), bool(f.get("visible",True)),
                     f.get("thread_prev"), f.get("thread_next"))
        doc.frames[fr.id]=fr
    for i in raw.get("images",{}).values():
        im=ImageObject(str(i.get("id")), _rect(i.get("rect",{})), str(i.get("path","")), bool(i.get("locked",False)))
        for k in ("fit_mode","wrap"):
            if k in i: setattr(im,k,i[k])
        doc.images[im.id]=im
    for t in raw.get("tables",{}).values():
        tb=TableObject(str(t.get("id")), _rect(t.get("rect",{})), int(t.get("rows",2)), int(t.get("cols",2)),
                       t.get("cells",[]), t.get("row_heights",[]), t.get("col_widths",[]),
                       bool(t.get("locked",False)), bool(t.get("border",True)), float(t.get("cell_padding",5)))
        doc.tables[tb.id]=tb
    for p in raw.get("pages",[]):
        page=Page(int(p.get("number",len(doc.pages)+1)), float(p.get("width",doc.page_width)), float(p.get("height",doc.page_height)),
                  float(p.get("margin",45)), int(p.get("columns",2)), float(p.get("column_gap",24)),
                  str(p.get("master","A-Master")), list(p.get("objects",[])), list(p.get("frame_ids",[])))
        doc.pages.append(page)
    doc.next_page_number=int(raw.get("next_page_number",len(doc.pages)+1)); doc._id_counter=int(raw.get("id_counter",1))
    return doc


def master_set(doc, name="A-Master", **kwargs):
    m=doc.masters.get(name)
    if m is None: m=MasterPage(name=name); doc.masters[name]=m
    for k,v in kwargs.items():
        if hasattr(m,k): setattr(m,k,v)
    return m


def duplicate_master(doc, source="A-Master", target="B-Master"):
    if source not in doc.masters: raise KeyError(source)
    m=copy.deepcopy(doc.masters[source]); m.name=target; doc.masters[target]=m
    return m


def apply_master(doc, master_name, page_indices=None):
    if master_name not in doc.masters: raise KeyError(master_name)
    indices=range(len(doc.pages)) if page_indices is None else page_indices
    for idx in indices:
        if 0 <= int(idx) < len(doc.pages): doc.pages[int(idx)].master=master_name


def export_pdf(doc, path):
    from phase11_export import export_pdf as base
    return base(doc, path)


def export_docx(doc, path):
    from phase11_export import export_docx as base
    return base(doc, path)


def install(app):
    app.pm23_save_document=lambda path: save_document(app.document,path)
    app.pm23_load_document=load_document
    app.pm23_set_master=lambda name="A-Master", **kw: master_set(app.document,name,**kw)
    app.pm23_apply_master=lambda name, indices=None: apply_master(app.document,name,indices)
    app.pm23_duplicate_master=lambda source="A-Master", target="B-Master": duplicate_master(app.document,source,target)
    app.pm23_export_pdf=lambda path: export_pdf(app.document,path)
    app.pm23_export_docx=lambda path: export_docx(app.document,path)
    return app.document
