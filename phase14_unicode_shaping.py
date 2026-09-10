"""PageMaker Pro Phase 14 — Unicode runs and shaping abstraction.

Keeps Unicode source text lossless while splitting visual text into font/style
runs.  The optional shaping backend is detected at runtime; when HarfBuzz or
Pango bindings are unavailable, Tk remains the safe renderer fallback.
"""
from dataclasses import dataclass
import unicodedata
import tkinter.font as tkfont


@dataclass
class TextRun:
    text: str
    start: int
    end: int
    font: str
    size: float
    bold: bool = False
    italic: bool = False
    script: str = "Latin"


def script_of(ch):
    n = unicodedata.name(ch, "")
    if "DEVANAGARI" in n:
        return "Devanagari"
    if "GREEK" in n:
        return "Greek"
    if "CYRILLIC" in n:
        return "Cyrillic"
    if "ARABIC" in n:
        return "Arabic"
    if "HEBREW" in n:
        return "Hebrew"
    if "BENGALI" in n:
        return "Bengali"
    return "Common" if not ch.isalpha() else "Latin"


class UnicodeRunEngine:
    """Lossless Unicode run segmentation with optional font fallback."""
    def __init__(self, default_font="Noto Sans", size=12):
        self.default_font = default_font
        self.size = float(size)
        self._fonts = {}

    def available(self, family, size=None):
        key=(family, int(size or self.size))
        if key in self._fonts: return self._fonts[key]
        try:
            f=tkfont.Font(family=family,size=key[1]); self._fonts[key]=f; return f
        except Exception:
            return None

    def runs(self, text, start=0, font=None, size=None, bold=False, italic=False):
        font = font or self.default_font; size=float(size or self.size)
        if not text: return []
        out=[]; run_start=start; last=None
        for off,ch in enumerate(text):
            script=script_of(ch)
            # Combining marks belong to the preceding run, preserving clusters.
            if unicodedata.combining(ch) and last is not None: script=last
            if last is not None and script != last:
                piece=text[run_start-start:off]
                out.append(TextRun(piece,run_start,start+off,font,size,bold,italic,last))
                run_start=start+off
            last=script
        out.append(TextRun(text[run_start-start:],run_start,start+len(text),font,size,bold,italic,last or "Common"))
        return out

    def measure(self, text, font=None, size=None, bold=False, italic=False):
        f=self.available(font or self.default_font,size)
        if f is None: return None
        try:
            actual=f.measure(text)
            return float(actual)
        except Exception: return None


def detect_shaper():
    try:
        import uharfbuzz  # noqa: F401
        return "uharfbuzz"
    except Exception:
        pass
    try:
        import gi  # noqa: F401
        return "pango"
    except Exception:
        return "fallback"
