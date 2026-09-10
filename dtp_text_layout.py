"""Phase 12 core DTP text layout engine.

Pure-Python, UI-independent line breaking and frame pagination.  It deliberately
never rewrites Unicode text: the original code points remain the Story source.
A Tk font measurement callback can be supplied by the UI for real font metrics;
a deterministic Unicode-aware fallback is used for tests/headless operation.
"""
from dataclasses import dataclass
import unicodedata


@dataclass
class GlyphRun:
    text: str
    start: int
    end: int
    advance: float


@dataclass
class LayoutLine:
    start: int
    end: int
    text: str
    advance: float
    x: float
    y: float
    justified: bool = False
    extra_space: float = 0.0


@dataclass
class ParagraphLayout:
    start: int
    end: int
    lines: list


class DTPTextLayout:
    """Small production-oriented text layout primitive for paper DTP.

    The engine works in document pixels.  It is intentionally independent of
    Tk so it can later back PDF, DOCX and a native canvas renderer consistently.
    """
    def __init__(self, measure=None, font_size=12.0, line_height=None):
        self.measure = measure
        self.font_size = float(font_size)
        self.line_height = float(line_height or max(12.0, self.font_size * 1.35))

    def advance(self, ch):
        if not ch:
            return 0.0
        if self.measure:
            try:
                return max(0.0, float(self.measure(ch)))
            except Exception:
                pass
        if ch == "\t":
            return self.font_size * 2.0
        if unicodedata.combining(ch):
            return 0.0
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            return self.font_size
        cat = unicodedata.category(ch)
        if cat.startswith("P"):
            return self.font_size * 0.48
        if cat.startswith("M"):
            return 0.0
        if ch.isspace():
            return self.font_size * 0.28
        return self.font_size * 0.55

    def text_width(self, text):
        return sum(self.advance(c) for c in text)

    @staticmethod
    def _breakable(ch, prev=""):
        if ch in " \t\u200b\u00a0":
            return True
        if ch in "-/\\|,.;:!?)]}»”’、。，！？；：":
            return True
        return False

    def _last_break(self, text, start, end):
        for i in range(end, start, -1):
            if self._breakable(text[i-1], text[i-2] if i > start else ""):
                return i
        return -1

    def _line_end(self, text, start, width):
        if start >= len(text):
            return start
        if text[start] == "\n":
            return start + 1
        used = 0.0
        i = start
        last_break = -1
        while i < len(text):
            ch = text[i]
            if ch == "\n":
                return i + 1
            a = self.advance(ch)
            if i > start and used + a > width:
                return last_break if last_break > start else i
            used += a
            i += 1
            if self._breakable(ch, text[i-2] if i > start else ""):
                last_break = i
        return i

    def layout_paragraph(self, text, width, y=0.0, indent=0.0,
                         first_indent=0.0, align="left", line_height=None,
                         max_lines=None):
        width = max(1.0, float(width))
        lh = float(line_height or self.line_height)
        lines = []
        start = 0
        first = True
        while start < len(text):
            available = max(1.0, width - (first and first_indent or indent))
            end = self._line_end(text, start, available)
            if end <= start:
                end = min(len(text), start + 1)
            raw = text[start:end]
            # Preserve source text exactly; only trim a line's terminal break
            # for measurement/display metadata.
            display = raw[:-1] if raw.endswith("\n") else raw
            advance = self.text_width(display)
            extra = max(0.0, available - advance)
            justified = align.lower() == "justify" and end < len(text) and "\n" not in raw
            x = first_indent if first else indent
            if align.lower() == "center":
                x += extra / 2.0
            elif align.lower() == "right":
                x += extra
            spaces = display.count(" ")
            extra_space = extra / spaces if justified and spaces else 0.0
            lines.append(LayoutLine(start, end, display, advance, x, y,
                                    justified, extra_space))
            start = end
            first = False
            y += lh
            if max_lines and len(lines) >= max_lines:
                break
        return ParagraphLayout(0, len(text), lines)

    def fit_prefix(self, text, width, height, **kwargs):
        """Return (prefix_end, lines) that fits the frame height.

        The cut is always at a line boundary, preferring whitespace/hyphen
        breaks, so overflow never bisects a Unicode code point.
        """
        lh = float(kwargs.pop("line_height", self.line_height))
        max_lines = max(1, int(float(height) // max(1.0, lh)))
        layout = self.layout_paragraph(text, width, line_height=lh,
                                       max_lines=max_lines, **kwargs)
        if not layout.lines:
            return 0, []
        end = layout.lines[-1].end
        return end, layout.lines

    def paginate(self, text, frames):
        """Paginate a story into frames.

        frames: iterable of dicts with width/height and optional formatting
        keys. Returns a list of (frame_dict, source_start, source_end, lines)
        plus the unplaced suffix.
        """
        result = []
        pos = 0
        for frame in frames:
            if pos >= len(text):
                break
            prefix = text[pos:]
            end_rel, lines = self.fit_prefix(
                prefix, frame["width"], frame["height"],
                align=frame.get("align", "left"),
                indent=frame.get("indent", 0),
                first_indent=frame.get("first_indent", 0),
                line_height=frame.get("line_height", self.line_height))
            if end_rel <= 0:
                continue
            end = pos + end_rel
            result.append((frame, pos, end, lines))
            pos = end
        return result, text[pos:]
