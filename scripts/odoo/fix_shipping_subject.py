"""Corrige le sujet du template d'expedition id=27.

Le champ subject est TRADUISIBLE : la version fr_FR contenait encore l'ancien
defaut generique '{{ object.company_id.name }} Bon de livraison...' (-> SARL STARTEC).
On aligne en_US ET fr_FR sur un sujet MY.LAB propre, oriente client (n° de commande).
"""
from scripts.odoo._client import execute

NEW = "MY.LAB — Votre commande {{ object.origin or object.name }} a été expédiée"

for lang in ("en_US", "fr_FR"):
    execute("mail.template", "write", [[27], {"subject": NEW}], {"context": {"lang": lang}})

# Verif
for lang in ("en_US", "fr_FR"):
    v = execute("mail.template", "read", [[27], ["subject"]], {"context": {"lang": lang}})
    print(f"subject[{lang}] = {v[0]['subject']!r}")
