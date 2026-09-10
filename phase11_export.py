"""PageMaker Pro Phase 11 — offline PDF/DOCX export adapters.

Exports the canonical Document model without depending on the Tk widgets. PDF
uses ReportLab when installed; DOCX uses python-docx when installed. Text is
written as Unicode, while geometry is converted from the model's point-like
A4 coordinates.
"""
import os


def _text_pages(doc):
    out = []
    for page in doc.pages:
        items = []
        for oid in page.objects:
            frame = doc.frames.get(oid)
            if frame and frame.text:
                items.append(frame)
        out.append((page, items))
    return out


def export_pdf(doc, path):
    try:
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError as exc:
        raise RuntimeError("PDF export requires the reportlab package") from exc

    c = canvas.Canvas(path, pagesize=(doc.page_width, doc.page_height))
    font_name = "Helvetica"
    candidates = [
        os.path.join(os.environ.get("WINDIR", ""), "Fonts", "arial.ttf"),
        os.path.join(os.environ.get("WINDIR", ""), "Fonts", "NotoSans-Regular.ttf"),
    ]
    for fp in candidates:
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont("PMUnicode", fp))
                font_name = "PMUnicode"
                break
            except Exception:
                pass

    for page, frames in _text_pages(doc):
        m = doc.masters.get(page.master)
        if m and getattr(m, "border", True):
            c.rect(1, 1, page.width-2, page.height-2)
        if m and m.watermark:
            c.saveState(); c.translate(page.width/2, page.height/2); c.rotate(45)
            c.setFont(font_name, 28); c.drawCentredString(0, 0, m.watermark); c.restoreState()
        if m and m.header:
            c.setFont(font_name, 9); c.drawCentredString(page.width/2, page.height-25, m.header)
        for f in frames:
            c.setFont(font_name, 10)
            x, y = f.rect.x, page.height - f.rect.y - 12
            for line in f.text.splitlines() or [""]:
                if y < f.rect.y: break
                c.drawString(x, y, line)
                y -= 13
        if m and m.footer:
            c.setFont(font_name, 9); c.drawCentredString(page.width/2, 25, m.footer)
        c.setFont(font_name, 8); c.drawCentredString(page.width/2, 10, f"Page {page.number}")
        c.showPage()
    c.save()
    return path


def export_docx(doc, path):
    try:
        from docx import Document as WordDocument
        from docx.shared import Mm
    except ImportError as exc:
        raise RuntimeError("DOCX export requires the python-docx package") from exc

    wdoc = WordDocument()
    section = wdoc.sections[0]
    section.page_width = Mm(doc.page_width * 25.4 / 72)
    section.page_height = Mm(doc.page_height * 25.4 / 72)
    for pi, (page, frames) in enumerate(_text_pages(doc)):
        if pi:
            wdoc.add_page_break()
        m = doc.masters.get(page.master)
        if m and m.header:
            section.header.paragraphs[0].text = m.header
        if m and m.footer:
            section.footer.paragraphs[0].text = m.footer
        if frames:
            for f in frames:
                for text in f.text.splitlines() or [""]:
                    wdoc.add_paragraph(text)
        else:
            wdoc.add_paragraph("")
        wdoc.add_paragraph(f"Page {page.number}")
    wdoc.save(path)
    return path


def install(app):
    if getattr(app, "_pm11_installed", False):
        return
    app._pm11_installed = True
    app.pm11_export_pdf = lambda path: export_pdf(app.document, path)
    app.pm11_export_docx = lambda path: export_docx(app.document, path)
