"""Notif REELLE client pour S00533 : ecrit les 2 trackings sur le BL parti (00089)
puis envoie le mail d'expedition au client JOSLAYHAIR.

Securite : rend d'abord le mail (sans envoyer), verifie que les 2 liens DPD
cliquables sont valides, et n'envoie au client QUE si c'est le cas.
ATTENTION : si la verif passe, le mail part REELLEMENT au client."""
from scripts.odoo._client import search_read, execute

PID = 105  # MYVO/OUT/00089 (partie expediee de S00533)
TRACKS = ["10843001262058", "10843001262059"]
TEMPLATE_ID = 27

pk = search_read("stock.picking", [("id", "=", PID)],
                 ["name", "partner_id", "state", "backorder_ids"])[0]
partner = search_read("res.partner", [("id", "=", pk["partner_id"][0])],
                      ["name", "email"])[0]
print(f"BL {pk['name']} state={pk['state']} | client={partner['name']} | email={partner.get('email')!r}")
print(f"backorder_ids={pk['backorder_ids']} (non vide => mail 'une partie expediee')")
assert partner.get("email"), "Client sans email -> ABORT"

# 1) Ecrit les 2 trackings (permanent, separes par virgule)
execute("stock.picking", "write", [[PID], {"carrier_tracking_ref": ",".join(TRACKS)}])
print(f"Tracking ecrit: {','.join(TRACKS)}")

# 2) Rend le mail SANS envoyer, verifie les 2 liens DPD
mid = execute("mail.template", "send_mail", [TEMPLATE_ID, PID], {"force_send": False})
body = search_read("mail.mail", [("id", "=", mid)], ["body_html"])[0]["body_html"]
ok = all(f"dpd.fr/trace/{t}" in body for t in TRACKS)
partial_ok = "Une partie de votre commande" in body
print(f"2 liens DPD valides: {ok} | wording partiel present: {partial_ok}")
execute("mail.mail", "unlink", [[mid]])  # supprime le rendu de verif

if not (ok and partial_ok):
    print("KO -> liens ou wording incorrects. Mail NON envoye au client. Tracking laisse en place.")
    raise SystemExit(1)

# 3) Envoi REEL au client
real = execute("mail.template", "send_mail", [TEMPLATE_ID, PID], {"force_send": True})
print(f"-> ENVOYE AU CLIENT {partner['email']} (mail#{real}). Wording: une partie expediee + 2 liens DPD.")
