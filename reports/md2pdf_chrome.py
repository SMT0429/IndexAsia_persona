#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""md → HTML（原報告風格）→ Headless Chrome → PDF。MD 為唯一內容來源。"""
import html, re, sys, os, asyncio

FONT_CSS = os.environ.get('FONT_CSS', '/tmp/fontsource')

CSS = """
@page { size: A4; margin: 1.8cm 2.0cm; }
* { box-sizing: border-box; }
body { font-family: 'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif;
       font-size: 10pt; line-height: 1.8; color: #1a1a1a; text-align: justify; margin: 0; }
h1.doc-title { font-size: 16.5pt; font-weight: 700; color: #111522; margin: 40px 0 16px; line-height: 1.5; }
p.meta { margin: 2px 0; }
h1.group { font-size: 15pt; font-weight: 700; color: #16213e; margin: 30px 0 10px; page-break-after: avoid; }
h2 { font-size: 12.5pt; font-weight: 700; color: #16213e; border-left: 5px solid #16213e;
     padding-left: 10px; margin: 26px 0 10px; page-break-after: avoid; }
h3 { font-size: 11pt; font-weight: 700; color: #16213e; margin: 20px 0 6px; page-break-after: avoid; }
p { margin: 6px 0; }
strong { color: #111522; }
hr { border: none; border-top: 1px solid #ddd; margin: 18px 0; }
table { width: 100%; border-collapse: collapse; margin: 10px 0 14px; page-break-inside: auto; }
thead { display: table-header-group; }
tr { page-break-inside: avoid; }
th { background: #1a3a5a; color: #fff; font-weight: 700; font-size: 9.2pt;
     padding: 8px 10px; border: 1px solid #b9bfc8; text-align: center; }
td { font-size: 9.2pt; padding: 7px 10px; border: 1px solid #bbb; text-align: left; }
tbody tr:nth-child(even) td { background: #f4f7fa; }
blockquote { border-left: 4px solid #c9ced6; background: #f8f9fb; color: #555;
             font-size: 9.2pt; line-height: 1.75; padding: 8px 14px; margin: 8px 0 12px; }
blockquote p { margin: 2px 0; }
ol, ul { margin: 6px 0; padding-left: 26px; }
li { margin: 3px 0; }
code { color: #c0392b; font-family: 'SFMono-Regular', Menlo, Consolas, monospace; font-size: 9pt; }
em { font-style: italic; }
"""

def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<![\w*])\*([^*\n]+?)\*(?![\w*])', r'<em>\1</em>', t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    return t

ALIGN = {None: '', 'l': '', 'c': ' style="text-align:center"', 'r': ' style="text-align:right"'}

def table_html(rows, aligns):
    out = ['<table>']
    out.append('<thead><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in rows[0]) + '</tr></thead><tbody>')
    for r in rows[1:]:
        cells = []
        for j, c in enumerate(r):
            a = aligns[j] if j < len(aligns) else None
            cells.append(f'<td{ALIGN[a]}>{inline(c)}</td>')
        out.append('<tr>' + ''.join(cells) + '</tr>')
    out.append('</tbody></table>')
    return '\n'.join(out)

def parse(md):
    lines = md.splitlines()
    out, i, title_done = [], 0, False
    n = len(lines)
    while i < n:
        st = lines[i].strip()
        if not st:
            i += 1; continue
        if st == '---':
            out.append('<hr>'); i += 1; continue
        if st.startswith('#### '):
            out.append(f'<h3>{inline(st[5:])}</h3>'); i += 1; continue
        if st.startswith('### '):
            out.append(f'<h3>{inline(st[4:])}</h3>'); i += 1; continue
        if st.startswith('## '):
            out.append(f'<h2>{inline(st[3:])}</h2>'); i += 1; continue
        if st.startswith('# '):
            if not title_done:
                out.append(f'<h1 class="doc-title">{inline(st[2:])}</h1>'); title_done = True
            else:
                out.append(f'<h1 class="group">{inline(st[2:])}</h1>')
            i += 1; continue
        if st.startswith('>'):
            buf = []
            while i < n and lines[i].strip().startswith('>'):
                buf.append(inline(lines[i].strip().lstrip('> ').strip())); i += 1
            out.append('<blockquote><p>' + '<br>'.join(buf) + '</p></blockquote>'); continue
        if st.startswith('|'):
            rows, aligns = [], []
            while i < n and lines[i].strip().startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if cells and all(re.fullmatch(r':?-{2,}:?', c) for c in cells):
                    aligns = ['c' if c.startswith(':') and c.endswith(':') else
                              'r' if c.endswith(':') else 'l' for c in cells]
                else:
                    rows.append(cells)
                i += 1
            if rows:
                if not aligns: aligns = ['l'] * len(rows[0])
                out.append(table_html(rows, aligns))
            continue
        m_ol = re.match(r'^(\d+)\.\s+(.*)$', st)
        if st.startswith(('- ', '* ')) or m_ol:
            tag = 'ol' if m_ol else 'ul'
            items = []
            while i < n:
                s2 = lines[i].strip()
                m2 = re.match(r'^(\d+)\.\s+(.*)$', s2)
                if tag == 'ol' and m2:
                    items.append(inline(m2.group(2))); i += 1
                elif tag == 'ul' and s2.startswith(('- ', '* ')):
                    items.append(inline(s2[2:])); i += 1
                elif s2 and lines[i].startswith(('  ', '\t')) and items and \
                        not s2.startswith(('|', '#', '>', '- ', '* ')) and not re.match(r'^\d+\.\s', s2):
                    items[-1] += '<br>' + inline(s2); i += 1
                else:
                    break
            out.append(f'<{tag}>' + ''.join(f'<li>{x}</li>' for x in items) + f'</{tag}>')
            continue
        buf = [st]
        while i + 1 < n:
            nx = lines[i + 1].strip()
            if not nx or nx.startswith(('#', '|', '>', '- ', '* ', '```', '---', '**')) or re.match(r'^\d+\.\s', nx):
                break
            i += 1; buf.append(nx)
        cls = ' class="meta"' if not any('</h2>' in x or '<h1 class="group"' in x for x in out) \
              and buf[0].startswith('**') and '：**' in buf[0] else ''
        out.append(f'<p{cls}>' + inline(''.join(buf)) + '</p>')
        i += 1
    return '\n'.join(out)

def main():
    src, dst = sys.argv[1], sys.argv[2]
    md = open(src, encoding='utf-8').read()
    first = md.splitlines()[0].lstrip('# ').strip()
    body = parse(md)
    page = (f'<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">'
            f'<title>{html.escape(first)}</title>'
            f'<link rel="stylesheet" href="file://{FONT_CSS}/400.css">'
            f'<link rel="stylesheet" href="file://{FONT_CSS}/500.css">'
            f'<link rel="stylesheet" href="file://{FONT_CSS}/700.css">'
            f'<style>{CSS}</style></head><body>{body}</body></html>')
    tmp = os.path.join(os.path.dirname(os.path.abspath(dst)) or '.', '_tmp_report.html')
    open(tmp, 'w', encoding='utf-8').write(page)

    async def render():
        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            b = await pw.chromium.launch(args=['--no-sandbox', '--force-color-profile=srgb'])
            pg = await b.new_page()
            await pg.goto('file://' + os.path.abspath(tmp))
            await pg.wait_for_timeout(800)  # 等字型載入
            await pg.pdf(path=dst, format='A4', print_background=True, prefer_css_page_size=True)
            await b.close()
    asyncio.run(render())
    print('OK', dst)

if __name__ == '__main__':
    main()
