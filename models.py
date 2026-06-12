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
