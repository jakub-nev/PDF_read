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
