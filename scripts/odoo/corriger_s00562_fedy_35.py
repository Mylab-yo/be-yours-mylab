"""Correctif S00562 (FEDY BOUTIQUE) : shampoing purifiant 48 -> 35.

Contexte : BL MYVO/OUT/00138 (done) a livre 35 shampoing (CORRECT).
Le reliquat MYVO/OUT/00195 (13 shampoing) est EN TROP -> a annuler.
La ligne SO passe de 48 -> 35.
FACTURE NON TOUCHEE (avoir a faire manuellement plus tard : 13 x 5.6 = 87.36 TTC).

Idempotent : ne fait rien si deja dans l'etat cible.
"""
from _client import execute, search_read, write

BACKORDER = "MYVO/OUT/00195"
SO_NAME = "S00562"
SHAMPOING_HANDLE = "shampoing-purifiant-200-ml"
QTE_CIBLE = 35.0

# --- 1. Annuler le reliquat des 13 en trop ---
bo = search_read("stock.picking", [("name", "=", BACKORDER)], ["id", "name", "state"])
if not bo:
    raise SystemExit(f"Reliquat {BACKORDER} introuvable")
bo = bo[0]
print(f"[reliquat] {bo['name']} (id={bo['id']}) state={bo['state']}")
if bo["state"] == "cancel":
    print("  -> deja annule, rien a faire")
elif bo["state"] == "done":
    raise SystemExit("  !! reliquat DEJA VALIDE (done) : les 13 sont partis, STOP -> revoir avec Yoann")
else:
    execute("stock.picking", "action_cancel", [[bo["id"]]])
    after = search_read("stock.picking", [("id", "=", bo["id"])], ["state"])[0]
    print(f"  -> action_cancel appele. Nouvel etat = {after['state']}")

# --- 2. Ramener la ligne SO shampoing de 48 -> 35 ---
so = search_read("sale.order", [("name", "=", SO_NAME)], ["id", "name"])
if not so:
    raise SystemExit(f"SO {SO_NAME} introuvable")
SID = so[0]["id"]
lines = search_read("sale.order.line", [("order_id", "=", SID)],
                    ["id", "product_id", "product_uom_qty", "qty_delivered", "qty_invoiced"])
target = None
for l in lines:
    if l.get("product_id") and SHAMPOING_HANDLE in (l["product_id"][1] or ""):
        target = l
        break
if not target:
    raise SystemExit(f"Ligne shampoing ({SHAMPOING_HANDLE}) introuvable sur {SO_NAME}")

print(f"\n[SO ligne] SOL {target['id']} | cmd={target['product_uom_qty']} "
      f"livr={target['qty_delivered']} fact={target['qty_invoiced']}")
if target["product_uom_qty"] == QTE_CIBLE:
    print(f"  -> deja a {QTE_CIBLE}, rien a faire")
else:
    write("sale.order.line", [target["id"]], {"product_uom_qty": QTE_CIBLE})
    after = search_read("sale.order.line", [("id", "=", target["id"])],
                        ["product_uom_qty", "qty_delivered", "qty_invoiced"])[0]
    print(f"  -> ecrit. cmd={after['product_uom_qty']} livr={after['qty_delivered']} "
          f"fact={after['qty_invoiced']}")

# --- 3. Etat final SO ---
sof = search_read("sale.order", [("id", "=", SID)], ["name", "invoice_status", "amount_total"])[0]
print(f"\n[SO final] {sof['name']} invoice_status={sof['invoice_status']} total={sof['amount_total']}")
print("\n>>> Facture FAC/2026/00117 NON modifiee. Avoir 13 u. (87,36 TTC) a faire manuellement.")
