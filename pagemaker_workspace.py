"""PageMaker-style workspace controller for PageMaker Pro.

Keeps the document model independent from the screen. The UI can use this
controller to show one active page, navigate by page number, and maintain a
pasteboard around the page.
"""
from dataclasses import dataclass

@dataclass
class ViewState:
    active_page: int = 0
    zoom: float = 0.72
    fit_page: bool = True
    pasteboard: int = 260

class WorkspaceController:
    def __init__(self, document=None):
        self.document = document
        self.view = ViewState()

    def page_count(self):
        return len(getattr(self.document, "pages", [])) if self.document else 0

    def goto_page(self, index):
        count = self.page_count()
        if not count:
            self.view.active_page = 0
            return 0
        self.view.active_page = max(0, min(int(index), count - 1))
        return self.view.active_page

    def next_page(self):
        return self.goto_page(self.view.active_page + 1)

    def previous_page(self):
        return self.goto_page(self.view.active_page - 1)

    def set_zoom(self, zoom):
        self.view.fit_page = False
        self.view.zoom = max(0.25, min(4.0, float(zoom)))
        return self.view.zoom

    def fit(self, viewport_width, viewport_height, page_width, page_height):
        if page_width <= 0 or page_height <= 0:
            return self.view.zoom
        self.view.fit_page = True
        self.view.zoom = max(0.25, min(1.0,
            (float(viewport_width) - 80) / page_width,
            (float(viewport_height) - 80) / page_height))
        return self.view.zoom
