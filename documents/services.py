from datetime import datetime
from io import BytesIO

from django.conf import settings
from django.utils import timezone

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ODPP_BLUE = colors.HexColor('#1e4699')
DEEP_BLUE = colors.HexColor('#12306b')
CREST_GOLD = colors.HexColor('#ffd200')
MUTED = colors.HexColor('#5d6675')
LINE = colors.HexColor('#b9cae4')
PAPER = colors.HexColor('#f4f6fa')

_CREST_PATH = settings.BASE_DIR / 'brand' / 'odpp-crest.png'
_crest_thumbnail_bytes = None


def _get_crest_reader():
    """Return a fresh file-like reader over a small, cached, in-memory copy of the crest.

    Caching the shrunk PNG bytes avoids both re-reading the full-resolution source file
    and reusing an exhausted stream across documents generated in the same process.
    """
    global _crest_thumbnail_bytes
    if _crest_thumbnail_bytes is None and _CREST_PATH.exists():
        with PILImage.open(_CREST_PATH) as source:
            source = source.convert('RGBA')
            source.thumbnail((160, 160))
            buffer = BytesIO()
            source.save(buffer, format='PNG')
            _crest_thumbnail_bytes = buffer.getvalue()
    if _crest_thumbnail_bytes is None:
        return None
    return BytesIO(_crest_thumbnail_bytes)

_styles = getSampleStyleSheet()
_eyebrow_style = ParagraphStyle('Eyebrow', parent=_styles['Normal'], textColor=ODPP_BLUE, fontName='Helvetica-Bold', fontSize=8, leading=10, spaceAfter=4, letterSpacing=1)
_title_style = ParagraphStyle('DocTitle', parent=_styles['Normal'], textColor=DEEP_BLUE, fontName='Times-Bold', fontSize=20, leading=24, spaceAfter=2)
_reference_style = ParagraphStyle('Reference', parent=_styles['Normal'], textColor=DEEP_BLUE, fontName='Helvetica-Bold', fontSize=11, leading=14)
_section_heading_style = ParagraphStyle('SectionHeading', parent=_styles['Normal'], textColor=DEEP_BLUE, fontName='Helvetica-Bold', fontSize=10, leading=13, spaceBefore=14, spaceAfter=6)
_body_style = ParagraphStyle('Body', parent=_styles['Normal'], textColor=colors.HexColor('#1a1a1a'), fontName='Helvetica', fontSize=10, leading=15)
_meta_label_style = ParagraphStyle('MetaLabel', parent=_styles['Normal'], textColor=MUTED, fontName='Helvetica-Bold', fontSize=7.5, leading=10)
_meta_value_style = ParagraphStyle('MetaValue', parent=_styles['Normal'], textColor=DEEP_BLUE, fontName='Helvetica-Bold', fontSize=9.5, leading=13)
_footer_style = ParagraphStyle('Footer', parent=_styles['Normal'], textColor=MUTED, fontName='Helvetica', fontSize=7.5, leading=10)
_footer_right_style = ParagraphStyle('FooterRight', parent=_footer_style, alignment=TA_RIGHT)


def _header_flowables():
    office_html = (
        '<font color="#ffd200" size="7.5">REPUBLIC OF UGANDA</font><br/>'
        '<font color="#ffffff" size="13"><b>Office of the Director of Public Prosecutions</b></font>'
    )
    office_paragraph = Paragraph(office_html, ParagraphStyle('Office', parent=_styles['Normal'], leading=16))
    crest_reader = _get_crest_reader()
    cells = [Image(crest_reader, width=13 * mm, height=13 * mm), office_paragraph] if crest_reader else [office_paragraph]
    col_widths = [18 * mm, 152 * mm] if crest_reader else [170 * mm]
    header_table = Table([cells], colWidths=col_widths)
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DEEP_BLUE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (0, 0), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    return [header_table, HRFlowable(width='100%', thickness=3, color=CREST_GOLD, spaceBefore=0, spaceAfter=16)]


def _meta_table(meta):
    if not meta:
        return None
    cells = [[Paragraph(label.upper(), _meta_label_style) for label, _ in meta], [Paragraph(str(value) if value else '—', _meta_value_style) for _, value in meta]]
    col_width = 170 * mm / len(meta)
    table = Table(cells, colWidths=[col_width] * len(meta))
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PAPER),
        ('BOX', (0, 0), (-1, -1), 0.75, LINE),
        ('INNERGRID', (0, 0), (-1, -1), 0.75, LINE),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 9),
    ]))
    return table


def render_letterhead_pdf(*, category_label, title, reference, meta=None, sections, generated_by=''):
    """Render a branded, letterhead-style PDF for a case or complaint record.

    Used in place of raw text files so linked evidence and correspondence render as
    a real document rather than plain text when opened from a case or complaint file.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=14 * mm, bottomMargin=16 * mm, leftMargin=20 * mm, rightMargin=20 * mm, title=title)

    elements = list(_header_flowables())
    elements.append(Paragraph(category_label.upper(), _eyebrow_style))
    elements.append(Paragraph(title, _title_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(reference, _reference_style))
    elements.append(Spacer(1, 14))

    meta_table = _meta_table(meta)
    if meta_table:
        elements.append(meta_table)

    for heading, paragraphs in sections:
        elements.append(Paragraph(heading, _section_heading_style))
        for paragraph in paragraphs:
            elements.append(Paragraph(paragraph, _body_style))
            elements.append(Spacer(1, 6))

    generated_at = timezone.localtime(timezone.now()) if timezone.is_aware(timezone.now()) else datetime.now()

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(20 * mm, 14 * mm, A4[0] - 20 * mm, 14 * mm)
        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(20 * mm, 10 * mm, f'Case Pipeline & Complaints Console · Generated {generated_at.strftime("%d %b %Y, %H:%M")}{" by " + generated_by if generated_by else ""}')
        canvas.drawRightString(A4[0] - 20 * mm, 10 * mm, f'Page {doc_.page}')
        canvas.restoreState()

    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
