"""Aligne le body du template d'expedition id=27 sur les 2 langues (en_US + fr_FR).

Le champ body_html est traduisible : la version fr_FR divergeait (texte 'livree',
sans le conditionnel partiel/complement). On ecrit la version en_US (correcte :
'Bonne nouvelle ! expediee/partie/complement' + tracking) dans les DEUX langues.
Idempotent."""
from scripts.odoo._client import execute

TEMPLATE_ID = 27

en = execute("mail.template", "read", [[TEMPLATE_ID], ["body_html"]],
             {"context": {"lang": "en_US"}})[0]["body_html"]
assert "Bonne nouvelle" in en and "backorder_id" in en, \
    "Le body en_US ne contient pas la version attendue (expediee + conditionnel)"

for lang in ("fr_FR", "en_US"):
    execute("mail.template", "write", [[TEMPLATE_ID], {"body_html": en}],
            {"context": {"lang": lang}})

print("Verif :")
for lang in ("en_US", "fr_FR"):
    b = execute("mail.template", "read", [[TEMPLATE_ID], ["body_html"]],
                {"context": {"lang": lang}})[0]["body_html"]
    print(f"  body[{lang}] len={len(b)} | expédiée={'expédié' in b} "
          f"| conditionnel={'backorder_id' in b} | plus de 'livrée'={'livré' not in b}")
