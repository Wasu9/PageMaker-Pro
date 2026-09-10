"""Phase 22: professional image and table object controls.

This layer keeps object geometry authoritative in the canonical Document and
adds safe, UI-independent operations used by the editor and future renderer.
"""
from dataclasses import dataclass

@dataclass
class ImageTransform:
    x: float
    y: float
    width: float
    height: float
    fit_mode: str = "fit"
    wrap: bool = False
    locked: bool = False

@dataclass
class TableCellFormat:
    text: str = ""
    bold: bool = False
    italic: bool = False
    align: str = "left"
    valign: str = "middle"

class ObjectEditor:
    FIT_MODES = ("fit", "fill", "crop")

    def __init__(self, document):
        self.document = document

    def transform_image(self, image_id, x=None, y=None, width=None, height=None,
                        fit_mode=None, wrap=None, keep_ratio=False):
        image = self.document.find_image(image_id)
        if not image or image.locked:
            return False
        if fit_mode is not None and fit_mode in self.FIT_MODES:
            image.fit_mode = fit_mode
        if wrap is not None:
            image.wrap = bool(wrap)
        if x is not None: image.rect.x = float(x)
        if y is not None: image.rect.y = float(y)
        if width is not None or height is not None:
            nw = max(20., float(width if width is not None else image.rect.width))
            nh = max(20., float(height if height is not None else image.rect.height))
            if keep_ratio and image.rect.width > 0 and image.rect.height > 0:
                ratio = image.rect.width / image.rect.height
                if width is not None and height is None: nh = nw / ratio
                elif height is not None and width is None: nw = nh * ratio
            image.rect.width, image.rect.height = nw, nh
        return True

    def reorder(self, page, object_id, direction):
        if object_id not in page.objects:
            return False
        i = page.objects.index(object_id)
        if direction == "front": j = len(page.objects) - 1
        elif direction == "back": j = 0
        elif direction == "forward": j = min(len(page.objects)-1, i+1)
        elif direction == "backward": j = max(0, i-1)
        else: return False
        if i != j:
            page.objects.pop(i); page.objects.insert(j, object_id)
        return True

    def resize_table(self, table_id, width=None, height=None):
        table = self.document.find_table(table_id)
        if not table or table.locked: return False
        oldw, oldh = table.rect.width, table.rect.height
        if width is not None:
            neww=max(30.,float(width)); scale=neww/oldw if oldw else 1
            table.rect.width=neww; table.col_widths=[v*scale for v in table.col_widths]
        if height is not None:
            newh=max(20.,float(height)); scale=newh/oldh if oldh else 1
            table.rect.height=newh; table.row_heights=[v*scale for v in table.row_heights]
        return True

    def resize_row(self, table_id, row, height):
        table=self.document.find_table(table_id)
        if not table or table.locked or not 0 <= int(row) < table.rows:return False
        table.row_heights[int(row)]=max(12.,float(height)); table.rect.height=sum(table.row_heights); return True

    def resize_column(self, table_id, col, width):
        table=self.document.find_table(table_id)
        if not table or table.locked or not 0 <= int(col) < table.cols:return False
        table.col_widths[int(col)]=max(20.,float(width)); table.rect.width=sum(table.col_widths); return True

    def set_cell(self, table_id, row, col, text=None, bold=None, italic=None,
                 align=None, valign=None):
        table=self.document.find_table(table_id)
        if not table or table.locked or not (0 <= int(row) < table.rows and 0 <= int(col) < table.cols): return False
        # Formatting metadata is stored separately when supported; never corrupt source text.
        table.cells[int(row)][int(col)] = str(text) if text is not None else table.cells[int(row)][int(col)]
        formats=getattr(table,"cell_formats",None)
        if formats is None: formats={}; table.cell_formats=formats
        key=f"{int(row)},{int(col)}"
        current=dict(formats.get(key,{}))
        for k,v in (("bold",bold),("italic",italic),("align",align),("valign",valign)):
            if v is not None: current[k]=v
        formats[key]=current
        return True

    def merge_cells(self, table_id, r1, c1, r2, c2):
        table=self.document.find_table(table_id)
        if not table or table.locked:return False
        r1,c1,r2,c2=map(int,(r1,c1,r2,c2))
        if not(0<=r1<=r2<table.rows and 0<=c1<=c2<table.cols):return False
        spans=getattr(table,"merged_cells",[])
        spans.append((r1,c1,r2,c2)); table.merged_cells=spans
        return True

    def split_merge(self, table_id, r1, c1, r2, c2):
        table=self.document.find_table(table_id)
        if not table or table.locked:return False
        target=(int(r1),int(c1),int(r2),int(c2)); spans=getattr(table,"merged_cells",[])
        if target not in spans:return False
        spans.remove(target); table.merged_cells=spans; return True

def install(app):
    doc=getattr(app,"document",None)
    if doc is None:return None
    editor=ObjectEditor(doc); app.pm22_objects=editor
    return editor
