"""Corrige le retour errone S00422 (CENDREE).

Contexte : un retour de la TOTALITE du dernier BL (MYVO/OUT/00185) a ete cree
et valide par erreur -> MYVO/IN/00024 (id 263), to_refund=True :
    - shampoing nourrissant 100ml : 192
    - masque nourrissant 100ml    : 5
    - masque reparateur 100ml     : 89

Cible : seuls 63 shampoing nourrissant 100ml doivent etre retournes. Le reste
reste livre chez CENDREE.

Strategie (annuler + recreer proprement, valide par Yoann) :
  A) Retour inverse de IN/00024 -> OUT 192+5+89 (neutralise l'erreur).
     Livre restaure a 444 / 500 / 494. Stock revient a l'etat d'avant.
  B) Retour correct de OUT/00185 -> IN de 63 shampoing nourrissant seulement.
     Livre nourrissant -> 381. Stock +63.

Verifs bloquantes apres chaque etape. APPLY requis pour valider.
Idempotent : re-executable, saute les etapes deja faites.
"""
import sys
from _client import execute, search_read, write

APPLY = "APPLY" in sys.argv

SO_ID = 389
PICK_ERRONEOUS_IN = 263   # MYVO/IN/00024 (retour errone)
PICK_LAST_OUT = 202       # MYVO/OUT/00185 (dernier BL)
PROD_NOURRISSANT = 2461   # shampoing nourrissant 100ml
MOVE_NOURR_ON_OUT = 873   # move nourrissant sur OUT/00185
RETURN_QTY = 63

# livre attendu par produit (line_id -> label, cible finale)
EXPECTED_FINAL = {401: ("shampoing nourrissant", 381.0),
                  410: ("masque nourrissant", 500.0),
                  406: ("masque reparateur", 494.0)}


def delivered_now():
    lines = search_read("sale.order.line",
                        [("id", "in", list(EXPECTED_FINAL))],
                        ["id", "product_id", "qty_delivered"])
    return {l["id"]: l["qty_delivered"] for l in lines}


def dump_delivered(tag):
    d = delivered_now()
    print(f"  [{tag}] livre : " + " | ".join(
        f"{EXPECTED_FINAL[lid][0]}={d.get(lid)}" for lid in EXPECTED_FINAL))
    return d


def create_return(source_pid, return_lines, label):
    """Cree un retour via stock.return.picking + valide. Retourne new_pid."""
    ctx = {"active_id": source_pid, "active_ids": [source_pid],
           "active_model": "stock.picking"}
    wiz_id = execute("stock.return.picking", "create",
                     [{"picking_id": source_pid,
                       "product_return_moves": return_lines}], {"context": ctx})
    print(f"    wizard #{wiz_id}")
    result = execute("stock.return.picking", "action_create_returns",
                     [[wiz_id]], {"context": ctx})
    new_pid = None
    if isinstance(result, dict):
        new_pid = result.get("res_id")
        if not new_pid and result.get("domain"):
            try:
                new_pid = result["domain"][0][2][0]
            except Exception:
                pass
    if not new_pid:
        raise RuntimeError(f"retour non trouve apres creation ({label})")
    np = search_read("stock.picking", [("id", "=", new_pid)],
                     ["name", "state", "move_line_ids"])[0]
    print(f"    nouveau picking {np['name']} (id={new_pid}) state={np['state']}")

    # renseigne les quantites sur les move lines
    for ml in search_read("stock.move.line",
                          [("id", "in", np["move_line_ids"])],
                          ["id", "quantity", "move_id"]):
        mv = search_read("stock.move", [("id", "=", ml["move_id"][0])],
                         ["product_uom_qty"])[0]
        if ml["quantity"] != mv["product_uom_qty"]:
            write("stock.move.line", [ml["id"]],
                  {"quantity": mv["product_uom_qty"]})
    execute("stock.picking", "button_validate", [[new_pid]],
            {"context": {"skip_backorder": True, "skip_sms": True}})
    after = search_read("stock.picking", [("id", "=", new_pid)], ["name", "state"])[0]
    print(f"    -> {after['name']} valide : state={after['state']}")
    return new_pid


print("=" * 70)
print(f"CORRECTION RETOUR S00422 — mode={'APPLY' if APPLY else 'DRY-RUN'}")
print("=" * 70)
dump_delivered("depart")

# --- deverrouillage SO ---
so = search_read("sale.order", [("id", "=", SO_ID)], ["locked"])[0]
if so["locked"] and APPLY:
    try:
        execute("sale.order", "action_unlock", [[SO_ID]])
    except Exception:
        write("sale.order", [SO_ID], {"locked": False})
    print("  SO deverrouille")

# ============ ETAPE A : neutraliser IN/00024 ============
print("\n--- ETAPE A : annuler le retour errone IN/00024 ---")
existing_rev = search_read("stock.picking",
    [("origin", "=", "Retour de MYVO/IN/00024"), ("state", "=", "done")],
    ["id", "name"])
if existing_rev:
    print(f"  DEJA FAIT : {existing_rev}")
else:
    moves = search_read("stock.move", [("picking_id", "=", PICK_ERRONEOUS_IN)],
                        ["id", "product_id", "quantity", "product_uom"])
    rlines = [(0, 0, {"product_id": m["product_id"][0], "quantity": m["quantity"],
                      "move_id": m["id"], "uom_id": m["product_uom"][0],
                      "to_refund": True}) for m in moves if m["quantity"] > 0]
    print(f"  lignes retour inverse : " +
          ", ".join(f"{m['product_id'][1]}={m['quantity']}" for m in moves))
    if APPLY:
        create_return(PICK_ERRONEOUS_IN, rlines, "reverse IN/00024")
    else:
        print("  (dry-run : pas de creation)")

if APPLY:
    d = dump_delivered("apres A")
    exp_a = {401: 444.0, 410: 500.0, 406: 494.0}
    bad = {lid: (d.get(lid), exp_a[lid]) for lid in exp_a if d.get(lid) != exp_a[lid]}
    if bad:
        print(f"  !! ABORT : livre apres A inattendu : {bad}")
        sys.exit(1)
    print("  OK : livre restaure (erreur neutralisee)")

# ============ ETAPE B : retour correct de 63 nourrissant ============
print("\n--- ETAPE B : retour correct 63 shampoing nourrissant (OUT/00185) ---")
if APPLY:
    d = delivered_now()
    if d.get(401) == 381.0:
        print("  DEJA FAIT (livre nourrissant deja a 381)")
    else:
        mv = search_read("stock.move", [("id", "=", MOVE_NOURR_ON_OUT)],
                         ["product_id", "product_uom"])[0]
        rlines = [(0, 0, {"product_id": PROD_NOURRISSANT, "quantity": RETURN_QTY,
                          "move_id": MOVE_NOURR_ON_OUT, "uom_id": mv["product_uom"][0],
                          "to_refund": True})]
        print(f"  ligne retour : shampoing nourrissant 100ml = {RETURN_QTY}")
        create_return(PICK_LAST_OUT, rlines, "return 63 nourrissant")
else:
    print(f"  (dry-run) creerait un retour de {RETURN_QTY} nourrissant depuis OUT/00185")

# ============ VERIF FINALE ============
if APPLY:
    print("\n--- VERIFICATION FINALE ---")
    d = dump_delivered("final")
    ok = True
    for lid, (label, target) in EXPECTED_FINAL.items():
        got = d.get(lid)
        flag = "OK" if got == target else "!! ECART"
        if got != target:
            ok = False
        print(f"  {label:22s} livre={got}  (cible {target})  {flag}")
    # re-verrouille le SO
    write("sale.order", [SO_ID], {"locked": True})
    print("  SO re-verrouille")
    print("\n" + ("=== SUCCES : retour corrige a 63 nourrissant ===" if ok
                  else "=== ATTENTION : ecarts, verifier manuellement ==="))
else:
    print("\n(DRY-RUN termine — relancer avec 'APPLY' pour executer)")
