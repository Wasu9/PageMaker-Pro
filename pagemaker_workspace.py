"""PageMaker-style workspace controller for PageMaker Pro."""
from dataclasses import dataclass

import phase4_visual  # noqa: F401
import phase5_canvas  # noqa: F401
import phase5_bootstrap  # noqa: F401
import phase6_object_editing  # noqa: F401
import phase7_text_engine  # noqa: F401
import phase8_images  # noqa: F401
import phase9_tables  # noqa: F401
import phase10_master_pages  # noqa: F401
import phase11_export  # noqa: F401

@dataclass
class ViewState:
    active_page:int=0; zoom:float=.72; fit_page:bool=True; pasteboard:int=260

class WorkspaceController:
    def __init__(self,document=None): self.document=document; self.view=ViewState()
    def page_count(self): return len(getattr(self.document,"pages",[])) if self.document else 0
    def goto_page(self,index):
        count=self.page_count(); self.view.active_page=0 if not count else max(0,min(int(index),count-1)); return self.view.active_page
    def next_page(self): return self.goto_page(self.view.active_page+1)
    def previous_page(self): return self.goto_page(self.view.active_page-1)
    def set_zoom(self,zoom): self.view.fit_page=False; self.view.zoom=max(.25,min(4.,float(zoom))); return self.view.zoom
    def fit(self,viewport_width,viewport_height,page_width,page_height):
        if page_width<=0 or page_height<=0:return self.view.zoom
        self.view.fit_page=True; self.view.zoom=max(.25,min(1.,(float(viewport_width)-80)/page_width,(float(viewport_height)-80)/page_height)); return self.view.zoom
