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
