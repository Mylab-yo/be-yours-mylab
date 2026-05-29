"""Setup Phase 2 : action serveur Odoo "Envoyer mandat de representation".

Cree :
  1. Un mail.activity.type "Envoyer mandat de representation"
  2. Une ir.actions.server (Python Code) qui filtre les factures eligibles
     et cree une activite de ce type
  3. Binding sur account.move pour que l'action apparaisse dans le menu Action
     de la fiche facture

Idempotent : si l'activity type ou l'action existent deja, ils sont mis a jour.

Run : python -m scripts.odoo.setup_phase2_action_mandat
"""
import sys
from scripts.odoo._client import search_read, create, write, execute

PRODUCT_DOSSIER_ID = 2313
ACTIVITY_TYPE_NAME = "Envoyer mandat de representation"
SERVER_ACTION_NAME = "Envoyer mandat de representation au client"

# === 1. mail.activity.type ===
print("Step 1: mail.activity.type")
existing = search_read("mail.activity.type", [("name", "=", ACTIVITY_TYPE_NAME)], ["id"])
if existing:
    activity_type_id = existing[0]["id"]
    print(f"  -> existe deja (id={activity_type_id})")
else:
    activity_type_id = create("mail.activity.type", {
        "name": ACTIVITY_TYPE_NAME,
        "summary": "Mandat de Personne Responsable a envoyer au client",
        "icon": "fa-file-text-o",
        "delay_count": 0,
        "delay_unit": "days",
        "delay_from": "current_date",
        "res_model": "account.move",
        "chaining_type": "suggest",
    })
    print(f"  + cree (id={activity_type_id})")

# === 2. ir.model.id de account.move ===
move_model = search_read("ir.model", [("model", "=", "account.move")], ["id"])
if not move_model:
    print("ERREUR : modele account.move introuvable")
    sys.exit(1)
move_model_id = move_model[0]["id"]

# === 3. ir.actions.server ===
print("\nStep 2: ir.actions.server")

# Python code that runs in the Odoo sandbox when the button is clicked.
# `records` is a recordset of account.move (the selected invoices).
# `env` is the Odoo Environment. `user` is the current user.
SERVER_CODE = f"""# Action: Envoyer mandat de representation
# Filtre les factures eligibles et cree une activite "a envoyer"
# qui sera traitee par le worker local process_mandat_queue.py.
PRODUCT_DOSSIER_ID = {PRODUCT_DOSSIER_ID}
ACTIVITY_TYPE_ID = {activity_type_id}

queued = []
skipped = []

for invoice in records:
    if invoice.move_type not in ('out_invoice', 'out_receipt'):
        skipped.append((invoice.name, 'pas une facture client'))
        continue
    if invoice.state != 'posted':
        skipped.append((invoice.name, 'non validee (state=%s)' % invoice.state))
        continue
    if invoice.payment_state != 'paid':
        skipped.append((invoice.name, 'non payee (payment_state=%s)' % invoice.payment_state))
        continue
    has_product = any(l.product_id.id == PRODUCT_DOSSIER_ID for l in invoice.invoice_line_ids)
    if not has_product:
        skipped.append((invoice.name, 'pas de dossier cosmeto'))
        continue

    # Idempotence : pas de doublon d'activite active
    existing_act = env['mail.activity'].search([
        ('res_model', '=', 'account.move'),
        ('res_id', '=', invoice.id),
        ('activity_type_id', '=', ACTIVITY_TYPE_ID),
    ], limit=1)
    if existing_act:
        skipped.append((invoice.name, 'activite deja en attente'))
        continue

    env['mail.activity'].create({{
        'res_model': 'account.move',
        'res_id': invoice.id,
        'res_model_id': {move_model_id},
        'activity_type_id': ACTIVITY_TYPE_ID,
        'summary': 'Mandat de Personne Responsable a envoyer au client',
        'note': '<p>Le client a paye le dossier cosmetologique. '
                'Le worker local process_mandat_queue.py va envoyer '
                'automatiquement le mandat de representation au client.</p>',
        'user_id': user.id,
        'date_deadline': datetime.date.today(),
    }})
    invoice.message_post(
        body='<p><strong>Mandat de representation</strong> place en file d\\'envoi. '
             'Sera envoye au client par le worker automatique.</p>',
        message_type='comment',
        subtype_xmlid='mail.mt_note',
    )
    queued.append(invoice.name)

# Notification utilisateur
if queued and not skipped:
    msg = 'Mandat(s) en file d\\'envoi : %s' % ', '.join(queued)
    msg_type = 'success'
elif queued and skipped:
    msg = 'En file: %s | Ignore: %s' % (
        ', '.join(queued),
        ', '.join('%s (%s)' % (n, r) for n, r in skipped),
    )
    msg_type = 'warning'
else:
    msg = 'Aucune facture eligible. Ignore: %s' % (
        ', '.join('%s (%s)' % (n, r) for n, r in skipped) or '(aucune selection)'
    )
    msg_type = 'danger'

action = {{
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {{
        'title': 'Mandat de representation',
        'message': msg,
        'type': msg_type,
        'sticky': False,
    }},
}}
"""

existing_action = search_read(
    "ir.actions.server",
    [("name", "=", SERVER_ACTION_NAME), ("model_id", "=", move_model_id)],
    ["id"],
)
action_vals = {
    "name": SERVER_ACTION_NAME,
    "model_id": move_model_id,
    "state": "code",
    "code": SERVER_CODE,
    "binding_model_id": move_model_id,
    "binding_view_types": "form,list",
}
if existing_action:
    server_action_id = existing_action[0]["id"]
    write("ir.actions.server", [server_action_id], action_vals)
    print(f"  -> mise a jour (id={server_action_id})")
else:
    server_action_id = create("ir.actions.server", action_vals)
    print(f"  + creation (id={server_action_id})")

print()
print("=" * 60)
print("OK Phase 2 setup terminee")
print(f"   - mail.activity.type id={activity_type_id}")
print(f"   - ir.actions.server id={server_action_id}")
print()
print("Comment utiliser dans Odoo :")
print("   1. Ouvre une fiche facture (account.move)")
print("   2. Menu 'Action' en haut a droite -> 'Envoyer mandat de representation au client'")
print("   3. Une activite est creee, visible dans le bandeau du dessus")
print()
print("Pour envoyer reellement, lance le worker :")
print("   python -m scripts.odoo.process_mandat_queue")
