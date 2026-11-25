#!/usr/bin/env python3
"""Build the uniform reading PDFs with XeLaTeX and verify every output page.

The reviewed UTF-8 text snapshots in ``reading_texts/*.json`` are the source of
truth.  This script regenerates the LaTeX sources under ``latex/``, compiles ten
single-article PDFs and the anthology, then audits page size, blank pages,
embedded fonts, text bounds, text order, hyphenation ligatures and common
encoding artifacts with Poppler's command-line tools.

Run from the repository root:

    python3 scripts/build_pdfs.py --verify --overwrite-inputs

Requires XeLaTeX, Liberation Serif, and Poppler (pdfinfo, pdffonts, pdftotext).
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf"
LATEX = ROOT / "latex"
ARTICLES = LATEX / "articles"
SINGLES = LATEX / "singles"
BUILD = ROOT / "build" / "latex"

PAGE_W = 595.276
PAGE_H = 841.89
MARGIN = 62
TOP_CROP = 50
BODY_H = 742  # from y=50 to the bottom margin, page numbers excluded

INK = "#202020"
HEAD_GREY = "#555555"
RULE = "#C8C8C8"
HEAD_BG = "#EEEEEC"




# ---------------------------------------------------------------------------
# Small text helpers


LIGATURES = {
    "\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl",
    "\ufb03": "ffi", "\ufb04": "ffl", "\ufb05": "ft", "\ufb06": "st",
}


def smart_quotes(text: str, prev: str = "\n", nxt: str = "\n") -> str:
    """Turn straight quotes into typographic quotes without touching tags."""
    out: list[str] = []
    for index, char in enumerate(text):
        before = text[index - 1] if index else prev
        after = text[index + 1] if index + 1 < len(text) else nxt
        if char == '"':
            if before.isspace() or before in "([{—–-/":
                out.append("“")
            else:
                out.append("”")
        elif char == "'":
            if before.isalnum() and after.isalnum():
                out.append("’")
            elif before.isalnum() or before in ".,;:!?)]}":
                out.append("’")
            elif after.isalnum():
                out.append("‘")
            else:
                out.append("’")
        else:
            out.append(char)
    return "".join(out)


LATEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "#": r"\#",
    "%": r"\%",
    "_": r"\_",
    "^": r"\textasciicircum{}",
    "~": r"\textasciitilde{}",
}


def latex_escape(text: str) -> str:
    return "".join(LATEX_ESCAPES.get(char, char) for char in text)


TOKEN_RE = re.compile(r"<(/?)(i|b|em|strong)>|<br\s*/?>", re.IGNORECASE)


def _markup_parts(markup: str):
    parts: list[tuple[str, str]] = []
    pos = 0
    for match in TOKEN_RE.finditer(markup):
        if match.start() > pos:
            parts.append(("text", markup[pos:match.start()]))
        parts.append(("tag", match.group(0)))
        pos = match.end()
    if pos < len(markup):
        parts.append(("text", markup[pos:]))
    return parts


def latex_markup(markup: str, *, verse: bool = False) -> str:
    """Convert the repository's tiny inline markup to LaTeX."""
    markup = html.unescape(markup)
    parts = _markup_parts(markup)
    text_indexes = [i for i, (kind, _) in enumerate(parts) if kind == "text"]
    text_values = {i: parts[i][1] for i in text_indexes}
    out: list[str] = []
    line_break = r"\\" if verse else " "

    for index, (kind, value) in enumerate(parts):
        if kind == "text":
            prev = "\n"
            nxt = "\n"
            position = text_indexes.index(index)
            if position:
                prev = text_values[text_indexes[position - 1]][-1:]
            if position + 1 < len(text_indexes):
                nxt = text_values[text_indexes[position + 1]][:1]
            value = smart_quotes(value, prev, nxt)
            value = latex_escape(value)
            if verse:
                value = re.sub(r"\s*\n\s*", "\x00", value)
            else:
                value = re.sub(r"\s+", " ", value)
            out.append(value)
        elif value.startswith("<br"):
            out.append("\x00")
        elif value.startswith("</"):
            out.append("}")
        elif value.lower().startswith("<i") or value.lower().startswith("<em"):
            out.append(r"\textit{")
        else:
            out.append(r"\textbf{")

    joined = "".join(out)
    if verse:
        lines = [line.strip() for line in joined.split("\x00")]
        lines = [line for line in lines if line]
        return " \\\\\n".join(lines)
    return re.sub(r"[ \t]+", " ", joined.replace("\x00", " ")).strip()


def latex_plain(text: str, *, verse: bool = False) -> str:
    return latex_markup(text, verse=verse)


def latex_url(url: str) -> str:
    return latex_escape(url)


def slug(title: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_")


# ---------------------------------------------------------------------------
# LaTeX generation


PREAMBLE = r"""% Generated by scripts/build_pdfs.py -- edit the generator, not this file.
\usepackage[english]{babel}
\usepackage{fontspec}
\setmainfont{Liberation Serif}

\usepackage{geometry}
\geometry{
  a4paper,
  left=62pt, right=62pt,
  top=60pt, bottom=55pt,
  headheight=14pt, headsep=9pt, footskip=24pt
}

\usepackage[table]{xcolor}
\definecolor{ink}{HTML}{202020}
\definecolor{headgrey}{HTML}{555555}
\definecolor{rule}{HTML}{C8C8C8}
\definecolor{headbg}{HTML}{EEEEEC}

\usepackage{fancyhdr}
\usepackage{graphicx}
\usepackage{tabularx}
\usepackage{changepage}
\usepackage{needspace}
\usepackage{hyperref}

\graphicspath{{../reading_texts/assets/}}

\hypersetup{
  colorlinks=true,
  linkcolor=ink,
  urlcolor=ink,
  citecolor=ink,
  filecolor=ink,
  bookmarksopen=true,
  bookmarksnumbered=false,
  pdfstartview=FitH
}

\setlength{\parindent}{0pt}
\setlength{\parskip}{7pt plus 1pt minus 0.5pt}
\widowpenalty=10000
\clubpenalty=10000
\displaywidowpenalty=10000
\raggedbottom
\emergencystretch=3em
\tolerance=2000
\hbadness=10000
\vbadness=10000
\hfuzz=0.5pt
\vfuzz=2pt

\AtBeginDocument{\fontsize{12}{16.5}\selectfont}

\newcommand{\collectionname}{ENGLISH WRITING COLLECTION}
\newcommand{\articlelabel}{}
\newcommand{\setarticlelabel}[1]{\gdef\articlelabel{#1}}
\newcommand{\articlebreak}{\par\ifdim\pagetotal>0pt\newpage\fi}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\fontsize{8.5}{10}\selectfont\color{headgrey}\articlelabel}
\fancyhead[R]{\fontsize{8.5}{10}\selectfont\color{headgrey}\collectionname}
\fancyfoot[C]{\fontsize{10}{12}\selectfont\thepage}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\headrule}{%
  \hbox to\headwidth{\color{rule}\leaders\hrule height \headrulewidth\hfill}}

\newenvironment{rquote}
  {\par\vspace{2pt}%
   \begin{adjustwidth}{18pt}{18pt}%
   \setlength{\parindent}{0pt}%
   \setlength{\parskip}{6pt}%
   \ignorespaces}
  {\par\end{adjustwidth}\par\vspace{4pt}}

\newenvironment{rverse}
  {\par\vspace{3pt}%
   \begin{adjustwidth}{22pt}{0pt}%
   \itshape
   \setlength{\parindent}{0pt}%
   \setlength{\parskip}{0pt}%
   \interlinepenalty=10000
   \raggedright
   \def\\{\unskip\newline\ignorespaces}%
   \ignorespaces}
  {\par\end{adjustwidth}\par\vspace{8pt}}

\newenvironment{readnote}
  {\par\vspace{1pt}\begingroup
   \fontsize{10.5}{13.6}\selectfont
   \setlength{\parindent}{0pt}%
   \setlength{\parskip}{3pt}%
   \ignorespaces}
  {\par\endgroup\vspace{1pt}}

\newcommand{\readingheading}[3]{%
  \par\needspace{4\baselineskip}%
  \pdfbookmark[1]{#2}{#3}%
  {\fontsize{13.5}{18}\selectfont\bfseries #1\par}%
  \vspace{8pt}%
}
"""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def title_block(item: dict) -> str:
    number = item["number"]
    title = latex_plain(item["title"])
    author = latex_plain(item["author"])
    year = latex_plain(item["year"])
    lines = [
        r"\setarticlelabel{%02d\quad/\quad %s}" % (number, author),
        r"\thispagestyle{fancy}",
        r"\pdfbookmark[0]{%02d. %s}{bm-article-%02d}" % (number, item["title"], number),
        r"\phantomsection\label{article-%02d}" % number,
        r"\begingroup\raggedright",
        r"{\fontsize{9}{12}\selectfont\color{headgrey}READING %02d\par}" % number,
        r"\vspace{4pt}",
        r"{\fontsize{23}{27}\selectfont\bfseries %s\par}" % title,
        r"\vspace{7pt}",
        r"{\fontsize{12}{17}\selectfont %s\quad|\quad %s\par}" % (author, year),
    ]
    if item.get("subtitle"):
        lines += [
            r"\vspace{4pt}",
            r"{\fontsize{11}{14.5}\selectfont\itshape %s\par}"
            % latex_plain(item["subtitle"]),
        ]
    source = latex_plain(item["source_label"])
    if item.get("source_url"):
        source = r"\href{%s}{%s}" % (latex_url(item["source_url"]), source)
    lines += [
        r"\vspace{4pt}",
        r"{\fontsize{9}{12}\selectfont\color{headgrey}Source: %s\par}" % source,
    ]
    if item.get("copyright_notice"):
        lines += [
            r"\vspace{2pt}",
            r"{\fontsize{8.5}{11}\selectfont\color{headgrey}%s\par}"
            % latex_plain(item["copyright_notice"]),
        ]
    lines += [r"\endgroup", r"\vspace{6pt}"]
    return "\n".join(lines)


def table_block(element: dict) -> str:
    rows = element["rows"]
    columns = len(rows[0])
    if columns == 3:
        spec = r"@{}p{130pt}p{165pt}X@{}"
    else:
        spec = r"@{}Xr@{}"
    lines = [
        r"\begingroup",
        r"\renewcommand{\arraystretch}{1.35}",
        r"\setlength{\tabcolsep}{6pt}",
        r"\noindent\begin{tabularx}{\textwidth}{%s}" % spec,
        r"\arrayrulecolor{rule}",
        r"\rowcolor{headbg}",
    ]
    for row_index, row in enumerate(rows):
        cells = [latex_plain(cell) for cell in row]
        if row_index == 0:
            cells = [r"\textbf{%s}" % cell for cell in cells]
        lines.append(" & ".join(cells) + r" \\")
        if row_index == 0:
            lines.append(r"\hline")
    lines += [
        r"\hline",
        r"\end{tabularx}",
        r"\endgroup",
        r"\vspace{8pt}",
    ]
    return "\n".join(lines)


def element_block(item: dict, index: int, element: dict) -> str:
    kind = element["kind"]
    if kind == "image":
        return (
            r"\par\vspace{3pt}" "\n"
            r"\begin{center}" "\n"
            r"\includegraphics[width=360pt,keepaspectratio]{%s}" "\n"
            r"\end{center}" "\n"
            r"\vspace{3pt}" % Path(element["file"]).name
        )
    if kind == "table":
        return table_block(element)
    if kind == "heading":
        text = latex_plain(element["text"])
        return r"\readingheading{%s}{%s}{section-%02d-%02d}" % (
            text, element["text"], item["number"], index
        )
    if kind == "verse":
        return r"\begin{rverse}" + "\n" + latex_plain(
            element.get("markup") or element["text"], verse=True
        ) + "\n" + r"\end{rverse}"
    if kind == "quote":
        return r"\begin{rquote}" + "\n" + latex_plain(
            element.get("markup") or element["text"]
        ) + "\n" + r"\end{rquote}"
    if kind == "note":
        return r"\begin{readnote}" + "\n" + latex_plain(
            element.get("markup") or element["text"]
        ) + "\n" + r"\end{readnote}"
    return latex_plain(element.get("markup") or element["text"]) + r"\par"


def article_body(item: dict) -> str:
    blocks = [title_block(item)]
    for index, element in enumerate(item["elements"]):
        blocks.append(element_block(item, index, element))
    return "\n\n".join(blocks)


def frontmatter(items: list[dict]) -> str:
    rows = []
    for item in items:
        number = item["number"]
        title = latex_plain(item["title"])
        author = latex_plain(item["author"])
        rows.append(
            r"\hyperref[article-%02d]{\textbf{%02d. %s}}\newline" % (number, number, title)
            + "\n"
            + r"{\small\color{headgrey}\hyperref[article-%02d]{%s}}"
            % (number, author)
            + "\n"
            + r"& \hyperref[article-%02d]{\pageref{article-%02d}}\\[6pt]"
            % (number, number)
        )
    row_text = "\n".join(rows)
    return "\n".join(
        [
            r"\setarticlelabel{}",
            r"\thispagestyle{fancy}",
            r"\pdfbookmark[0]{Ten Readings for English Writing}{bm-contents}",
            r"\begingroup\raggedright",
            r"{\fontsize{23}{27}\selectfont\bfseries Ten Readings\\ for English Writing\par}",
            r"\vspace{9pt}",
            r"{\fontsize{12}{17}\selectfont A unified reading edition\par}",
            r"\vspace{14pt}",
            r"{\fontsize{13.5}{18}\selectfont\bfseries Contents\par}",
            r"\vspace{8pt}",
            r"\endgroup",
            r"\begingroup",
            r"\renewcommand{\arraystretch}{1.55}",
            r"\setlength{\tabcolsep}{0pt}",
            r"\noindent\begin{tabularx}{\textwidth}{@{}X r@{}}",
            row_text,
            r"\end{tabularx}",
            r"\endgroup",
            r"\vfill",
            r"{\fontsize{9}{12}\selectfont\color{headgrey}Scope follows the repository reading list. "
            r"Smith: Book I, Chapters 1--3. Mill: Chapter II. Burke: the complete speech. "
            r"Texts have been checked against online editions; sources and corrections are "
            r"documented in the repository.\par}",
        ]
    )


def write_latex_sources(items: list[dict]) -> None:
    if len(items) != 10:
        raise ValueError("Expected exactly ten articles")
    LATEX.mkdir(parents=True, exist_ok=True)
    write_text(LATEX / "preamble.tex", PREAMBLE)
    for item in items:
        name = f"{item['number']:02d}_{slug(item['title'])}"
        write_text(ARTICLES / f"{name}.tex", article_body(item))
        write_text(
            SINGLES / f"{name}.tex",
            "\n".join(
                [
                    r"\documentclass[12pt,a4paper]{article}",
                    r"\input{preamble}",
                    r"\hypersetup{pdftitle={%s},pdfauthor={%s}}"
                    % (item["title"], item["author"]),
                    r"\begin{document}",
                    r"\input{articles/%s}" % name,
                    r"\end{document}",
                ]
            ),
        )
    write_text(LATEX / "frontmatter.tex", frontmatter(items))
    collection = [
        r"\documentclass[12pt,a4paper]{article}",
        r"\input{preamble}",
        r"\hypersetup{pdftitle={Ten Readings for English Writing},"
        r"pdfauthor={Various authors}}",
        r"\begin{document}",
        r"\input{frontmatter}",
    ]
    for item in items:
        name = f"{item['number']:02d}_{slug(item['title'])}"
        collection += [r"\articlebreak", r"\input{articles/%s}" % name]
    collection.append(r"\end{document}")
    write_text(LATEX / "collection.tex", "\n".join(collection))


# ---------------------------------------------------------------------------
# Compilation and verification


def run(command: list[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    process = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if process.returncode != 0:
        raise RuntimeError(
            f"Command failed ({process.returncode}): {' '.join(command)}\n"
            + process.stdout[-8000:]
        )
    return process


def compile_tex(tex_file: str, *, passes: int) -> Path:
    pdf = BUILD / (Path(tex_file).stem + ".pdf")
    for pass_number in range(passes):
        run(
            [
                "xelatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-file-line-error",
                f"-output-directory={BUILD}",
                tex_file,
            ],
            cwd=LATEX,
        )
    log = BUILD / (Path(tex_file).stem + ".log")
    log_text = log.read_text(encoding="utf-8", errors="replace")
    if "Rerun to get" in log_text and passes < 3:
        run(
            [
                "xelatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-file-line-error",
                f"-output-directory={BUILD}",
                tex_file,
            ],
            cwd=LATEX,
        )
        log_text = log.read_text(encoding="utf-8", errors="replace")
    check_log(log_text, tex_file)
    return pdf


def check_log(log_text: str, name: str) -> None:
    problems: list[str] = []
    for line in log_text.splitlines():
        if "Overfull \\hbox" in line:
            match = re.search(r"\(([0-9.]+)pt too wide\)", line)
            if match and float(match.group(1)) > 0.5:
                problems.append(line.strip())
        if "Missing character" in line:
            problems.append(line.strip())
        if "Token not allowed in a PDF string" in line:
            problems.append(line.strip())
        if "There were undefined references" in line:
            problems.append(line.strip())
        if "Reference `" in line and "undefined" in line:
            problems.append(line.strip())
        if "Rerun to get" in line:
            problems.append(line.strip())
    if problems:
        raise RuntimeError(f"{name}: LaTeX problems:\n" + "\n".join(problems))


def pdfinfo(path: Path) -> dict[str, str]:
    text = run(["pdfinfo", str(path)]).stdout
    info: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()
    return info


def pdffonts(path: Path) -> list[dict[str, str]]:
    text = run(["pdffonts", str(path)]).stdout
    pattern = re.compile(
        r"^(?P<name>\S+)\s+(?P<type>.+?)\s+(?P<encoding>\S+)\s+"
        r"(?P<emb>yes|no)\s+(?P<sub>yes|no)\s+(?P<uni>yes|no)\s+\d+\s+\d+$"
    )
    fonts: list[dict[str, str]] = []
    for line in text.splitlines():
        match = pattern.match(line.strip())
        if match:
            fonts.append(match.groupdict())
    if not fonts:
        raise ValueError(f"{path.name}: no embedded font rows")
    return fonts


def page_text(path: Path, first: int, last: int) -> str:
    return run(
        [
            "pdftotext",
            "-f", str(first),
            "-l", str(last),
            "-x", str(MARGIN - 1),
            "-y", str(TOP_CROP),
            "-W", str(int(PAGE_W - 2 * MARGIN + 2)),
            "-H", str(BODY_H),
            str(path),
            "-",
        ]
    ).stdout


def page_box_words(path: Path):
    xml_text = run(["pdftotext", "-bbox-layout", str(path), "-"]).stdout
    root = ET.fromstring(xml_text)
    pages = []
    for page in root.iter():
        if not page.tag.endswith("page"):
            continue
        width = float(page.attrib.get("width", PAGE_W))
        height = float(page.attrib.get("height", PAGE_H))
        words = []
        for word in page.iter():
            if not word.tag.endswith("word"):
                continue
            words.append(
                {
                    "text": "".join(word.itertext()),
                    "x0": float(word.attrib["xMin"]),
                    "x1": float(word.attrib["xMax"]),
                    "top": float(word.attrib["yMin"]),
                    "bottom": float(word.attrib["yMax"]),
                }
            )
        pages.append({"width": width, "height": height, "words": words})
    return pages


def compact(text: str) -> str:
    text = text.translate(LIGATURES)
    for source, replacement in [
        ("\u00a0", " "), ("\u202f", " "), ("\u2009", " "),
        ("\u00ad", ""), ("\u200b", ""), ("\ufeff", ""),
        ("‘", "'"), ("’", "'"), ("‚", "'"), ("‛", "'"),
        ("“", '"'), ("”", '"'), ("„", '"'), ("‟", '"'),
        ("–", "-"), ("—", "-"), ("‑", "-"), ("‐", "-"), ("−", "-"),
    ]:
        text = text.replace(source, replacement)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", "", text)
    return text.replace("-", "")


def expected_strings(item: dict) -> list[str]:
    values = [item["title"], item["author"], item["year"]]
    if item.get("subtitle"):
        values.append(item["subtitle"])
    values.append(item["source_label"])
    if item.get("copyright_notice"):
        values.append(item["copyright_notice"])
    for element in item["elements"]:
        if element["kind"] == "image":
            continue
        if element["kind"] == "table":
            values.extend(cell for row in element["rows"] for cell in row)
        else:
            values.append(element["text"])
    return values


def parse_article_pages(aux: Path) -> dict[int, int]:
    text = aux.read_text(encoding="utf-8", errors="replace")
    pages = {}
    for match in re.finditer(
        r"\\newlabel\{article-(\d+)\}\{\{[^{}]*\}\{(\d+)\}", text
    ):
        pages[int(match.group(1))] = int(match.group(2))
    return pages


def verify_pdf(
    path: Path,
    items: list[dict],
    *,
    article_pages: dict[int, int] | None = None,
    collection: bool = False,
) -> dict:
    info = pdfinfo(path)
    pages = int(info["Pages"])
    width = float(re.search(r"([0-9.]+)", info["Page size"]).group(1))
    height = float(re.search(r"x\s*([0-9.]+)", info["Page size"]).group(1))
    if abs(width - PAGE_W) > 0.2 or abs(height - PAGE_H) > 0.2:
        raise ValueError(f"{path.name}: wrong page size {width} x {height}")

    fonts = pdffonts(path)
    unembedded = [font for font in fonts if font.get("emb", "").lower() != "yes"]
    if unembedded:
        raise ValueError(f"{path.name}: unembedded fonts: {unembedded}")
    if not all("LiberationSerif" in font.get("name", "").replace(" ", "") for font in fonts):
        raise ValueError(f"{path.name}: unexpected fonts: {fonts}")

    boxes = page_box_words(path)
    if len(boxes) != pages:
        raise ValueError(f"{path.name}: bbox page count mismatch")
    bounds: list[int] = []
    blank: list[int] = []
    garbled: list[int] = []
    for number, page in enumerate(boxes, 1):
        for word in page["words"]:
            if (
                word["x0"] < 1
                or word["x1"] > page["width"] - 1
                or word["top"] < 1
                or word["bottom"] > page["height"] - 1
            ):
                bounds.append(number)
                break
            if TOP_CROP <= word["top"] and word["bottom"] <= PAGE_H - 45:
                if (
                    word["x0"] < MARGIN - 2
                    or word["x1"] > PAGE_W - MARGIN + 2
                ):
                    bounds.append(number)
                    break
        body = page_text(path, number, number)
        if len(body.strip()) < 12:
            blank.append(number)
        if "\ufffd" in body or "\x00" in body or re.search(
            r"Ã.|Â.|â€|ï¿½", body
        ):
            garbled.append(number)
    bounds = sorted(set(bounds))
    if blank:
        raise ValueError(f"{path.name}: blank pages {blank}")
    if bounds:
        raise ValueError(f"{path.name}: out-of-bounds text on pages {bounds}")
    if garbled:
        raise ValueError(f"{path.name}: possible encoding artifacts on pages {garbled}")

    start_pages: dict[int, int] = {}
    for item in items:
        number = item["number"]
        start = 1 if article_pages is None else article_pages[number]
        starts = [article_pages[n] for n in sorted(article_pages)] if article_pages else [1]
        if article_pages:
            index = sorted(article_pages).index(number)
            end = (
                article_pages[sorted(article_pages)[index + 1]] - 1
                if index + 1 < len(article_pages)
                else pages
            )
        else:
            end = pages
        start_pages[number] = start
        rendered = compact(page_text(path, start, end))
        cursor = 0
        for value in expected_strings(item):
            needle = compact(value)
            position = rendered.find(needle, cursor)
            if position < 0:
                raise ValueError(
                    f"{path.name}: missing or reordered text after page {start}: "
                    f"{value[:120]!r}"
                )
            cursor = position + len(needle)

    return {
        "file": path.name,
        "pages": pages,
        "blank_pages": blank,
        "out_of_bounds_pages": bounds,
        "garbled_pages": garbled,
        "complete_text_in_order": True,
        "fonts_embedded": True,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "article_start_pages": start_pages if collection else None,
    }


def build() -> None:
    items = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((ROOT / "reading_texts").glob("[0-9][0-9]_*.json"))
    ]
    if len(items) != 10:
        raise ValueError("Expected exactly ten article JSON files")
    write_latex_sources(items)

    shutil.rmtree(BUILD, ignore_errors=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    manifest = []
    for item in items:
        name = f"{item['number']:02d}_{slug(item['title'])}"
        pdf = compile_tex(f"singles/{name}.tex", passes=1)
        destination = OUT / f"{name}.pdf"
        shutil.copyfile(pdf, destination)
        entry = verify_pdf(destination, [item])
        entry.update({"number": item["number"], "title": item["title"]})
        manifest.append(entry)
        print(f"{destination.name}: {entry['pages']} pages", flush=True)

    collection_pdf = compile_tex("collection.tex", passes=2)
    collection_destination = OUT / "English_Writing_Collection.pdf"
    shutil.copyfile(collection_pdf, collection_destination)
    article_pages = parse_article_pages(BUILD / "collection.aux")
    if sorted(article_pages) != list(range(1, 11)):
        raise ValueError(f"Missing article page labels: {article_pages}")
    combined = verify_pdf(
        collection_destination, items, article_pages=article_pages, collection=True
    )
    combined["article_start_pages"] = article_pages
    combined["toc_page"] = 1
    print(f"{collection_destination.name}: {combined['pages']} pages", flush=True)

    report = {
        "engine": "XeLaTeX (TeX Live 2026)",
        "paper": "A4",
        "body_font": "Liberation Serif, embedded",
        "body_size_pt": 12,
        "line_spacing_pt": 16.5,
        "side_margins_pt": MARGIN,
        "single_articles": manifest,
        "collection": combined,
    }
    (OUT / "build_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return items, manifest


def overwrite_inputs(items: list[dict], manifest: list[dict]) -> None:
    for item, entry in zip(items, manifest):
        destination = (ROOT / item["repository_pdf"]).resolve()
        if ROOT not in destination.parents:
            raise ValueError("Unexpected repository PDF path")
        shutil.copyfile(OUT / entry["file"], destination)
    print("Replaced all ten repository PDFs with verified XeLaTeX editions.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Kept for compatibility; every build is verified",
    )
    parser.add_argument(
        "--overwrite-inputs",
        action="store_true",
        help="Replace the ten repository PDFs with their reading editions",
    )
    args = parser.parse_args(argv)
    for command in ("xelatex", "pdfinfo", "pdffonts", "pdftotext"):
        if shutil.which(command) is None:
            raise SystemExit(f"Required command not found: {command}")
    items, manifest = build()
    if args.overwrite_inputs:
        overwrite_inputs(items, manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
