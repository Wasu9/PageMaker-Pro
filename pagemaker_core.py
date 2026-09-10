"""Core DTP document model for PageMaker Pro."""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

@dataclass
class Rect:
    x: float
    y: float
    width: float
    height: float

@dataclass
class TextFrame:
    id: str
    rect: Rect
    column: int = 0
    story_id: Optional[str] = None
    text: str = ""
    locked: bool = False
    visible: bool = True
    thread_prev: Optional[str] = None
    thread_next: Optional[str] = None

@dataclass
class ImageObject:
    id: str
    rect: Rect
    path: str = ""
    locked: bool = False

@dataclass
class TableObject:
    id: str
    rect: Rect
    rows: int = 2
    cols: int = 2
    cells: List[List[str]] = field(default_factory=list)
    row_heights: List[float] = field(default_factory=list)
    col_widths: List[float] = field(default_factory=list)
    locked: bool = False
    border: bool = True
    cell_padding: float = 5.0

    def __post_init__(self):
        self.rows=max(1,int(self.rows)); self.cols=max(1,int(self.cols))
        if not self.cells: self.cells=[["" for _ in range(self.cols)] for _ in range(self.rows)]
        else:
            self.cells=[list(r[:self.cols])+[""]*max(0,self.cols-len(r)) for r in self.cells[:self.rows]]
            while len(self.cells)<self.rows: self.cells.append([""]*self.cols)
        if len(self.row_heights)!=self.rows: self.row_heights=[self.rect.height/self.rows]*self.rows
        if len(self.col_widths)!=self.cols: self.col_widths=[self.rect.width/self.cols]*self.cols

@dataclass
class Page:
    number: int
    width: float = 794
    height: float = 1123
    margin: float = 45
    columns: int = 2
    column_gap: float = 24
    master: str = "A-Master"
    objects: List[Any] = field(default_factory=list)
    frame_ids: List[str] = field(default_factory=list)

@dataclass
class MasterPage:
    name: str = "A-Master"
    width: float = 794
    height: float = 1123
    margin: float = 45
    columns: int = 2
    column_gap: float = 24
    header: str = ""
    footer: str = ""
    watermark: str = ""
    border: bool = True

@dataclass
class Story:
    id: str
    text: str = ""
    frame_ids: List[str] = field(default_factory=list)

class Document:
    def __init__(self):
        self.page_width=794; self.page_height=1123; self.pages=[]
        self.masters={"A-Master":MasterPage()}; self.stories={}; self.frames={}; self.images={}; self.tables={}
        self.next_page_number=1; self._id_counter=1

    def new_id(self,prefix="obj"):
        value=f"{prefix}-{self._id_counter}"; self._id_counter+=1; return value

    def add_page(self,master="A-Master"):
        m=self.masters[master]; p=Page(self.next_page_number,self.page_width,self.page_height,m.margin,m.columns,m.column_gap,master)
        self.pages.append(p); self.next_page_number+=1; return p

    def add_story(self,text=""):
        s=Story(self.new_id("story"),text); self.stories[s.id]=s; return s

    def add_text_frame(self,page,rect,story=None,column=0):
        f=TextFrame(self.new_id("frame"),rect,column,story.id if story else None); self.frames[f.id]=f
        page.objects.append(f.id); page.frame_ids.append(f.id)
        if story: story.frame_ids.append(f.id)
        return f

    def add_image(self,page,rect,path=""):
        image=ImageObject(self.new_id("image"),rect,path or ""); self.images[image.id]=image; page.objects.append(image.id); return image

    def add_table(self,page,rect,rows=2,cols=2):
        table=TableObject(self.new_id("table"),rect,rows,cols); self.tables[table.id]=table; page.objects.append(table.id); return table

    def find_frame(self,frame_id): return self.frames.get(frame_id)
    def find_image(self,image_id): return self.images.get(image_id)
    def find_table(self,table_id): return self.tables.get(table_id)

    def frame_order(self,page):
        return sorted((self.frames[x] for x in page.frame_ids if x in self.frames),key=lambda f:(f.column,f.rect.y,f.rect.x))

    def move_frame(self,frame_id,x,y):
        f=self.frames.get(frame_id)
        if not f or f.locked:return False
        f.rect.x=float(x); f.rect.y=float(y); return True

    def resize_frame(self,frame_id,width,height):
        f=self.frames.get(frame_id)
        if not f or f.locked:return False
        f.rect.width=max(20.,float(width)); f.rect.height=max(20.,float(height)); return True

    def move_image(self,image_id,x,y):
        i=self.images.get(image_id)
        if not i or i.locked:return False
        i.rect.x=float(x); i.rect.y=float(y); return True

    def resize_image(self,image_id,width,height):
        i=self.images.get(image_id)
        if not i or i.locked:return False
        i.rect.width=max(20.,float(width)); i.rect.height=max(20.,float(height)); return True

    def move_table(self,table_id,x,y):
        t=self.tables.get(table_id)
        if not t or t.locked:return False
        t.rect.x=float(x); t.rect.y=float(y); return True

    def resize_table(self,table_id,width,height):
        t=self.tables.get(table_id)
        if not t or t.locked:return False
        t.rect.width=max(30.,float(width)); t.rect.height=max(20.,float(height)); return True

    def serialize(self):
        return {"version":6,"page_width":self.page_width,"page_height":self.page_height,
                "masters":{k:asdict(v) for k,v in self.masters.items()},"pages":[asdict(p) for p in self.pages],
                "stories":{k:asdict(v) for k,v in self.stories.items()},"frames":{k:asdict(v) for k,v in self.frames.items()},
                "images":{k:asdict(v) for k,v in self.images.items()},"tables":{k:asdict(v) for k,v in self.tables.items()},
                "next_page_number":self.next_page_number,"id_counter":self._id_counter}
