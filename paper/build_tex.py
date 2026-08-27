#!/usr/bin/env python3
"""Convert camera_ready.md into an IEEEtran conference-class LaTeX document."""
import re
import sys
from pathlib import Path

SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2])

# Every table spans both columns (table*): all six are too wide for one
# IEEEtran column, and a plain `table` silently overflows into the body text.
WIDE = {"I", "II", "III", "IV", "V", "VI"}

# Column specs, keyed by table numeral. Text-bearing columns MUST be p{} --
# an `l` column does not wrap, so a long cell runs off the page and prints
# over the surrounding text. Widths are fractions of \textwidth and are kept
# a little under 1.0 to leave room for \tabcolsep between columns.
COLSPEC = {
    "I":   "p{0.17\\textwidth}p{0.16\\textwidth}p{0.13\\textwidth}p{0.42\\textwidth}",
    "II":  "lp{0.26\\textwidth}cccc",
    "III": "llcccc",
    "IV":  "p{0.44\\textwidth}p{0.46\\textwidth}",
    "V":   "p{0.19\\textwidth}p{0.07\\textwidth}p{0.26\\textwidth}p{0.37\\textwidth}",
    "VI":  "lcccccc",
}

# Figures wide enough that \columnwidth would render them illegibly small in a
# two-column layout are promoted to figure* across both columns.
WIDE_FIGURES = {2, 3}

# LaTeX-special characters that must be escaped in ordinary text.
SPECIALS = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_"}


def esc_text(s):
    """Escape a plain-text run (no markdown markup left in it)."""
    s = s.replace("\\", r"\textbackslash{}")
    for ch, rep in SPECIALS.items():
        s = s.replace(ch, rep)
    s = s.replace("^", r"\^{}").replace("~", r"\~{}")
    s = s.replace("{", r"\{").replace("}", r"\}")
    # typography
    s = s.replace("—", "---").replace("–", "--")
    s = s.replace("\u201c", "``").replace("\u201d", "''")
    # straight quotes come in pairs: first opens, second closes
    out, opening = [], True
    for ch in s:
        if ch == '"':
            out.append("``" if opening else "''")
            opening = not opening
        else:
            out.append(ch)
    s = "".join(out)
    s = s.replace("’", "'").replace("‘", "`")
    s = s.replace("×", r"$\times$").replace("µ", r"$\mu$")
    s = s.replace("≥", r"$\geq$").replace("≤", r"$\leq$")
    return s


def esc_code(s):
    """Escape the inside of a \\texttt{} span. Underscores MUST be escaped;
    bare _ is a math-mode character in text mode and fails to compile."""
    s = s.replace("\\", r"\textbackslash{}")
    s = s.replace("{", r"\{").replace("}", r"\}")
    for ch in "&%$#_":
        s = s.replace(ch, "\\" + ch)
    s = s.replace("^", r"\^{}").replace("~", r"\~{}")
    return s


INLINE = re.compile(r"(\*\*.+?\*\*|`.+?`|\*[^*]+?\*)")


CITE = re.compile(r"\[(\d+)\]")


def conv(text, cite=True):
    """Convert one line of inline markdown to LaTeX."""
    out = []
    for tok in INLINE.split(text):
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**"):
            out.append(r"\textbf{" + esc_text(tok[2:-2]) + "}")
        elif tok.startswith("`") and tok.endswith("`"):
            out.append(r"\texttt{" + esc_code(tok[1:-1]) + "}")
        elif tok.startswith("*") and tok.endswith("*"):
            out.append(r"\textit{" + esc_text(tok[1:-1]) + "}")
        else:
            out.append(esc_text(tok))
    res = "".join(out)
    if cite:
        # [3] in body text is a reference to \bibitem{b3}, not literal text
        res = CITE.sub(lambda m: r"\cite{b" + m.group(1) + "}", res)
    return res


lines = SRC.read_text(encoding="utf-8").split("\n")

L = []
A = L.append

A(r"%% Bridging Pre- and Post-Silicon Stimulus Generation for RISC-V Debug")
A(r"%% DVCon Europe / IEEE conference format.")
A(r"\documentclass[conference]{IEEEtran}")
A(r"\IEEEoverridecommandlockouts")
A(r"\usepackage{cite}")
A(r"\usepackage{amsmath,amssymb,amsfonts}")
A(r"\usepackage{algorithmic}")
A(r"\usepackage{graphicx}")
A(r"\usepackage{textcomp}")
A(r"\usepackage{xcolor}")
A(r"\usepackage{booktabs}")
A(r"\usepackage{tabularx}")
A(r"\usepackage[hidelinks]{hyperref}")
A(r"\usepackage{url}")
A(r"\def\BibTeX{{\rm B\kern-.05em{\sc i\kern-.025em b}\kern-.08em"
  r"T\kern-.1667em\lower.7ex\hbox{E}\kern-.125emX}}")
A("")
A(r"\begin{document}")
A("")
A(r"\title{Bridging Pre- and Post-Silicon Stimulus Generation for RISC-V Debug\\")
A(r"{\large A Python-Based Cross-Platform Framework}}")
A("")
A(r"\author{")
A(r"\IEEEauthorblockN{Jahanzeb Khalid}")
A(r"\IEEEauthorblockA{\textit{10xEngineers} \\")
A(r"Lahore, Pakistan \\")
A(r"jahanzeb.khalid@10xengineers.ai}")
A(r"\and")
A(r"\IEEEauthorblockN{Hassan Ashraf}")
A(r"\IEEEauthorblockA{\textit{10xEngineers} \\")
A(r"Lahore, Pakistan \\")
A(r"hassan.ashraf@10xengineers.ai}")
A(r"}")
A("")
A(r"\maketitle")
A("")

i = 0
in_title_block = True
pending_caption = None
fig_no = 0
buf_para = []


def flush():
    if buf_para:
        A(" ".join(buf_para))
        A("")
        buf_para.clear()


ROMAN = re.compile(r"^(I{1,3}|IV|V|VI{0,3}|IX|X)\.\s+(.*)$")

while i < len(lines):
    s = lines[i].strip()

    if in_title_block:
        if s.startswith("## Abstract"):
            in_title_block = False
        i += 1
        continue

    if not s:
        flush()
        i += 1
        continue

    # keywords
    if s.startswith("**Keywords**"):
        flush()
        rest = s.split("—", 1)[1].strip()
        A(r"\begin{IEEEkeywords}")
        A(conv(rest))
        A(r"\end{IEEEkeywords}")
        A("")
        i += 1
        continue

    # headings
    m = ROMAN.match(s[3:]) if s.startswith("## ") else None
    if s.startswith("## "):
        flush()
        title = s[3:]
        if m:
            A(r"\section{" + esc_text(m.group(2)) + "}")
        elif title.lower() == "acknowledgment":
            A(r"\section*{Acknowledgment}")
        elif title.lower() == "references":
            pass  # emitted as thebibliography below
        i += 1
        continue

    if s.startswith("### "):
        flush()
        sub = re.sub(r"^[A-G]\.\s+", "", s[4:])
        A(r"\subsection{" + esc_text(sub) + "}")
        i += 1
        continue

    # figure
    fm = re.match(r"^!\[.*?\]\((.+?)\)$", s)
    if fm:
        flush()
        fig_no += 1
        path = fm.group(1).rsplit(".", 1)[0]      # \includegraphics: no ext, _ is safe
        cap = ""
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        cm = re.match(r"^\*Figure \d+\.\s*(.*)\*$", lines[j].strip()) if j < len(lines) else None
        if cm:
            cap = conv(cm.group(1))
            i = j
        wide_fig = fig_no in WIDE_FIGURES
        fenv = "figure*" if wide_fig else "figure"
        fw = r"\textwidth" if wide_fig else r"\columnwidth"
        A(r"\begin{" + fenv + "}[!t]")
        A(r"\centering")
        A(r"\includegraphics[width=" + fw + "]{" + path + "}")
        A(r"\caption{" + cap + "}")
        A(r"\label{fig:" + str(fig_no) + "}")
        A(r"\end{" + fenv + "}")
        A("")
        i += 1
        continue

    # table caption
    tm = re.match(r"^\*\*(Table ([IVX]+) — (.+?))\*\*$", s)
    if tm:
        flush()
        pending_caption = (tm.group(2), tm.group(3))
        i += 1
        continue

    # table
    if s.startswith("|"):
        flush()
        rows = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                rows.append(cells)
            i += 1
        num, cap = pending_caption if pending_caption else ("?", "")
        pending_caption = None
        ncol = max(len(r) for r in rows)
        env = "table*" if num in WIDE else "table"
        spec = COLSPEC.get(num)
        if spec is None:
            raise SystemExit(
                f"Table {num} has no COLSPEC entry ({ncol} columns). Add one; "
                "the 'l'*n fallback does not wrap and overflows the page.")
        # count top-level column specifiers, ignoring the contents of p{...}
        n_spec = len(re.findall(r"p\{[^{}]*(?:\{[^{}]*\})?[^{}]*\}|[lcr]",
                                re.sub(r"\\textwidth", "", spec)))
        if n_spec != ncol:
            raise SystemExit(
                f"Table {num}: COLSPEC declares {n_spec} columns but the table "
                f"has {ncol}. Fix COLSPEC -- a mismatch silently misrenders.")
        A(r"\begin{" + env + "}[!t]")
        A(r"\caption{" + esc_text(cap) + "}")
        A(r"\label{tab:" + num + "}")
        A(r"\centering")
        A(r"\footnotesize")
        A(r"\begin{tabular}{" + spec + "}")
        A(r"\toprule")
        for ri, cells in enumerate(rows):
            cells = cells + [""] * (ncol - len(cells))
            A(" & ".join(conv(c) for c in cells) + r" \\")
            if ri == 0:
                A(r"\midrule")
        A(r"\bottomrule")
        A(r"\end{tabular}")
        A(r"\end{" + env + "}")
        A("")
        continue

    # references
    if re.match(r"^\[\d+\]\s", s):
        flush()
        if not any(x.startswith(r"\begin{thebibliography}") for x in L):
            A(r"\begin{thebibliography}{00}")
        body = re.sub(r"^\[\d+\]\s+", "", s)
        # URLs pass through \url{} verbatim; do not escape their underscores
        parts = re.split(r"(https?://\S+)", body)
        rendered = "".join(
            (r"\url{" + p.rstrip(".") + "}") if p.startswith("http") else conv(p, cite=False)
            for p in parts
        )
        A(r"\bibitem{b" + s[1:s.index("]")] + "} " + rendered)
        i += 1
        continue

    # lists
    if s.startswith("- ") or re.match(r"^\d+\.\s", s):
        flush()
        ordered = bool(re.match(r"^\d+\.\s", s))
        A(r"\begin{" + ("enumerate" if ordered else "itemize") + "}")
        while i < len(lines):
            t = lines[i].strip()
            if not (t.startswith("- ") or re.match(r"^\d+\.\s", t)):
                break
            item = re.sub(r"^(-\s|\d+\.\s)", "", t)
            A(r"\item " + conv(item))
            i += 1
        A(r"\end{" + ("enumerate" if ordered else "itemize") + "}")
        A("")
        continue

    # abstract body (first paragraph after "## Abstract")
    if not any(x.startswith(r"\begin{IEEEkeywords}") for x in L) and \
       not any(x == r"\end{abstract}" for x in L):
        A(r"\begin{abstract}")
        A(conv(s))
        A(r"\end{abstract}")
        A("")
        i += 1
        continue

    buf_para.append(conv(s))
    i += 1

flush()
if any(x.startswith(r"\begin{thebibliography}") for x in L):
    A(r"\end{thebibliography}")
A("")
A(r"\end{document}")

text = "\n".join(L) + "\n"

# Guard against the double-escape trap: an automated _ -> \_ pass can turn an
# already-escaped \_ into \\_ , which is itself a compile error.
before = text.count("\\\\_")
text = text.replace("\\\\_", "\\_")
OUT.write_text(text, encoding="utf-8")
print(f"wrote {OUT} ({len(text)} chars); collapsed {before} double-escaped underscores")

# static checks (no LaTeX toolchain available to compile against)
depth = 0
for ch in text:
    if ch == "{":
        depth += 1
    elif ch == "}":
        depth -= 1
print("brace balance:", depth)
bad = re.findall(r"\\texttt\{[^{}]*(?<!\\)_[^{}]*\}", text)
print("unescaped _ inside texttt:", len(bad))
