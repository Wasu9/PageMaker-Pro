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


@dataclass
class ImageObject:
    id: str
    rect: Rect
    path: str = ""
    locked: bool = False


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
        self.page_width = 794
        self.page_height = 1123
        self.pages: List[Page] = []
        self.masters: Dict[str, MasterPage] = {"A-Master": MasterPage()}
        self.stories: Dict[str, Story] = {}
        self.frames: Dict[str, TextFrame] = {}
        self.images: Dict[str, ImageObject] = {}
        self.next_page_number = 1
        self._id_counter = 1

    def new_id(self, prefix="obj"):
        value = f"{prefix}-{self._id_counter}"
        self._id_counter += 1
        return value

    def add_page(self, master="A-Master"):
        m = self.masters[master]
        p = Page(self.next_page_number, self.page_width, self.page_height,
                 m.margin, m.columns, m.column_gap, master)
        self.pages.append(p)
        self.next_page_number += 1
        return p

    def add_story(self, text=""):
        s = Story(self.new_id("story"), text)
        self.stories[s.id] = s
        return s

    def add_text_frame(self, page: Page, rect: Rect, story: Optional[Story] = None,
                       column=0):
        f = TextFrame(self.new_id("frame"), rect, column,
                      story.id if story else None)
        self.frames[f.id] = f
        page.objects.append(f.id)
        page.frame_ids.append(f.id)
        if story:
            story.frame_ids.append(f.id)
        return f

    def frame_order(self, page: Page):
        return sorted((self.frames[x] for x in page.frame_ids if x in self.frames),
                      key=lambda f: (f.column, f.rect.y, f.rect.x))

    def find_frame(self, frame_id):
        return self.frames.get(frame_id)

    def move_frame(self, frame_id, x, y):
        frame = self.frames.get(frame_id)
        if not frame or frame.locked:
            return False
        frame.rect.x = float(x)
        frame.rect.y = float(y)
        return True

    def resize_frame(self, frame_id, width, height):
        frame = self.frames.get(frame_id)
        if not frame or frame.locked:
            return False
        frame.rect.width = max(20.0, float(width))
        frame.rect.height = max(20.0, float(height))
        return True

    def serialize(self):
        return {
            "version": 3,
            "page_width": self.page_width,
            "page_height": self.page_height,
            "masters": {k: asdict(v) for k, v in self.masters.items()},
            "pages": [asdict(p) for p in self.pages],
            "stories": {k: asdict(v) for k, v in self.stories.items()},
            "frames": {k: asdict(v) for k, v in self.frames.items()},
            "images": {k: asdict(v) for k, v in self.images.items()},
            "next_page_number": self.next_page_number,
            "id_counter": self._id_counter,
        }
