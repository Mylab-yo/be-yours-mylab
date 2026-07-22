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
passe par le wizard `account.move.send`, qui peut recalculer le From. À vérifier au canari
— finalement tranché par inspection de la source, cf. § *Chemin manuel « Envoyer & Imprimer »*.

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
   puis même contrôle d'en-tête — finalement tranché par inspection de la source, cf. § *Chemin
   manuel « Envoyer & Imprimer »*.

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
| Le wizard `account.move.send` (envoi manuel UI) recalcule le From | Canari sur ce chemin spécifique — finalement tranché par inspection de la source, cf. § *Chemin manuel « Envoyer & Imprimer »* |
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

### Chemin manuel « Envoyer & Imprimer » (wizard account.move.send)

Inspection de la source dans le conteneur `odoo` (lecture seule, aucun envoi). Version
constatée : **Odoo 18.0, build `20260609`** (`odoo/release.py`, `version_info = (18, 0, 0,
FINAL, 0, '')`, `version = '18.0-20260609'`).

Fichiers (module `account`, chemin racine `/usr/lib/python3/dist-packages/odoo/addons/`) :
- `account/models/account_move_send.py`
- `mail/models/mail_thread.py`
- `mail/models/models.py`
- `mail/models/mail_template.py` (pour contraste avec le chemin automatique)

#### Point 1 — `email_from` : le wizard **hérite** du template

`account/models/account_move_send.py:597` (dans `_send_mails`) :

```python
email_from = self._get_mail_default_field_value_from_template(mail_template, mail_lang, move, 'email_from')
```

`_get_mail_default_field_value_from_template` est définie `account/models/account_move_send.py:132-137` :

```python
def _get_mail_default_field_value_from_template(self, mail_template, lang, move, field, **kwargs):
    if not mail_template:
        return
    return mail_template\
        .with_context(lang=lang)\
        ._render_field(field, move.ids, **kwargs)[move._origin.id]
```

`mail_template` ici est le template lié au type de document (tpl 18 « Invoice: Sending » pour
une facture). Le wizard rend donc bien le champ `email_from` **du template**, pas une valeur
recalculée (pas de `company_id.email`, pas de `invoice_user_id.email_formatted` en dur dans ce
chemin). **Conclusion : le chemin manuel hérite de la bascule contact@/comptabilite@ appliquée
sur les 8 templates — rien à corriger sur ce point.**

#### Point 2 — Reply-To : le wizard **force le catchall**, confirmé par lecture de source + état live

Contrairement à `mail.template.send_mail()` (chemin automatique), le wizard **ne passe jamais
`reply_to`** dans son appel à `message_post`. Preuve :

- `account/models/account_move_send.py:473-497` (`_send_mail`) appelle
  `move.with_context(...).message_post(message_type='comment', **kwargs, **{... , 'reply_to_force_new': False})`.
  Le seul kwarg lié à reply-to est `reply_to_force_new` (ligne 492) — un booléen qui contrôle le
  threading des réponses (`mail/models/mail_message.py:175-176` : *"If true, answers do not go
  in the original document discussion thread"*), **pas** la valeur de l'adresse. Le champ
  `reply_to` lui-même n'apparaît **nulle part** dans `account_move_send.py`,
  `account/wizard/account_move_send_wizard.py` ni `account_move_send_batch_wizard.py` (grep
  exhaustif des trois fichiers, seule occurrence : `reply_to_force_new` L492).
- Par contraste, le chemin automatique (`mail.template.send_mail()` → `send_mail_batch` →
  `_generate_template`) inclut explicitement `'reply_to'` dans les champs rendus depuis le
  template : `mail/models/mail_template.py:677` (liste de champs passée à `_generate_template`
  dans `send_mail_batch`, def L645). C'est ce mécanisme qui a fait passer le canari Task 5 sur
  `reply_to='comptabilite@mylab-shop.com'`. Le wizard manuel ne l'emprunte pas.

Faute de `reply_to` explicite, `mail.thread.message_post` retombe sur son calcul générique,
`mail/models/mail_thread.py:2282-2283` :

```python
if 'reply_to' not in msg_values:
    msg_values['reply_to'] = self._notify_get_reply_to(default=email_from)[self.id]
```

`_notify_get_reply_to` (`mail/models/models.py:234-300`) documente elle-même sa priorité dans
sa docstring (L241-243) : **alias spécifique au document > catchall société > `default`**
(ici `default=email_from`, donc même l'e-mail du template n'est utilisé qu'en tout dernier
recours). Vérifié en lecture seule sur l'instance live (`scripts/odoo/_client.py`,
`search_read`, aucune écriture) :

- `mail.alias` avec `alias_parent_model_id.model = 'account.move'` → **liste vide**. Aucun
  alias dédié aux factures n'existe, donc la première branche ne matche jamais.
- `res.company(3).catchall_email = 'catchall@mylab-shop.com'` → toujours renseigné, donc la
  deuxième branche (catchall) l'emporte systématiquement avant que `default` (l'email_from du
  template) ne soit atteint (`mail/models/models.py:283-290`, bloc `# continue with company
  alias`).

**Conclusion, point 2 : CONFIRMÉ (pas indéterminé).** Tout envoi manuel « Envoyer & Imprimer »
d'une facture depuis l'UI Odoo pose `Reply-To: catchall@mylab-shop.com` — une adresse
qu'Odoo annonce mais qui n'existe pas dans Gmail (bounce `550 5.1.1` déjà observé sur
FAC/2026/00170). Ce comportement est indépendant de cette bascule : il existait avant, et
persiste après, pour ce chemin précis. Un client qui répondrait uniquement au Reply-To d'une
facture envoyée à la main perdrait sa réponse, silencieusement.

#### Limite connue — non corrigée dans ce lot

Le point 2 (et, si un jour le point 1 changeait de mécanisme, le point 1 aussi) relève du
wizard standard Odoo `account.move.send` / `mail.thread.message_post`, hors périmètre de
cette spec. Le corriger impliquerait soit de surcharger `_send_mail` pour y injecter
`reply_to` depuis le template, soit de configurer un `catchall_email` valide côté Gmail (ou un
alias `mail.alias` dédié à `account.move`) — une décision produit/infra à part entière, pas un
correctif de routage d'identité d'envoi. **Non traité ici, volontairement.**
