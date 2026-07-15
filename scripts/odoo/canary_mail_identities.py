"""Canari — envoie 1 devis + 1 facture + 1 relance de test vers yoann@mylab-shop.com.

Cree un partenaire et des brouillons dedies, envoie, puis nettoie. Aucun client reel
n'est destinataire : le partenaire de test porte l'adresse yoann@mylab-shop.com.
La facture reste en brouillon -> aucun numero de sequence consomme.

Le but est de comparer ce qu'Odoo CROIT envoyer (mail.mail.email_from) a ce que Gmail
LIVRE reellement (en-tete From recu). Gmail reecrit silencieusement le From si l'alias
n'est pas un « send as » verifie : seul l'en-tete recu fait foi.

Usage :
    python canary_mail_identities.py           # envoie puis nettoie
    python canary_mail_identities.py --keep    # laisse les enregistrements pour inspection
"""
import argparse
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from _client import execute, search_read, create, unlink

TEST_EMAIL = "yoann@mylab-shop.com"
TEST_PARTNER_NAME = "ZZ Canari Identites Mail — NE PAS UTILISER"
COMPANY_ID = 3

# (tpl_id, libelle, identite attendue dans le From recu)
SENDS = [
    (34, "Devis", "contact@mylab-shop.com"),
    (18, "Facture", "comptabilite@mylab-shop.com"),
    (37, "Relance facture L1", "comptabilite@mylab-shop.com"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="ne pas supprimer les enregistrements")
    args = ap.parse_args()

    created = {"partner": [], "order": [], "move": []}
    try:
        partner_id = create("res.partner", {
            "name": TEST_PARTNER_NAME,
            "email": TEST_EMAIL,
            "company_id": COMPANY_ID,
        })
        created["partner"].append(partner_id)
        print(f"Partenaire de test : {partner_id} <{TEST_EMAIL}>")

        product = search_read("product.product", [("sale_ok", "=", True)], ["id", "name"], limit=1)
        if not product:
            print("ABANDON — aucun produit vendable trouve")
            return 1
        pid = product[0]["id"]

        order_id = create("sale.order", {
            "partner_id": partner_id,
            "company_id": COMPANY_ID,
            "order_line": [(0, 0, {"product_id": pid, "product_uom_qty": 1})],
        })
        created["order"].append(order_id)
        print(f"Devis de test : {order_id}")

        move_id = create("account.move", {
            "partner_id": partner_id,
            "company_id": COMPANY_ID,
            "move_type": "out_invoice",
            "invoice_line_ids": [(0, 0, {"product_id": pid, "quantity": 1, "price_unit": 10.0})],
        })
        created["move"].append(move_id)
        print(f"Facture de test (brouillon) : {move_id}")

        # Affichage de controle humain (PAS un garde-fou automatique) : ces 3 templates
        # adressent en principe le partenaire du document. On imprime le champ BRUT
        # partner_to/email_to du template (ex. "{{ object.partner_id.id }}") pour verification
        # a l'oeil avant envoi -- le code ne refuse rien, il poursuit vers l'envoi quoi qu'il
        # arrive. Et `read()` renvoie ce champ brut, jamais la valeur RENDUE pour ce document :
        # il ne peut donc pas detecter une resolution vers un tiers. Le controle qui compte est
        # celui de l'en-tete From/To RECU dans Gmail apres envoi (cf. docstring du module).
        for tpl_id, _, _ in SENDS:
            rendered = execute("mail.template", "read", [[tpl_id], ["partner_to", "email_to"]])
            print(f"  garde tpl {tpl_id:>2} partner_to={rendered[0].get('partner_to')!r} "
                  f"email_to={rendered[0].get('email_to')!r}")

        print()
        res_for = {34: order_id, 18: move_id, 37: move_id}
        for tpl_id, libelle, attendu in SENDS:
            mail_id = execute("mail.template", "send_mail", [tpl_id, res_for[tpl_id]],
                              {"force_send": True})
            print(f"  envoye  tpl {tpl_id:>2} {libelle:<20} -> From attendu : {attendu}")
            # Ce qu'Odoo a REELLEMENT pose comme en-tetes (l'intention, pas le resultat).
            # mail.mail peut avoir ete auto-supprime apres envoi (auto_delete).
            try:
                m = search_read("mail.mail", [("id", "=", mail_id)],
                                ["email_from", "email_to", "state", "recipient_ids"])
                if m:
                    print(f"          Odoo a pose  from={m[0].get('email_from')!r}")
                    print(f"                       to={m[0].get('email_to')!r} "
                          f"recipients={m[0].get('recipient_ids')} state={m[0].get('state')!r}")
                else:
                    print(f"          (mail.mail {mail_id} auto-supprime apres envoi)")
            except Exception as exc:
                print(f"          (lecture mail.mail impossible : {exc})")
            time.sleep(2)

        print("\nEnvoi termine. Verifier maintenant les EN-TETES RECUS dans Gmail,")
        print("PAS mail.mail.email_from ci-dessus (qui ne reflete que l'intention).")
        return 0
    finally:
        # Aucun `return` dans ce finally : il avalerait l'exception en cours et
        # ferait sortir le script en code 0 alors que l'envoi a echoue.
        if args.keep:
            print(f"\n--keep : enregistrements conserves {created}")
        else:
            for model, ids in (("account.move", created["move"]),
                               ("sale.order", created["order"]),
                               ("res.partner", created["partner"])):
                for rid in ids:
                    try:
                        unlink(model, [rid])
                        print(f"  supprime {model} {rid}")
                    except Exception as exc:
                        print(f"  ATTENTION — {model} {rid} non supprime : {exc}")


if __name__ == "__main__":
    sys.exit(main())
