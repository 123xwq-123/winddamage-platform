# -*- coding: utf-8 -*-
"""Format the user manual docx per requirements:
1. Chinese font = SimSun (SimSun), Western = Times New Roman (everywhere)
2. No new numbering added to the document (list/heading numbering untouched)
3. New images get captions with figure numbers; existing captions get numbers
4. L1 headings: bold black size 14 (sz 28); L2: bold black small 4 (sz 24);
   L3 + body: small 4 black not bold; captions: size 5 (sz 21) black, centered
5. Body: justified, first-line indent 2 chars; images centered
"""
import copy
import re

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC = 'merged.docx'
OUT = '前端界面使用说明书-风电塔灾损测算多模态大模型可视化软件-格式完善.docx'

doc = Document(SRC)
body_el = doc.element.body

# ---------------------------------------------------------------- helpers

def set_run_props(r, sz=None, bold=None, color_black=True):
    """Force run fonts (SimSun/TNR) and optionally size/bold/color."""
    rPr = r.find(qn('w:rPr'))
    if rPr is None:
        rPr = OxmlElement('w:rPr')
        r.insert(0, rPr)
    # fonts: drop theme refs / hint, then set explicit SimSun + Times New Roman
    old = rPr.find(qn('w:rFonts'))
    if old is not None:
        rPr.remove(old)
    fonts = OxmlElement('w:rFonts')
    fonts.set(qn('w:ascii'), 'Times New Roman')
    fonts.set(qn('w:hAnsi'), 'Times New Roman')
    fonts.set(qn('w:eastAsia'), 'SimSun')
    fonts.set(qn('w:cs'), 'Times New Roman')
    rPr.insert(0, fonts)
    if sz is not None:
        for tag in ('w:sz', 'w:szCs'):
            el = rPr.find(qn(tag))
            if el is None:
                el = OxmlElement(tag)
                rPr.append(el)
            el.set(qn('w:val'), str(sz))
    if bold is not None:
        el = rPr.find(qn('w:b'))
        if el is None:
            el = OxmlElement('w:b')
            rPr.append(el)
        if bold:
            el.attrib.pop(qn('w:val'), None)
        else:
            el.set(qn('w:val'), '0')
        bcs = rPr.find(qn('w:bCs'))
        if bcs is None:
            bcs = OxmlElement('w:bCs')
            rPr.append(bcs)
        bcs.set(qn('w:val'), '0' if not bold else '1')
    if color_black:
        el = rPr.find(qn('w:color'))
        if el is None:
            el = OxmlElement('w:color')
            rPr.append(el)
        el.set(qn('w:val'), '000000')


PPR_ORDER = ['w:pStyle', 'w:keepNext', 'w:keepLines', 'w:pageBreakBefore', 'w:framePr',
             'w:widowControl', 'w:numPr', 'w:suppressLineNumbers', 'w:pBdr', 'w:shd',
             'w:tabs', 'w:suppressAutoHyphens', 'w:kinsoku', 'w:wordWrap', 'w:overflowPunct',
             'w:topLinePunct', 'w:autoSpaceDE', 'w:autoSpaceDN', 'w:bidi', 'w:adjustRightInd',
             'w:snapToGrid', 'w:spacing', 'w:ind', 'w:contextualSpacing', 'w:mirrorIndents',
             'w:suppressOverlap', 'w:jc', 'w:textDirection', 'w:textAlignment',
             'w:textboxTightWrap', 'w:outlineLvl', 'w:divId', 'w:cnfStyle', 'w:rPr', 'w:sectPr']


def insert_ordered(pPr, el):
    tag = el.tag
    idx = PPR_ORDER.index('w:' + tag.split('}')[1])
    for child in pPr:
        ctag = 'w:' + child.tag.split('}')[1]
        if ctag in PPR_ORDER and PPR_ORDER.index(ctag) > idx:
            child.addprevious(el)
            return
    pPr.append(el)


def set_p_props(p, jc=None, first_line_chars=None):
    pPr = p.find(qn('w:pPr'))
    if pPr is None:
        pPr = OxmlElement('w:pPr')
        p.insert(0, pPr)
    if jc is not None:
        el = pPr.find(qn('w:jc'))
        if el is None:
            el = OxmlElement('w:jc')
            insert_ordered(pPr, el)
        el.set(qn('w:val'), jc)
    if first_line_chars is not None:
        ind = pPr.find(qn('w:ind'))
        if ind is None:
            ind = OxmlElement('w:ind')
            insert_ordered(pPr, ind)
        for a in ('w:firstLine',):
            ind.attrib.pop(qn(a), None)
        ind.set(qn('w:firstLineChars'), str(first_line_chars))


def para_style_id(p):
    ps = p.find(qn('w:pPr') + '/' + qn('w:pStyle')) if p.find(qn('w:pPr')) is not None else None
    if ps is None:
        ps = p.find(qn('w:pPr'))
        ps = ps.find(qn('w:pStyle')) if ps is not None else None
    return ps.get(qn('w:val')) if ps is not None else None


def para_text(p):
    return ''.join(t.text or '' for t in p.iter(qn('w:t')))


def has_image(p):
    return p.find('.//' + qn('w:drawing')) is not None or p.find('.//' + qn('w:pict')) is not None


def is_list(p):
    """True if the paragraph (or its style) carries list numbering."""
    pPr = p.find(qn('w:pPr'))
    if pPr is not None:
        numPr = pPr.find(qn('w:numPr'))
        if numPr is not None:
            numId = numPr.find(qn('w:numId'))
            if numId is not None and numId.get(qn('w:val')) not in (None, '0'):
                return True
    sid = para_style_id(p)
    if sid in ('a0', '20', '30', 'a', '2', '3', 'ae', 'af1', '25', '35'):
        # style-level numbering, unless the paragraph disables it with numId 0
        if pPr is not None and pPr.find(qn('w:numPr')) is not None:
            numId = pPr.find(qn('w:numPr')).find(qn('w:numId'))
            if numId is not None and numId.get(qn('w:val')) == '0':
                return False
        return True
    return False


paras = body_el.findall(qn('w:p'))
print('paragraphs:', len(paras))

# ---------------------------------------------------------------- 1. style-level fixes

styles_el = doc.styles.element
for st in styles_el.findall(qn('w:style')):
    sid = st.get(qn('w:styleId'))
    if sid not in ('1', '21', '31', 'aff9'):
        continue
    rPr = st.find(qn('w:rPr'))
    if rPr is None:
        rPr = OxmlElement('w:rPr')
        st.append(rPr)
    old = rPr.find(qn('w:rFonts'))
    if old is not None:
        rPr.remove(old)
    fonts = OxmlElement('w:rFonts')
    fonts.set(qn('w:ascii'), 'Times New Roman')
    fonts.set(qn('w:hAnsi'), 'Times New Roman')
    fonts.set(qn('w:eastAsia'), 'SimSun')
    fonts.set(qn('w:cs'), 'Times New Roman')
    rPr.insert(0, fonts)
    sz = {'1': '28', '21': '24', '31': '24', 'aff9': '21'}[sid]
    for tag in ('w:sz', 'w:szCs'):
        el = rPr.find(qn(tag))
        if el is None:
            el = OxmlElement(tag)
            rPr.append(el)
        el.set(qn('w:val'), sz)
    bold = sid in ('1', '21')
    el = rPr.find(qn('w:b'))
    if el is None:
        el = OxmlElement('w:b')
        rPr.append(el)
    if not bold:
        el.set(qn('w:val'), '0')
    else:
        el.attrib.pop(qn('w:val'), None)
    col = rPr.find(qn('w:color'))
    if col is None:
        col = OxmlElement('w:color')
        rPr.append(col)
    col.set(qn('w:val'), '000000')

# ---------------------------------------------------------------- 2. new captions for bare images

CAPTION_STYLE = 'aff9'
NEW_CAPTIONS = [
    '软件主界面概览',
    '登录与注册页面',
    '单图检测页面',
    '批量检测页面',
    '历史记录页面',
    '用户管理页面（管理员）',
    '显示设置面板',
]

def find_section_heading(idx):
    """Nearest preceding heading text, for fallback caption titles."""
    for j in range(idx, -1, -1):
        sid = para_style_id(paras[j])
        if sid in ('1', '21', '31'):
            return para_text(paras[j])
    return ''

def make_caption(text):
    p = OxmlElement('w:p')
    pPr = OxmlElement('w:pPr')
    ps = OxmlElement('w:pStyle')
    ps.set(qn('w:val'), CAPTION_STYLE)
    pPr.append(ps)
    jc = OxmlElement('w:jc')
    jc.set(qn('w:val'), 'center')
    pPr.append(jc)
    p.append(pPr)
    r = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    fonts = OxmlElement('w:rFonts')
    fonts.set(qn('w:ascii'), 'Times New Roman')
    fonts.set(qn('w:hAnsi'), 'Times New Roman')
    fonts.set(qn('w:eastAsia'), 'SimSun')
    fonts.set(qn('w:cs'), 'Times New Roman')
    rPr.append(fonts)
    sz = OxmlElement('w:sz')
    sz.set(qn('w:val'), '21')
    rPr.append(sz)
    col = OxmlElement('w:color')
    col.set(qn('w:val'), '000000')
    rPr.append(col)
    r.append(rPr)
    t = OxmlElement('w:t')
    t.text = text
    r.append(t)
    p.append(r)
    return p

# find runs of consecutive image paragraphs without a following caption
i = 0
inserted = 0
while i < len(paras):
    if has_image(paras[i]):
        j = i
        while j + 1 < len(paras) and has_image(paras[j + 1]):
            j += 1
        nxt = paras[j + 1] if j + 1 < len(paras) else None
        has_cap = (nxt is not None and para_style_id(nxt) == CAPTION_STYLE)
        if not has_cap:
            title = NEW_CAPTIONS[inserted] if inserted < len(NEW_CAPTIONS) else find_section_heading(i)
            cap = make_caption(title)
            paras[j].addnext(cap)
            paras.insert(j + 1, cap)
            inserted += 1
            print(f'inserted caption after image para {i}: {title}')
            j += 1
        i = j + 1
    else:
        i += 1
print('new captions inserted:', inserted)

# ---------------------------------------------------------------- 3. per-paragraph formatting

paras = body_el.findall(qn('w:p'))
first_heading_idx = next(i for i, p in enumerate(paras) if para_style_id(p) == '1')
print('cover paragraphs: 0..', first_heading_idx - 1)

fig_no = 0
for idx, p in enumerate(paras):
    sid = para_style_id(p)
    text = para_text(p)
    in_cover = idx < first_heading_idx
    is_img = has_image(p)

    if sid == '1':          # heading 1: bold black size 4
        for r in p.findall(qn('w:r')):
            set_run_props(r, sz=28, bold=True)
    elif sid == '21':       # heading 2: bold black small 4
        for r in p.findall(qn('w:r')):
            set_run_props(r, sz=24, bold=True)
    elif sid == '31':       # heading 3: small 4 black, not bold
        for r in p.findall(qn('w:r')):
            set_run_props(r, sz=24, bold=False)
    elif sid == CAPTION_STYLE:
        # caption: number it, size 5 black, centered
        fig_no += 1
        stripped = re.sub(r'^图\s*\d*\s*', '', text.strip())
        new_text = f'图{fig_no} {stripped}'
        if new_text != text:
            # put whole text into first run, clear the rest
            runs = p.findall(qn('w:r'))
            first_t = None
            for r in runs:
                for t in r.findall(qn('w:t')):
                    if first_t is None:
                        first_t = t
                        t.text = new_text
                        t.set(qn('xml:space'), 'preserve')
                    else:
                        t.text = ''
            print(f'caption #{fig_no}: {new_text}')
        for r in p.findall(qn('w:r')):
            set_run_props(r, sz=21, bold=False)
        set_p_props(p, jc='center')
    elif is_img:
        set_p_props(p, jc='center')
        # strip stray list indents so the image truly centers
        pPr = p.find(qn('w:pPr'))
        if pPr is not None:
            ind = pPr.find(qn('w:ind'))
            if ind is not None:
                pPr.remove(ind)
    elif in_cover:
        for r in p.findall(qn('w:r')):   # cover: fonts only
            set_run_props(r)
    else:
        # body: small 4 black, not bold; justify; first-line indent 2 chars
        for r in p.findall(qn('w:r')):
            set_run_props(r, sz=24, bold=False)
        set_p_props(p, jc='both')
        if not is_list(p) and text.strip():
            set_p_props(p, first_line_chars=200)

print('total figures numbered:', fig_no)
doc.save(OUT)
print('saved:', OUT)
