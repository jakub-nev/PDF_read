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

# Compile regex at module level for parse_skladba
_NUM_RE = re.compile(r"(\d+(?:[.,]\d+)?)")


def _to_int(value: object, default: int = 1) -> int:
    """Safely convert a cell value to int, defaulting only when truly empty/None."""
    if value is None or str(value).strip() == "":
        return default
    return int(float(str(value)))


def parse_skladba(s: object) -> tuple[list[float] | None, list[float] | None]:
    """'4-18-4-18-4' -> ([4,4,4], [18,18]); '33.2 XN-16-4-16-6 XN' -> ([33.2,4,6], [16,16]).

    Returns (None, None) when the string cannot be interpreted as an
    alternating pane/gap sequence (the caller then degrades to a
    side-by-side display instead of reporting a false mismatch).
    """
    tokens = [t.strip() for t in str(s or "").split("-")]
    values: list[float] = []
    for t in tokens:
        m = _NUM_RE.match(t)
        if not m:
            return None, None
        values.append(float(m.group(1).replace(",", ".")))
    if len(values) % 2 == 0:  # alternating glass-gap-glass... is always odd
        return None, None
    return values[0::2], values[1::2]


def _column_matches(name: str, prefix: str) -> bool:
    """Check if normalized column name matches prefix as a whole word."""
    return name == prefix or name.startswith(prefix + " ") or name.startswith(prefix + "(")


def parse_order(path: str | Path) -> list[OrderItem]:
    wb = openpyxl.load_workbook(path, data_only=True)
    try:
        ws = wb.worksheets[0]
        rows = ws.iter_rows(values_only=True)
        header = next(rows, None) or ()

        col_idx: dict[str, int] = {}
        for i, cell in enumerate(header):
            name = _norm(cell)
            for prefix, attr in _COLUMNS.items():
                if _column_matches(name, prefix) and attr not in col_idx:
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
                width=_to_int(w),
                height=_to_int(h),
                quantity=_to_int(get(row, "quantity"), default=1),
                skladba_raw=skladba_raw,
                typ=str(get(row, "typ") or "").strip(),
                panes=panes,
                gaps=gaps,
            ))
        return items
    finally:
        wb.close()
