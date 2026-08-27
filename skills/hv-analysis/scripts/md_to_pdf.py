#!/usr/bin/env python3
"""
横纵分析法报告 Markdown → PDF 转换脚本

双引擎设计:
  1. 首选 WeasyPrint  —— 排版精美(封面/页眉页脚/表格/中文混排),需要 GTK 库
  2. 兜底 fpdf2       —— 纯 Python,零外部依赖,任何环境都能出 PDF

用法:
  python md_to_pdf.py input.md output.pdf [--title "报告标题"] [--author "作者"]

依赖(任选其一即可跑通):
  pip install weasyprint markdown        # 走 WeasyPrint 高品质路径
  pip install fpdf2 markdown             # 走 fpdf2 兜底路径
"""

import sys
import os
import re
import argparse
import markdown

# ═══════════════════════════════════════════════════════════════════
# 第一部分:WeasyPrint 路径(CSS + HTML)
# ═══════════════════════════════════════════════════════════════════

CSS_TEMPLATE = """
@page {
    size: A4;
    margin: 25mm 20mm 20mm 20mm;

    @top-center {
        content: "HEADER_TEXT";
        font-family: "Microsoft YaHei", "SimSun", "SimHei", "Droid Sans Fallback", Helvetica, Arial, sans-serif;
        font-size: 8pt;
        color: #95a5a6;
        border-bottom: 0.5pt solid #ecf0f1;
        padding-bottom: 3mm;
    }

    @bottom-center {
        content: "第 " counter(page) " 页";
        font-family: "Microsoft YaHei", "SimSun", "SimHei", "Droid Sans Fallback", Helvetica, Arial, sans-serif;
        font-size: 8pt;
        color: #95a5a6;
        border-top: 0.8pt solid #1a5276;
        padding-top: 2mm;
    }
}

@page :first {
    @top-center { content: none; }
    @bottom-center { content: none; }
}

body {
    font-family: "Microsoft YaHei", "SimSun", "SimHei", "Droid Sans Fallback", Helvetica, Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.75;
    color: #2c3e50;
    text-align: justify;
}

h1 { color: #1a5276; font-size: 22pt; margin-top: 0; }
h2 { color: #1e8449; font-size: 16pt; }
h3 { color: #2e86c1; font-size: 13pt; }
h4 { color: #5b2c6f; font-size: 11pt; }

blockquote {
    border-left: 3pt solid #1a5276;
    background: #f4f6f7;
    margin: 10pt 0;
    padding: 6pt 12pt;
}

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 9pt;
}
th { background: #1a5276; color: white; padding: 6pt; text-align: left; }
td { border: 1pt solid #ddd; padding: 5pt 6pt; }
tr:nth-child(even) { background: #f4f6f7; }

.cover {
    text-align: center;
    padding-top: 80pt;
}
.cover h1 {
    font-size: 28pt;
    color: #1a5276;
    border: none;
}
.subtitle { color: #1e8449; font-size: 14pt; margin-top: 10pt; }
.meta { color: #7f8c8d; font-size: 10pt; margin-top: 6pt; }
.divider {
    border: none;
    border-top: 1pt solid #1a5276;
    width: 60%;
    margin: 24pt auto;
}
"""


def md_to_html(md_text, title="横纵分析报告", subtitle="横纵分析法深度研究报告",
               meta_line="", author="数字生命卡兹克"):
    """将 Markdown 转为带封面的 HTML(供 WeasyPrint 使用)"""
    html_body = markdown.markdown(
        md_text,
        extensions=['tables', 'fenced_code', 'nl2br'],
        output_format='html5'
    )

    first_h1_match = re.search(r'<h1>(.*?)</h1>', html_body)
    if first_h1_match:
        extracted_title = first_h1_match.group(1)
        if not title or title == "横纵分析报告":
            title = extracted_title
        html_body = html_body.replace(first_h1_match.group(0), '', 1)

    css = CSS_TEMPLATE.replace("HEADER_TEXT", f"{title}  |  横纵分析法深度研究报告")

    cover_html = f"""
    <div class="cover">
        <h1 style="page-break-before: avoid; border: none;">{title}</h1>
        <div class="subtitle">{subtitle}</div>
        {"<div class='meta'>" + meta_line + "</div>" if meta_line else ""}
        <hr class="divider">
        <div class="meta">作者: {author}</div>
    </div>
    """

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <style>{css}</style>
</head>
<body>
{cover_html}
{html_body}
</body>
</html>"""


def render_with_weasyprint(html, output_path):
    """用 WeasyPrint 渲染(需 GTK)"""
    from weasyprint import HTML
    HTML(string=html).write_pdf(output_path)


# ═══════════════════════════════════════════════════════════════════
# 第二部分:fpdf2 兜底路径(纯 Python,零外部依赖)
# ═══════════════════════════════════════════════════════════════════

def find_cjk_font():
    """跨平台查找中文字体"""
    candidates = [
        # Windows
        "C:\\Windows\\Fonts\\simsun.ttc",
        "C:\\Windows\\Fonts\\msyh.ttc",
        "C:\\Windows\\Fonts\\simhei.ttf",
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        # Linux
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def parse_blocks(md_text):
    """极简 Markdown 块解析(兜底用)"""
    blocks = []
    lines = md_text.split('\n')
    i = 0
    table_rows = []
    in_table = False

    while i < len(lines):
        line = lines[i].rstrip()

        m = re.match(r'^(#{1,6})\s+(.+)$', line)
        if m:
            blocks.append(('h' + str(len(m.group(1))), m.group(2).strip()))
            i += 1
            continue

        if line.startswith('>'):
            blocks.append(('quote', line[1:].strip()))
            i += 1
            continue

        if '|' in line and i + 1 < len(lines) and re.match(r'^\|?[\s\-:|]+\|?$', lines[i + 1]):
            if not in_table:
                in_table, table_rows = True, []
            table_rows.append(line)
            i += 1
            if i >= len(lines) or '|' not in lines[i]:
                in_table = False
                blocks.append(('table', table_rows))
                table_rows = []
            continue
        elif in_table:
            in_table = False
            blocks.append(('table', table_rows))
            table_rows = []

        if re.match(r'^\s*[-*+]\s+', line) or re.match(r'^\s*\d+\.\s+', line):
            blocks.append(('list', re.sub(r'^\s*([-*+]|\d+\.)\s+', '', line)))
            i += 1
            continue

        if re.match(r'^\s*---+\s*$', line):
            blocks.append(('hr', ''))
            i += 1
            continue

        if not line.strip():
            if not blocks or blocks[-1][0] != 'blank':
                blocks.append(('blank', ''))
            i += 1
            continue

        blocks.append(('p', line))
        i += 1

    return blocks


def render_with_fpdf2(md_text, output_path, title=None, author="数字生命卡兹克"):
    """用 fpdf2 渲染(不需 GTK)"""
    from fpdf import FPDF

    font_path = find_cjk_font()
    if not font_path:
        raise RuntimeError(
            "未找到中文字体,且 WeasyPrint 不可用。\n"
            "请安装中文字体(如 Windows 的宋体),或安装 GTK 后使用 WeasyPrint。"
        )

    pdf = FPDF(format='A4')
    pdf.set_margins(20, 25, 20)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_font("CJK", "", font_path)
    pdf.add_font("CJK", "B", font_path)

    # 封面
    pdf.add_page()
    pdf.set_font("CJK", "B", 28)
    pdf.set_text_color(26, 82, 118)
    pdf.ln(55)
    pdf.multi_cell(0, 15, "横纵分析法深度研究报告", align='C')
    pdf.set_font("CJK", "", 12)
    pdf.set_text_color(100, 100, 100)
    pdf.ln(5)
    pdf.cell(0, 8, "Horizontal-Vertical Analysis Framework", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(25)

    main_title = title
    if not main_title:
        for line in md_text.split('\n'):
            mm = re.match(r'^#\s+(.+)$', line.strip())
            if mm:
                main_title = mm.group(1)
                break

    if main_title:
        pdf.set_font("CJK", "B", 18)
        pdf.set_text_color(30, 132, 73)
        pdf.multi_cell(0, 11, main_title, align='C')
        pdf.ln(8)
    pdf.set_font("CJK", "", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"作者: {author}", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    y = pdf.get_y()
    pdf.set_draw_color(26, 82, 118)
    pdf.line(40, y, pdf.w - 40, y)

    # 正文
    pdf.add_page()
    pdf.set_text_color(44, 62, 80)
    blocks = parse_blocks(md_text)
    first_h1_done = main_title is not None

    for btype, content in blocks:
        if btype == 'h1':
            if first_h1_done:
                continue
            first_h1_done = True
        elif btype == 'h1':
            pdf.set_font("CJK", "B", 18)
            pdf.set_text_color(26, 82, 118)
            pdf.ln(6)
            pdf.multi_cell(0, 10, content)
            pdf.ln(3)
        elif btype == 'h2':
            pdf.set_font("CJK", "B", 14)
            pdf.set_text_color(30, 132, 73)
            pdf.ln(5)
            pdf.multi_cell(0, 9, content)
            pdf.ln(2)
        elif btype == 'h3':
            pdf.set_font("CJK", "B", 12)
            pdf.set_text_color(46, 134, 193)
            pdf.ln(3)
            pdf.multi_cell(0, 7, content)
            pdf.ln(1)
        elif btype == 'h4':
            pdf.set_font("CJK", "B", 11)
            pdf.set_text_color(91, 44, 111)
            pdf.ln(2)
            pdf.multi_cell(0, 6, content)
        elif btype == 'p':
            pdf.set_font("CJK", "", 10.5)
            pdf.set_text_color(44, 62, 80)
            pdf.multi_cell(0, 6, content)
            pdf.ln(2)
        elif btype == 'quote':
            pdf.set_font("CJK", "", 10)
            pdf.set_text_color(100, 100, 100)
            pdf.set_x(pdf.l_margin + 5)
            pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 5, 6, "│ " + content)
            pdf.ln(2)
        elif btype == 'list':
            pdf.set_font("CJK", "", 10.5)
            pdf.set_text_color(44, 62, 80)
            pdf.set_x(pdf.l_margin + 5)
            pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 5, 6, "• " + content)
            pdf.ln(1)
        elif btype == 'hr':
            y = pdf.get_y()
            pdf.set_draw_color(200, 200, 200)
            pdf.line(40, y, pdf.w - 40, y)
            pdf.ln(4)
        elif btype == 'table':
            _render_table_fpdf(pdf, content)
        elif btype == 'blank':
            pdf.ln(2)

    pdf.output(output_path)


def _render_table_fpdf(pdf, rows):
    if len(rows) < 2:
        return
    parsed = []
    for r in rows:
        parsed.append([c.strip() for c in r.strip('|').split('|')])
    header = parsed[0]
    data_rows = [r for r in parsed[1:] if not re.match(r'^[\s\-:]+$', ''.join(r))]
    n = len(header)
    col_w = (pdf.w - pdf.l_margin - pdf.r_margin) / n

    pdf.set_font("CJK", "B", 9)
    pdf.set_fill_color(26, 82, 118)
    pdf.set_text_color(255, 255, 255)
    for c in header:
        pdf.cell(col_w, 8, c[:18], border=1, fill=True, align='C')
    pdf.ln()
    pdf.set_font("CJK", "", 8.5)
    pdf.set_text_color(44, 62, 80)
    fill = False
    for r in data_rows:
        if fill:
            pdf.set_fill_color(240, 245, 250)
        for i, c in enumerate(r[:n]):
            pdf.cell(col_w, 7, (c[:26] + '…') if len(c) > 27 else c, border=1, fill=fill, align='L')
        pdf.ln()
        fill = not fill
    pdf.ln(3)


# ═══════════════════════════════════════════════════════════════════
# 第三部分:主入口(自动选择引擎)
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="横纵分析法报告 Markdown → PDF")
    parser.add_argument("input", help="输入的 Markdown 文件路径")
    parser.add_argument("output", help="输出的 PDF 文件路径")
    parser.add_argument("--title", default=None, help="报告标题(默认取正文第一个 #)")
    parser.add_argument("--author", default="数字生命卡兹克", help="作者名")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        md_text = f.read()

    meta_line = ""
    for line in md_text.split("\n"):
        stripped = line.strip().lstrip(">").strip()
        if any(k in stripped for k in ("研究时间", "所属领域", "研究对象类型")):
            meta_line = stripped
            break

    # ── 尝试 WeasyPrint(高品质) ──
    try:
        import weasyprint  # noqa
        html = md_to_html(md_text, title=args.title or "横纵分析报告",
                          meta_line=meta_line, author=args.author)
        html_path = args.output.replace('.pdf', '.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"[引擎] WeasyPrint")
        print(f"[OK] HTML 已生成: {html_path}")
        render_with_weasyprint(html, args.output)
        size_kb = os.path.getsize(args.output) / 1024
        print(f"[OK] PDF 已生成: {args.output} ({size_kb:.1f} KB)")
        return
    except Exception as e:
        print(f"[提示] WeasyPrint 不可用({type(e).__name__}),自动切换到 fpdf2 兜底引擎。")
        print(f"       如需高品质排版,请安装 GTK 后重试:pip install weasyprint")

    # ── 兜底 fpdf2 ──
    try:
        render_with_fpdf2(md_text, args.output, title=args.title, author=args.author)
        size_kb = os.path.getsize(args.output) / 1024
        print(f"[引擎] fpdf2 (兜底)")
        print(f"[OK] PDF 已生成: {args.output} ({size_kb:.1f} KB)")
    except Exception as e:
        print(f"[错误] 两种引擎均失败:{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
