#!/usr/bin/env python3
"""
md_to_pdf.py — 將報告 Markdown 轉成同風格 PDF（MD 與 PDF 相依，單一來源）

用法：
    python3 md_to_pdf.py taipei_analysis_report.md [output.pdf]

規則：
- MD 為唯一內容來源；PDF 由本腳本重新生成，兩者永遠一致
- 所有參考數據以 Markdown 表格撰寫，渲染為深藍表頭表格
- 全文使用 CJK 字型（依平台自動尋找），避免中文亂碼
"""

import os, re, sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── 字型（依平台 fallback）─────────────────────────────────────────────────────
FONT_CANDIDATES = [
    '/System/Library/Fonts/STHeiti Light.ttc',                 # macOS
    '/System/Library/Fonts/PingFang.ttc',                      # macOS
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',  # Linux
    '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
    'C:/Windows/Fonts/msjh.ttc',                               # Windows 微軟正黑
]
FONT = None
for path in FONT_CANDIDATES:
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont('CJK', path))
            FONT = 'CJK'
            break
        except Exception:
            continue
if FONT is None:
    raise SystemExit('找不到可用的中文字型，請於 FONT_CANDIDATES 補上路徑')
pdfmetrics.registerFontFamily('CJK', normal='CJK', bold='CJK', italic='CJK', boldItalic='CJK')

# 拉丁字型（部分 CJK fallback 字型不含英數字母，需另掛西文字型）
LATIN = None
LATIN_CANDIDATES = [
    ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
     '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
]
for reg, bold in LATIN_CANDIDATES:
    if os.path.exists(reg):
        pdfmetrics.registerFont(TTFont('LATIN', reg))
        pdfmetrics.registerFont(TTFont('LATIN-Bold', bold if os.path.exists(bold) else reg))
        pdfmetrics.registerFontFamily('LATIN', normal='LATIN', bold='LATIN-Bold',
                                      italic='LATIN', boldItalic='LATIN-Bold')
        LATIN = 'LATIN'
        break

# CJK 字型實際涵蓋的字元集（用於決定逐字路由）
try:
    CJK_CHARS = set(pdfmetrics.getFont(FONT).face.charToGlyph.keys())
except Exception:
    CJK_CHARS = None

# ── 樣式 ──────────────────────────────────────────────────────────────────────
NAVY = colors.HexColor('#1a1a2e')
ROW_ALT = colors.HexColor('#f2f4f8')

def s(name, **kw):
    return ParagraphStyle(name, fontName=FONT, **kw)

TITLE    = s('TITLE', fontSize=18, leading=26, spaceAfter=6, alignment=TA_CENTER, textColor=NAVY)
SUBTITLE = s('SUBTITLE', fontSize=10.5, leading=16, spaceAfter=14, alignment=TA_CENTER,
             textColor=colors.HexColor('#555555'))
H1 = s('H1', fontSize=13, leading=20, spaceBefore=16, spaceAfter=6, textColor=NAVY)
H2 = s('H2', fontSize=11, leading=17, spaceBefore=12, spaceAfter=4, textColor=colors.HexColor('#16213e'))
H3 = s('H3', fontSize=10, leading=16, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor('#16213e'))
BODY = s('BODY', fontSize=9, leading=15, spaceAfter=4)
NOTE = s('NOTE', fontSize=8, leading=13, spaceBefore=2, spaceAfter=6,
         textColor=colors.HexColor('#555555'), leftIndent=8)
CELL = s('CELL', fontSize=8, leading=12)
CELL_HDR = s('CELL_HDR', fontSize=8, leading=12, textColor=colors.white)

# ── 行內格式 ──────────────────────────────────────────────────────────────────
def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def _route(seg):
    """CJK 字型缺字的字元（英數、符號）改走西文字型"""
    if CJK_CHARS is None or LATIN is None or not seg:
        return seg
    runs, buf, cur = [], [], None
    for ch in seg:
        tgt = 'cjk' if ord(ch) in CJK_CHARS else 'lat'
        if ch == ' ' and cur is not None:
            buf.append(ch); continue
        if tgt != cur and buf:
            runs.append((cur, ''.join(buf))); buf = []
        cur = tgt; buf.append(ch)
    if buf:
        runs.append((cur, ''.join(buf)))
    return ''.join(t if f == 'cjk' else f'<font name="{LATIN}">{t}</font>' for f, t in runs)

def inline(t):
    t = t.replace('✅', '✔')
    t = esc(t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'`([^`]+)`', r'<font color="#c0392b">\1</font>', t)
    # 逐段路由字型（略過標籤本身）
    parts = re.split(r'(<[^>]+>)', t)
    return ''.join(p if p.startswith('<') else _route(p) for p in parts)

# ── 表格 ──────────────────────────────────────────────────────────────────────
USABLE = A4[0] - 4 * cm  # 左右各 2cm

def cjk_len(t):
    return sum(2 if ord(c) > 0x2E7F else 1 for c in t)

def build_table(rows, aligns):
    ncol = max(len(r) for r in rows)
    rows = [r + [''] * (ncol - len(r)) for r in rows]
    # 欄寬：依內容長度比例分配（設上下限）
    maxlen = [max(cjk_len(r[i]) for r in rows) for i in range(ncol)]
    total = sum(maxlen) or 1
    widths = [max(1.4 * cm, min(9 * cm, USABLE * m / total)) for m in maxlen]
    widths = [w * USABLE / sum(widths) for w in widths]  # 一律撐滿版面寬
    data = [[Paragraph(inline(c), CELL_HDR) for c in rows[0]]] + \
           [[Paragraph(inline(c), CELL) for c in r] for r in rows[1:]]
    cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#cccccc')),
    ]
    for i in range(1, len(rows)):
        if i % 2 == 0:
            cmds.append(('BACKGROUND', (0, i), (-1, i), ROW_ALT))
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle(cmds))
    return t

# ── Markdown 解析 ─────────────────────────────────────────────────────────────
def parse(md_path):
    lines = open(md_path, encoding='utf-8').read().splitlines()
    story, i, title_done = [], 0, False
    while i < len(lines):
        ln = lines[i]
        st = ln.strip()
        if not st:
            i += 1; continue
        if st == '---' and not ln.startswith('|'):
            story.append(HRFlowable(width='100%', thickness=0.5,
                         color=colors.HexColor('#cccccc'), spaceBefore=4, spaceAfter=8))
            i += 1; continue
        if st.startswith('# ') and not title_done:
            story.append(Paragraph(inline(st[2:]), TITLE)); title_done = True
            # 緊接的非標題行視為副標
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and not lines[j].startswith(('#', '|', '-', '>')):
                story.append(Paragraph(inline(lines[j].strip()), SUBTITLE))
                i = j
            i += 1; continue
        if st.startswith('#### '):
            story.append(Paragraph(inline(st[5:]), H3)); i += 1; continue
        if st.startswith('### '):
            story.append(Paragraph(inline(st[4:]), H2)); i += 1; continue
        if st.startswith('## '):
            story.append(Paragraph(inline(st[3:]), H1))
            story.append(HRFlowable(width='100%', thickness=0.5,
                         color=colors.HexColor('#cccccc'), spaceBefore=0, spaceAfter=6))
            i += 1; continue
        if st.startswith('# '):
            story.append(Paragraph(inline(st[2:]), H1)); i += 1; continue
        if st.startswith('>'):
            story.append(Paragraph(inline('▶ ' + st.lstrip('> ').strip()), NOTE))
            i += 1; continue
        if st.startswith('|'):
            rows, aligns = [], []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if all(re.fullmatch(r':?-{2,}:?', c) for c in cells):
                    aligns = cells
                else:
                    rows.append(cells)
                i += 1
            if rows:
                story.append(Spacer(1, 2))
                story.append(build_table(rows, aligns))
                story.append(Spacer(1, 4))
            continue
        if st.startswith('```'):
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith('```'):
                buf.append(lines[i]); i += 1
            i += 1
            for b in buf:
                story.append(Paragraph(inline(b) or '&nbsp;', NOTE))
            continue
        if st.startswith(('- ', '* ')):
            story.append(Paragraph(inline('• ' + st[2:]), BODY)); i += 1; continue
        if re.match(r'^\d+\.\s', st):
            story.append(Paragraph(inline(st), BODY)); i += 1; continue
        # 一般段落（合併連續行）
        buf = [st]
        while i + 1 < len(lines) and lines[i + 1].strip() and \
                not lines[i + 1].strip().startswith(('#', '|', '>', '-', '*', '```')) and \
                not re.match(r'^\d+\.\s', lines[i + 1].strip()):
            i += 1; buf.append(lines[i].strip())
        story.append(Paragraph(inline(''.join(buf)), BODY))
        i += 1
    return story

# ── 主程式 ────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        raise SystemExit('用法：python3 md_to_pdf.py input.md [output.pdf]')
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + '.pdf'
    first = open(src, encoding='utf-8').readline().lstrip('# ').strip()
    doc = SimpleDocTemplate(dst, pagesize=A4,
                            leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title=first, author='Indexasia')
    doc.build(parse(src))
    print(f'✅ {dst}')

if __name__ == '__main__':
    main()
