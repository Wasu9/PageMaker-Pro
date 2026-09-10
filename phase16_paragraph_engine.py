"""PageMaker Pro Phase 16 — professional paragraph layout.

Adds paragraph-level layout metadata on top of the Phase 12 geometry engine:
alignment, spacing, indents, tabs, keep-with-next and widow/orphan controls.
The source string is never rewritten.
"""
from dataclasses import dataclass, field
from dtp_text_layout import DTPTextLayout


@dataclass
class ParagraphStyle:
    name: str = "Body"
    align: str = "left"
    line_spacing: float = 1.35
    space_before: float = 0.0
    space_after: float = 0.0
    left_indent: float = 0.0
    right_indent: float = 0.0
    first_line_indent: float = 0.0
    tabs: list = field(default_factory=list)
    keep_with_next: bool = False
    widow_lines: int = 2
    orphan_lines: int = 2


class ParagraphEngine:
    """Paragraph splitter/formatter independent from Tk widgets."""
    def __init__(self, font_size=12):
        self.font_size=float(font_size)
        self.styles={"Body":ParagraphStyle()}

    def split(self,text):
        # Keep paragraph terminators in their original text slices.
        parts=[]; start=0
        for i,ch in enumerate(text):
            if ch=="\n":
                parts.append((start,i+1,text[start:i+1])); start=i+1
        if start<len(text): parts.append((start,len(text),text[start:]))
        return parts

    def layout(self,text,width,height,style=None):
        style=style or self.styles["Body"]
        usable=max(1.0,float(width)-style.left_indent-style.right_indent)
        lh=max(1.0,self.font_size*style.line_spacing)
        engine=DTPTextLayout(font_size=self.font_size,line_height=lh)
        result=[]; cursor=0; y=style.space_before
        for start,end,para in self.split(text):
            content=para[:-1] if para.endswith("\n") else para
            first=style.first_line_indent
            pl=engine.layout_paragraph(content,usable,y=y,indent=style.left_indent,first_indent=first,align=style.align,line_height=lh)
            # Widow/orphan policy: expose constraints to the pagination layer.
            pl.keep_with_next=style.keep_with_next
            pl.widow_lines=style.widow_lines
            pl.orphan_lines=style.orphan_lines
            result.append((start,end,pl))
            y += len(pl.lines)*lh + style.space_after
            cursor=end
            if y>=height: break
        return result


def install(app):
    if getattr(app,"_pm16_installed",False): return
    app._pm16_installed=True
    app.pm16_paragraph_engine=ParagraphEngine
    app.pm16_styles={"Body":ParagraphStyle()}
