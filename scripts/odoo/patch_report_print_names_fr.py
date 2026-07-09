"""Patch print_report_name on key Odoo reports to format:
    {num} - {client} - {type}

with French type labels :
- 412 PDF Quote                -> Devis / Bon de commande
- 413 PRO-FORMA                -> PRO-FORMA
- 449 Quotation / Order (raw)  -> Devis / Bon de commande
- 775 BL MyLab (custom)        -> Bon de livraison
- 507 Packages                 -> Colisage
- 325 Invoice PDF              -> Facture / Avoir
- 327 PDF without Payment      -> Facture / Avoir

Set DRY_RUN=False to apply.
"""
from scripts.odoo._client import search_read, write

DRY_RUN = False  # APPLIED 2026-06-09

# Map report id -> new print_report_name Python expression
PATCHES = {
    # 412 PDF Quote (sale order)
    412: (
        "PDF Quote",
        "'%s - %s - %s' % ("
        "object.name, "
        "(object.partner_id.name or '').replace('/', '-'), "
        "(object.state in ('draft', 'sent') and 'Devis' or 'Bon de commande')"
        ")",
    ),
    # 413 PRO-FORMA
    413: (
        "PRO-FORMA Invoice",
        "'%s - %s - PRO-FORMA' % ("
        "object.name, "
        "(object.partner_id.name or '').replace('/', '-')"
        ")",
    ),
    # 449 Quotation / Order (raw)
    449: (
        "Quotation / Order (raw)",
        "'%s - %s - %s' % ("
        "object.name, "
        "(object.partner_id.name or '').replace('/', '-'), "
        "(object.state in ('draft', 'sent') and 'Devis' or 'Bon de commande')"
        ")",
    ),
    # 775 BL MyLab (custom mylab.report_deliveryslip)
    775: (
        "Bon de livraison MyLab",
        "'%s - %s - Bon de livraison' % ("
        "object.name.replace('/', '-'), "
        "(object.partner_id.name or '').replace('/', '-')"
        ")",
    ),
    # 507 Packages (colisage)
    507: (
        "Packages (colisage)",
        "'%s - %s - Colisage' % ("
        "object.name.replace('/', '-'), "
        "(object.partner_id.name or '').replace('/', '-')"
        ")",
    ),
    # 325 Invoice PDF (with payments)
    325: (
        "Invoice PDF",
        "'%s - %s - %s' % ("
        "(object.name or '').replace('/', '-'), "
        "(object.partner_id.name or '').replace('/', '-'), "
        "(object.move_type == 'out_refund' and 'Avoir' "
        "or object.move_type == 'in_refund' and 'Avoir fournisseur' "
        "or object.move_type == 'in_invoice' and 'Facture fournisseur' "
        "or 'Facture')"
        ")",
    ),
    # 327 Invoice PDF without Payment
    327: (
        "PDF without Payment",
        "'%s - %s - %s' % ("
        "(object.name or '').replace('/', '-'), "
        "(object.partner_id.name or '').replace('/', '-'), "
        "(object.move_type == 'out_refund' and 'Avoir' "
        "or object.move_type == 'in_refund' and 'Avoir fournisseur' "
        "or object.move_type == 'in_invoice' and 'Facture fournisseur' "
        "or 'Facture')"
        ")",
    ),
}


def main():
    print("=== Patching ir.actions.report print_report_name ===\n")
    print(f"DRY_RUN = {DRY_RUN}\n")

    # Load current state
    ids = list(PATCHES.keys())
    reports = search_read(
        "ir.actions.report",
        [("id", "in", ids)],
        ["id", "name", "report_name", "print_report_name"],
    )
    current = {r["id"]: r for r in reports}

    for rid, (label, new_expr) in PATCHES.items():
        r = current.get(rid)
        if not r:
            print(f"  ID {rid} ({label}) : NOT FOUND, skip")
            continue
        print(f"--- ID {rid} : {label} ({r['report_name']}) ---")
        print(f"  BEFORE : {r['print_report_name']!r}")
        print(f"  AFTER  : {new_expr!r}")
        if not DRY_RUN:
            write("ir.actions.report", [rid], {"print_report_name": new_expr})
            print(f"  -> Updated")
        print()

    if DRY_RUN:
        print("[DRY_RUN=True] No changes applied. Set DRY_RUN=False to apply.")
    else:
        # Verify
        print("=== Verification ===")
        verify = search_read(
            "ir.actions.report",
            [("id", "in", ids)],
            ["id", "print_report_name"],
        )
        for r in verify:
            ok = r["print_report_name"] == PATCHES[r["id"]][1]
            mark = "OK" if ok else "MISMATCH"
            print(f"  ID {r['id']} : {mark}")


if __name__ == "__main__":
    main()
