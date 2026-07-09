"""For the 8 already-paid-on-Shopify invoices, check if Odoo already has a
payment (reconciled or not) before we create anything (avoid double payment)."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from _client import search_read

INV = {
    456 - 0: None,  # placeholder
}
# invoice ids by FAC name
fac_names = ["FAC/2026/00096", "FAC/2026/00097", "FAC/2026/00098",
             "FAC/2026/00099", "FAC/2026/00101", "FAC/2026/00102",
             "FAC/2026/00104", "FAC/2026/00107"]
invs = search_read("account.move", [("name", "in", fac_names)],
                   ["id", "name", "partner_id", "amount_total", "amount_residual",
                    "payment_state", "invoice_origin"])

for i in sorted(invs, key=lambda x: x["name"]):
    pid = i["partner_id"][0]
    print(f"\n=== {i['name']} | {i['partner_id'][1]} | "
          f"{i['amount_residual']:.2f}/{i['amount_total']:.2f}€ | {i['payment_state']} ===")

    # commercial partner (payments may be on parent)
    cp = search_read("res.partner", [("id", "=", pid)], ["commercial_partner_id"])
    cpid = cp[0]["commercial_partner_id"][0] if cp and cp[0].get("commercial_partner_id") else pid

    # Any account.payment for this partner not fully reconciled?
    pays = search_read("account.payment",
        [("partner_id", "child_of", cpid),
         ("payment_type", "=", "inbound")],
        ["id", "name", "amount", "state", "journal_id", "is_reconciled",
         "memo", "date", "reconciled_invoice_ids"])
    if pays:
        for p in pays:
            print(f"   PAYMENT {p['name']} {p['amount']}€ {p['journal_id'][1]} "
                  f"reconciled={p['is_reconciled']} memo={p.get('memo')!r} "
                  f"recon_inv={p.get('reconciled_invoice_ids')}")
    else:
        print("   no inbound payment found for this partner")
