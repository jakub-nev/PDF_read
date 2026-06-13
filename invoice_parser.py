"""Parse the Glassolutions invoice PDF into InvoiceItem objects."""
from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from models import InvoiceItem

# Diagnostic note: pdfplumber emits "1346 x975" (no space before H after 'x'),
# so the regex uses \s*x\s* to allow zero or more spaces around the 'x'.
#
# 001 kanceláře 6 1346 x975 16mm SWS Černý 21 1412.40 8474.40
# pol(3) [label] qty W x H spacer"mm" rest
_ITEM_RE = re.compile(
    r"^(?P<pos>\d{3})\s+"
    r"(?:(?P<label>\S+)\s+)?"
    r"(?P<qty>\d+)\s+"
    r"(?P<w>\d+)\s*x\s*(?P<h>\d+)\s+"
    r"(?P<spacer>\d+)\s*mm\b",
    re.IGNORECASE,
)

# 4mm / 4 mm -> pane thickness; bare decimal like 33.2 -> laminated pane.
# Bare integers without "mm" (e.g. "OR 572", VAT "21") must NOT match.
_PANE_RE = re.compile(r"(?P<mm>\d+(?:[.,]\d+)?)\s*mm|(?P<lam>\d+[.,]\d+)")

# Lines worth appending to a composition block must mention a thickness.
_THICKNESS_HINT_RE = re.compile(r"\d+\s*mm|\d+[.,]\d+")


def parse_composition(text: str) -> list[float]:
    """Extract ordered pane thicknesses from a composition description."""
    panes: list[float] = []
    for m in _PANE_RE.finditer(text):
        value = m.group("mm") or m.group("lam")
        panes.append(float(value.replace(",", ".")))
    return panes


def parse_invoice(path: str | Path) -> list[InvoiceItem]:
    items: list[InvoiceItem] = []
    comp_lines: list[str] = []
    in_comp_block = False

    with pdfplumber.open(str(path)) as pdf:
        lines = [
            line
            for page in pdf.pages
            for line in (page.extract_text() or "").split("\n")
        ]

    for line in lines:
        line = line.strip()
        m = _ITEM_RE.match(line)
        if m:
            in_comp_block = False
            composition = " ".join(comp_lines)
            items.append(InvoiceItem(
                position=m.group("pos"),
                label=m.group("label") or "",
                quantity=int(m.group("qty")),
                width=int(m.group("w")),
                height=int(m.group("h")),
                spacer=int(m.group("spacer")),
                composition_raw=composition,
                panes=parse_composition(composition),
            ))
        elif line.startswith("SGG"):
            comp_lines = [line]
            in_comp_block = True
        elif in_comp_block and _THICKNESS_HINT_RE.search(line):
            comp_lines.append(line)
        elif in_comp_block:
            in_comp_block = False  # block ended without an item yet; keep comp_lines
    return items
