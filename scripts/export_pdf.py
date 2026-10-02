#!/usr/bin/env python3
"""Export the complete book with Python, reportlab and pypdf.

Usage: python3 scripts/export_pdf.py
Override fonts with --font-regular / --font-bold, or DOT_BOOK_FONT_REGULAR /
DOT_BOOK_FONT_BOLD. Font collection indices default to 0 and can be overridden.
The site is rebuilt first with Node.js, preserving the existing deployment base.
The About page is then read from the newly generated dist/about/index.html.
The previous PDF is replaced atomically only after content validation succeeds.
"""

from __future__ import annotations

import argparse
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from html import escape, unescape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

try:
    from pypdf import PdfReader
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        BaseDocTemplate, Flowable, Frame, KeepTogether, LongTable, PageBreak,
        PageTemplate, Paragraph, Spacer, Table, TableStyle,
    )
    from reportlab.platypus.tableofcontents import TableOfContents
except ImportError as exc:
    raise SystemExit(
        "PDF export needs separate Python dependencies: "
        "python3 -m pip install reportlab pypdf\n" + str(exc)
    )

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SITE = "https://tiee7.github.io/dot-green-book/"
PUBLIC_REPO = "https://github.com/Tiee7/dot-green-book/"
PUBLIC_READING = "https://dot.1idea.xyz/"
PUBLIC_SHOWCASE = "https://dot.1idea.xyz/showcase/"
FACT_DATE = "2026-10-01"
PAGE_W, PAGE_H = A4
LEFT, RIGHT, TOP, BOTTOM = 55, 55, 66, 55
CONTENT_W = PAGE_W - LEFT - RIGHT
GREEN = colors.HexColor("#245a45")
INK = colors.HexColor("#243c32")
MUTED = colors.HexColor("#64766b")
PALE = colors.HexColor("#eef3e7")
LINE = colors.HexColor("#c8d5bf")
DASHES = str.maketrans({c: "-" for c in "‐‑‒–—−"})


def clean(value: object) -> str:
    return unescape(str(value)).translate(DASHES).replace("\u00a0", " ")


def normalized(value: object) -> str:
    return re.sub(r"\s+", "", clean(value))


@dataclass
class Element:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list[Element | str] = field(default_factory=list)

    def text(self) -> str:
        return "".join(x.text() if isinstance(x, Element) else x for x in self.children)


class HTMLTree(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.root = Element("root")
        self.stack = [self.root]
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        node = Element(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in {"br", "hr", "img", "input", "meta", "link", "source", "wbr"}:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self.stack[-1].tag == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def find_elements(node: Element, tag: str):
    if node.tag == tag:
        yield node
    for child in node.children:
        if isinstance(child, Element):
            yield from find_elements(child, tag)


class Cover(Flowable):
    def __init__(self, date: str, counts: tuple[int, int, int], version: str):
        super().__init__()
        self.width = CONTENT_W
        self.height = PAGE_H - TOP - BOTTOM - 2
        self.date, self.counts, self.version = date, counts, version

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        c.setFillColor(PALE)
        c.rect(-LEFT, -BOTTOM, PAGE_W, PAGE_H, fill=1, stroke=0)
        c.setFillColor(GREEN)
        c.setFont("BookRegular", 11)
        c.drawString(0, h - 32, "THE DOT GREEN BOOK")
        c.setFont("BookBold", 57)
        c.drawString(0, h - 150, "Dot")
        c.drawString(0, h - 222, "小绿皮书")
        c.setStrokeColor(GREEN)
        c.setLineWidth(1.2)
        c.line(0, h - 250, w, h - 250)
        c.setFont("BookRegular", 17)
        c.drawString(0, h - 296, "从第一次交代任务，到持续协作。")
        c.setFont("BookRegular", 11)
        a, b, d = self.counts
        c.drawString(0, h - 344, f"{a} 章渐进教程  /  {b} 条实用问答  /  {d} 个精选 Dot 案例")
        c.setFont("BookRegular", 10)
        c.drawString(0, 109, f"完整阅读版 · 导出日期 {self.date} · 内容版本 {self.version}")
        c.drawString(0, 87, f"原始产品事实核对日期 {FACT_DATE}")
        c.drawString(0, 47, "开源中文教程 · 持续更新")


class BookTemplate(BaseDocTemplate):
    def __init__(self, path: Path, date: str):
        super().__init__(str(path), pagesize=A4, leftMargin=LEFT, rightMargin=RIGHT,
                         topMargin=TOP, bottomMargin=BOTTOM,
                         title="Dot小绿皮书 - 完整阅读版", author="Dot小绿皮书 contributors")
        self.date = date
        frame = Frame(LEFT, BOTTOM, CONTENT_W, PAGE_H - TOP - BOTTOM,
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate("book", [frame], onPage=self.decorate))

    def decorate(self, canvas, doc):
        if doc.page == 1:
            return
        canvas.saveState()
        canvas.setFont("BookRegular", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(LEFT, PAGE_H - 31, "Dot小绿皮书")
        canvas.drawRightString(PAGE_W - RIGHT, PAGE_H - 31,
                               "完整阅读版 · " + self.date.replace("-", "."))
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(.4)
        canvas.line(LEFT, PAGE_H - 43, PAGE_W - RIGHT, PAGE_H - 43)
        canvas.line(LEFT, 39, PAGE_W - RIGHT, 39)
        canvas.setFont("BookRegular", 7.7)
        canvas.drawString(LEFT, 26, "开源中文教程 · 内容事实核对于 " + FACT_DATE.replace("-", "."))
        canvas.drawRightString(PAGE_W - RIGHT, 26, f"第 {doc.page} 页")
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if hasattr(flowable, "bookmark"):
            key, title, level = flowable.bookmark
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, level=level, closed=level == 0)
            self.notify("TOCEntry", (level, title, self.page, key))


class Exporter:
    def __init__(self, root: Path, date: str):
        self.root, self.date = root, date
        build_info = root / "dist/build-info.json"
        self.site_base = json.loads(build_info.read_text()).get("base", "/") if build_info.exists() else "/"
        self.expected: list[str] = []
        self.serial = 0
        self.link_urls: set[str] = set()
        base = dict(fontName="BookRegular", fontSize=10.3, leading=17,
                    textColor=INK, wordWrap="CJK", alignment=TA_LEFT, spaceAfter=9,
                    splitLongWords=True)
        self.styles = {
            "body": ParagraphStyle("body", **base),
            "small": ParagraphStyle("small", **{**base, "fontSize": 8.4, "leading": 12.2, "textColor": MUTED, "spaceAfter": 8}),
            "case": ParagraphStyle("case", **{**base, "fontSize": 9.1, "leading": 14.7, "spaceAfter": 7}),
            "faq": ParagraphStyle("faq", **{**base, "fontSize": 9.6, "leading": 15.2, "spaceAfter": 7}),
            "table": ParagraphStyle("table", **{**base, "fontSize": 8.3, "leading": 12.8, "spaceAfter": 0}),
            "link": ParagraphStyle("link", **{**base, "fontSize": 7.7, "leading": 10.9, "textColor": GREEN, "spaceAfter": 9}),
            "subtitle": ParagraphStyle("subtitle", **{**base, "fontSize": 11.4, "leading": 18, "textColor": MUTED}),
            "h1": ParagraphStyle("h1", **{**base, "fontName": "BookBold", "fontSize": 21.5, "leading": 29, "textColor": GREEN, "spaceAfter": 13, "keepWithNext": True}),
            "case-title": ParagraphStyle("case-title", **{**base, "fontName": "BookBold", "fontSize": 18.7, "leading": 26, "textColor": GREEN, "spaceAfter": 10, "keepWithNext": True}),
            "h2": ParagraphStyle("h2", **{**base, "fontName": "BookBold", "fontSize": 12, "leading": 18, "spaceBefore": 8, "spaceAfter": 7, "keepWithNext": True}),
            "h3": ParagraphStyle("h3", **{**base, "fontName": "BookBold", "fontSize": 10.5, "leading": 16, "spaceBefore": 6, "spaceAfter": 5, "keepWithNext": True}),
            "case-h2": ParagraphStyle("case-h2", **{**base, "fontName": "BookBold", "fontSize": 11, "leading": 16, "spaceBefore": 5, "spaceAfter": 5, "keepWithNext": True}),
            "code": ParagraphStyle("code", **{**base, "fontSize": 8.7, "leading": 13.4, "spaceAfter": 0}),
        }

    def remember(self, text: str):
        if normalized(text):
            self.expected.append(clean(text))

    def paragraph(self, text: str, style="body", markup=False, expected=None):
        plain = clean(expected if expected is not None else text)
        self.remember(plain)
        return Paragraph(clean(text) if markup else escape(plain), self.styles[style])

    def heading(self, text: str, level=0, style="h1", bookmark=False):
        p = self.paragraph(text, style)
        if bookmark:
            self.serial += 1
            p.bookmark = (f"book-{self.serial}", clean(text), level)
        return p

    def link(self, label: str, target: str, style="link"):
        target = self.resolve_link(target)
        self.link_urls.add(target)
        markup = f'<link href="{escape(target, quote=True)}" color="#245a45">{escape(clean(label))}<br/>{escape(clean(target))}</link>'
        return self.paragraph(markup, style, markup=True, expected=label + " " + target)

    def resolve_link(self, target: str) -> str:
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
            return target
        if target.startswith("/"):
            relative = target[len(self.site_base):] if target.startswith(self.site_base) else target.lstrip("/")
            return urljoin(PUBLIC_SITE, relative)
        return urljoin(PUBLIC_REPO + "blob/main/", target)

    def box(self, text: str, style="body"):
        p = self.paragraph(text, style)
        t = Table([[p]], colWidths=[CONTENT_W], hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE),
                              ("BOX", (0, 0), (-1, -1), .4, LINE),
                              ("LEFTPADDING", (0, 0), (-1, -1), 9),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                              ("TOPPADDING", (0, 0), (-1, -1), 8),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
        return t

    def list_items(self, values: list[str], style="body", numbered=False, checkbox=False):
        return [self.paragraph((f"{i}. " if numbered else "□ " if checkbox else "• ") + text, style)
                for i, text in enumerate(values, 1)]

    def source_links(self, urls: list[str], label="继续核对产品资料"):
        return [self.link(label, url) for url in dict.fromkeys(urls)]

    def exercise(self, prompt: str, style="body"):
        return [self.heading("试着这样交代", style="case-h2" if style == "case" else "h2"),
                self.box(prompt, style),
                self.paragraph("这是教学改编指令，尚未替你执行；请按实际账户、资料与日期调整。", "small")]

    def table(self, rows, widths=None, html=False):
        if not rows:
            return Spacer(1, 1)
        n = len(rows[0])
        if widths is None:
            widths = ({2: [.32, .68], 3: [.27, .17, .56],
                       4: [.23, .09, .43, .25], 5: [.2] * 5}.get(n, [1 / n] * n))
        cells = []
        for row in rows:
            prepared = []
            for cell in row:
                markup, plain = cell if html else self.markdown_inline(cell)
                prepared.append(self.paragraph(markup, "table", markup=True, expected=plain))
            cells.append(prepared)
        t = LongTable(cells, colWidths=[CONTENT_W * w for w in widths], repeatRows=1,
                      hAlign="LEFT", splitByRow=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), PALE),
                              ("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("LINEBELOW", (0, 0), (-1, -1), .35, LINE),
                              ("LEFTPADDING", (0, 0), (-1, -1), 7),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                              ("TOPPADDING", (0, 0), (-1, -1), 7),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
        return t

    def markdown_inline(self, value: str):
        value = clean(value)
        pieces, plain = [], []
        pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*|`([^`]+)`")
        pos = 0
        for m in pattern.finditer(value):
            before = value[pos:m.start()]
            pieces.append(escape(before)); plain.append(before)
            if m.group(1) is not None:
                label, target = m.group(1), self.resolve_link(m.group(2))
                self.link_urls.add(target)
                pieces.append(f'<link href="{escape(target, quote=True)}" color="#245a45">{escape(label)}</link>')
                pieces.append(f'<font size="7.7" color="#64766b"> ({escape(target)})</font>')
                plain.append(label + " (" + target + ")")
            elif m.group(3) is not None:
                pieces.append(f'<b>{escape(m.group(3))}</b>'); plain.append(m.group(3))
            else:
                pieces.append(escape(m.group(4))); plain.append(m.group(4))
            pos = m.end()
        pieces.append(escape(value[pos:])); plain.append(value[pos:])
        return "".join(pieces), "".join(plain)

    def markdown(self, source: str):
        lines = source.splitlines()
        out = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1; continue
            if line.startswith("```"):
                i += 1; code = []
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code.append(lines[i]); i += 1
                content = "<br/>".join(escape(clean(x)) for x in code)
                p = self.paragraph(content, "code", markup=True, expected="\n".join(code))
                t = Table([[p]], colWidths=[CONTENT_W])
                t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE),
                                      ("TOPPADDING", (0, 0), (-1, -1), 8),
                                      ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                                      ("LEFTPADDING", (0, 0), (-1, -1), 9),
                                      ("RIGHTPADDING", (0, 0), (-1, -1), 9)]))
                out.extend([t, Spacer(1, 8)]); i += 1; continue
            match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if match:
                markup, plain = self.markdown_inline(match.group(2))
                out.append(self.paragraph(markup, "h2" if len(match.group(1)) <= 2 else "h3", markup=True, expected=plain))
                i += 1; continue
            if "|" in line and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-+", lines[i + 1]):
                rows = [line.strip("|").split("|")]
                i += 2
                while i < len(lines) and "|" in lines[i] and lines[i].strip():
                    rows.append(lines[i].strip().strip("|").split("|")); i += 1
                out.extend([self.table([[c.strip() for c in row] for row in rows]), Spacer(1, 9)]); continue
            if re.match(r"^[-*+]\s+", line) or re.match(r"^\d+\.\s+", line):
                content = re.sub(r"^[-*+]\s+", "• ", line)
                markup, plain = self.markdown_inline(content)
                out.append(self.paragraph(markup, markup=True, expected=plain)); i += 1; continue
            paragraph = [line]; i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,6}\s|```|[-*+]\s|\d+\.\s)", lines[i].strip()):
                if "|" in lines[i] and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-+", lines[i + 1]):
                    break
                paragraph.append(lines[i].strip()); i += 1
            markup, plain = self.markdown_inline(" ".join(paragraph))
            out.append(self.paragraph(markup, markup=True, expected=plain))
        return out

    def html_inline(self, node: Element | str):
        if isinstance(node, str):
            return escape(clean(node)), clean(node)
        if node.tag == "br":
            return "<br/>", " "
        parts = [self.html_inline(x) for x in node.children]
        markup, plain = "".join(x[0] for x in parts), "".join(x[1] for x in parts)
        if node.tag == "a" and node.attrs.get("href"):
            target = self.resolve_link(node.attrs["href"])
            self.link_urls.add(target)
            markup = f'<link href="{escape(target, quote=True)}" color="#245a45">{markup}</link>'
            markup += f'<font size="7.7" color="#64766b"> ({escape(target)})</font>'
            plain += " (" + target + ")"
        if node.tag in {"b", "strong"}:
            markup = "<b>" + markup + "</b>"
        return markup, plain

    def about(self, source: str):
        tree = HTMLTree(source)
        main = next(find_elements(tree.root, "main"), None)
        if main is None:
            raise ValueError("Built About page has no main element; run npm run build first.")
        out = []
        blocks = {"h1", "h2", "h3", "h4", "p", "ul", "ol", "li", "table", "section", "div", "aside", "article", "nav"}

        def walk(node):
            if isinstance(node, str):
                if node.strip():
                    out.append(self.paragraph(node))
                return
            if node.tag in {"script", "style", "button", "input"} or "breadcrumb" in node.attrs.get("class", "").split():
                return
            if node.tag in {"h1", "h2", "h3", "h4", "p", "li"}:
                markup, plain = self.html_inline(node)
                style = "h2" if node.tag in {"h1", "h2"} else "h3" if node.tag in {"h3", "h4"} else "body"
                if node.tag == "li":
                    markup, plain = "• " + markup, "• " + plain
                out.append(self.paragraph(markup, style, markup=True, expected=plain))
            elif node.tag == "table":
                rows = []
                for tr in find_elements(node, "tr"):
                    cells = [self.html_inline(td) for td in tr.children if isinstance(td, Element) and td.tag in {"td", "th"}]
                    if cells:
                        rows.append(cells)
                widths = [.19, .25, .28, .28] if rows and len(rows[0]) == 4 else None
                out.extend([self.table(rows, widths=widths, html=True), Spacer(1, 9)])
            elif not any(isinstance(c, Element) and c.tag in blocks for c in node.children):
                markup, plain = self.html_inline(node)
                if plain.strip():
                    out.append(self.paragraph(markup, markup=True, expected=plain))
            else:
                for child in node.children:
                    walk(child)
        walk(main)
        return out

    def build_story(self):
        load = lambda name: json.loads((self.root / "content" / (name + ".json")).read_text())
        chapters, faq, cases = [load(name) for name in ["chapters", "faq", "cases"]]
        version = json.loads((self.root / "package.json").read_text()).get("version", "0.1.0")
        self.remember("Dot小绿皮书")
        story = [Cover(self.date, (len(chapters), len(faq), len(cases)), version), PageBreak()]
        story.extend([
            self.heading("写在前面"),
            self.paragraph("把一个小任务做好，再交给 Dot 一份持续的责任。", "subtitle"),
            self.paragraph("本 PDF 收录当前版本的全部教程、问答与精选 Dot 案例，并附上关于与来源、共建方式、案例审查、项目说明、网站验收记录和许可证。文字可以搜索和复制，目录、书签和来源链接可以点击。"),
            self.paragraph("产品事实保留原来的 2026-10-01 核对时间；导出 PDF 不会自动重新调用 Dot 或验证产品行为。教学练习、作者自述、画面支持和未验证信息分别保留。"),
            self.heading("公开阅读与持续更新"),
            self.link("dot-guide 公开阅读入口", PUBLIC_READING, "body"),
            self.link("持续更新的 Showcase", PUBLIC_SHOWCASE, "body"),
            self.paragraph("外站展厅包含不同产品的作品。本书精选仍逐条核对 Dot 归属、原帖与证据，不把外站新增展示自动视为本书已经核对的案例。"),
            self.link("Dot小绿皮书在线阅读", PUBLIC_SITE),
            self.heading("阅读方法"),
            self.paragraph(f"第一次使用，从第一章开始。遇到具体问题，查问答手册；读案例时，同时查看结果、证据和限制。所有 {len(chapters) + len(cases)} 条章内及案例练习指令均完整保留，可以复制后按自己的材料调整。"),
            self.paragraph("产品事实和案例原帖会变化；使用前核对当前账户、权限、工具、日期与原始来源。案例分数衡量编辑学习价值，不能替代你对结果的检查。"),
            PageBreak(), self.heading("目录"),
            self.paragraph("点击目录项目或打开 PDF 阅读器的书签面板，即可跳转。页码包含封面。", "small"),
        ])
        toc = TableOfContents()
        toc.levelStyles = [
            ParagraphStyle("toc0", fontName="BookBold", fontSize=10.1, leading=16.5,
                           leftIndent=0, firstLineIndent=0, textColor=GREEN, spaceBefore=8),
            ParagraphStyle("toc1", fontName="BookRegular", fontSize=9.2, leading=14.5,
                           leftIndent=13, firstLineIndent=0, textColor=INK, spaceBefore=2,
                           wordWrap="CJK"),
        ]
        story.extend([toc, PageBreak()])
        story.extend([self.heading("第一部分 循序渐进", bookmark=True),
                      self.paragraph("按八章走完一次完整协作。每章的阅读时间是编辑建议，练习结果需要你实际核对。", "subtitle"), PageBreak()])
        chapter_labels = {c["id"]: f"第 {i} 章 {c['title']}" for i, c in enumerate(chapters, 1)}
        for i, c in enumerate(chapters, 1):
            story.extend([self.heading(f"第 {i} 章 {c['title']}", level=1, bookmark=True),
                          self.paragraph(f"{c['level']} · 建议 {c['minutes']} 分钟", "small"),
                          self.paragraph(c["subtitle"], "subtitle"), self.paragraph(c["intro"])])
            for section in c["sections"]:
                story.append(self.heading(section["title"], style="h2"))
                for body in section["body"].split("\n"):
                    if body.strip():
                        story.append(self.paragraph(body))
            story.append(self.heading("跟着做一次", style="h2"))
            story.extend(self.list_items(c["steps"], numbered=True))
            story.extend(self.exercise(c["prompt"]))
            story.append(KeepTogether([self.heading("做到这里，怎么验收？", style="h2"),
                                       *self.list_items(c["checks"], checkbox=True)]))
            story.append(KeepTogether([self.heading("先避开这两个坑", style="h2"),
                                       *self.list_items(c["pitfalls"])]))
            story.extend(self.source_links(c["sourceUrls"]))
            story.append(self.link("打开本章网页版", PUBLIC_SITE + f"learn/{c['id']}/"))
            story.append(PageBreak())
        story.extend([self.heading("第二部分 问答手册", bookmark=True),
                      self.paragraph(f"{len(faq)} 条常见问题。每条保留完整回答、可以采取的下一步、关联章节与一手产品资料。", "subtitle"), PageBreak()])
        groups = OrderedDict()
        for q in faq:
            groups.setdefault(q["category"], []).append(q)
        for category, questions in groups.items():
            for start in range(0, len(questions), 3):
                if start == 0:
                    story.append(self.heading(category, level=1, style="h2", bookmark=True))
                for q in questions[start:start + 3]:
                    item = [self.heading(f"{q['id'].upper()} {q['question']}", style="h2"),
                            self.paragraph(q["answer"], "faq"),
                            self.paragraph("可以先做：" + q["action"], "faq"),
                            self.paragraph("关联章节：" + chapter_labels[q["chapterId"]], "small")]
                    item.extend(self.source_links(q["sourceUrls"]))
                    item.append(self.link("打开这条问答", PUBLIC_SITE + f"faq/#{q['id']}"))
                    item.append(Spacer(1, 12))
                    story.append(KeepTogether(item))
                story.append(PageBreak())
        story.extend([self.heading("第三部分 Dot 用户案例", bookmark=True),
                      self.paragraph(f"{len(cases)} 个经过原帖核对的精选案例，编辑学习价值评分均为 8 分及以上。学习步骤和指令是教学改编，不是原作者逐字提示词或已经完成的实测。", "subtitle"),
                      self.link("持续更新的 Showcase", PUBLIC_SHOWCASE),
                      self.paragraph("在线展厅是后续阅读和候选线索；本书当前案例仍以逐条核对的来源与审查日期为准。"), PageBreak()])
        for i, c in enumerate(cases, 1):
            story.extend([self.heading(f"案例 {i:02d} {c['title']}", level=1, style="case-title", bookmark=True),
                          self.paragraph(f"{c['category']} · {c['author']} · 编辑学习价值 {c['score']}/10", "small"),
                          self.paragraph(c["summary"], "case"), self.link("查看用户原帖", c["sourceUrl"])])
            for title, key in [("Dot 接住了哪一步？", "dotRole"), ("原作者描述的结果", "outcome"), ("证据支持到哪一步？", "evidence")]:
                story.extend([self.heading(title, style="case-h2"), self.paragraph(c[key], "case")])
            story.append(self.paragraph(c["limits"], "case"))
            story.append(self.paragraph(f"本轮原帖核对批次：{c['checkedAt']} · 原帖日期：{c['date']} · 核对来源不等于独立复现", "small"))
            story.extend([self.heading("你可以怎样学习这个做法？", style="case-h2"), self.paragraph(c["lesson"], "case")])
            story.extend(self.list_items(c["steps"], "case", numbered=True))
            story.extend(self.exercise(c["prompt"], "case"))
            story.append(self.heading("为什么收录？", style="case-h2"))
            story.append(self.table([["目标清晰", "过程可学习", "结果具体", "证据充分", "迁移价值"],
                                     [f"{c['scores'][k]}/2" for k in ["goal", "workflow", "result", "evidence", "transfer"]]]))
            story.append(Spacer(1, 10))
            story.append(self.link("打开本案例网页版", PUBLIC_SITE + f"cases/{c['id']}/"))
            story.append(PageBreak())
        story.append(self.heading("第四部分 关于、来源与共建", bookmark=True))
        story.extend(self.about((self.root / "dist/about/index.html").read_text()))
        story.append(PageBreak())
        appendices = [
            ("附录 A 来源与事实边界", "docs/sources.md"),
            ("附录 B 一起写这本书", "CONTRIBUTING.md"),
            ("附录 C 案例审查记录与评分", "docs/case-review.md"),
            ("附录 D 项目说明与本地阅读", "README.md"),
            ("附录 E 网站首版验收记录", "docs/verification.md"),
            ("附录 F MIT 许可证", "LICENSE"),
        ]
        for i, (title, path) in enumerate(appendices):
            story.append(self.heading(title, bookmark=True))
            source = (self.root / path).read_text()
            story.extend(self.markdown(source))
            if i + 1 < len(appendices):
                story.append(PageBreak())
        return story, (len(chapters), len(faq), len(cases))

    def validate(self, pdf: Path, counts):
        reader = PdfReader(pdf)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        norm = normalized(text)
        private_project = "/".join(["Tiee7", "dot" + "-guide"])
        prohibited = [
            r"(?:https?://(?:www\.)?github\.com/|git@github\.com:)" + re.escape(private_project),
            r"dot-guide[^。\n]{0,80}(?:commit|提交|版本|SHA|main)[^。\n]{0,40}\b[0-9a-f]{40}\b",
            r"(?:非|不是)\s*OpenAI\s*官方(?:项目|文档)",
            r"(?:本书|本项目)不是\s*OpenAI\s*官方[^。\n]*(?:产品承诺)",
        ]
        if any(re.search(pattern, text, re.I) for pattern in prohibited):
            raise ValueError("PDF contains withdrawn project identity text or a private source reference.")
        missing = [value for value in self.expected if normalized(value) not in norm]
        if missing:
            examples = "\n".join(repr(x[:180]) for x in missing[:8])
            raise ValueError(f"PDF is missing {len(missing)} source blocks:\n{examples}")
        for url in [PUBLIC_READING, PUBLIC_SHOWCASE]:
            if normalized(url) not in norm:
                raise ValueError("Required public reading URL missing: " + url)
        annotations = [a.get_object() for page in reader.pages for a in page.get("/Annots", [])]
        links = [a for a in annotations if a.get("/Subtype") == "/Link"]
        if not reader.outline or not links:
            raise ValueError("PDF bookmarks or links were not generated.")
        actual_urls = {str(a.get("/A", {}).get("/URI")) for a in links if a.get("/A", {}).get("/S") == "/URI"}
        missing_urls = self.link_urls - actual_urls
        unexpected_urls = actual_urls - self.link_urls
        if missing_urls or unexpected_urls:
            raise ValueError(f"PDF URI mismatch: missing={sorted(missing_urls)}, unexpected={sorted(unexpected_urls)}")
        if any(re.search(pattern, url, re.I) for url in actual_urls for pattern in prohibited):
            raise ValueError("PDF contains a withdrawn private link.")
        return {"pages": len(reader.pages), "chapters": counts[0], "faq": counts[1],
                "cases": counts[2], "full_source_blocks_checked": len(self.expected),
                "complete_exercise_prompts": counts[0] + counts[2], "link_annotations": len(links),
                "bookmarks": self.serial, "unique_urls_checked": len(actual_urls),
                "text_validation": "passed", "url_validation": "passed",
                "withdrawn_content_check": "passed"}


def arguments():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=ROOT, help="Book repository root")
    parser.add_argument("--output", type=Path, default=None, help="Default: output/pdf/Dot小绿皮书-完整版.pdf")
    parser.add_argument("--date", default=datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat(), help="Export date (YYYY-MM-DD, defaults to Asia/Shanghai)")
    parser.add_argument("--node", default=os.getenv("DOT_BOOK_NODE"), help="Node.js executable for rebuilding the site")
    parser.add_argument("--font-regular", default=os.getenv("DOT_BOOK_FONT_REGULAR", "/System/Library/Fonts/STHeiti Light.ttc"))
    parser.add_argument("--font-bold", default=os.getenv("DOT_BOOK_FONT_BOLD", "/System/Library/Fonts/STHeiti Medium.ttc"))
    parser.add_argument("--font-regular-index", type=int, default=int(os.getenv("DOT_BOOK_FONT_REGULAR_INDEX", "0")))
    parser.add_argument("--font-bold-index", type=int, default=int(os.getenv("DOT_BOOK_FONT_BOLD_INDEX", "0")))
    return parser.parse_args()


def rebuild_site(root: Path, node_override: str | None):
    build_info = root / "dist/build-info.json"
    existing_base = json.loads(build_info.read_text()).get("base", "/") if build_info.exists() else "/"
    base = os.getenv("SITE_BASE", existing_base)
    bundled_node = Path(sys.executable).parents[2] / "node/bin/node"
    node = node_override or (str(bundled_node) if bundled_node.is_file() else shutil.which("node"))
    if not node:
        raise SystemExit("Node.js 20.11+ is needed to rebuild the site; use --node to specify it.")
    try:
        subprocess.run([node, str(root / "scripts/build.mjs")], cwd=root,
                       env={**os.environ, "SITE_BASE": base}, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit("Site rebuild failed; the previous PDF was preserved. " + str(exc))


def main():
    args = arguments()
    root = args.root.resolve()
    output = args.output or root / "output/pdf/Dot小绿皮书-完整版.pdf"
    output = output.resolve()
    rebuild_site(root, args.node)
    for name, path, index in [("BookRegular", args.font_regular, args.font_regular_index),
                              ("BookBold", args.font_bold, args.font_bold_index)]:
        if not Path(path).is_file():
            raise SystemExit(f"Font not found: {path}. Set --font-regular / --font-bold to CJK TrueType fonts.")
        pdfmetrics.registerFont(TTFont(name, path, subfontIndex=index))
    pdfmetrics.registerFontFamily("BookRegular", normal="BookRegular", bold="BookBold",
                                  italic="BookRegular", boldItalic="BookBold")
    exporter = Exporter(root, args.date)
    story, counts = exporter.build_story()
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".dot-book-", suffix=".pdf", dir=output.parent)
    os.close(handle)
    temp_pdf = Path(temporary)
    try:
        BookTemplate(temp_pdf, args.date).multiBuild(story)
        report = exporter.validate(temp_pdf, counts)
        os.replace(temp_pdf, output)
        report["output"] = str(output)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        temp_pdf.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
