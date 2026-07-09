"""Corrige l'affichage du suivi dans le template 27 : un lien DPD propre PAR colis.

L'ancienne logique (get_multiple_carrier_tracking / carrier_tracking_url) colle les
numeros separes par virgule dans une seule URL cassee. On remplace par un split sur
la virgule -> https://www.dpd.fr/trace/<num> pour chaque colis. Marche pour 1 ou N.
Applique aux 2 langues. Idempotent."""
from scripts.odoo._client import execute

TEMPLATE_ID = 27
NEW_STRONG = ('<strong>'
              '<t t-foreach="object.carrier_tracking_ref.split(\',\')" t-as="ref">'
              '<br/><a t-attf-href="https://www.dpd.fr/trace/{{ ref.strip() }}" '
              'target="_blank" t-out="ref.strip()"/>'
              '</t></strong>')


def patched_body(b):
    if "carrier_tracking_ref.split" in b:
        return None  # deja patche
    i = b.find("Votre num")
    assert i >= 0, "Ancre 'Votre numéro de suivi' introuvable"
    start = b.find("<strong>", i)
    end = b.find("</strong>", start) + len("</strong>")
    assert start > 0 and end > start, "Bloc <strong> tracking introuvable"
    return b[:start] + NEW_STRONG + b[end:]


def main():
    src = execute("mail.template", "read", [[TEMPLATE_ID], ["body_html"]],
                  {"context": {"lang": "en_US"}})[0]["body_html"]
    new = patched_body(src)
    if new is None:
        print("Déjà patché -> no-op.")
        return
    for lang in ("en_US", "fr_FR"):
        execute("mail.template", "write", [[TEMPLATE_ID], {"body_html": new}],
                {"context": {"lang": lang}})
    # verif
    for lang in ("en_US", "fr_FR"):
        b = execute("mail.template", "read", [[TEMPLATE_ID], ["body_html"]],
                    {"context": {"lang": lang}})[0]["body_html"]
        print(f"  body[{lang}] : split present={'carrier_tracking_ref.split' in b} "
              f"| ancienne logique retiree={'get_multiple_carrier_tracking' not in b}")


if __name__ == "__main__":
    main()
