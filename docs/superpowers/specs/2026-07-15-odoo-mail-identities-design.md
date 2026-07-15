# Séparation des identités d'envoi Odoo : contact@ vs comptabilite@

**Date** : 2026-07-15
**Branche** : `feat/mail-identities-split`
**Statut** : design validé, à implémenter

## Problème

Tous les mails transactionnels Odoo partent aujourd'hui de `yoann@mylab-shop.com`, y compris
les relances de recouvrement. Deux conséquences :

1. Le client reçoit ses devis, ses factures et ses mises en demeure de la même adresse
   personnelle — aucune séparation entre l'avant-vente et le recouvrement.
2. Les relances sont déjà étiquetées `"Service Comptabilité MY.LAB"` dans le nom affiché,
   mais l'adresse réelle reste `yoann@` : l'étiquette ment.

MY.LAB dispose de deux alias Gmail vérifiés sur le compte `yoann@mylab-shop.com` :
`contact@mylab-shop.com` (201 fils envoyés) et `comptabilite@mylab-shop.com` (9 fils envoyés,
dont les échanges fournisseur Fatton de juin 2026). Ils ne sont pas exploités par Odoo.

## Objectif

Router chaque template Odoo vers la bonne identité d'expéditeur, et donner à chaque identité
sa propre signature — dans Odoo **et** dans Gmail.

## État des lieux (sondé le 2026-07-15)

### Infrastructure SMTP — aucune modification nécessaire

| Serveur | Hôte | User | `from_filter` |
|---------|------|------|---------------|
| id=1 « SERVEUR ITHOUSE » | mail02.ithouse.fr | julien@ithouse.fr | *(vide)* |
| id=2 « Gmail Mylab » | smtp.gmail.com:465 | yoann@mylab-shop.com | `mylab-shop.com` |

Le serveur id=2 a `from_filter = mylab-shop.com` : Odoo l'élit pour toute adresse
`@mylab-shop.com` et **ne réécrit pas le From**. `res.company(3).email` vaut déjà
`contact@mylab-shop.com`, et `mail.alias.domain(2)` couvre `mylab-shop.com`.

### Templates concernés

| tpl | Nom | `email_from` actuel | Signature actuelle |
|-----|-----|---------------------|--------------------|
| 34 | MYLAB - Envoi Devis | `{{ object.user_id.email_formatted or … }}` → yoann@ | `user_id.signature` |
| 18 | Invoice: Sending | `"Service Comptabilité MY.LAB" <yoann@>` | en dur, ligne E = contact@ |
| 20 | Credit Note: Sending | `{{ object.invoice_user_id.email_formatted or … }}` → yoann@ | `user_id.signature` |
| 35 | mylab_devis_relance_l1 | `"Service Comptabilité MY.LAB" <yoann@>` | en dur, ligne E = contact@ |
| 36 | mylab_devis_relance_l2 | idem | idem |
| 37 | mylab_facture_relance_l1 | idem | idem |
| 38 | mylab_facture_relance_l2 | idem | idem |
| 39 | mylab_facture_relance_l3 | idem | idem |

Deux mécanismes de signature coexistent : `user_id.signature` (tpl 34, 20) et un bloc HTML
en dur (tpl 18, 35-39). Un utilisateur Odoo n'ayant qu'une seule signature, le mécanisme
dynamique est incompatible avec l'objectif de deux signatures distinctes.

### Chemins d'envoi

Tous les flux automatiques appellent `mail.template.send_mail()` **sans forcer `email_from`**,
donc ils héritent de la valeur posée sur le template :

- Devis → workflow n8n `PStBV5` (`mail.template.send_mail(34)`)
- Facture auto Shopify → `scripts/n8n/shopify_order_workflow/08_create_invoice.js:114`
  (`send_mail(INVOICE_TEMPLATE_ID, iid)`)
- Relances → action serveur cron, `tpl.send_mail(order.id | inv.id, force_send=True)`
  (cf. `scripts/odoo/fix_followup_recipients_and_harden.py:92,131`)

**Chemin non couvert** : l'envoi manuel d'une facture depuis l'UI Odoo (« Envoyer & Imprimer »)
passe par le wizard `account.move.send`, qui peut recalculer le From. À vérifier au canari.

## Décisions

| Question | Décision |
|----------|----------|
| Frontière contact / compta | **Compta large** : seul le devis est « avant-vente » |
| Portée des signatures | Odoo **et** Gmail (Gmail = manuel) |
| Identité compta | « L'équipe MY.LAB » / rôle COMPTABILITÉ |
| Nom affiché compta | « MY.LAB – Comptabilité » |
| Téléphone signature compta | Identique : 04 85 69 33 47 |

## Design

### 1. Routage cible

| tpl | `email_from` | `reply_to` | Signature |
|-----|--------------|------------|-----------|
| 34 | `"MY.LAB" <contact@mylab-shop.com>` | `contact@mylab-shop.com` | CONTACT |
| 18 | `"MY.LAB – Comptabilité" <comptabilite@mylab-shop.com>` | `comptabilite@mylab-shop.com` | COMPTA |
| 20 | `"MY.LAB – Comptabilité" <comptabilite@mylab-shop.com>` | `comptabilite@mylab-shop.com` | COMPTA |
| 35 | `"MY.LAB – Comptabilité" <comptabilite@mylab-shop.com>` | `comptabilite@mylab-shop.com` | COMPTA |
| 36 | `"MY.LAB – Comptabilité" <comptabilite@mylab-shop.com>` | `comptabilite@mylab-shop.com` | COMPTA |
| 37 | `"MY.LAB – Comptabilité" <comptabilite@mylab-shop.com>` | `comptabilite@mylab-shop.com` | COMPTA |
| 38 | `"MY.LAB – Comptabilité" <comptabilite@mylab-shop.com>` | `comptabilite@mylab-shop.com` | COMPTA |
| 39 | `"MY.LAB – Comptabilité" <comptabilite@mylab-shop.com>` | `comptabilite@mylab-shop.com` | COMPTA |

Les deux alias étant rattachés à la boîte `yoann@`, basculer le `reply_to` ne détourne aucune
réponse : elles arrivent au même endroit, mais correctement étiquetées.

### 2. Fichiers signature — source de vérité

Gabarit commun conservé : table 2 colonnes, logo rond 55px, filet vertical doré `#c5a467`,
DM Sans, corps `#333`, baseline en italique doré.

| Fichier | Nom | Rôle | Ligne E | Baseline |
|---------|-----|------|---------|----------|
| `docs/signature-email-contact.html` | Yoann DURAND | Dirigeant | contact@mylab-shop.com | « Créez votre marque en quelques clics et devenez unique ! » |
| `docs/signature-email-comptabilite.html` | L'équipe MY.LAB | Comptabilité | comptabilite@mylab-shop.com | « SARL STARTEC · SIRET 499 500 668 00059 · TVA FR38499500668 » |

`docs/signature-email-contact.html` est le renommage de `docs/signature-email.html` (contenu
inchangé — il pointait déjà vers contact@). La mémoire `feedback_gmail_signature.md` référence
l'ancien chemin et devra être mise à jour.

Ces deux fichiers servent à la fois le script Odoo et le copier-coller Gmail : une seule
source, deux destinations.

### 3. Script de déploiement

`scripts/odoo/step41_split_mail_identities.py`, idempotent, suivant les conventions de
`scripts/odoo/` (`_client.py`, préfixe `stepNN_`).

Séquence :

1. **Backup** — dump `id`, `name`, `email_from`, `reply_to`, `body_html` des 8 templates vers
   `scripts/odoo/backups/mail_templates_pre-identity-split_2026-07-15.json`. Abandon si le
   backup échoue.
2. **Écriture `email_from` / `reply_to`** selon la table de routage.
3. **Injection de la signature** dans `body_html`, encadrée par
   `<!-- ML_SIG_START -->` … `<!-- ML_SIG_END -->`.

Stratégie d'injection, par ordre de priorité :

- Si les marqueurs sont présents → remplacer leur contenu. C'est le cas de tous les passages
  après le premier : idempotent par construction, aucun risque de double-injection.
- Sinon, si le corps contient un bloc `<t t-if="not is_html_empty(object.user_id.signature)">…</t>`
  (tpl 34, 20) → le remplacer par la signature encadrée.
- Sinon, si le corps contient une `<table>` de signature en dur, identifiée par la présence de
  `231 Avenue de la Voguette` → la remplacer par la signature encadrée.
- Sinon → échec explicite sur ce template, sans écriture. Pas de fallback silencieux.

Le script affiche un diff par template (ancien → nouveau `email_from`, longueur du corps) et
supporte `--dry-run` pour tout inspecter sans écrire.

### 4. Signatures Gmail — procédure manuelle

L'API Gmail exposée ici ne couvre pas les paramètres « send as ». Étapes à faire par Yoann :
Paramètres → Comptes et importation → *Envoyer des e-mails en tant que* → `contact@` puis
`comptabilite@` → coller le HTML correspondant dans le bloc signature.

### 5. Vérification — test canari

Le risque principal est silencieux : Gmail réécrit le From en `yoann@` si l'alias n'est pas
un « send as » vérifié pour le chemin SMTP. Les fils envoyés depuis les deux alias le rendent
peu probable, mais l'interface web et le relais SMTP sont des chemins distincts.

Protocole, **avant tout envoi client** :

1. Sur un devis et une facture de test, envoyer via `send_mail()` vers une adresse MY.LAB.
2. Relire l'en-tête `From` **réellement reçu** (via Gmail, pas via `mail.mail.email_from`
   dans Odoo, qui reflète l'intention et non le résultat).
3. Vérifier le chemin manuel : « Envoyer & Imprimer » sur une facture de test depuis l'UI,
   puis même contrôle d'en-tête.

Critère de succès : les en-têtes reçus portent `contact@mylab-shop.com` pour le devis et
`comptabilite@mylab-shop.com` pour la facture et la relance. Toute réécriture en `yoann@`
invalide le déploiement et impose de traiter l'alias côté Gmail avant de continuer.

## Hors périmètre

- Templates de vente non compta (22 Order Confirmation, 23 Payment Done, 24 Cancellation)
  et expédition (27) : inchangés, ils continuent de partir de `yoann@`.
- `res.users(8).signature` : conservée telle quelle (signature perso de Yoann pour Discuss et
  les mails ad hoc). Elle n'est plus lue par les 8 templates après ce changement.
- Création d'un utilisateur Odoo « Comptabilité » dédié : écartée (consomme un siège payant
  et modifierait l'attribution commerciale sur les factures).

## Risques

| Risque | Mitigation |
|--------|------------|
| Gmail réécrit le From en `yoann@` | Canari avant tout envoi client, contrôle d'en-tête reçu |
| Le wizard `account.move.send` (envoi manuel UI) recalcule le From | Canari sur ce chemin spécifique |
| Corruption d'un `body_html` par l'injection | Backup JSON préalable + échec explicite si le point d'ancrage est introuvable |
| Perte d'une réponse client sur le nouveau `reply_to` | Nul : les deux alias arrivent dans la boîte `yoann@` |

## Résultat du canari (2026-07-15)

**Verdict : ✅ Gmail n'a pas réécrit le From.** Les deux alias sont bien des « send as »
valides pour le chemin SMTP, et pas seulement pour l'interface web.

Protocole : partenaire de test dédié (`ZZ Canari Identites Mail`, email `yoann@mylab-shop.com`),
devis + facture laissée en **brouillon** (aucun numéro de séquence consommé), envoi via
`mail.template.send_mail(force_send=True)`, puis suppression des trois enregistrements.
Un garde-fou a confirmé avant envoi que les 3 templates adressent `{{ object.partner_id.id }}` —
donc le partenaire de test, jamais un tiers.

| Template | `From` **reçu** (en-tête brut) | Attendu | |
|----------|-------------------------------|---------|---|
| 34 — Devis (`Votre devis MY.LAB n°S00652`) | `contact@mylab-shop.com` | `contact@mylab-shop.com` | ✅ |
| 18 — Facture (`SARL STARTEC Facture`) | `comptabilite@mylab-shop.com` | `comptabilite@mylab-shop.com` | ✅ |
| 37 — Relance L1 (`Facture — petit rappel`) | `comptabilite@mylab-shop.com` | `comptabilite@mylab-shop.com` | ✅ |

`reply_to` vérifié séparément sur un `mail.mail` créé avec `force_send=False` puis supprimé
avant envoi : Odoo pose bien `reply_to='comptabilite@mylab-shop.com'` et **ne l'écrase pas**
par le catchall. Le volet `reply_to` de la bascule fonctionne donc aussi.

### État live après bascule

- `verify_mail_identities.py` → exit 0, les 8 templates conformes.
- Balises équilibrées sur les 8 (table 1/1, div 1/1, marqueurs 1/1, une seule table dans la
  signature), aucun `</table>` orphelin, aucun résidu `is_html_empty`.
- Backup vierge : `scripts/odoo/backups/mail_templates_pre-identity-split_2026-07-15.json`
  (23 Ko, 8 templates, `email_from` pré-bascule confirmé).

### Correction au design : « idempotent » était imprécis

Odoo **décode les entités HTML au stockage** (`&eacute;` → `é`, `&rsquo;` → `’`,
`&mdash;` → `—`, `&middot;` → `·`), soit ~41 caractères de moins que ce que le script envoie.
Le script relit donc une version normalisée et se croit toujours obligé de réécrire.

La formulation exacte : il **converge** (l'état stocké est un point fixe — réécrire produit le
même résultat) sans être **inerte** (8 écritures RPC à chaque rejeu). Sans conséquence : le
rendu est identique et les marqueurs survivent au décodage — les 8 templates repassent bien
`via marqueurs` au second passage. Ne pas tenter de normaliser les entités côté client.

## Découverte hors périmètre : le catchall bounce (à trancher)

Repéré dans la boîte pendant la vérification du canari, **sans rapport avec cette bascule et
antérieur à elle** : un `mailer-daemon` du 2026-07-15 15:18 —
`550 5.1.1 … catchall@mylab-shop.com … l'adresse est introuvable`.

`res.company(3).catchall_email = catchall@mylab-shop.com`, adresse qu'Odoo présente comme
adresse de retour, **mais qui n'existe pas dans Gmail**. Un client (facture FAC/2026/00170,
envoyée à 08:39, soit avant la bascule) a répondu à `catchall@mylab-shop.com` + `contact@` :
seule la copie vers `contact@` est arrivée. Un client qui répondrait **uniquement** au
catchall verrait sa réponse rebondir — réponse perdue, silencieusement côté MY.LAB.

Un serveur `fetchmail` existe (id=1 « ITHOUSE », imap, state=done) mais pointe sur
`ithouse.fr`, pas sur le domaine du catchall.

Les 8 templates de cette spec ne sont **pas** concernés : leur `reply_to` est désormais
explicite (vérifié ci-dessus). Le risque porte sur les autres chemins — notamment l'envoi
manuel via le wizard `account.move.send`, qui passe par `message_post` et peut recalculer le
Reply-To vers le catchall. C'est l'objet de la vérification du chemin manuel.
