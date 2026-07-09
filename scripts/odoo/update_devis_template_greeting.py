"""Met a jour le body du template 'MYLAB - Envoi Devis' (id=34).

- "Merci pour votre interet pour MY.LAB !" -> "Merci pour votre commande !"
- Intro: ajoute "a valider pour lancer sa preparation."
- Ajoute une ligne "prochaines etapes" apres les moyens de paiement.

Idempotent : si "Merci pour votre commande" est deja present, ne fait rien.
"""
from scripts.odoo._client import search_read, write

TEMPLATE_ID = 34

OLD_INTRO_GREET = "Merci pour votre intérêt pour MY.LAB !"
NEW_INTRO_GREET = "Merci pour votre commande !"

OLD_INTRO_END = " TTC).</p>"
NEW_INTRO_END = " TTC), à valider pour lancer sa préparation.</p>"

NEXT_STEPS_ANCHOR = '<p style="margin: 1rem 0;">Pour toute question'
NEXT_STEPS_BLOCK = (
    '<p style="margin: 0 0 1rem 0;">Dès réception de votre règlement, '
    'nous préparons votre commande et vous tenons informé(e) de son expédition.</p>\n'
    + NEXT_STEPS_ANCHOR
)


def main():
    tmpl = search_read("mail.template", [("id", "=", TEMPLATE_ID)],
                       ["name", "body_html"])[0]
    body = tmpl["body_html"]
    print(f"Template: {tmpl['name']} (id={TEMPLATE_ID}), body len={len(body)}")

    if "Merci pour votre commande" in body:
        print("Deja a jour ('Merci pour votre commande' present) -> no-op.")
        return

    # 1) Greeting
    assert OLD_INTRO_GREET in body, "Ancre intro greeting introuvable"
    body = body.replace(OLD_INTRO_GREET, NEW_INTRO_GREET, 1)

    # 2) Fin d'intro -> "a valider..."
    assert body.count(OLD_INTRO_END) == 1, f"Ancre fin intro non unique: {body.count(OLD_INTRO_END)}"
    body = body.replace(OLD_INTRO_END, NEW_INTRO_END, 1)

    # 3) Ligne prochaines etapes
    assert body.count(NEXT_STEPS_ANCHOR) == 1, "Ancre 'Pour toute question' non unique"
    body = body.replace(NEXT_STEPS_ANCHOR, NEXT_STEPS_BLOCK, 1)

    write("mail.template", [TEMPLATE_ID], {"body_html": body})
    print(f"OK -> body ecrit, nouvelle len={len(body)}")

    # Verif relecture
    after = search_read("mail.template", [("id", "=", TEMPLATE_ID)], ["body_html"])[0]["body_html"]
    checks = {
        "Merci pour votre commande !": NEW_INTRO_GREET in after,
        "a valider pour lancer sa preparation": "lancer sa préparation" in after,
        "ligne prochaines etapes": "nous préparons votre commande" in after,
        "ancien greeting absent": OLD_INTRO_GREET not in after,
    }
    for label, ok in checks.items():
        print(f"  [{'OK' if ok else 'KO'}] {label}")
    assert all(checks.values()), "Verification post-write echouee"


if __name__ == "__main__":
    main()
