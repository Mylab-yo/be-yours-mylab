# Envoi automatique des mandats de représentation — Design

**Date :** 2026-06-29
**Auteur :** Yoann + Claude
**Statut :** Validé, en implémentation

## Problème

Le mandat de Personne Responsable (Règlement CE 1223/2009) doit être envoyé à chaque client
ayant **payé** le « dossier cosmétologique » (`product.product` id=2313). Aujourd'hui :

- Le bouton Odoo « Envoyer mandat » ne fait que **mettre en file** (crée une `mail.activity`).
- L'envoi réel dépend d'un worker local (`process_mandat_queue.py`) qu'**aucun cron ne lance**.
- Résultat : **4 clients ont payé mais n'ont jamais reçu leur mandat** (Myan Coiffure,
  Nb Hair spa, Rima Aziza, Josué Linhares). Seul cedric chyzak a été servi (manuellement, le 29/06).

## Objectif

Envoi **100 % autonome** : dès qu'une facture contenant le produit 2313 passe à `paid`,
le mandat part tout seul, sans intervention, **même PC éteint** → hébergé sur le **VPS 24/7**.

## Décisions d'architecture

### Poll-based, pas event-based
Worker sur **cron VPS toutes les 15 min** qui interroge Odoo :
> factures `out_invoice|out_receipt`, `state=posted`, `payment_state=paid`,
> avec une ligne `product_id=2313`, `x_mandat_sent_at` vide, `invoice_date >= MANDAT_AUTO_SINCE`.

Le « trigger paiement » = ce filtre. Vs `base.automation` Odoo : **auto-réparateur**
(réessaie au run suivant si échec), aucun événement manqué, latence max = 15 min (acceptable :
le client doit de toute façon signer et renvoyer).

### Idempotence : champ `x_mandat_sent_at` (Datetime sur `account.move`)
Tamponné **uniquement à l'envoi réussi** (auto **ou** manuel) → jamais de double envoi.
Sémantique honnête : le champ = « mandat réellement envoyé le … ».

### Garde anti-rafale : cutoff `MANDAT_AUTO_SINCE`
À l'activation, `MANDAT_AUTO_SINCE = 2026-06-29`. Les 5 factures existantes (dates Avr–Juin)
sont **exclues de l'auto-envoi** par le cutoff → seuls les **futurs** paiements déclenchent.
- cedric (00146) : aussi **tamponné** (réellement envoyé le 29/06).
- Les 4 manquants : **non tamponnés** (honnête : pas envoyés), exclus par cutoff,
  envoyés **manuellement par Yoann** après nettoyage des fiches (le CLI tamponne alors).

## Composants

| Composant | Rôle |
|---|---|
| Champ `x_mandat_sent_at` | Marqueur idempotence sur `account.move`. Créé 1× via XML-RPC. |
| `_client.py` (refactor) | Charge `.env.local` Windows **sinon** variables d'env OS → portable VPS. |
| `auto_send_mandats.py` (nouveau) | Le poll : sélectionne éligibles, appelle `process_invoice()`, tamponne, notifie Telegram. Options `--dry-run/--limit/--to`. |
| `send_mandat_representation.py` (conservé) | CLI manuel (renvoi / cas particulier) — tamponne aussi `x_mandat_sent_at`. |
| Notif Telegram (Hermes bot) | Ping à chaque mandat auto-envoyé. |

L'ancien chemin (bouton serveur + `mail.activity` type 8 + `process_mandat_queue.py`) est
**superseded** — laissé en place mais plus branché sur le cron.

## Déploiement VPS

- `/root/mandat-automation/` : scripts + venv (`google-api-python-client`, `google-auth`,
  `python-dotenv`) + `.env` (Odoo + Google + Telegram) + `secrets/google-sa-mandat.json`
  (copié en SFTP, **jamais loggé**) + `logs/`.
- Cron `*/15 * * * *` avec `flock -n` (anti-chevauchement), sortie → `logs/mandat.log`.

## Rollout (l'ordre compte)

- **A.** Créer le champ. Tamponner cedric (00146).
- **B.** Coder + dry-run local → le poll doit sélectionner **0 facture** (cutoff OK) → sûr.
- **C.** Déployer VPS + activer cron. 1er run = no-op (tout exclu) → sûr.
- **Hors-scope auto :** les 4 manquants = check + nettoyage fiche par Yoann, puis envoi
  manuel à la demande.

## Les 4 clients à checker (qualité fiche)

| Facture | Client | Email | État fiche |
|---|---|---|---|
| FAC/2026/00012 (move 221) | Myan Coiffure | myancoiffure@gmail.com | ✅ complète |
| FAC/2026/00038 (move 390) | Nb Hair spa | nadege.boulangeot@yahoo.fr | 🇨🇭 adresse suisse mais pays=France ; pas de TVA |
| FAC/2026/00076 (move 402) | Rima Aziza | rima_0007@live.fr | raison sociale « Rima » ; ville en double ; pas de TVA |
| FAC/2026/00138 (move 733) | Josué Linhares | josuelinhares.contact@gmail.com | ❌ aucune adresse, pas de raison sociale |

## Limites connues

- Client sans email → `process_invoice` retourne `no_email`, pas d'envoi, **non tamponné** →
  réessayé chaque run (log bruyant mais inoffensif). À traiter manuellement.
- Latence max = intervalle cron (15 min).
- Cutoff sur `invoice_date` : une vieille facture (avant cutoff) payée tardivement est
  exclue de l'auto → Yoann la traite manuellement (rare).
