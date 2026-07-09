# Spec — Skill Hermes `faire-of` (lancer un Ordre de Fabrication depuis Telegram)

**Date** : 2026-06-12
**Auteur** : Yoann + Claude
**Statut** : design validé, en attente review spec

## Objectif

Permettre à Yoann de lancer un Ordre de Fabrication Odoo (conditionnement vrac →
produit fini, avec consommation des composants et pose du n° de lot) depuis le bot
Telegram Hermes, sans passer par le poste/Odoo.

L'OF **mute le stock de production** (consomme vrac + packaging, produit du fini) et
est **difficile à annuler** (cf. session 2026-06-12 : un OF terminé n'est pas
supprimable via XML-RPC). D'où un garde-fou de confirmation obligatoire.

## Décisions de design

| Sujet | Décision |
|---|---|
| Nom du skill / déclencheur | `faire-of` |
| Garde-fou | **Confirmation en 2 temps** : aperçu → « confirme » explicite → exécution |
| N° de lot du fini | **= lot du vrac consommé**, proposé automatiquement (surchargeable par `lot X`) |
| Stock composant insuffisant | **Avertir mais laisser passer** (négatifs tolérés sur composants `consu`) |
| Portée | Un seul OF par demande ; uniquement produits ayant une nomenclature (`mrp.bom`) |

## Runtime

- Creds dans `os.environ` (déjà dans `/opt/data/.env` du container) : `ODOO_URL`,
  `ODOO_DB` (= `OdooYJ`), `ODOO_UID` (= 8), `ODOO_API_KEY`. Ne jamais hardcoder/afficher.
- `xmlrpc.client` disponible. Pas de `company_id` forcé (le MO #2 de la session a été
  créé sans, et a fonctionné).
- Emplacement fini : `MYVO/Stock/Fini` (id 47).

## Format d'entrée

```
OF <produit> <qté>                    → ex. "OF shampoing volume 200ml 150"
OF <produit> <qté> lot <numéro>       → lot explicite qui prime sur la déduction
```

Parsing :
1. Extraire quantité (entier/décimal) et lot optionnel (après `lot`).
2. Le reste = nom produit → matching flou sur `product.product` ayant un `mrp.bom`.
   - 0 match avec BoM → « ce produit n'est pas fabriqué (pas de nomenclature) ».
   - >1 match → lister et demander de préciser.

## Flux en 2 temps

### Temps 1 — Aperçu (lecture seule)

1. Résout le variant fini + sa BoM ; calcule les besoins composants (`qté × ratio BoM`).
2. Identifie le(s) composant(s) **suivi(s) par lot** (= le vrac) ; lit ses lots en
   stock interne (`stock.quant`, qty>0). Propose le lot :
   - 1 lot dispo → ce lot.
   - >1 lot → le plus ancien proposé, les autres listés.
   - `lot X` fourni par l'utilisateur → prime sur la déduction.
3. Vérifie la dispo de chaque composant (`qty_available`) ; calcule le stock résultant.
4. Affiche l'**APERÇU** :
   - Produit + quantité à produire
   - Lot fini (proposé / fourni)
   - Composants consommés (avec lot pour le vrac) + stock avant→après
   - ⚠️ Alerte par composant qui passerait en négatif (mais on n'empêche pas)
   - Invite : « Réponds **confirme** pour lancer, autre chose pour annuler. »

### Temps 2 — Exécution (sur « confirme » uniquement)

Toute réponse ≠ confirmation affirmative ⇒ annulation, rien d'écrit.

Flux canonique validé (cf. `scripts/odoo/creer_of_production_lot.py` et memory
`feedback-odoo-mrp-xmlrpc-lot-production`) :

1. Lot fini : `get_or_create` un `stock.lot {name, product_id=variant_fini}`.
2. `create mrp.production {product_id, product_qty, bom_id, product_uom_id}` →
   `action_confirm` (explose la BoM, réserve, auto-assigne les lots composants).
3. `write {qty_producing, lot_producing_id}`.
4. **`write picked=True` sur les `move_raw_ids`** ← piège clé, sinon composants non consommés.
5. `write location_dest_id=47` sur les `move_finished_ids`.
6. `button_mark_done` avec contexte `{skip_backorder: True}`.
   **JAMAIS `skip_consumption: True`** (annule les move_raw → produit sans consommer).
7. Rapport : nom de l'OF (`MYVO/MO/xxxxx`), état `done`, nouveaux `qty_available`
   du fini + des composants consommés.

## Règles de sécurité (dures)

1. Aucune écriture Odoo sans « confirme » explicite après aperçu.
2. Jamais `skip_consumption`.
3. Un seul OF par demande.
4. Ne jamais afficher/logguer les creds.
5. Création lot fini autorisée (lot lié à 1 seul produit, normal en Odoo).

## Déploiement

- Fichier : `scripts/hermes/skills/faire-of/SKILL.md`.
- Ajouter `"faire-of"` à la liste `SKILLS` de `scripts/hermes/deploy_skills_to_hermes.py`.
- Déployer : `python scripts/hermes/deploy_skills_to_hermes.py` (SFTP → `/root/.hermes/skills/faire-of/`, chown hermes, restart gateway).
- Vérifier : `docker exec hermes-gateway hermes skills list | grep faire-of`.

## Hors périmètre (YAGNI)

- Pas de gestion de réparation/suppression d'OF cassé depuis Hermes (recovery = poste).
- Pas de production multi-produits ou multi-lots en une demande.
- Pas de génération auto de numéro de lot (toujours dérivé du vrac ou fourni).

## Test

Test manuel post-déploiement depuis Telegram (allowlist = Yoann) :
- `OF <produit test> <petite qté>` → vérifier l'aperçu (lot vrac proposé, stocks).
- Répondre autre chose que confirme → vérifier qu'aucun OF n'est créé.
- Répondre `confirme` → vérifier l'OF `done` + stocks décrémentés côté Odoo.
- Cas produit sans BoM → message d'erreur clair.
