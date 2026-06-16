# Code de l'action serveur "Preparer le dispo" (ir.actions.server, state='code').
# Contexte: env, records (stock.picking), model, log, UserError disponibles.

for picking in records:
    if picking.state not in ('confirmed', 'assigned', 'waiting'):
        continue
    # 1. Reserve tout le stock disponible
    picking.action_assign()
    # 2. Pre-remplit "Fait" = reserve (storable) / demande (service/non stocke)
    total = 0.0
    for move in picking.move_ids:
        if move.state in ('done', 'cancel'):
            continue
        if move.product_id.is_storable:
            qty = move.quantity            # reserve par action_assign (0 si rupture)
        else:
            qty = move.product_uom_qty     # service/conso : tout part
        move.write({"quantity": qty, "picked": qty > 0})  # STORE_ATTR interdit en safe_eval
        total += qty
    # 3. Garde-fou : rien dispo
    if total <= 0:
        raise UserError("Aucun stock disponible pour ce bon de livraison - rien a expedier. Reapprovisionnez ou ajustez les quantites manuellement avant de valider.")
