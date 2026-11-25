#!/usr/bin/env python3
"""Build the uniform reading PDFs from the reviewed UTF-8 text snapshots.

Requires reportlab and pypdf; use --verify with pdfplumber installed to audit
page content, margins, embedded fonts and complete text round-tripping.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, PageBreak, Spacer,
    Table, TableStyle, KeepTogether,
)
from reportlab.platypus.tableofcontents import TableOfContents
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output' / 'pdf'
PAGE_W, PAGE_H = A4
MARGIN = 62
INK = colors.HexColor('#202020')
MUTED = colors.HexColor('#555555')


def register_fonts(directory: Path | None):
    candidates = [directory] if directory else [
        Path('/usr/share/fonts/liberation-serif-fonts'),
        Path('/usr/share/fonts/truetype/liberation2'),
        Path('/usr/share/fonts/truetype/liberation'),
    ]
    font_dir = next((d for d in candidates if d and (d / 'LiberationSerif-Regular.ttf').exists()), None)
    if font_dir is None:
        raise SystemExit('Install Liberation Serif or supply --font-dir with its four TTF files.')
    for suffix, name in [('Regular', 'ReadingSerif'), ('Bold', 'ReadingSerif-Bold'),
                         ('Italic', 'ReadingSerif-Italic'), ('BoldItalic', 'ReadingSerif-BoldItalic')]:
        pdfmetrics.registerFont(TTFont(name, str(font_dir / f'LiberationSerif-{suffix}.ttf')))
    pdfmetrics.registerFontFamily('ReadingSerif', normal='ReadingSerif', bold='ReadingSerif-Bold',
                                 italic='ReadingSerif-Italic', boldItalic='ReadingSerif-BoldItalic')


BODY = ParagraphStyle('Body', fontName='ReadingSerif', fontSize=12, leading=16.5,
                      textColor=INK, alignment=TA_JUSTIFY, spaceAfter=7,
                      allowWidows=0, allowOrphans=0, splitLongWords=False)
STYLES = {
    'paragraph': BODY,
    'quote': ParagraphStyle('Quote', parent=BODY, leftIndent=18, rightIndent=18),
    'verse': ParagraphStyle('Verse', parent=BODY, fontName='ReadingSerif-Italic',
                            alignment=TA_LEFT, leftIndent=22, spaceBefore=3, spaceAfter=11),
    'note': ParagraphStyle('Note', parent=BODY, fontSize=10.5, leading=14.3, spaceAfter=6),
    'heading': ParagraphStyle('Section', parent=BODY, fontName='ReadingSerif-Bold',
                              fontSize=13.5, leading=18, alignment=TA_LEFT,
                              spaceBefore=11, spaceAfter=8, keepWithNext=True),
}
TITLE = ParagraphStyle('Title', parent=BODY, fontName='ReadingSerif-Bold', fontSize=23,
                       leading=27, alignment=TA_LEFT, spaceAfter=9, keepWithNext=True)
AUTHOR = ParagraphStyle('Author', parent=BODY, fontSize=12, leading=17,
                        alignment=TA_LEFT, spaceAfter=7, keepWithNext=True)
SUBTITLE = ParagraphStyle('Subtitle', parent=BODY, fontName='ReadingSerif-Italic',
                          fontSize=11, leading=14.5, alignment=TA_LEFT,
                          spaceAfter=8, keepWithNext=True)
SOURCE = ParagraphStyle('Source', parent=BODY, fontSize=9, leading=12,
                        alignment=TA_LEFT, textColor=MUTED, spaceAfter=12,
                        keepWithNext=True)
TABLE_TEXT = ParagraphStyle('TableText', parent=BODY, fontSize=10.5, leading=14,
                            alignment=TA_LEFT, spaceAfter=0)


class ReadingDoc(BaseDocTemplate):
    def __init__(self, path, *, anthology=False, **kw):
        super().__init__(str(path), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                         topMargin=60, bottomMargin=55, pageCompression=1,
                         title=kw.pop('title'), author=kw.pop('author'),
                         subject='Uniform reading edition for English writing study',
                         allowSplitting=True, **kw)
        self.anthology = anthology
        self.article_pages = {}
        self.current_article = None
        frame = Frame(MARGIN, 55, PAGE_W-2*MARGIN, PAGE_H-115,
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id='Reading', frames=[frame], onPageEnd=self.chrome))

    def beforeDocument(self):
        self.current_article = None
        self.article_pages = {}

    def afterFlowable(self, flowable):
        if hasattr(flowable, 'article'):
            item = flowable.article
            self.current_article = item
            key = f'article-{item["number"]}'
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(f'{item["number"]:02d}. {item["title"]}', key, 0)
            self.article_pages[item['number']] = self.page
            if self.anthology:
                self.notify('TOCEntry', (0, escape(f'{item["number"]:02d}. {item["title"]}')
                                        + f'<br/><font size="10">{escape(item["author"])}</font>', self.page, key))
        elif hasattr(flowable, 'section_key'):
            self.canv.bookmarkPage(flowable.section_key)
            self.canv.addOutlineEntry(flowable.getPlainText(), flowable.section_key, 1)

    def chrome(self, canv, doc):
        canv.saveState()
        canv.setFillColor(MUTED)
        canv.setFont('ReadingSerif', 8.5)
        if self.current_article:
            d = self.current_article
            canv.drawString(MARGIN, PAGE_H-34, f'{d["number"]:02d}  /  {d["author"]}')
            canv.drawRightString(PAGE_W-MARGIN, PAGE_H-34, 'ENGLISH WRITING COLLECTION')
        else:
            canv.drawString(MARGIN, PAGE_H-34, 'ENGLISH WRITING COLLECTION')
        canv.setStrokeColor(colors.HexColor('#c8c8c8'))
        canv.setLineWidth(0.4)
        canv.line(MARGIN, PAGE_H-42, PAGE_W-MARGIN, PAGE_H-42)
        canv.setFont('ReadingSerif', 10)
        canv.drawCentredString(PAGE_W/2, 30, str(doc.page))
        canv.restoreState()


def article_story(item):
    story=[]
    number=Paragraph(f'READING {item["number"]:02d}', SOURCE)
    number.article=item
    story.append(number)
    story.append(Paragraph(escape(item['title']), TITLE))
    story.append(Paragraph(f'{escape(item["author"])}  |  {item["year"]}', AUTHOR))
    if item.get('subtitle'):
        story.append(Paragraph(escape(item['subtitle']), SUBTITLE))
    source=escape(item['source_label'])
    if item['source_url']:
        source=f'<link href="{escape(item["source_url"])}" color="#555555">{source}</link>'
    story.append(Paragraph('Source: '+source, SOURCE))
    if item.get('copyright_notice'):
        story.append(Paragraph(escape(item['copyright_notice']), SOURCE))
    for ix,e in enumerate(item['elements']):
        if e['kind']=='table':
            rows=[[Paragraph(escape(c), TABLE_TEXT) for c in row] for row in e['rows']]
            widths=[145,180,PAGE_W-2*MARGIN-325] if len(rows[0])==3 else [PAGE_W-2*MARGIN-110,110]
            tab=Table(rows, colWidths=widths, hAlign='LEFT', repeatRows=1, spaceBefore=4, spaceAfter=12)
            tab.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eeeeec')),
                ('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#aaaaaa')),
                ('LINEABOVE',(0,-1),(-1,-1),.5,colors.HexColor('#aaaaaa')),
                ('VALIGN',(0,0),(-1,-1),'TOP'),
                ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
                ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
            ]))
            story.append(tab)
        else:
            p=Paragraph(escape(e['text']).replace('\n','<br/>'),STYLES[e['kind']])
            if e['kind']=='heading':p.section_key=f'section-{item["number"]}-{ix}'
            if e['kind']=='verse':story.append(KeepTogether([p]))
            else:story.append(p)
    return story


def contents_story():
    story=[Paragraph('Ten Readings<br/>for English Writing', TITLE),
           Paragraph('A unified reading edition', AUTHOR), Spacer(1,9),
           Paragraph('Contents',STYLES['heading'])]
    toc=TableOfContents()
    toc.levelStyles=[ParagraphStyle('TOC',fontName='ReadingSerif',fontSize=11.5,leading=16,
                                    leftIndent=0,firstLineIndent=0,rightIndent=26,
                                    spaceBefore=5,spaceAfter=4)]
    toc.dotsMinLevel=0
    story += [toc, Spacer(1,15),
              Paragraph('Scope follows the repository reading list. Smith: Book I, Chapters 1-3. '
                        'Burke: the supplied excerpt. Original spelling is retained; transcription '
                        'and encoding repairs are documented in the repository.',SOURCE),PageBreak()]
    return story


def compact(t):
    return re.sub(r'\s+','',t)


def verify(path, items, *, anthology=False):
    import pdfplumber
    reader=PdfReader(path)
    texts=[p.extract_text() or '' for p in reader.pages]
    blank=[i+1 for i,t in enumerate(texts) if len(t.strip())<80]
    if blank:raise ValueError(f'{path.name}: empty pages {blank}')
    for p in reader.pages:
        if abs(float(p.mediabox.width)-PAGE_W)>.1 or abs(float(p.mediabox.height)-PAGE_H)>.1:
            raise ValueError('Inconsistent page size')
        for fontref in p['/Resources']['/Font'].values():
            font=fontref.get_object()
            # ReportLab declares Helvetica as an unused default resource.
            if font.get('/Subtype')=='/TrueType':
                desc=font['/FontDescriptor'].get_object()
                if not desc.get('/FontFile2'):raise ValueError('Unembedded reading font')
    bounds=[]
    body_text=[]
    sparse=[]
    with pdfplumber.open(path) as pdf:
        for ix,p in enumerate(pdf.pages):
            chars=[c for c in p.chars if c['text'].strip()]
            bad=[c for c in chars if c['x0']<MARGIN-1 or c['x1']>PAGE_W-MARGIN+1 or c['top']<20 or c['bottom']>PAGE_H-20]
            if bad:bounds.append(ix+1)
            body=p.crop((MARGIN-1,50,PAGE_W-MARGIN+1,PAGE_H-50)).extract_text(x_tolerance=1,y_tolerance=3) or ''
            body_text.append(body)
            if len(body.strip())<80:sparse.append(ix+1)
    if bounds:raise ValueError(f'Out-of-bounds glyphs: {bounds}')
    if sparse:raise ValueError(f'Pages without meaningful body text: {sparse}')
    # Compare every complete paragraph, poem, heading and table cell, in order,
    # after excluding running headers / footers. This also covers page splits.
    rendered=compact('\n'.join(body_text))
    cursor=0
    for item in items:
        for e in item['elements']:
            values=[c for row in e['rows'] for c in row] if e['kind']=='table' else [e['text']]
            for v in values:
                needle=compact(v)
                pos=rendered.find(needle,cursor)
                if pos<0:raise ValueError(f'{path.name}: missing or reordered text: {v[:100]}')
                cursor=pos+len(needle)
    return {'file':path.name,'pages':len(texts),'blank_pages':blank,'out_of_bounds_pages':bounds,
            'complete_text_in_order':True,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font-dir',type=Path)
    parser.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    register_fonts(args.font_dir)
    items=[json.loads(p.read_text()) for p in sorted((ROOT/'reading_texts').glob('[0-9][0-9]_*.json'))]
    if len(items)!=10:raise ValueError('Expected exactly ten articles')
    for item in items:
        for e in item['elements']:
            content=' '.join(c for row in e['rows'] for c in row) if e['kind']=='table' else e['text']
            for c in content:
                if c!='\n' and (ord(c)<32 or 0xe000<=ord(c)<=0xf8ff or c in '\ufffd\u25a0\u25a1'):
                    raise ValueError(f'Unresolved encoding artifact: {repr(c)}')
                if not c.isspace() and ord(c) not in pdfmetrics.getFont('ReadingSerif').face.charWidths:
                    raise ValueError(f'Font cannot render {repr(c)}')
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for item in items:
        slug=re.sub('[^A-Za-z0-9]+','_',item['title']).strip('_')
        name=f'{item["number"]:02d}_{slug}.pdf'
        path=OUT/name
        doc=ReadingDoc(path,title=item['title'],author=item['author'])
        doc.build(article_story(item))
        entry=verify(path,[item]) if args.verify else {'file':name,'pages':len(PdfReader(path).pages)}
        entry.update({'number':item['number'],'title':item['title']})
        manifest.append(entry)
        print(f'{name}: {entry["pages"]} pages',flush=True)
    path=OUT/'English_Writing_Collection.pdf'
    doc=ReadingDoc(path,anthology=True,title='Ten Readings for English Writing',author='Various authors')
    story=contents_story()
    for ix,item in enumerate(items):
        if ix:story.append(PageBreak())
        story.extend(article_story(item))
    doc.multiBuild(story)
    combined=verify(path,items,anthology=True) if args.verify else {'file':path.name,'pages':len(PdfReader(path).pages)}
    combined['article_start_pages']=doc.article_pages
    print(f'{path.name}: {combined["pages"]} pages',flush=True)
    report={'paper':'A4','body_font':'Liberation Serif, embedded','body_size_pt':12,
            'line_spacing_pt':16.5,'side_margins_pt':62,'single_articles':manifest,'collection':combined}
    (OUT/'build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':
    main()
