# Kontrola skla — Glass Order/Invoice Cross-Check App

**Date:** 2026-06-13
**Status:** Approved

## Problem

The user orders glass panels by sending the supplier (Glassolutions / Saint-Gobain) an
Excel order file. The supplier replies with a PDF invoice (zálohová faktura). The supplier
sometimes makes mistakes in dimensions, quantities, or glass type. The user needs an app
that cross-checks the invoice against the order and flags discrepancies.

The two files currently in the repo (`faktura_sklo.pdf`, `objednavka_sklo_VltavaHolding_16.9.25.xlsx`)
are **format samples from different orders** — they are used to define the parsers, not to
be cross-checked against each other.

## Requirements

- Input: one invoice PDF + one order Excel, both in the formats of the sample files.
- Pair items between the two documents **by dimensions (width × height) and quantity**.
- Compare, per matched pair: dimensions, total quantity, and **glass structure** derived
  from each side's notation (pane count, pane thicknesses, gap/spacer widths).
- Simple GUI (tkinter): two file pickers, a check button, a color-coded results table,
  a summary line, and an export-to-Excel button. UI text in Czech.
- Runs on Windows with plain Python (`python glass_check.py` or double-click).

## Architecture

Single small Python app, three core units plus the GUI:

```
glass_check.py        — tkinter GUI, entry point
invoice_parser.py     — PDF → list[InvoiceItem]
order_parser.py       — XLSX → list[OrderItem]
matcher.py            — (order items, invoice items) → list[MatchResult]
```

### invoice_parser.py

Extracts line items from the PDF using pdfplumber (text-based extraction, reusing the
approach from the existing `pdf_read.py` but with a corrected dimension regex).

Per item:
- position number (`pol.`, 3 digits), position label (`pozice`)
- quantity (`počet kusů`)
- width × height in mm (`rozměry v mm`, pattern `(\d+)\s*x\s*(\d+)`)
- glass composition from the preceding group-header lines
  (e.g. `SGG Climatop XN PXN 4mm / PLC 4mm / PXN 4mm` → panes [4, 4, 4];
  laminated panes like `Stadip 33.2 XN` recorded as `33.2`)
- spacer width from `distanční rámeček` (e.g. `18mm SWS Černý` → 18)

Non-glass lines are skipped: zálohová částka (pol. 990), energetická přirážka (pol. 995),
and any line without a `W x H` dimension.

### order_parser.py

Reads the order workbook with openpyxl, locating columns **by header name** (Šířka, Výška,
Kus, Skladba skla, Typ skla, Objekt, Označení pozice, …) so column order may vary.
Parses `Skladba skla` strings like `4-18-4-18-4` into panes [4, 4, 4] and gaps [18, 18];
laminated tokens like `33.2 XN` are kept as the string `33.2`. Empty trailing rows ignored.

### matcher.py

1. **Exact dimension match** (width == width, height == height) between unmatched order
   and invoice items; quantities aggregated per dimension on both sides before comparison.
2. **Swapped-orientation match** (width == height and vice versa) for remainders — these
   match but produce a *warning*.
3. Remainders become *missing on invoice* (ordered but not invoiced) or *extra on invoice*
   (invoiced but not ordered).

For each matched pair, compare:
- total quantity per dimension
- glass structure: pane count, pane thicknesses (laminated `33.2` on the order side
  matches invoice compositions mentioning `33.2`/`Stadip`), gap widths vs. spacer width

Result statuses: `OK`, `WARNING` (swapped orientation, quantity mismatch, or type
mismatch — with a human-readable Czech description of what differs), `MISSING`,
`EXTRA`. If a skladba string on either side cannot be parsed, the type check for that
item degrades to a side-by-side display (no false mismatch).

### glass_check.py (GUI)

tkinter window:
- two file pickers (PDF invoice, XLSX order) with the chosen paths displayed
- "Zkontrolovat" button → runs parsers + matcher
- results table (ttk.Treeview) with one row per result, color-coded:
  green = OK, orange = WARNING, red = MISSING/EXTRA
- summary label, e.g. "23 z 25 položek v pořádku, 2 problémy"
- "Uložit report" button → writes the results to an Excel file via openpyxl

## Error handling

- If the PDF parses to **zero items**, report "formát faktury nebyl rozpoznán" instead of
  marking every order row missing. Same for an Excel file without the expected headers.
- Unparseable composition strings degrade to visual side-by-side, never a false mismatch.
- Parser exceptions surface as an error dialog with the message, not a crash.

## Dependencies

`pdfplumber`, `openpyxl`, `pytest` (dev). tkinter ships with Python. Declared in
`pyproject.toml`.

## Testing

pytest unit tests:
- **invoice_parser**: parses `faktura_sklo.pdf` fixture → exactly 25 items with known
  spot-checked values (e.g. pol. 001: qty 6, 1346×975, spacer 16; pol. 018: qty 6,
  634×1245); pol. 990/995 excluded.
- **order_parser**: parses the sample XLSX → 11 rows with known spot-checked values;
  skladba `4-18-4-18-4` → panes/gaps; `33.2 XN-16-4-16-6 XN` handled.
- **matcher**: synthetic cases — exact match, swapped dims, wrong quantity, wrong
  skladba, missing item, extra item, unparseable skladba.

GUI is kept thin (no logic beyond wiring) and verified manually.
