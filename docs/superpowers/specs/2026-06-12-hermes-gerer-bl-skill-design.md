# Spec — Skill Hermes `gerer-bl` (gérer les bons de livraison depuis Telegram)

**Date** : 2026-06-12
**Auteur** : Yoann + Claude
**Statut** : design validé, en attente review spec

## Objectif

Permettre à Yoann de gérer le cycle de vie des bons de livraison Odoo (`stock.picking`
sortants) depuis le bot Telegram Hermes : annuler, régénérer, modifier, et préparer à
l'expédition — sans passer par le poste pour les opérations courantes.

Toutes les opérations **écrivent en production** (stock, livraison) → garde-fou de
confirmation, et la validation/expédition (irréversible) reste un clic dans Odoo.

## Décisions de design

| Sujet | Décision |
|---|---|
| Nom / déclencheur | `gerer-bl` |
| Opérations exécutées depuis Telegram | **annuler**, **régénérer**, **modifier** (qté/lots) — avec confirmation |
| Validation/expédition | **Aperçu seulement** : Hermes prépare et vérifie, mais le mark-done se fait dans Odoo (bouton Valider). JAMAIS exécuté depuis Telegram. |
| Garde-fou | Lecture d'abord (toujours montrer l'état) → aperçu de l'action → « confirme » explicite → exécution |
| Hors périmètre | Facturation (jamais touchée), expédition réelle (Odoo) |

## Runtime

- Creds dans `os.environ` (déjà dans `/opt/data/.env`) : `ODOO_URL`, `ODOO_DB` (`OdooYJ`),
  `ODOO_UID` (8), `ODOO_API_KEY`. `xmlrpc.client` dispo. Ne jamais hardcoder/afficher.
- Périmètre pickings : type sortant `MYLAB: Bons de livraison` (`picking_type_id` = 10).
- Helper `call()` identique à `faire-of` (cf [[feedback_odoo_mrp_xmlrpc_lot_production]] pour
  les pièges de signature : `create` reçoit un dict, `read` d'une liste d'ids ne re-wrappe pas).

## Identification du BL

Un message peut désigner le BL par :
- **numéro** : `00132` ou `MYVO/OUT/00132` (`name ilike`)
- **client** : `Hairdex` (`partner_id.name ilike`, pickings sortants)
- **commande** : `S00566` (`origin =` ou `sale_id`)

Si >1 BL matche → Hermes liste (n°, client, état) et demande lequel.
**Toujours lire et afficher l'état** avant d'agir : n°, client, commande, état, et lignes
(produit, qté demandée, qté réservée, lot).

```python
# pickings sortants matchant un terme (numéro / client / commande)
dom = ['|', '|',
       ('name', 'ilike', term),
       ('partner_id.name', 'ilike', term),
       ('origin', 'ilike', term)]
dom += [('picking_type_id', '=', 10)]
pks = call('stock.picking', 'search_read', dom,
           fields=['name', 'state', 'partner_id', 'origin', 'sale_id', 'move_ids'])
```

## Les 4 opérations

Flux commun : **identifier → afficher l'état → aperçu de l'action → attendre « confirme » → exécuter**.
Toute réponse ≠ confirmation affirmative ⇒ annulation, aucune écriture.

### a) Annuler
- Refus si déjà `cancel`, ou si `done` (un BL expédié ne s'annule pas ici → renvoyer Odoo / procédure retour).
- Sinon aperçu « j'annule MYVO/OUT/X (client, commande) » → confirme → `action_cancel`.

```python
call('stock.picking', 'action_cancel', [pid])
```

### b) Régénérer
- Cas : une commande dont le BL est annulé, et on veut un BL frais.
- Copie du picking annulé → confirm + assign (réserve) → nouveau BL prêt, rattaché à la
  commande (`group_id`/`sale_id` préservés par la copie).

```python
new_id = call('stock.picking', 'copy', src_pid)      # draft, nouveau n°
call('stock.picking', 'action_confirm', [new_id])
call('stock.picking', 'action_assign', [new_id])
```
- Aperçu : « je crée un BL frais sur S00566 (mêmes lignes) ». Rapport : nouveau n° + état + lignes réservées.

### c) Modifier (qté / lots)
- **Seulement si BL non validé** (`draft`/`waiting`/`confirmed`/`assigned`). Refus si `done`/`cancel`.
- Hermes liste les lignes **numérotées** avec qté + lot actuels. Yoann exprime le changement
  en langage naturel : « ligne 2 → 30 », « shampoing volume → 30 », « lot de shampoing volume → 220A526C ».
- Aperçu du **diff** (avant → après) → confirme → `write` sur la `stock.move.line` (champ
  `quantity` pour la qté à expédier, `lot_id` pour le lot — le lot doit exister pour ce produit).

```python
# qté à expédier sur une ligne
call('stock.move.line', 'write', [ml_id], {'quantity': new_qty})
# changer le lot
call('stock.move.line', 'write', [ml_id], {'lot_id': lot_id})
```

### d) Préparer / expédier (APERÇU SEULEMENT)
- Hermes vérifie que le BL est prêt : `state == 'assigned'`, toutes les lignes réservées, lots
  assignés pour les produits suivis par lot.
- Montre ce qui sera expédié/décrémenté, signale ce qui manque (réservation incomplète, lot manquant).
- Conclut : « ✅ prêt — clique **Valider** sur MYVO/OUT/X dans Odoo. » **N'exécute jamais `button_validate`/mark-done.**

## Règles de sécurité (dures)

1. Aucune écriture sans « confirme » explicite après aperçu.
2. **Valider/expédier : jamais exécuté** depuis Telegram (aperçu + renvoi Odoo).
3. Lecture d'abord : toujours montrer l'état du BL avant d'agir.
4. Modifier/annuler refusés sur un BL `done` (et modifier refusé sur `cancel`).
5. Ne jamais toucher la facture. Si l'erreur impacte la facture → le signaler et renvoyer au poste.
6. Une opération par demande ; jamais d'action sur plusieurs BL en lot.
7. Ne jamais afficher/logguer les creds.

## Déploiement

- Fichier : `scripts/hermes/skills/gerer-bl/SKILL.md`.
- Ajouter `"gerer-bl"` à la liste `SKILLS` de `scripts/hermes/deploy_skills_to_hermes.py`
  (+ au grep de vérification).
- Déployer : `python scripts/hermes/deploy_skills_to_hermes.py`. Vérifier le listing.

## Test

Validation read-only côté poste (mirroir du pattern `validate_faire_of_preview.py`) :
identification d'un BL par n°/client/commande + rendu de l'état + diff d'une modif simulée,
sans écrire. Puis smoke test Telegram (allowlist Yoann) :
- « le BL de Hairdex » → Hermes affiche l'état du BL courant.
- « régénère le BL de Hairdex » sur une commande à BL annulé → confirme → nouveau BL prêt.
- « sur le BL 00132, mets shampoing volume à 30 » → aperçu diff → confirme → ligne modifiée.
- « prépare le BL 00132 » → aperçu prêt + renvoi Odoo (aucune validation exécutée).
- « annule le BL X » déjà `done` → refus clair + renvoi Odoo.

## Hors périmètre (YAGNI)

- Pas de validation/expédition réelle depuis Telegram.
- Pas de création de BL ex nihilo (seulement régénération depuis une commande existante).
- Pas d'action multi-BL en lot.
- Pas de gestion des retours/avoirs ni de la facturation.
