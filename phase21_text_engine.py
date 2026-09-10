"""Phase 21: unified professional text engine integration.

Provides a single text-layout facade over the existing DTP paragraph/layout,
Unicode-run and pagination engines. It intentionally keeps source Unicode
code points lossless while exposing question-paper friendly paragraph rules.
"""
from dataclasses import dataclass, field
import re

try:
    from phase14_unicode_shaping import UnicodeRunEngine
except Exception:
    UnicodeRunEngine = None
try:
    from phase16_paragraph_engine import ParagraphStyle, ParagraphEngine
except Exception:
    ParagraphStyle = None
    ParagraphEngine = None
try:
    from phase17_pagination_engine import PaginationEngine
except Exception:
    PaginationEngine = None

@dataclass
class CharacterStyle:
    font: str = "TkDefaultFont"
    size: float = 11.0
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: str = ""

@dataclass
class TextEngineConfig:
    default_style: CharacterStyle = field(default_factory=CharacterStyle)
    hyphenate: bool = False
    preserve_unicode: bool = True
    question_breaks: bool = True

class ProfessionalTextEngine:
    """Facade used by the application and future native renderer."""
    def __init__(self, config=None):
        self.config = config or TextEngineConfig()
        self.paragraph_styles = {}
        self.character_styles = {}
        self._install_defaults()
        self.run_engine = UnicodeRunEngine() if UnicodeRunEngine else None
        self.paragraph_engine = ParagraphEngine() if ParagraphEngine else None
        self.pagination_engine = PaginationEngine() if PaginationEngine else None

    def _install_defaults(self):
        if ParagraphStyle:
            self.paragraph_styles.update({
                "Normal": ParagraphStyle(name="Normal"),
                "Question": ParagraphStyle(name="Question", space_after=4.0,
                                            widow_lines=2, orphan_lines=2),
                "Option": ParagraphStyle(name="Option", left_indent=12.0,
                                          first_line_indent=0.0),
            })
        self.character_styles["Default"] = self.config.default_style

    @staticmethod
    def paragraphs(text):
        """Return paragraph source slices without Unicode normalization."""
        if text is None:
            return []
        return re.split(r"\n", str(text))

    @staticmethod
    def question_blocks(text):
        """Recognize common NEET/JEE question starts without rewriting text."""
        if text is None:
            return []
        lines = str(text).splitlines(keepends=True)
        blocks, current = [], []
        pat = re.compile(r"^\s*(?:Q\.?\s*)?\d{1,4}[.)]\s*")
        for line in lines:
            if pat.match(line) and current:
                blocks.append("".join(current)); current=[]
            current.append(line)
        if current:
            blocks.append("".join(current))
        return blocks or [str(text)]

    def runs(self, text, tags=None):
        """Produce Unicode script runs; original text is never normalized."""
        if self.run_engine is not None:
            try:
                return self.run_engine.runs(text, tags=tags)
            except TypeError:
                try:
                    return self.run_engine.runs(text)
                except Exception:
                    pass
        return [(text, self.config.default_style)] if text else []

    def layout_paragraphs(self, text, width, style="Normal"):
        """Delegate geometry-aware paragraph layout when the engine is available."""
        ps = self.paragraph_styles.get(style, self.paragraph_styles.get("Normal"))
        if self.paragraph_engine is not None:
            try:
                return self.paragraph_engine.layout(str(text), float(width), ps)
            except TypeError:
                try:
                    return self.paragraph_engine.layout(str(text), float(width))
                except Exception:
                    pass
        return self.paragraphs(text)

    def classify_question_content(self, text):
        s = str(text or "")
        return {
            "has_options": bool(re.search(r"(?:^|\n)\s*\(?[A-Da-d]\)?[.)]\s+", s)),
            "has_numbering": bool(re.search(r"(?:^|\n)\s*(?:Q\.?\s*)?\d{1,4}[.)]\s*", s)),
            "has_math_symbols": bool(re.search(r"[∑∫√∞≤≥≠≈±×÷∝α-ωΑ-Ω]", s)),
            "has_devanagari": bool(re.search(r"[\u0900-\u097F]", s)),
        }

def install(app):
    engine = ProfessionalTextEngine()
    app.pm21_text_engine = engine
    return engine
