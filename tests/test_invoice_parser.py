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
