"""Reset SO S00418 (LA TRESSE PARISIENNE) to a clean state.

Steps:
  1. Reverse invoice FAC/2026/00004 (cancel + auto-reconcile credit note)
  2. Cancel confirmed pickings MYVO/OUT/00038, MYVO/OUT/00040
  3. Return done pickings MYVO/OUT/00039 + MYVO/OUT/00008 (validate IN)
  4. Unlock SO S00418

Idempotent: re-running skips already-done steps.
After this script, manually in Odoo UI:
  - Go to SO S00418 -> Create Delivery -> Repartir en cartons
"""
from scripts.odoo._client import search_read, execute, create, write

SO_ID = 385
INV_ID = 210
PICK_CONFIRMED = [(47, "MYVO/OUT/00038"), (51, "MYVO/OUT/00040")]
PICK_DONE_TO_RETURN = [(50, "MYVO/OUT/00039"), (8, "MYVO/OUT/00008")]
REASON = "Reinitialisation BL — repartir d'un colisage propre (erreurs en cascade)"
REVERSAL_DATE = "2026-05-05"


def step1_reverse_invoice():
    print("\n=== STEP 1: Reverse invoice FAC/2026/00004 ===")
    inv = search_read("account.move", [("id", "=", INV_ID)],
                      ["id", "name", "state", "payment_state", "reversal_move_ids"])[0]
    print(f"  current: state={inv['state']}  payment_state={inv['payment_state']}  reversal_move_ids={inv['reversal_move_ids']}")

    # Get or create credit note
    if inv['reversal_move_ids']:
        credit_note_id = inv['reversal_move_ids'][0]
        print(f"  Avoir deja cree: id={credit_note_id}")
    else:
        if inv['state'] != 'posted':
            print(f"  -> SKIP (facture non posted)")
            return
        inv_full = search_read("account.move", [("id", "=", INV_ID)], ["journal_id"])[0]
        wizard_vals = {
            "move_ids": [(6, 0, [INV_ID])],
            "date": REVERSAL_DATE,
            "reason": REASON,
            "journal_id": inv_full['journal_id'][0],
        }
        ctx = {"active_model": "account.move", "active_ids": [INV_ID], "active_id": INV_ID}
        wiz_id = execute("account.move.reversal", "create", [wizard_vals], {"context": ctx})
        result = execute("account.move.reversal", "reverse_moves",
                         [[wiz_id]], {"context": ctx})
        credit_note_id = result.get("res_id")
        print(f"  Avoir cree: id={credit_note_id}")

    # Post the credit note if still draft
    cn = search_read("account.move", [("id", "=", credit_note_id)],
                     ["name", "state", "payment_state"])[0]
    print(f"  Avoir {cn['name']}: state={cn['state']}  payment_state={cn['payment_state']}")
    if cn['state'] == 'draft':
        execute("account.move", "action_post", [[credit_note_id]])
        cn = search_read("account.move", [("id", "=", credit_note_id)],
                         ["state", "payment_state"])[0]
        print(f"  -> posted: state={cn['state']}  payment_state={cn['payment_state']}")

    # Reconcile invoice with credit note (manual: collect receivable lines, reconcile)
    inv_check = search_read("account.move", [("id", "=", INV_ID)],
                            ["payment_state"])[0]
    if inv_check['payment_state'] == 'paid':
        print(f"  Reconciliation OK (facture deja paid)")
    else:
        recv_lines = search_read("account.move.line",
            [("move_id", "in", [INV_ID, credit_note_id]),
             ("account_type", "=", "asset_receivable"),
             ("reconciled", "=", False)],
            ["id", "move_id", "balance"])
        line_ids = [l['id'] for l in recv_lines]
        print(f"  Reconcile receivable lines: {line_ids}")
        if line_ids:
            execute("account.move.line", "reconcile", [line_ids])
        inv_after = search_read("account.move", [("id", "=", INV_ID)],
                                ["state", "payment_state"])[0]
        cn_after = search_read("account.move", [("id", "=", credit_note_id)],
                               ["state", "payment_state"])[0]
        print(f"  AFTER: invoice payment_state={inv_after['payment_state']}, credit_note payment_state={cn_after['payment_state']}")

    inv_after = search_read("account.move", [("id", "=", INV_ID)],
                            ["state", "payment_state", "reversal_move_ids"])[0]
    print(f"  AFTER: state={inv_after['state']}  payment_state={inv_after['payment_state']}")
    print(f"  Avoir(s): {inv_after['reversal_move_ids']}")


def step2_cancel_confirmed():
    print("\n=== STEP 2: Cancel confirmed pickings ===")
    for pid, name in PICK_CONFIRMED:
        p = search_read("stock.picking", [("id", "=", pid)], ["state"])[0]
        if p['state'] == 'cancel':
            print(f"  {name} -> SKIP (deja cancel)")
            continue
        execute("stock.picking", "action_cancel", [[pid]])
        p_after = search_read("stock.picking", [("id", "=", pid)], ["state"])[0]
        print(f"  {name}: {p['state']} -> {p_after['state']}")


def step3_return_done():
    print("\n=== STEP 3: Return done pickings + validate IN ===")
    for pid, name in PICK_DONE_TO_RETURN:
        p = search_read("stock.picking", [("id", "=", pid)], ["state"])[0]
        print(f"\n  --- {name} (state={p['state']}) ---")

        if p['state'] != 'done':
            print(f"  SKIP (state != done)")
            continue

        # Idempotence: existing done return ?
        existing = search_read("stock.picking",
            [("origin", "=", f"Retour de {name}"), ("state", "=", "done")],
            ["id", "name"])
        if existing:
            print(f"  SKIP (retour deja done: {existing})")
            continue

        # Build product_return_moves manually from picking's stock.move
        moves = search_read("stock.move", [("picking_id", "=", pid)],
            ["id", "product_id", "product_uom_qty", "quantity", "product_uom"])
        return_lines = []
        for m in moves:
            qty = m.get('quantity') or m.get('product_uom_qty') or 0
            if qty > 0:
                return_lines.append((0, 0, {
                    "product_id": m['product_id'][0],
                    "quantity": qty,
                    "move_id": m['id'],
                    "uom_id": m['product_uom'][0],
                    "to_refund": True,
                }))
        print(f"    return_lines built: {len(return_lines)} lines")

        ctx = {"active_id": pid, "active_ids": [pid], "active_model": "stock.picking"}
        wiz_vals = {
            "picking_id": pid,
            "product_return_moves": return_lines,
        }
        wiz_id = execute("stock.return.picking", "create", [wiz_vals], {"context": ctx})
        print(f"    Wizard #{wiz_id}")

        # Trigger return creation
        result = execute("stock.return.picking", "action_create_returns",
                         [[wiz_id]], {"context": ctx})
        print(f"    action_create_returns -> {result}")

        # Find new picking id
        new_pid = None
        if isinstance(result, dict):
            new_pid = result.get("res_id") or (result.get("domain", [{}])[0][2][0] if result.get("domain") else None)
        if not new_pid:
            recent = search_read("stock.picking",
                [("origin", "=", f"Retour de {name}")],
                ["id", "name", "state", "create_date"],
                limit=10)
            recent_sorted = sorted(recent, key=lambda x: x.get('create_date') or '', reverse=True)
            for r in recent_sorted:
                if r['state'] != 'cancel':
                    new_pid = r['id']
                    print(f"    Found new return via search: {r['name']} (id={new_pid}, state={r['state']})")
                    break

        if not new_pid:
            print(f"    !! No new picking found, abort this step")
            continue

        # Validate the return
        new_p = search_read("stock.picking", [("id", "=", new_pid)],
                            ["name", "state", "move_line_ids"])[0]
        if new_p['state'] == 'done':
            print(f"    {new_p['name']} deja done, skip validation")
            continue

        # Set quantities on move lines
        for ml in search_read("stock.move.line", [("id", "in", new_p['move_line_ids'])],
                              ["id", "quantity", "move_id"]):
            if ml['quantity'] == 0 and ml.get('move_id'):
                move = search_read("stock.move", [("id", "=", ml['move_id'][0])],
                                   ["product_uom_qty"])[0]
                write("stock.move.line", [ml['id']], {"quantity": move['product_uom_qty']})

        try:
            execute("stock.picking", "button_validate", [[new_pid]],
                    {"context": {"skip_backorder": True, "skip_sms": True}})
        except Exception as e:
            print(f"    button_validate raised: {e}")

        new_p_after = search_read("stock.picking", [("id", "=", new_pid)], ["state"])[0]
        print(f"    {new_p['name']}: {new_p['state']} -> {new_p_after['state']}")


def step4_unlock_so():
    print("\n=== STEP 4: Unlock SO S00418 ===")
    so = search_read("sale.order", [("id", "=", SO_ID)], ["name", "state", "locked"])[0]
    print(f"  current: state={so['state']}  locked={so['locked']}")
    if so['locked']:
        # Try action_unlock first (preferred), fallback to direct write
        try:
            execute("sale.order", "action_unlock", [[SO_ID]])
        except Exception:
            write("sale.order", [SO_ID], {"locked": False})
        so_after = search_read("sale.order", [("id", "=", SO_ID)], ["locked"])[0]
        print(f"  locked -> {so_after['locked']}")
    else:
        print(f"  SKIP (deja deverrouille)")


if __name__ == "__main__":
    step1_reverse_invoice()
    step2_cancel_confirmed()
    step3_return_done()
    step4_unlock_so()
    print("\n=== DONE ===")
    print("Etape suivante MANUELLE dans l'UI Odoo:")
    print(f"  1. Aller sur SO S00418 (id={SO_ID})")
    print("  2. Cliquer 'Creer livraison' / 'Verifier la disponibilite'")
    print("  3. Sur le nouveau picking, cliquer 'Repartir en cartons'")
