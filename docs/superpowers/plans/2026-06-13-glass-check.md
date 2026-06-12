# Kontrola skla Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A tkinter app that cross-checks a Glassolutions invoice PDF against the user's order Excel and flags dimension/quantity/glass-type discrepancies.

**Architecture:** Three pure units (`invoice_parser.py`, `order_parser.py`, `matcher.py`) sharing dataclasses in `models.py`, an Excel report writer (`report.py`), and a thin tkinter GUI entry point (`glass_check.py`). Items are paired by width×height (exact, then swapped orientation), quantities aggregated per dimension, glass structure derived from both notations and compared.

**Tech Stack:** Python ≥3.10, pdfplumber, openpyxl, tkinter (stdlib), pytest.

**Spec:** `docs/superpowers/specs/2026-06-13-glass-check-design.md`

**Fixtures:** the real sample files at repo root — `faktura_sklo.pdf` (25 glass items, different order than the xlsx) and `objednavka_sklo_VltavaHolding_16.9.25.xlsx` (11 rows). They are format samples only; they do NOT match each other.

---

### Task 1: Dependencies and project skeleton

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/__init__.py` (empty)

- [ ] **Step 1: Declare dependencies**

Replace the `dependencies` line in `pyproject.toml`:

```toml
[project]
name = "pdf-read"
version = "0.1.0"
description = "Cross-check glass panel orders (xlsx) against supplier invoices (pdf)"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "pdfplumber>=0.11",
    "openpyxl>=3.1",
]

[dependency-groups]
dev = ["pytest>=8"]
```

- [ ] **Step 2: Install**

Run: `pip install pdfplumber openpyxl pytest`
(If the project uses `uv`: `uv sync` works too — either way the next step must pass.)

- [ ] **Step 3: Verify imports**

Run: `python -c "import pdfplumber, openpyxl, tkinter; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Create empty `tests/__init__.py` and commit**

```bash
git add pyproject.toml tests/__init__.py
git commit -m "chore: add pdfplumber/openpyxl/pytest dependencies"
```

---

### Task 2: Shared data models

**Files:**
- Create: `models.py`

No behavior — just dataclasses, so no test-first here. Both parsers and the matcher import these.

- [ ] **Step 1: Write `models.py`**

```python
"""Shared data structures for the glass order/invoice cross-check."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OrderItem:
    """One row of the customer's order Excel."""
    number: str          # Položka
    objekt: str          # Objekt (project name)
    label: str           # Označení pozice
    width: int           # Šířka (mm)
    height: int          # Výška (mm)
    quantity: int        # Kus
    skladba_raw: str     # e.g. "4-18-4-18-4" or "33.2 XN-16-4-16-6 XN"
    typ: str             # Typ skla, e.g. "Izolační trojsklo"
    panes: list[float] | None = None   # e.g. [4, 4, 4] or [33.2, 4, 6]; None = unparseable
    gaps: list[float] | None = None    # e.g. [18, 18]; None = unparseable


@dataclass
class InvoiceItem:
    """One glass line of the supplier invoice PDF."""
    position: str        # pol., e.g. "001"
    label: str           # pozice, e.g. "kanceláře" or "1,2" ("" if absent)
    quantity: int        # počet kusů
    width: int           # rozměry v mm: first number
    height: int          # rozměry v mm: second number
    spacer: int | None   # distanční rámeček width in mm, e.g. 18
    composition_raw: str # e.g. "SGG Climatop XN PXN 4mm / PLC 4mm / PXN 4mm"
    panes: list[float] = field(default_factory=list)  # e.g. [4, 4, 4]; [] = unknown


@dataclass
class MatchResult:
    """Outcome of comparing one order row (or an unmatched invoice line)."""
    status: str                        # "OK" | "WARNING" | "MISSING" | "EXTRA"
    order_item: OrderItem | None
    invoice_item: InvoiceItem | None
    problems: list[str] = field(default_factory=list)  # human-readable, Czech
```

- [ ] **Step 2: Sanity check and commit**

Run: `python -c "import models; print(models.MatchResult('OK', None, None))"`
Expected: `MatchResult(status='OK', order_item=None, invoice_item=None, problems=[])`

```bash
git add models.py
git commit -m "feat: add shared dataclasses for order/invoice items and match results"
```

---

### Task 3: Order parser (Excel)

**Files:**
- Create: `order_parser.py`
- Test: `tests/test_order_parser.py`

The sample workbook has sheet `List1`, header row 1:
`Položka | Objekt | Označení pozice | Šířka (mm) | Výška (mm) | Tloušťka skla (mm) | Kus | Skladba skla | Typ skla | Poznámka | poznámka2`
then 11 data rows, then one fully empty row. Columns are located by normalized
(lowercased, diacritics-stripped) header prefix so column order may vary.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_order_parser.py
from pathlib import Path

import pytest

from order_parser import parse_order, parse_skladba

SAMPLE = Path(__file__).resolve().parent.parent / "objednavka_sklo_VltavaHolding_16.9.25.xlsx"


# --- parse_skladba ---------------------------------------------------------

def test_skladba_triple():
    assert parse_skladba("4-18-4-18-4") == ([4.0, 4.0, 4.0], [18.0, 18.0])


def test_skladba_double():
    assert parse_skladba("4-16-4") == ([4.0, 4.0], [16.0])


def test_skladba_laminated_with_suffixes():
    panes, gaps = parse_skladba("33.2 XN-16-4-16-6 XN")
    assert panes == [33.2, 4.0, 6.0]
    assert gaps == [16.0, 16.0]


def test_skladba_unparseable_returns_none():
    assert parse_skladba("trojsklo standard") == (None, None)
    assert parse_skladba("") == (None, None)
    assert parse_skladba("4-18") == (None, None)  # even token count = ambiguous


# --- parse_order on the real sample file -----------------------------------

@pytest.fixture(scope="module")
def items():
    return parse_order(SAMPLE)


def test_row_count(items):
    assert len(items) == 11  # trailing empty row ignored


def test_first_row(items):
    it = items[0]
    assert (it.objekt, it.width, it.height, it.quantity) == ("becica", 830, 1400, 1)
    assert it.skladba_raw == "4-18-4-18-4"
    assert it.panes == [4.0, 4.0, 4.0]
    assert it.gaps == [18.0, 18.0]


def test_laminated_row(items):
    it = items[7]  # Položka 8, RD_zelechovice
    assert (it.width, it.height, it.quantity) == (654, 1140, 6)
    assert it.panes == [33.2, 4.0, 6.0]
    assert it.gaps == [16.0, 16.0]
    assert "protihlukov" in it.typ.lower()


def test_missing_column_raises(tmp_path):
    import openpyxl
    wb = openpyxl.Workbook()
    wb.active.append(["Položka", "Objekt"])  # no width/height/kus
    bad = tmp_path / "bad.xlsx"
    wb.save(bad)
    with pytest.raises(ValueError, match="chybí sloupec"):
        parse_order(bad)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_order_parser.py -v`
Expected: FAIL / errors with `ModuleNotFoundError: No module named 'order_parser'`

- [ ] **Step 3: Implement `order_parser.py`**

```python
"""Parse the customer's glass order Excel into OrderItem objects."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import openpyxl

from models import OrderItem


def _norm(s: object) -> str:
    """Lowercase and strip diacritics: 'Šířka (mm)' -> 'sirka (mm)'."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


# normalized header prefix -> attribute
_COLUMNS = {
    "polozka": "number",
    "objekt": "objekt",
    "oznaceni": "label",
    "sirka": "width",
    "vyska": "height",
    "kus": "quantity",
    "skladba": "skladba",
    "typ skla": "typ",
}
_REQUIRED = ("width", "height", "quantity")


def parse_skladba(s: object) -> tuple[list[float] | None, list[float] | None]:
    """'4-18-4-18-4' -> ([4,4,4], [18,18]); '33.2 XN-16-4-16-6 XN' -> ([33.2,4,6], [16,16]).

    Returns (None, None) when the string cannot be interpreted as an
    alternating pane/gap sequence (the caller then degrades to a
    side-by-side display instead of reporting a false mismatch).
    """
    tokens = [t.strip() for t in str(s or "").split("-")]
    values: list[float] = []
    for t in tokens:
        m = re.match(r"(\d+(?:[.,]\d+)?)", t)
        if not m:
            return None, None
        values.append(float(m.group(1).replace(",", ".")))
    if len(values) % 2 == 0:  # alternating glass-gap-glass... is always odd
        return None, None
    return values[0::2], values[1::2]


def parse_order(path: str | Path) -> list[OrderItem]:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.worksheets[0]
    rows = ws.iter_rows(values_only=True)
    header = next(rows, None) or ()

    col_idx: dict[str, int] = {}
    for i, cell in enumerate(header):
        name = _norm(cell)
        for prefix, attr in _COLUMNS.items():
            if name.startswith(prefix) and attr not in col_idx:
                col_idx[attr] = i

    for attr in _REQUIRED:
        if attr not in col_idx:
            raise ValueError(f"V objednávce chybí sloupec: {attr} (šířka/výška/kus)")

    def get(row: tuple, attr: str) -> object:
        i = col_idx.get(attr)
        return row[i] if i is not None and i < len(row) else None

    items: list[OrderItem] = []
    for row in rows:
        w, h = get(row, "width"), get(row, "height")
        if w is None or h is None:
            continue  # trailing empty rows
        skladba_raw = str(get(row, "skladba") or "").strip()
        panes, gaps = parse_skladba(skladba_raw)
        items.append(OrderItem(
            number=str(get(row, "number") or ""),
            objekt=str(get(row, "objekt") or "").strip(),
            label=str(get(row, "label") or "").strip(),
            width=int(w),
            height=int(h),
            quantity=int(get(row, "quantity") or 1),
            skladba_raw=skladba_raw,
            typ=str(get(row, "typ") or "").strip(),
            panes=panes,
            gaps=gaps,
        ))
    return items
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_order_parser.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add order_parser.py tests/test_order_parser.py
git commit -m "feat: parse order xlsx into OrderItems incl. skladba structure"
```

---

### Task 4: Invoice parser (PDF)

**Files:**
- Create: `invoice_parser.py`
- Test: `tests/test_invoice_parser.py`

Invoice text layout (one line per item, composition in header lines above groups):

```
707 Lesní Domov                              <- object header (ignored)
SGG Climaplus XN                             <- composition block start
Planitherm XN 4mm Satinato 4 mm              <- composition continuation
001 kanceláře 6 1346 x 975 16mm SWS Černý 21 1412.40 8474.40   <- item
...
SGG Climatop XN PXN 4mm / PLC 4mm / PXN 4mm  <- one-line composition block
006 1,2 2 809 x 2065 18mm SWS Černý 21 1932.00 3864.00
007 3,4 2 783 x 2065 18mm SWS Černý 21 1863.00 3726.00         <- same block applies
990 1 21 66299.60 66299.60                   <- no "W x H" -> skipped (záloha)
995 1 0.50Kč/kg 21 762.15 762.15             <- skipped (energetická přirážka)
```

Item line: `pol(3 digits)  [pozice label, one token]  qty  W x H  <spacer>mm ...`.
A composition block starts at a line beginning with `SGG` and accumulates following
lines containing thickness info, until the next item or `SGG` line. Items inherit
the most recent block (item 014 has no block of its own — it reuses 006's).

- [ ] **Step 1: Diagnostic — inspect real pdfplumber output**

The exact spacing/characters pdfplumber emits may differ from the sketch above.
Before writing assertions, dump the text:

Run: `python -c "import pdfplumber; pdf = pdfplumber.open('faktura_sklo.pdf'); [print(repr(l)) for p in pdf.pages for l in (p.extract_text() or '').split('\n')]"`

Verify the item lines match the pattern `^\d{3} <token> <qty> <w> x <h> <spacer>mm ...`
and note any deviations (e.g. `x` glued to numbers, different spacer text). If the
real output deviates, adjust the regexes in Step 4 and the expected values in Step 2
accordingly — the tests below encode the layout shown above.

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_invoice_parser.py
from pathlib import Path

import pytest

from invoice_parser import parse_invoice, parse_composition

SAMPLE = Path(__file__).resolve().parent.parent / "faktura_sklo.pdf"


# --- parse_composition ------------------------------------------------------

def test_composition_triple_slash_notation():
    assert parse_composition("SGG Climatop XN PXN 4mm / PLC 4mm / PXN 4mm") == [4.0, 4.0, 4.0]


def test_composition_double_with_spaced_mm():
    assert parse_composition("SGG Climaplus XN Planitherm XN 4mm Satinato 4 mm") == [4.0, 4.0]


def test_composition_laminated_stadip():
    text = "SGG Climatop XN Stadip Antelio ® silver 6 mm Planitherm XN 4mm Stadip 33.2 XN"
    assert parse_composition(text) == [6.0, 4.0, 33.2]


def test_composition_ignores_non_thickness_numbers():
    # "OR 572 CL4" must not contribute panes
    text = "Planitherm XN 4mm OR 572 CL4 kura čirá Planitherm XN 4mm"
    assert parse_composition(text) == [4.0, 4.0]


# --- parse_invoice on the real sample file ----------------------------------

@pytest.fixture(scope="module")
def items():
    return parse_invoice(SAMPLE)


def test_item_count_excludes_non_glass_lines(items):
    assert len(items) == 25  # pol. 990 and 995 must not appear
    assert {it.position for it in items} == {f"{n:03d}" for n in range(1, 26)}


def test_total_quantity(items):
    assert sum(it.quantity for it in items) == 48


def test_first_item(items):
    it = items[0]
    assert (it.position, it.label, it.quantity) == ("001", "kanceláře", 6)
    assert (it.width, it.height, it.spacer) == (1346, 975, 16)
    assert it.panes == [4.0, 4.0]


def test_laminated_item(items):
    it = items[1]  # 002 vchod
    assert (it.width, it.height, it.quantity, it.spacer) == (796, 2222, 1, 18)
    assert it.panes == [6.0, 4.0, 33.2]


def test_numeric_label_and_qty_disambiguation(items):
    it = items[17]  # "018 5 6 634 x 1245" -> label "5", qty 6
    assert (it.position, it.label, it.quantity) == ("018", "5", 6)
    assert (it.width, it.height) == (634, 1245)


def test_composition_carries_over_groups(items):
    it = items[13]  # 014 has no own SGG block; inherits triple from block at 006
    assert (it.width, it.height) == (820, 505)
    assert it.panes == [4.0, 4.0, 4.0]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_invoice_parser.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'invoice_parser'`

- [ ] **Step 4: Implement `invoice_parser.py`**

```python
"""Parse the Glassolutions invoice PDF into InvoiceItem objects."""
from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from models import InvoiceItem

# 001 kanceláře 6 1346 x 975 16mm SWS Černý 21 1412.40 8474.40
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

# lines worth appending to a composition block must mention a thickness
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
```

Note: pol. 990 (zálohová částka) and 995 (energetická přirážka) have no `W x H`
token, so `_ITEM_RE` never matches them — they are excluded by construction.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_invoice_parser.py -v`
Expected: all PASS. If individual assertions fail, re-check against the Step 1
diagnostic dump — fix the regex (or, if the PDF text genuinely differs from the
sketch, the expected constants) so the tests reflect the real file.

- [ ] **Step 6: Commit**

```bash
git add invoice_parser.py tests/test_invoice_parser.py
git commit -m "feat: parse invoice pdf into InvoiceItems incl. glass composition"
```

---

### Task 5: Matcher

**Files:**
- Create: `matcher.py`
- Test: `tests/test_matcher.py`

All matcher tests use synthetic items (the two sample files are different orders).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_matcher.py
from models import InvoiceItem, OrderItem
from matcher import match_items


def order(w, h, qty=1, panes=None, gaps=None, skladba="4-18-4-18-4", **kw):
    if panes is None and skladba == "4-18-4-18-4":
        panes, gaps = [4.0, 4.0, 4.0], [18.0, 18.0]
    return OrderItem(number="1", objekt="obj", label="1", width=w, height=h,
                     quantity=qty, skladba_raw=skladba, typ="trojsklo",
                     panes=panes, gaps=gaps, **kw)


def invoice(w, h, qty=1, panes=None, spacer=18, comp="PXN 4mm / PLC 4mm / PXN 4mm"):
    return InvoiceItem(position="001", label="1", quantity=qty, width=w, height=h,
                       spacer=spacer, composition_raw=comp,
                       panes=panes if panes is not None else [4.0, 4.0, 4.0])


def test_exact_match_ok():
    [r] = match_items([order(830, 1400)], [invoice(830, 1400)])
    assert r.status == "OK"
    assert r.problems == []


def test_swapped_orientation_is_warning():
    [r] = match_items([order(830, 1400)], [invoice(1400, 830)])
    assert r.status == "WARNING"
    assert any("prohozen" in p for p in r.problems)


def test_quantity_mismatch():
    [r] = match_items([order(830, 1400, qty=2)], [invoice(830, 1400, qty=1)])
    assert r.status == "WARNING"
    assert any("objednáno 2" in p and "fakturováno 1" in p for p in r.problems)


def test_quantity_aggregated_across_lines():
    # order 2+2 pieces of same size; invoice bills 4 in one line -> OK
    res = match_items(
        [order(800, 600, qty=2), order(800, 600, qty=2)],
        [invoice(800, 600, qty=4)],
    )
    assert [r.status for r in res] == ["OK", "OK"]


def test_pane_thickness_mismatch():
    [r] = match_items(
        [order(830, 1400)],                                   # 4/4/4
        [invoice(830, 1400, panes=[6.0, 4.0, 4.0])],
    )
    assert r.status == "WARNING"
    assert any("tloušťky" in p for p in r.problems)


def test_pane_count_mismatch():
    [r] = match_items(
        [order(830, 1400)],                                   # triple
        [invoice(830, 1400, panes=[4.0, 4.0], comp="dvojsklo")],
    )
    assert r.status == "WARNING"
    assert any("počet skel" in p for p in r.problems)


def test_spacer_mismatch():
    [r] = match_items([order(830, 1400)], [invoice(830, 1400, spacer=16)])
    assert r.status == "WARNING"
    assert any("rámeček" in p for p in r.problems)


def test_laminated_panes_compare_equal_regardless_of_order():
    o = order(654, 1140, panes=[33.2, 4.0, 6.0], gaps=[16.0, 16.0],
              skladba="33.2 XN-16-4-16-6 XN")
    i = invoice(654, 1140, panes=[6.0, 4.0, 33.2], spacer=16)
    [r] = match_items([o], [i])
    assert r.status == "OK"


def test_unparseable_skladba_degrades_to_no_type_check():
    o = order(830, 1400, panes=None, gaps=None, skladba="speciální sklo")
    [r] = match_items([o], [invoice(830, 1400, panes=[6.0, 6.0])])
    assert r.status == "OK"  # type not comparable -> no false mismatch


def test_missing_on_invoice():
    [r] = match_items([order(830, 1400)], [])
    assert r.status == "MISSING"
    assert r.invoice_item is None


def test_extra_on_invoice():
    [r] = match_items([], [invoice(830, 1400)])
    assert r.status == "EXTRA"
    assert r.order_item is None


def test_same_dims_different_types_pair_correctly():
    # two order rows with identical dims but different skladba (real case:
    # RD_zelechovice rows 8+9) must each find the invoice line of their type
    o1 = order(654, 1140, qty=6, panes=[33.2, 4.0, 6.0], gaps=[16.0, 16.0],
               skladba="33.2 XN-16-4-16-6 XN")
    o2 = order(654, 1140, qty=2)  # standard 4/4/4
    i1 = invoice(654, 1140, qty=2, spacer=18)                    # 4/4/4
    i2 = invoice(654, 1140, qty=6, panes=[33.2, 4.0, 6.0], spacer=16)
    res = match_items([o1, o2], [i1, i2])
    assert [r.status for r in res] == ["OK", "OK"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_matcher.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'matcher'`

- [ ] **Step 3: Implement `matcher.py`**

```python
"""Pair order rows with invoice lines and compare them."""
from __future__ import annotations

from models import InvoiceItem, MatchResult, OrderItem


def _fmt(values: list[float]) -> str:
    return "/".join(f"{v:g}" for v in values)


def _structure_problems(o: OrderItem, inv: InvoiceItem) -> list[str]:
    """Compare derived glass structure; [] also when not comparable."""
    problems: list[str] = []
    if o.panes is None or not inv.panes:
        return problems  # unparseable on either side -> side-by-side only
    if len(o.panes) != len(inv.panes):
        problems.append(
            f"počet skel: objednáno {len(o.panes)}, faktura {len(inv.panes)}")
    elif sorted(o.panes) != sorted(inv.panes):
        problems.append(
            f"tloušťky skel: objednáno {_fmt(o.panes)}, faktura {_fmt(inv.panes)}")
    if o.gaps and inv.spacer is not None:
        if any(g != inv.spacer for g in o.gaps):
            problems.append(
                f"rámeček: objednáno {_fmt(o.gaps)} mm, faktura {inv.spacer} mm")
    return problems


def _structures_compatible(o: OrderItem, inv: InvoiceItem) -> bool:
    return not _structure_problems(o, inv)


def match_items(order_items: list[OrderItem],
                invoice_items: list[InvoiceItem]) -> list[MatchResult]:
    inv_groups: dict[tuple[int, int], list[InvoiceItem]] = {}
    for it in invoice_items:
        inv_groups.setdefault((it.width, it.height), []).append(it)

    ord_groups: dict[tuple[int, int], list[OrderItem]] = {}
    for it in order_items:
        ord_groups.setdefault((it.width, it.height), []).append(it)

    results: list[MatchResult] = []
    for dims, ord_group in ord_groups.items():
        inv_group = inv_groups.pop(dims, None)
        swapped = False
        if inv_group is None:
            inv_group = inv_groups.pop((dims[1], dims[0]), None)
            swapped = inv_group is not None

        if inv_group is None:
            for o in ord_group:
                results.append(MatchResult(
                    "MISSING", o, None,
                    [f"rozměr {o.width} x {o.height} na faktuře chybí"]))
            continue

        shared: list[str] = []
        if swapped:
            shared.append("prohozená šířka × výška na faktuře")
        ordered_qty = sum(o.quantity for o in ord_group)
        invoiced_qty = sum(i.quantity for i in inv_group)
        if ordered_qty != invoiced_qty:
            shared.append(
                f"počet kusů: objednáno {ordered_qty}, fakturováno {invoiced_qty}")

        # pair within the dimension group: prefer the invoice line whose
        # structure matches, so two same-size items of different type
        # (e.g. protihlukové vs. standardní) each check against the right line
        remaining = list(inv_group)
        for o in ord_group:
            inv = next((i for i in remaining if _structures_compatible(o, i)),
                       (remaining or inv_group)[0])
            if inv in remaining:
                remaining.remove(inv)
            problems = shared + _structure_problems(o, inv)
            results.append(MatchResult(
                "OK" if not problems else "WARNING", o, inv, problems))

    for inv_group in inv_groups.values():
        for it in inv_group:
            results.append(MatchResult(
                "EXTRA", None, it,
                [f"rozměr {it.width} x {it.height} nebyl objednán"]))
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_matcher.py -v`
Expected: all PASS

- [ ] **Step 5: Run the whole suite and commit**

Run: `pytest -v`
Expected: all PASS

```bash
git add matcher.py tests/test_matcher.py
git commit -m "feat: match order rows to invoice lines and flag discrepancies"
```

---

### Task 6: Excel report writer

**Files:**
- Create: `report.py`
- Test: `tests/test_report.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_report.py
import openpyxl

from models import InvoiceItem, MatchResult, OrderItem
from report import write_report


def test_write_report(tmp_path):
    o = OrderItem(number="1", objekt="becica", label="1", width=830, height=1400,
                  quantity=1, skladba_raw="4-18-4-18-4", typ="trojsklo",
                  panes=[4.0, 4.0, 4.0], gaps=[18.0, 18.0])
    i = InvoiceItem(position="001", label="1", quantity=1, width=830, height=1400,
                    spacer=18, composition_raw="PXN 4mm / PLC 4mm / PXN 4mm",
                    panes=[4.0, 4.0, 4.0])
    results = [
        MatchResult("OK", o, i, []),
        MatchResult("MISSING", o, None, ["rozměr 830 x 1400 na faktuře chybí"]),
        MatchResult("EXTRA", None, i, ["rozměr 830 x 1400 nebyl objednán"]),
    ]
    out = tmp_path / "report.xlsx"
    write_report(results, out)

    ws = openpyxl.load_workbook(out).active
    rows = list(ws.iter_rows(values_only=True))
    assert rows[0][0] == "Stav"
    assert len(rows) == 4  # header + 3 results
    assert rows[1][0] == "OK"
    assert rows[2][0] == "chybí na faktuře"
    assert rows[3][0] == "navíc na faktuře"
    assert "830 x 1400" in str(rows[1][3])   # order dims column
    assert "830 x 1400" in str(rows[3][4])   # invoice dims column
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_report.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'report'`

- [ ] **Step 3: Implement `report.py`**

```python
"""Write match results to a color-coded Excel report."""
from __future__ import annotations

from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill

from models import MatchResult

STATUS_TEXT = {
    "OK": "OK",
    "WARNING": "rozdíl",
    "MISSING": "chybí na faktuře",
    "EXTRA": "navíc na faktuře",
}
_FILLS = {
    "OK": PatternFill("solid", start_color="C6EFCE"),       # green
    "WARNING": PatternFill("solid", start_color="FFEB9C"),  # orange
    "MISSING": PatternFill("solid", start_color="FFC7CE"),  # red
    "EXTRA": PatternFill("solid", start_color="FFC7CE"),    # red
}

HEADERS = ["Stav", "Objekt", "Pozice", "Rozměr objednávka", "Rozměr faktura",
           "Ks objednáno", "Ks fakturováno", "Skladba objednávka",
           "Skladba faktura", "Problémy"]


def result_row(r: MatchResult) -> list[str]:
    o, i = r.order_item, r.invoice_item
    return [
        STATUS_TEXT[r.status],
        o.objekt if o else "",
        o.label if o else (i.label if i else ""),
        f"{o.width} x {o.height}" if o else "",
        f"{i.width} x {i.height}" if i else "",
        str(o.quantity) if o else "",
        str(i.quantity) if i else "",
        o.skladba_raw if o else "",
        f"{i.composition_raw} | rámeček {i.spacer} mm" if i else "",
        "; ".join(r.problems),
    ]


def write_report(results: list[MatchResult], path: str | Path) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Kontrola"
    ws.append(HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for r in results:
        ws.append(result_row(r))
        fill = _FILLS[r.status]
        for cell in ws[ws.max_row]:
            cell.fill = fill
    for col, width in zip("ABCDEFGHIJ", (16, 16, 10, 16, 16, 12, 12, 24, 40, 50)):
        ws.column_dimensions[col].width = width
    wb.save(path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_report.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add report.py tests/test_report.py
git commit -m "feat: export match results to color-coded xlsx report"
```

---

### Task 7: tkinter GUI and README

**Files:**
- Create: `glass_check.py`
- Modify: `README.md`

The GUI is wiring only — no business logic — and is verified manually.

- [ ] **Step 1: Write `glass_check.py`**

```python
"""Kontrola skla — GUI: cross-check a glass order xlsx against an invoice pdf."""
from __future__ import annotations

import tkinter as tk
import traceback
from tkinter import filedialog, messagebox, ttk

from invoice_parser import parse_invoice
from matcher import match_items
from order_parser import parse_order
from report import result_row, write_report

_TAG_COLORS = {"OK": "#c6efce", "WARNING": "#ffeb9c",
               "MISSING": "#ffc7ce", "EXTRA": "#ffc7ce"}
_COLUMNS = ["Stav", "Objekt", "Pozice", "Rozměr obj.", "Rozměr fakt.",
            "Ks obj.", "Ks fakt.", "Skladba obj.", "Skladba fakt.", "Problémy"]


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Kontrola skla — objednávka vs. faktura")
        self.geometry("1200x600")
        self.pdf_path = tk.StringVar()
        self.xlsx_path = tk.StringVar()
        self.results = []

        picker = ttk.Frame(self, padding=8)
        picker.pack(fill="x")
        self._file_row(picker, 0, "Faktura (PDF):", self.pdf_path,
                       [("PDF", "*.pdf")])
        self._file_row(picker, 1, "Objednávka (Excel):", self.xlsx_path,
                       [("Excel", "*.xlsx")])
        picker.columnconfigure(1, weight=1)

        bar = ttk.Frame(self, padding=(8, 0, 8, 8))
        bar.pack(fill="x")
        ttk.Button(bar, text="Zkontrolovat", command=self.check).pack(side="left")
        self.export_btn = ttk.Button(bar, text="Uložit report",
                                     command=self.export, state="disabled")
        self.export_btn.pack(side="left", padx=8)
        self.summary = ttk.Label(bar, text="", font=("", 10, "bold"))
        self.summary.pack(side="left", padx=16)

        self.tree = ttk.Treeview(self, columns=_COLUMNS, show="headings")
        widths = (110, 110, 70, 100, 100, 60, 60, 150, 260, 320)
        for col, w in zip(_COLUMNS, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, stretch=col == "Problémy")
        for status, color in _TAG_COLORS.items():
            self.tree.tag_configure(status, background=color)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _file_row(self, parent, row, text, var, types):
        ttk.Label(parent, text=text, width=18).grid(row=row, column=0, sticky="w")
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1,
                                                 sticky="ew", padx=4)
        ttk.Button(parent, text="Vybrat…",
                   command=lambda: var.set(
                       filedialog.askopenfilename(filetypes=types) or var.get())
                   ).grid(row=row, column=2)

    def check(self) -> None:
        if not self.pdf_path.get() or not self.xlsx_path.get():
            messagebox.showwarning("Kontrola skla",
                                   "Vyberte prosím oba soubory.")
            return
        try:
            invoice_items = parse_invoice(self.pdf_path.get())
            order_items = parse_order(self.xlsx_path.get())
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror("Chyba při čtení souborů", str(exc))
            return
        if not invoice_items:
            messagebox.showerror(
                "Kontrola skla",
                "Formát faktury nebyl rozpoznán — nenašel jsem žádné položky.")
            return
        if not order_items:
            messagebox.showerror(
                "Kontrola skla",
                "V objednávce nebyly nalezeny žádné řádky.")
            return

        self.results = match_items(order_items, invoice_items)
        self.tree.delete(*self.tree.get_children())
        for r in self.results:
            values = result_row(r)
            self.tree.insert("", "end", values=values, tags=(r.status,))
        ok = sum(1 for r in self.results if r.status == "OK")
        total = len(self.results)
        problems = total - ok
        self.summary.config(
            text=f"{ok} z {total} položek v pořádku, {problems} "
                 + ("problém" if problems == 1 else
                    "problémy" if 2 <= problems <= 4 else "problémů"))
        self.export_btn.config(state="normal")

    def export(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
            initialfile="kontrola_skla.xlsx")
        if not path:
            return
        try:
            write_report(self.results, path)
        except Exception as exc:
            messagebox.showerror("Chyba při ukládání", str(exc))
            return
        messagebox.showinfo("Kontrola skla", f"Report uložen:\n{path}")


if __name__ == "__main__":
    App().mainloop()
```

- [ ] **Step 2: Smoke-test it launches**

Run: `python -c "import glass_check"` (import must not open a window)
Expected: no output, exit 0.

Then launch manually: `python glass_check.py`
Verify: window opens; picking `faktura_sklo.pdf` + the sample xlsx and clicking
Zkontrolovat shows a table (everything red MISSING/EXTRA is CORRECT here — the
sample files are different orders); summary text appears; "Uložit report" writes
an xlsx that opens in Excel with colored rows. Close the window.

- [ ] **Step 3: Write README**

Replace `README.md` content:

```markdown
# Kontrola skla

Porovná objednávku skel (Excel) s fakturou od dodavatele (PDF) a upozorní na
rozdíly v rozměrech, počtech kusů a skladbě skla.

## Spuštění

    pip install pdfplumber openpyxl
    python glass_check.py

1. Vyberte fakturu (PDF) a objednávku (Excel).
2. Klikněte na **Zkontrolovat**.
3. Zelené řádky jsou v pořádku, oranžové mají rozdíl (popsaný ve sloupci
   Problémy), červené položky chybí na faktuře nebo jsou tam navíc.
4. **Uložit report** vytvoří barevný Excel s výsledky.

Položky se párují podle rozměru (šířka × výška, případně prohozené) a
porovnává se počet kusů a skladba (tloušťky skel a meziskelní rámeček).

## Testy

    pip install pytest
    pytest
```

- [ ] **Step 4: Run full suite and commit**

Run: `pytest -v`
Expected: all PASS

```bash
git add glass_check.py README.md
git commit -m "feat: tkinter GUI for order/invoice cross-check + README"
```
