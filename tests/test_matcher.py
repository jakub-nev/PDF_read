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


def test_swap_does_not_steal_exact_match():
    # order has both a panel and its transpose; invoice has only the transpose.
    # The exact-dimension order row must claim it (OK); the other is MISSING —
    # the swapped row must not grab the exact row's invoice line first.
    res = match_items([order(830, 1400), order(1400, 830)],
                      [invoice(1400, 830)])
    by_dims = {(r.order_item.width, r.order_item.height): r.status
               for r in res if r.order_item}
    assert by_dims[(1400, 830)] == "OK"
    assert by_dims[(830, 1400)] == "MISSING"


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
