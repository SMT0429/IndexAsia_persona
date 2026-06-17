#!/usr/bin/env python3
"""將 Markdown 報告轉為 PDF（Markdown → HTML → headless Chrome 列印）。"""
import sys, subprocess, tempfile, os, markdown

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
@page { size: A4; margin: 20mm 18mm; }
body { font-family: "PingFang TC", "Heiti TC", "Microsoft JhengHei", sans-serif;
       font-size: 10.5pt; line-height: 1.7; color: #1a1a1a; }
h1 { font-size: 20pt; border-bottom: 3px solid #2c3e50; padding-bottom: 8px; }
h2 { font-size: 15pt; color: #2c3e50; border-bottom: 1px solid #bdc3c7;
     padding-bottom: 4px; margin-top: 1.6em; }
h3 { font-size: 12.5pt; color: #34495e; margin-top: 1.3em; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 9.5pt; }
th, td { border: 1px solid #ccc; padding: 5px 8px; }
th { background: #2c3e50; color: #fff; text-align: left; }
tr:nth-child(even) td { background: #f5f7fa; }
td[align=right], th[align=right] { text-align: right; }
blockquote { border-left: 4px solid #95a5a6; margin: 1em 0; padding: 0.4em 1em;
             background: #f8f9fa; color: #555; font-size: 9.5pt; }
code { background: #f0f0f0; padding: 1px 4px; border-radius: 3px;
       font-family: "Menlo", monospace; font-size: 9pt; }
hr { border: none; border-top: 1px solid #ddd; margin: 1.5em 0; }
strong { color: #1a1a1a; }
"""

def fix_lists(text):
    """在清單前補空行：Python-Markdown 需清單前有空行才會正確辨識為列點。"""
    out = []
    for line in text.split("\n"):
        is_item = line.lstrip().startswith(("- ", "* ", "+ ")) or \
                  (line.lstrip()[:2].rstrip(".").isdigit() and ". " in line[:5])
        if is_item and out:
            prev = out[-1]
            prev_item = prev.lstrip().startswith(("- ", "* ", "+ "))
            prev_cont = prev.startswith(("  ", "\t")) and prev.strip()
            if prev.strip() and not prev_item and not prev_cont:
                out.append("")
        out.append(line)
    return "\n".join(out)


def main(md_path, pdf_path):
    with open(md_path, encoding="utf-8") as f:
        text = f.read()
    text = fix_lists(text)
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tf:
        tf.write(html)
        html_path = tf.name
    try:
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={pdf_path}", f"file://{html_path}"],
                       check=True, capture_output=True)
        print(f"wrote {pdf_path}")
    finally:
        os.unlink(html_path)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
