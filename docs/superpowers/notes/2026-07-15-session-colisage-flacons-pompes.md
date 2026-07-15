# Session 15/07/2026 — Colisage : la capacité carton dépend du flacon, et deux fichiers dérivaient du LIVE

## Point de départ

Yoann, sur le BL **MYVO/OUT/00129** (BENOIT SAUVAGE, S00530) : les masques coloristeur 200ml sont en
format **bouteille + pompe** et se colisent par **35**, les shampoings coloristeur par **35** aussi, les
huiles et sérums par **69**. Précision décisive : *« ce n'est pas pour le client mais pour mylab en
général »* → donc `x_carton_capacity` au produit (défaut tous clients), **pas** un override dans
`PARTNER_PRODUCT_CARTON`.

## La règle métier qui explique le bug

**La capacité carton est une propriété du FLACON, pas de la gamme commerciale.** Deux produits qui
partagent le même contenant partagent le même carton.

C'est exactement ce que l'ancien colisage ne savait pas : il triait par le **nom** du produit
(« masque » → famille 24, « shampoing » → famille 40). Les coloristeur ne sont ni l'un ni l'autre —
ce sont des flacons pompe — et se retrouvaient éclatés entre deux familles auxquelles ils
n'appartiennent pas.

Corollaire assumé : deux produits de la même famille **peuvent se mélanger dans un carton de bord de
famille** (ex. carton 14 du BL : 2 chocolat + 24 cuivre + 9 marron noisette). C'est physiquement juste,
ce n'est pas un bug à « corriger ».

## Arbitrages avec Yoann (le catalogue ne pouvait pas trancher)

| Question | Réponse |
|---|---|
| Déjaunisseur platine 200ml (masque à 24, shampoing à 40) suit-il les coloristeur ? | **Oui, les deux → 35** |
| Le gloss 200ml (passé à 40 le 07/07 comme « flacons pompes ») ? | **35 aussi** — le 40 était une estimation, c'est le même flacon |
| Périmètre « huiles et sérums → 69 » | **Les 6 réfs en bouteille verre ambré 50ml**, y compris bain miraculeux et repair oil qui ne s'appellent ni huile ni sérum mais partagent le flacon |
| `masque coloristeur tulipe noire 1000ml` à capacité 0 | **→ 12** comme les 11 autres 1L |

Le gloss était une **contradiction directe** avec la mémoire du 07/07 (« flacons pompes » → 40) : deux
produits décrits comme le même flacon avec deux chiffres différents. Il fallait demander.

## Le changement (PR #10)

21 `product.template`, `x_carton_capacity` :

| Vers | Produits | Avant |
|---|---|---|
| **35** | 5 masques + 5 shampoings coloristeur 200ml, déjaunisseur platine (masque + shampoing), gloss (masque + shampoing) | éclatés entre 24 et 40 |
| **69** | 6 réfs verre ambré 50ml (bain miraculeux, huile à barbe, repair oil, sérums barbe / finition ultime / fortifiant) | 63 |
| **12** | masque coloristeur tulipe noire 1000ml | 0 → carton « Divers » |

`FAMILY_LABELS` : ajout de 35 et 69. **Le libellé de 63 devient « 100ml shampoing/masque »** — la famille
ne contient plus que les 8 réfs 100ml une fois les 50ml partis vers 69 ; « 50ml sérum/huile » y serait
devenu faux. *Piège général : quand une famille se vide au profit d'une autre, son libellé ment.*

Nouveau `set_carton_capacity_flacons_pompes.py` : idempotent, `--dry-run`, avec un **garde-fou nom↔id**
qui refuse d'écrire si un `tmpl_id` ne pointe plus sur le produit attendu.

## Trois mines désamorcées

### 1. `server_action_code.py` avait 8 jours de retard sur le LIVE

Absents du repo, présents en LIVE : l'override CENDREE (`PARTNER_PRODUCT_CARTON`), le tri par produit,
`x_carton_capacity` sur `stock.quant.package`. **Un `step03_` depuis le repo les effaçait.** Rapatrié
verbatim et commité **séparément** (48edd0c) *avant* toute modif, pour que le diff de la feature reste
lisible.

### 2. `step02_init_carton_capacity` était une bombe à retardement

Il re-déduisait **toutes** les capacités en parsant les noms — modèle faux (il ne voit pas le flacon).
Rejoué un jour, il remettait les 50ml à 50, les coloristeur à 24/40, les **100ml à 0** (aucune règle ne
les couvre) et écrasait la marque blanche (silver care 54, hydratant/silver glow 80). Désormais **bloqué
derrière `--force`** avec la liste de ce qu'il casserait.

### 3. `bl_deliveryslip.xml` dérivait aussi (PR #11) — trouvé en nettoyant les branches

La branche `chore/odoo-colisage-capacite-effective` (07/07) n'a **jamais été mergée** alors que son code
tournait en LIVE. #10 en avait rapatrié la moitié par ricochet ; l'autre moitié était le template du BL,
à qui il manquait **deux** correctifs :

| | Repo (avant) | LIVE |
|---|---|---|
| `pkg_capacity` | capacité du **premier produit** du carton | capacité du **paquet**, repli produit |
| Reliquat | inconditionnel | gardé par `total_reserve > 0 or state == 'done'` |

Ce qu'un `step04_` depuis le repo aurait cassé en prod :

1. **Liste de colisage CENDREE : 36/36 → 36/24** — l'override client vit sur le paquet, pas sur le produit.
2. **Reliquat d'un BL non réservé : tous les produits listés à tort** — en Odoo 18 `move.quantity` vaut 0
   tant que la dispo n'est pas vérifiée.

Le LIVE était correct, **c'est le repo qui était périmé** → PR repo-only, rien de déployé.

## Pièges rencontrés (à retenir)

- **Ce repo et le LIVE Odoo divergent silencieusement** : tout est éditable depuis l'UI (champ `code` des
  actions serveur, `arch_db` des vues QWeb). **Deux fichiers sur deux étaient périmés.** Toujours
  rapatrier le LIVE et differ avant `step03_`/`step04_`.
- **Un diff naïf de vue QWeb ment** : Odoo normalise `<td></td>` en `<td/>` et strippe la déclaration XML
  au stockage. Ce bruit noie le vrai écart. Recette (ajoutée au README) :
  `ET.canonicalize(arch, strip_text=True)`.
- **Ne pas déduire une famille d'une capacité partagée** : la famille 63 mélangeait 6 réfs 50ml et 8 réfs
  100ml. Un « tout ce qui est à 63 → 69 » aurait embarqué les 100ml à tort.
- **Le `default_code` est la clé des overrides client** — un produit sans référence ne peut pas recevoir
  de colisage négocié (cf. TODO).

## Vérification

Action 774 rejouée sur MYVO/OUT/00129 → **30 cartons** :

- **916 unités réparties = total exact du BL** — rien perdu, rien dupliqué
- aucun dépassement, aucune ligne orpheline, plus aucun carton « Divers »
- **code LIVE == repo** après redéploiement, **override CENDREE préservé**
- script rejoué une 2ᵉ fois → « les 21 produits sont déjà à la bonne capacité »
- template : comparaison canonique XML repo ↔ LIVE → **True**

BL laissé en `assigned` (l'action ne valide rien). Liste de colisage à réimprimer : elle affiche
désormais 35/35 et 69/69.

## État final

| Sujet | Avant | Après |
|---|---|---|
| Coloristeur / platine / gloss 200ml | 24 ou 40 selon le nom | **35 (famille flacon pompe)** |
| Huiles / sérums 50ml | 63 | **69** |
| Tulipe noire 1L | 0 → carton « Divers » | **12** |
| `server_action_code.py` | 8 j de retard sur LIVE | **synchro (master)** |
| `bl_deliveryslip.xml` | 2 correctifs manquants | **synchro (master)** |
| `step02_init_carton_capacity` | rejouable, destructeur | **bloqué `--force`** |
| Règle de colisage | implicite, déduite du nom | **documentée (README) : le flacon** |

PRs #10 et #11 mergées, master `e63cc82`.

## TODO

- **Supprimer `chore/odoo-colisage-capacite-effective`** : entièrement redondante (ses 2 fichiers sont
  dans master). Tant qu'elle traîne, elle ressemble à du travail en attente.
- **Doublon catalogue** : `creme-protectrice-de-couleur-200-ml` (2276) et
  `creme-protecteur-de-couleur-200-ml` (2552) portent le même nom.
- **Les 8 réfs 100ml sont à 63** — valeur héritée des sérums 50ml par copie. Douteux pour un flacon 2×
  plus gros : à mesurer.
- **`shampoing gloss 200ml` (2424) et `masque coloristeur tulipe noire 1000ml` (2457) n'ont pas de
  `default_code`** → impossible de leur négocier un colisage client tant que la réf manque.
- **Check automatique repo ↔ LIVE** (action 774 + vues QWeb) : deux dérives silencieuses en une session,
  ça vaut un garde-fou plutôt qu'une vigilance humaine.
