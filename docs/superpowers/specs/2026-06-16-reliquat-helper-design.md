# Design — Reliquat (backorder) assisté sur les BL Odoo MY.LAB

Date : 2026-06-16
Statut : validé (design), spec à relire avant plan d'implémentation

## Problème

Quand une commande ne peut pas être servie en totalité (rupture sur une ou
plusieurs réfs), il faut **expédier ce qui est disponible** et garder le manquant
en **reliquat**. Aujourd'hui ce partage se décide hors Odoo (dans Station / le
physique) : Odoo n'en sait rien (ex. S00533 — BL intact 24+48 demandés, 0 fait,
aucun reliquat, alors qu'une partie est physiquement partie).

On veut que ce partage se fasse **dans Odoo**, simplement, pour que :
- le stock se recale,
- le reliquat existe comme 2e BL (réexpédiable plus tard),
- la notif client (BL custom MY.LAB + tracking) porte sur la bonne partie.

## Décisions de cadrage (validées)

- **Mode hybride (C)** : Odoo propose la répartition (réservation stock), le
  préparateur l'ajuste à l'écran avant de valider.
- **Helper custom (B), via Approche 1** : un **bouton action-serveur** qui
  pré-remplit le disponible ; le préparateur revoit sur l'écran BL standard puis
  valide nativement. Pas de module addon, déployable en XML-RPC.

## Vue d'ensemble du flux

```
1. Commande confirmée → BL Odoo (état « à faire »)
2. Préparateur ouvre le BL → [ Préparer le dispo ]   ← composant à coder
     → action_assign (réserve le dispo) + pré-remplit les qté « Fait »
3. Préparateur vérifie / ajuste les quantités
4. [ Valider ] (natif) → popup native « Créer un reliquat ? » → Oui
     → BL #1 (expédié, validé) + BL #2 (reliquat, rouvert)
5. Étiquette DPD dans Station pour le BL #1 → n° de suivi
6. Le soir : job Station écrit le tracking sur le BL #1 + envoie la notif
     (BL custom MY.LAB report 775 + tracking)
7. Reliquat (#2) : réexpédié au réappro → même flux → notifié à son tour
```

## Composants

### C1 — Bouton « Préparer le dispo » (le seul vrai dev)

- `ir.actions.server` (`model = stock.picking`, `state = 'code'`), ajouté en
  **bouton d'en-tête** du BL via héritage de vue (même pattern que
  `step05_add_picking_button.py` / actions cartons existantes).
- Logique (sur le(s) picking(s) sélectionné(s)) :
  1. Garde : ne traiter que `state in ('confirmed','assigned','waiting')` ; ignorer `done`/`cancel`.
  2. `picking.action_assign()` → réserve tout le stock disponible.
  3. Pré-remplir la quantité « Fait » = quantité réservée, sur chaque ligne
     (lignes **service/consommable** non stockables : « Fait » = demandé, elles
     ne partent jamais en reliquat).
  4. **Garde-fou « rien dispo »** : si total réservé == 0 → `UserError`
     « Aucun stock disponible — rien à expédier » (pas de validation). Pas de
     mode « forcer » en v1 (le préparateur peut toujours saisir à la main sur
     l'écran standard si vraiment nécessaire).
- Idempotent : re-cliquer relance `action_assign` (sans effet de bord).
- Le préparateur reste sur l'écran BL, ajuste, puis **Valider** (natif).

### C2 — Reliquat = natif Odoo (zéro dev)

- La validation partielle déclenche le wizard natif `stock.backorder.confirmation`
  → crée le BL reliquat. Le reliquat **hérite du transporteur** (DPD) du BL parent
  (à vérifier en impl.) → notifiable de la même façon quand il partira.

### C3 — Notif adaptée au partiel (ajout sur le template mail id=27)

Condition QWeb dans le corps :
- BL **complet** → « Votre commande a été expédiée. »
- BL **partiel** (`object.backorder_ids` non vide → a généré un reliquat) →
  « Une **partie** de votre commande a été expédiée ; le reste suivra dès
  réception du stock. »
- BL **reliquat** (`object.backorder_id` rempli) → « Le **complément** de votre
  commande a été expédié. »

### C4 — Raffinement du matcher tracking

- Dans `station_notify_tracking.build_plan` : en cas de **plusieurs BL candidats**
  pour un même client, préférer l'état `done`/`assigned` (réellement parti) au
  `waiting` (reliquat en attente de stock), en plus du tri par date. Évite
  d'écrire le tracking sur le reliquat encore non expédié.

## Cas limites / erreurs

- **Rien dispo** → garde-fou (C1.4), pas d'expédition vide.
- **Lignes service/consommable** → « Fait » = demandé (jamais en reliquat).
- **Stock négatif / inexact** (constaté en simulation : `bain-miraculeux-50ml`
  = -24, etc.) → le préparateur ajuste (hybride C) ; la pré-proposition reste
  indicative, pas contraignante.
- **2 BL par commande** (expédié + reliquat) → chacun notifié le soir où **son**
  étiquette Station est générée ; C4 évite la confusion.

## Validation

- ✅ **Simulation lecture seule** déjà faite : `scripts/odoo/simulate_reliquat.py`
  (montre le split demandé/dispo/expédié/reliquat sur les BL réels, sans rien
  écrire). 20 BL scannés : 10 partiels, 1 complet, 9 sans stock.
- **Test e2e** (à faire avec accord explicite de Yoann sur une vraie commande
  qu'il s'apprête à expédier, car valider crée de vrais mouvements de stock) :
  bouton → ajuster → valider → vérifier les 2 BL → preview notif à Yoann.

## Déploiement

Scripts XML-RPC idempotents (pattern `scripts/odoo/stepNN_`) :
- `step_create_ship_available_action.py` — action serveur + bouton d'en-tête.
- patch du body du template mail id=27 (formulations C3).
- patch `station_notify_tracking.py` (raffinement matcher C4).

Aucun module addon, aucun redémarrage Odoo.

## Hors périmètre (YAGNI)

- Écran wizard 100 % sur-mesure (Approche 2) — seulement si le geste natif coince.
- Mode « forcer » l'expédition quand rien n'est dispo.
- Activation `--send` + tâche planifiée 20h30 (lot « mise en prod » séparé, quand
  le workflow préparateur tourne).
- Auto-cartonnage (action « Répartir en cartons » existante, séparée).
