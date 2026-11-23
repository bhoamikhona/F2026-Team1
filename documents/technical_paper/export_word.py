"""Export the IEEE manuscript and its revision table as an editable Word file."""
import os
import tempfile
import re
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, Mm, RGBColor
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement, parse_xml
from latex2mathml.converter import convert as latex_to_mathml
from mathml2omml import convert as mathml_to_omml
from docx.oxml.ns import qn

os.chdir(Path(__file__).resolve().parent)
d = Document()
s = d.sections[0]
s.page_width = Mm(210)
s.page_height = Mm(297)
s.left_margin = s.right_margin = Inches(0.56)
s.top_margin = Inches(0.75)
s.bottom_margin = Mm(43)
for st in ["Normal", "Title", "Heading 1", "Heading 2"]:
    f = d.styles[st].font
    f.name = "Times New Roman"
    f.size = Pt({"Normal": 10, "Title": 22, "Heading 1": 11, "Heading 2": 10}[st])
    f.color.rgb = RGBColor(0, 0, 0)
    fmt = d.styles[st].paragraph_format
    fmt.space_after = Pt(0)
    fmt.line_spacing = 1


title_style = d.styles["Title"]
border = title_style.element.find(".//" + qn("w:pBdr"))
if border is not None:
    border.getparent().remove(border)
for name in ("Title", "Heading 1", "Heading 2"):
    style = d.styles[name]
    style.font.bold = False
    fonts = style.element.get_or_add_rPr().rFonts
    for attr in ("asciiTheme", "hAnsiTheme"):
        fonts.attrib.pop(qn("w:" + attr), None)
d.styles["Heading 1"].font.small_caps = True
d.styles["Heading 2"].font.italic = True


def cols(n, kind=WD_SECTION.CONTINUOUS):
    sec = d.add_section(kind)
    paragraph = d.paragraphs[-1]
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = Pt(1)
    paragraph.add_run().font.size = Pt(1)
    c = sec._sectPr.find(qn("w:cols"))
    c.set(qn("w:num"), str(n))
    c.set(qn("w:space"), str(Mm(4.22).twips))


def clean(x):
    x = re.sub(
        r"\\cite\{([^}]+)\}",
        lambda m: ", ".join(
            "[" + k.strip().replace("ref", "") + "]" for k in m[1].split(",")
        ),
        x,
    )
    x = re.sub(r"\\ref\{(?:tab|fig):([^}]+)\}", r"\1", x)
    x = re.sub(r"\\(?:path|url|texttt)\{([^}]*)\}", r"\1", x)
    return " ".join(
        x.replace(r"\(\times\)", "×")
        .replace(r"\%", "%")
        .replace(r"\_", "_")
        .replace(r"\&", "&")
        .replace("--", "–").replace("~", " ").replace("``", "“").replace("''", "”")
        .split()
    )



REVIEW_COLORS = {
    "pendingedit": "FFFF00", "peachaddition": "FFDAB9",
    "proposedreplacement": "FFDCDC", "suggestedwording": "DCF5DC",
}
format_stack = []


def braced(text, start):
    """Read a balanced TeX argument, preserving nested formula braces."""
    if text[start] != "{":
        raise ValueError("Expected a braced LaTeX argument")
    depth = 1
    i = start + 1
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text) and text[i + 1] in "{}":
            i += 2
            continue
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
        i += 1
    raise ValueError("Unclosed LaTeX argument")


def review_markup(text):
    """Translate review wrappers to markers without dropping their contents."""
    pattern = re.compile(r"\\(" + "|".join(REVIEW_COLORS) + r"|textbf)\{")
    result = []
    pos = 0
    while match := pattern.search(text, pos):
        result.append(text[pos:match.start()])
        content, end = braced(text, match.end() - 1)
        name = match[1]
        result.append("\x01" + name + "\x02")
        if name == "suggestedwording":
            content = "[Suggested replacement: " + content + "]"
        result.append(review_markup(content))
        result.append("\x01end\x02")
        pos = end
    result.append(text[pos:])
    return "".join(result)


def shade(properties, fill):
    element = OxmlElement("w:shd")
    element.set(qn("w:fill"), fill)
    element.set(qn("w:val"), "clear")
    properties.append(element)


def active_color():
    return next((REVIEW_COLORS[f] for f in reversed(format_stack)
                 if f in REVIEW_COLORS), None)


def equation(p, tex):
    """Convert LaTeX math to native, editable Office Math."""
    tex = tex.replace(r"\operatorname{arg\,max}", r"\text{arg max}")
    tex = re.sub(r"\\mathrm\{([^}]+)\}", r"\\text{\1}", tex)
    xml = mathml_to_omml(latex_to_mathml(tex.strip()))
    xml = xml.replace("<m:oMath>", '<m:oMath xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">', 1)
    node = parse_xml(xml)
    if active_color():
        for run in node.iter(qn("m:r")):
            properties = OxmlElement("w:rPr")
            shade(properties, active_color())
            run.insert(0, properties)
    p._p.append(node)


def write(x, style=None, center=False):
    p = d.add_paragraph(style=style)
    if style is None and not center:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.first_line_indent = Inches(0.14)
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if x.strip().startswith(r"\["):
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Pt(0)
    tokens = re.split(r"(\x01[^\x02]+\x02|\\\[.*?\\\]|\\\(.*?\\\)|\$[^$]+\$)", x, flags=re.S)
    for token in tokens:
        if token.startswith("\x01"):
            name = token[1:-1]
            if name == "end":
                format_stack.pop()
            else:
                format_stack.append(name)
        elif token.startswith((r"\[", r"\(", "$")):
            equation(p, token[1:-1] if token.startswith("$") else token[2:-2])
        elif token:
            # Keep spaces on both sides of inline math and review spans.
            value = clean(token)
            if token[0].isspace():
                value = " " + value
            if token[-1].isspace():
                value += " "
            run = p.add_run(value)
            if active_color():
                shade(run._r.get_or_add_rPr(), active_color())
            if "textbf" in format_stack:
                run.bold = True
    if x.startswith(("Abstract  ", "Index Terms  ")):
        first = p.runs[0]
        label, _, rest = first.text.partition(" ")
        if x.startswith("Index Terms"):
            label, rest = "Index Terms", first.text[len("Index Terms "):]
        first.text = rest
        prefix = p.add_run(label + "—")
        first._r.addprevious(prefix._r)
        prefix.italic = True
        for run in p.runs:
            run.bold = True
            run.font.size = Pt(9)
    return p


def caption(text, center=False):
    p = write(text, center=center)
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.keep_with_next = text.startswith("TABLE")
    for run in p.runs:
        run.font.size = Pt(8)


def table(rows, widths, grid=False, review_columns=(), header_rows=1):
    t = d.add_table(rows=0, cols=len(widths))
    if grid:
        t.style = "Table Grid"
    else:
        borders = OxmlElement("w:tblBorders")
        for edge in ("top", "bottom"):
            rule = OxmlElement("w:" + edge)
            rule.set(qn("w:val"), "single")
            rule.set(qn("w:sz"), "6")
            borders.append(rule)
        t._tbl.tblPr.append(borders)
    t.autofit = False
    for col, w in zip(t.columns, widths):
        col.width = Inches(w)
    for i, row in enumerate(rows):
        assert len(row) == len(widths), row
        row_element = t.add_row()
        row_element._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for column, (cell, txt, w) in enumerate(zip(row_element.cells, row, widths)):
            if column in review_columns:
                shade(cell._tc.get_or_add_tcPr(), "FFDAB9")
            if i == header_rows - 1 and not grid:
                borders = OxmlElement("w:tcBorders")
                rule = OxmlElement("w:bottom")
                rule.set(qn("w:val"), "single")
                rule.set(qn("w:sz"), "4")
                borders.append(rule)
                cell._tc.get_or_add_tcPr().append(borders)
            cell.width = Inches(w)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = i < header_rows
            r = p.add_run(clean(txt))
            r.font.size = Pt(8 if len(widths) > 5 else 9)
            r.bold = i < header_rows


src = Path("paper.tex").read_text(encoding="utf-8")
write(re.search(r"\\title\{([^}]*)", src)[1], "Title", True)
for x in [
    re.search(r"\\IEEEauthorblockN\{([^}]*)", src)[1].replace(r"\\", " "),
    *re.search(r"\\IEEEauthorblockA\{(.*?)\}\}\s*\\begin\{document", src, re.S)[
        1
    ].split(r"\\"),
]:
    p = write(x, None, True)
    for run in p.runs:
        if "@" in x:
            run.font.name = "Courier New"
            run.font.size = Pt(9)
        elif x.strip().startswith(("Seidenberg", "Pace University")):
            run.italic = True
cols(2)
body = src.split(r"\maketitle")[1].split(r"\input")[0]
body = re.sub(r"(?m)^%.*", "", body)
for env, label in [("abstract", "Abstract"), ("IEEEkeywords", "Index Terms")]:
    body = body.replace(r"\begin{" + env + "}", label + "  ").replace(
        r"\end{" + env + "}", ""
    )
body = re.sub(r"(Abstract|Index Terms)  \s*", r"\1  ", body)
body = body.replace(r"\begin{thebibliography}{99}", r"\section*{References}").replace(
    r"\end{thebibliography}", ""
)
body = re.sub(r"\\bibitem\{ref(\d+)\}\s*", r"[\1] ", body)
pat = r"(\\begin\{(?:figure|table)\*?\}.*?\\end\{(?:figure|table)\*?\}|\\(?:subsection|section)\*?\{[^}]+\})"
num = 0
sub = 0
for x in re.split(pat, body, flags=re.S):
    x = x.strip()
    if not x:
        continue
    if x.startswith(r"\begin"):
        wide = "*}" in x.splitlines()[0]
        if wide:
            cols(1)
        cap = re.search(r"\\caption\{(.*?)\}\\?(?:label|\s)", x, re.S)[1]
        label = re.search(r"\\label\{(fig|tab):([^}]+)", x)
        if label[1] == "fig":
            p = d.add_paragraph()
            p.alignment = 1
            p.add_run().add_picture(
                re.search(r"\\includegraphics\[[^]]*\]\{([^}]+)", x)[1],
                width=Inches(6.4 if wide else 3.25),
            )
            caption("Fig. " + label[2] + ". " + cap)
        else:
            caption("TABLE " + label[2] + "\n" + cap, True)
            blocks = list(re.finditer(r"\\toprule(.*?)\\bottomrule", x, re.S))
            for index, block in enumerate(blocks):
                if index:
                    write("Proposed expanded table for review (new columns in peach)", center=True)
                data = block[1].replace(r"\midrule", "")
                # Flatten nested shortstack cells before splitting row delimiters.
                while match := re.search(r"\\shortstack(?:\[[^]]*\])?\{", data):
                    content, end = braced(data, match.end() - 1)
                    data = data[:match.start()] + content.replace(r"\\", " ") + data[end:]
                data = re.sub(r"\\\\\[[^]]*\]", lambda m: r"\\", data)
                rows = [re.split(r"\s*&\s*", row.strip()) for row in data.split(r"\\") if row.strip()]
                count = len(rows[0])
                widths = {3: [1.12, 1, 1.15], 5: [1.72, 0.90, 1.77, 1.24, 1.24],
                          9: [1.3, .65, 1.12, .78, .78, .55, .55, .65, .55]}[count]
                table(rows, widths, review_columns=range(5, 9) if count == 9 else (),
                      header_rows=2 if count == 9 else 1)
            # Preserve the explanatory peach note after the tables.
            tail = x[blocks[-1].end():]
            note = re.search(r"\\peachaddition\{", tail)
            if note:
                content, end = braced(tail, note.end() - 1)
                content = re.sub(r"\\footnotesize\s*", "", content)
                write(review_markup(r"\peachaddition{" + content + "}"))
        if wide:
            cols(2)
    elif x.startswith((r"\section", r"\subsection")):
        title = x.split("{")[1][:-1]
        if x.startswith(r"\sub"):
            sub += 1
            write(chr(64 + sub) + ". " + title, "Heading 2")
        else:
            if "*" not in x:
                num += 1
                title = (
                    "I II III IV V VI VII VIII IX X XI".split()[num - 1] + ". " + title
                )
            sub = 0
            write(title, "Heading 1", True)
    else:
        x = review_markup(x)
        x = re.sub(r"(\\\[.*?\\\])", r"\n\n\1\n\n", x, flags=re.S)
        for a in re.split(r"\n\s*\n", x):
            if a.strip():
                p = write(a)
                if re.match(r"^\[\d+\] ", a):
                    p.paragraph_format.left_indent = Inches(0.24)
                    p.paragraph_format.first_line_indent = Inches(-0.24)
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    for run in p.runs:
                        run.font.size = Pt(8)
cols(1, WD_SECTION.NEW_PAGE)
write("Version History", "Heading 1", True)
rows = [["Version", "Date", "Changes"]] + [
    line.split(r"\\")[0].strip().split(" & ")
    for line in Path("version-history.tex").read_text(encoding="utf-8").splitlines()
    if re.match(r"^\s*\d+(?:\.\d+)*\s+&", line)
]
table(rows, [0.57, 1, 5.38], grid=True)
def save_document(document, filename):
    with tempfile.NamedTemporaryFile(dir=".", suffix=".docx", delete=False) as temporary:
        output = Path(temporary.name)
    try:
        document.save(output)
        output.replace(filename)
    finally:
        output.unlink(missing_ok=True)


save_document(d, "paper.docx")
