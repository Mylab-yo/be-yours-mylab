"""Adapte le corps du template d'expedition id=27 : complet / partiel / complement.
Idempotent : ne re-patche pas si deja fait."""
from scripts.odoo._client import search_read, write

TEMPLATE_ID = 27
OLD = "Bonne nouvelle ! Votre commande a été expédiée."
NEW = ("Bonne nouvelle ! "
       "<t t-if=\"object.backorder_id\">Le complément de votre commande a bien été expédié.</t>"
       "<t t-elif=\"object.backorder_ids\">Une partie de votre commande a été expédiée ; "
       "le reste vous sera envoyé dès réception du stock.</t>"
       "<t t-else=\"\">Votre commande a bien été expédiée.</t>")


def main():
    body = search_read("mail.template", [("id", "=", TEMPLATE_ID)], ["body_html"])[0]["body_html"]
    if "object.backorder_id" in body:
        print("Déjà patché -> no-op.")
        return
    assert OLD in body, "Ancre introuvable dans le body du template 27"
    write("mail.template", [TEMPLATE_ID], {"body_html": body.replace(OLD, NEW, 1)})
    after = search_read("mail.template", [("id", "=", TEMPLATE_ID)], ["body_html"])[0]["body_html"]
    assert "object.backorder_ids" in after and OLD not in after, "Patch non appliqué"
    print("OK -> body template 27 patché (complet/partiel/complément).")


if __name__ == "__main__":
    main()
