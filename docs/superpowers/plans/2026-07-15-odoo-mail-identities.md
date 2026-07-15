# Séparation des identités d'envoi Odoo — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Router les 8 templates mail Odoo vers deux identités d'expéditeur distinctes — `contact@mylab-shop.com` pour le devis, `comptabilite@mylab-shop.com` pour la facture, l'avoir et les 5 relances — chacune avec sa propre signature.

**Architecture:** Aucune modification d'infra : le serveur SMTP « Gmail Mylab » (id=2) a déjà `from_filter = mylab-shop.com` et n'altère pas le From pour ce domaine. Tout le travail consiste à écrire `email_from`, `reply_to` et un bloc signature en dur dans `mail.template.body_html` via XML-RPC. Les signatures sont sourcées depuis deux fichiers HTML du repo, servant à la fois Odoo et le copier-coller Gmail.

**Tech Stack:** Python 3 + XML-RPC via `scripts/odoo/_client.py` (helpers `search_read`, `write`). Pas de pytest sur ce périmètre — la vérification suit l'idiome du repo : scripts `probe_*` / `verify_*` exécutés contre l'Odoo live, plus un mode `--dry-run`.

## Global Constraints

- **Odoo** : `odoo.startec-paris.com`, DB via `.env.local`, UID=8, `company_id=3` (SARL STARTEC).
- **Jamais d'édition parallèle** dans l'UI Odoo pendant qu'un script tourne (UID 8 partagé → état incohérent).
- **Encodage** : les scripts impriment de l'accentué ; commencer chaque script par
  `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` sinon la console Windows (cp1252) lève `UnicodeEncodeError`.
- **Valeurs exactes** (copiées verbatim de la spec, à ne pas paraphraser) :
  - `email_from` contact : `"MY.LAB" <contact@mylab-shop.com>`
  - `email_from` compta : `"MY.LAB – Comptabilité" <comptabilite@mylab-shop.com>` (tiret demi-cadratin U+2013)
  - `reply_to` contact : `contact@mylab-shop.com`
  - `reply_to` compta : `comptabilite@mylab-shop.com`
  - Marqueurs : `<!-- ML_SIG_START -->` et `<!-- ML_SIG_END -->`
- **Routage** : tpl 34 → contact ; tpl 18, 20, 35, 36, 37, 38, 39 → compta.
- **Aucun envoi vers une adresse client réelle** à aucune étape. Le canari (Task 5) n'utilise que des enregistrements de test rattachés à un partenaire dédié dont l'email est `yoann@mylab-shop.com`.
- **Gate d'irréversibilité** : Task 5 envoie de vrais mails et Task 6 écrit sur le live. Ne pas les lancer sans validation explicite de Yoann.

## File Structure

| Fichier | Responsabilité |
|---------|----------------|
| `docs/signature-email-contact.html` | Signature CONTACT (renommage de `signature-email.html`, contenu inchangé). Source de vérité. |
| `docs/signature-email-comptabilite.html` | Signature COMPTA (nouveau). Source de vérité. |
| `scripts/odoo/verify_mail_identities.py` | Assertions sur l'état cible des 8 templates. Re-exécutable, exit 0/1. C'est le « test ». |
| `scripts/odoo/step41_split_mail_identities.py` | Déploiement idempotent : backup → `email_from`/`reply_to` → injection signature. |
| `scripts/odoo/canary_mail_identities.py` | Canari : crée les enregistrements de test, envoie, nettoie. |
| `scripts/odoo/backups/mail_templates_pre-identity-split_2026-07-15.json` | Backup généré par step41. Commité. |

`verify_*` est séparé de `step41_*` volontairement : le vérificateur doit pouvoir juger l'état
sans partager le code qui l'a produit — sinon un bug d'injection se validerait lui-même.

---

### Task 1 : Les deux fichiers signature

**Files:**
- Rename: `docs/signature-email.html` → `docs/signature-email-contact.html`
- Create: `docs/signature-email-comptabilite.html`

**Interfaces:**
- Produces: deux fichiers HTML lus par `step41_split_mail_identities.py` (Task 3) via
  `Path(REPO/"docs"/"signature-email-contact.html").read_text(encoding="utf-8")`.
  Chacun est un `<table>…</table>` autonome, sans `<html>`/`<body>`.

- [ ] **Step 1: Renommer la signature existante**

```bash
cd d:/be-yours-mylab
git mv docs/signature-email.html docs/signature-email-contact.html
```

Le contenu reste strictement inchangé : il pointait déjà vers `contact@mylab-shop.com`.

- [ ] **Step 2: Créer la signature comptabilité**

Créer `docs/signature-email-comptabilite.html`. Même gabarit que la version contact (table 2
colonnes, logo rond 55px, filet vertical doré `#c5a467`, DM Sans). Quatre différences seulement :
nom, rôle, ligne E, baseline.

```html
<table cellpadding="0" cellspacing="0" border="0" style="font-family: 'DM Sans', Arial, sans-serif; font-size: 11px; color: #333333; line-height: 1.4;">
  <tr>
    <td style="padding-right: 12px; border-right: 2px solid #c5a467; vertical-align: top;">
      <img src="https://cdn.shopify.com/s/files/1/0924/1922/7982/files/Logo-rond-noir-sans-fond.png?v=1773170347" alt="MY.LAB" width="55" height="55" style="border-radius: 50%; display: block;" />
    </td>
    <td style="padding-left: 12px; vertical-align: top;">
      <p style="margin: 0 0 1px 0; font-size: 13px; font-weight: 700; color: #1a1a1a;">L&rsquo;&eacute;quipe MY.LAB</p>
      <p style="margin: 0 0 6px 0; font-size: 10px; font-weight: 500; color: #c5a467; text-transform: uppercase; letter-spacing: 1px;">Comptabilit&eacute;</p>
      <p style="margin: 0 0 2px 0; font-size: 11px;"><span style="color: #999;">T</span>&nbsp;<a href="tel:+33485693347" style="color: #333; text-decoration: none;">04 85 69 33 47</a></p>
      <p style="margin: 0 0 2px 0; font-size: 11px;"><span style="color: #999;">E</span>&nbsp;<a href="mailto:comptabilite@mylab-shop.com" style="color: #333; text-decoration: none;">comptabilite@mylab-shop.com</a></p>
      <p style="margin: 0 0 6px 0; font-size: 11px;"><span style="color: #999;">W</span>&nbsp;<a href="https://mylab-shop.com" style="color: #c5a467; text-decoration: none; font-weight: 600;">mylab-shop.com</a></p>
      <p style="margin: 0; font-size: 9px; color: #999;">231 Avenue de la Voguette, 84300 Cavaillon &mdash; France</p>
      <p style="margin: 5px 0 0 0; padding-top: 5px; border-top: 1px solid #e5e5e5; font-size: 9px; color: #c5a467; font-style: italic;">SARL STARTEC &middot; SIRET 499 500 668 00059 &middot; TVA FR38499500668</p>
    </td>
  </tr>
</table>
```

- [ ] **Step 3: Vérifier les deux fichiers**

```bash
cd d:/be-yours-mylab
python -c "
from pathlib import Path
c = Path('docs/signature-email-contact.html').read_text(encoding='utf-8')
k = Path('docs/signature-email-comptabilite.html').read_text(encoding='utf-8')
assert 'contact@mylab-shop.com' in c and 'comptabilite@' not in c, 'contact sig pollué'
assert 'comptabilite@mylab-shop.com' in k, 'compta sig sans son adresse'
assert 'Yoann DURAND' in c and 'Yoann DURAND' not in k, 'nom mal réparti'
assert '231 Avenue de la Voguette' in c and '231 Avenue de la Voguette' in k, 'ancre adresse manquante'
assert c.count('<table') == 1 and k.count('<table') == 1, 'table imbriquée: casserait la regex step41'
print('OK — 2 signatures conformes')
"
```

Attendu : `OK — 2 signatures conformes`

L'assertion sur `<table` unique et sur `231 Avenue de la Voguette` n'est pas cosmétique : ce
sont les points d'ancrage sur lesquels la regex d'injection de Task 3 repose.

- [ ] **Step 4: Commit**

```bash
cd d:/be-yours-mylab
git add docs/signature-email-contact.html docs/signature-email-comptabilite.html
git commit -m "feat(mail): deux signatures sourcées, contact et comptabilité

Renomme signature-email.html en -contact.html (contenu inchangé, il
pointait déjà vers contact@) et ajoute la variante comptabilité
(L'équipe MY.LAB / Comptabilité / comptabilite@ / baseline SIRET-TVA).

Ces fichiers sont la source de vérité pour Odoo et pour Gmail.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2 : Le vérificateur (échoue d'abord)

**Files:**
- Create: `scripts/odoo/verify_mail_identities.py`

**Interfaces:**
- Consumes: `docs/signature-email-contact.html`, `docs/signature-email-comptabilite.html` (Task 1).
- Produces: exit code 0 si les 8 templates sont conformes, 1 sinon. Réutilisé tel quel en Task 4
  et Task 6 comme critère d'acceptation.

- [ ] **Step 1: Écrire le vérificateur**

Créer `scripts/odoo/verify_mail_identities.py` :

```python
"""Verifie l'etat cible des 8 templates mail (identites contact@ / comptabilite@).

Exit 0 si conforme, 1 sinon. Volontairement independant de step41 : un verificateur
qui partagerait le code d'injection validerait ses propres bugs.
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from _client import search_read

MARK_START = "<!-- ML_SIG_START -->"
MARK_END = "<!-- ML_SIG_END -->"

CONTACT_FROM = '"MY.LAB" <contact@mylab-shop.com>'
CONTACT_REPLY = "contact@mylab-shop.com"
COMPTA_FROM = '"MY.LAB – Comptabilité" <comptabilite@mylab-shop.com>'
COMPTA_REPLY = "comptabilite@mylab-shop.com"

# tpl_id -> (identite, email_from attendu, reply_to attendu)
EXPECTED = {
    34: ("contact", CONTACT_FROM, CONTACT_REPLY),
    18: ("compta", COMPTA_FROM, COMPTA_REPLY),
    20: ("compta", COMPTA_FROM, COMPTA_REPLY),
    35: ("compta", COMPTA_FROM, COMPTA_REPLY),
    36: ("compta", COMPTA_FROM, COMPTA_REPLY),
    37: ("compta", COMPTA_FROM, COMPTA_REPLY),
    38: ("compta", COMPTA_FROM, COMPTA_REPLY),
    39: ("compta", COMPTA_FROM, COMPTA_REPLY),
}

# Marqueurs d'identite attendus DANS le bloc signature injecte
SIG_MARKERS = {
    "contact": ("Yoann DURAND", "contact@mylab-shop.com", "comptabilite@mylab-shop.com"),
    "compta": ("MY.LAB", "comptabilite@mylab-shop.com", "contact@mylab-shop.com"),
}


def check(tpl_id, identite, want_from, want_reply, failures):
    rows = search_read(
        "mail.template", [("id", "=", tpl_id)],
        ["id", "name", "email_from", "reply_to", "body_html"],
    )
    if not rows:
        failures.append(f"tpl {tpl_id}: introuvable")
        return
    t = rows[0]
    body = t.get("body_html") or ""
    tag = f"tpl {tpl_id} ({t['name']})"

    if t.get("email_from") != want_from:
        failures.append(f"{tag}: email_from={t.get('email_from')!r} attendu {want_from!r}")
    if t.get("reply_to") != want_reply:
        failures.append(f"{tag}: reply_to={t.get('reply_to')!r} attendu {want_reply!r}")

    n_start, n_end = body.count(MARK_START), body.count(MARK_END)
    if n_start != 1 or n_end != 1:
        failures.append(f"{tag}: marqueurs signature = {n_start} start / {n_end} end, attendu 1/1")
        return

    sig = body.split(MARK_START, 1)[1].split(MARK_END, 1)[0]
    must_a, must_b, must_not = SIG_MARKERS[identite]
    if must_a not in sig:
        failures.append(f"{tag}: signature sans {must_a!r}")
    if must_b not in sig:
        failures.append(f"{tag}: signature sans {must_b!r}")
    if must_not and must_not in sig:
        failures.append(f"{tag}: signature contient {must_not!r} alors qu'elle est {identite}")

    if "user_id.signature" in body:
        failures.append(f"{tag}: reference residuelle a user_id.signature")
    if "231 Avenue de la Voguette" in body.replace(sig, ""):
        failures.append(f"{tag}: bloc signature residuel HORS marqueurs (double signature)")


def main():
    failures = []
    for tpl_id, (identite, want_from, want_reply) in sorted(EXPECTED.items()):
        check(tpl_id, identite, want_from, want_reply, failures)

    if failures:
        print(f"ECHEC — {len(failures)} probleme(s) :")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"OK — les {len(EXPECTED)} templates sont conformes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Lancer le vérificateur — il DOIT échouer**

```bash
cd d:/be-yours-mylab/scripts/odoo && python verify_mail_identities.py
```

Attendu : exit 1, et une liste d'échecs cohérente avec l'état actuel — les 8 templates ont un
`email_from` en `yoann@`, aucun n'a de marqueurs. Typiquement :

```
ECHEC — 24 probleme(s) :
  - tpl 18 (Invoice: Sending): email_from='"Service Comptabilité MY.LAB" <yoann@mylab-shop.com>' attendu '"MY.LAB – Comptabilité" <comptabilite@mylab-shop.com>'
  - tpl 18 (Invoice: Sending): reply_to='yoann@mylab-shop.com' attendu 'comptabilite@mylab-shop.com'
  - tpl 18 (Invoice: Sending): marqueurs signature = 0 start / 0 end, attendu 1/1
  ...
```

Si le vérificateur passe à ce stade, il est faux — ne pas continuer.

- [ ] **Step 3: Commit**

```bash
cd d:/be-yours-mylab
git add scripts/odoo/verify_mail_identities.py
git commit -m "test(mail): vérificateur d'état cible des identités d'envoi

Assertions sur les 8 templates : email_from, reply_to, marqueurs de
signature uniques, bonne signature par identité, aucun bloc résiduel
hors marqueurs. Échoue sur l'état actuel (tout part de yoann@).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3 : Le script de déploiement (dry-run uniquement)

**Files:**
- Create: `scripts/odoo/step41_split_mail_identities.py`

**Interfaces:**
- Consumes: `docs/signature-email-{contact,comptabilite}.html` (Task 1) ; helpers `search_read`,
  `write` de `_client.py`.
- Produces: `scripts/odoo/backups/mail_templates_pre-identity-split_2026-07-15.json` et l'état
  que `verify_mail_identities.py` (Task 2) valide. CLI : `--dry-run` (défaut : écrit).

- [ ] **Step 1: Écrire le script**

Créer `scripts/odoo/step41_split_mail_identities.py` :

```python
"""step41 — Separe les identites d'envoi : contact@ (devis) / comptabilite@ (compta).

Idempotent. Au 1er passage, remplace le bloc signature existant (en dur ou dynamique)
par la signature cible encadree de marqueurs. Aux passages suivants, remplace simplement
le contenu entre marqueurs.

Usage :
    python step41_split_mail_identities.py --dry-run   # inspecte, n'ecrit rien
    python step41_split_mail_identities.py             # backup puis ecrit
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from _client import search_read, write

REPO = Path(__file__).resolve().parents[2]
SIG_FILES = {
    "contact": REPO / "docs" / "signature-email-contact.html",
    "compta": REPO / "docs" / "signature-email-comptabilite.html",
}
BACKUP = Path(__file__).resolve().parent / "backups" / "mail_templates_pre-identity-split_2026-07-15.json"

MARK_START = "<!-- ML_SIG_START -->"
MARK_END = "<!-- ML_SIG_END -->"

CONTACT_FROM = '"MY.LAB" <contact@mylab-shop.com>'
CONTACT_REPLY = "contact@mylab-shop.com"
COMPTA_FROM = '"MY.LAB – Comptabilité" <comptabilite@mylab-shop.com>'
COMPTA_REPLY = "comptabilite@mylab-shop.com"

ROUTING = {
    34: ("contact", CONTACT_FROM, CONTACT_REPLY),
    18: ("compta", COMPTA_FROM, COMPTA_REPLY),
    20: ("compta", COMPTA_FROM, COMPTA_REPLY),
    35: ("compta", COMPTA_FROM, COMPTA_REPLY),
    36: ("compta", COMPTA_FROM, COMPTA_REPLY),
    37: ("compta", COMPTA_FROM, COMPTA_REPLY),
    38: ("compta", COMPTA_FROM, COMPTA_REPLY),
    39: ("compta", COMPTA_FROM, COMPTA_REPLY),
}

# 1. deja marque (passages >= 2)
RE_MARKED = re.compile(re.escape(MARK_START) + r".*?" + re.escape(MARK_END), re.S)
# 2. bloc signature dynamique Odoo (tpl 34, 20) ; groupe 1 = nom du champ (user_id, invoice_user_id...)
RE_USER_SIG = re.compile(
    r'<t t-if="not is_html_empty\(object\.(\w+)\.signature\)".*?</t>\s*</t>', re.S
)
# 3. signature en dur (tpl 18, 35-39) : table contenant l'adresse, sans table imbriquee
RE_HARD_SIG = re.compile(
    r"<table\b(?:(?!<table\b).)*?231 Avenue de la Voguette.*?</table>", re.S
)


def wrap(sig_html):
    return f"{MARK_START}{sig_html}{MARK_END}"


def inject(body, sig_html):
    """Retourne (nouveau_body, strategie). Leve ValueError si aucun point d'ancrage."""
    block = wrap(sig_html)
    if RE_MARKED.search(body):
        return RE_MARKED.sub(lambda _: block, body, count=1), "marqueurs"
    m = RE_USER_SIG.search(body)
    if m:
        field = m.group(1)
        new_body = body[:m.start()] + block + body[m.end():]
        return new_body, f"{field}.signature"
    if RE_HARD_SIG.search(body):
        return RE_HARD_SIG.sub(lambda _: block, body, count=1), "signature en dur"
    raise ValueError("aucun point d'ancrage signature trouve")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="inspecte sans ecrire")
    args = ap.parse_args()

    sigs = {}
    for key, path in SIG_FILES.items():
        if not path.exists():
            print(f"ABANDON — signature introuvable : {path}")
            return 1
        sigs[key] = path.read_text(encoding="utf-8").strip()

    rows = search_read(
        "mail.template", [("id", "in", sorted(ROUTING))],
        ["id", "name", "email_from", "reply_to", "body_html"],
    )
    found = {r["id"]: r for r in rows}
    missing = sorted(set(ROUTING) - set(found))
    if missing:
        print(f"ABANDON — templates introuvables : {missing}")
        return 1

    # Plan construit AVANT tout backup : un ancrage introuvable doit sortir sans
    # avoir touche au backup (rows est deja fige, deplacer le backup plus loin
    # ne change rien a sa fidelite).
    plan = []
    for tpl_id in sorted(ROUTING):
        identite, want_from, want_reply = ROUTING[tpl_id]
        t = found[tpl_id]
        try:
            new_body, strategie = inject(t.get("body_html") or "", sigs[identite])
        except ValueError as exc:
            print(f"ABANDON — tpl {tpl_id} ({t['name']}) : {exc}. Aucune ecriture effectuee.")
            return 1
        plan.append((tpl_id, t, identite, want_from, want_reply, new_body, strategie))

    print(f"\n{'=' * 72}")
    for tpl_id, t, identite, want_from, want_reply, new_body, strategie in plan:
        print(f"tpl {tpl_id:>2} {t['name'][:34]:<36} [{identite}] via {strategie}")
        print(f"      from  {t.get('email_from')!r}")
        print(f"        ->  {want_from!r}")
        print(f"      reply {t.get('reply_to')!r} -> {want_reply!r}")
        print(f"      body  {len(t.get('body_html') or '')} -> {len(new_body)} car.")

    if args.dry_run:
        print(f"\n--dry-run : aucune ecriture. {len(plan)} templates seraient modifies.")
        return 0

    # Backup APRES validation du plan, juste AVANT la boucle d'ecriture. Le backup
    # a une semantique "etat pre-bascule" : il ne doit etre ecrit qu'une seule fois,
    # au tout premier run reel — un rejeu ne doit jamais l'ecraser avec l'etat deja
    # splitte, sinon le seul chemin de rollback disparait.
    if BACKUP.exists():
        print(f"Backup deja present, conserve tel quel (etat vierge pre-bascule) : {BACKUP}")
    else:
        try:
            BACKUP.parent.mkdir(parents=True, exist_ok=True)
            BACKUP.write_text(
                json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"Backup ecrit : {BACKUP} ({len(rows)} templates)")
        except Exception as exc:
            print(f"ABANDON — backup impossible : {exc}. Aucune ecriture effectuee.")
            return 1

    for tpl_id, _t, _identite, want_from, want_reply, new_body, _strategie in plan:
        write("mail.template", [tpl_id], {
            "email_from": want_from,
            "reply_to": want_reply,
            "body_html": new_body,
        })
        print(f"  ecrit tpl {tpl_id}")

    print(f"\n{len(plan)} templates mis a jour. Lancer verify_mail_identities.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Lancer en dry-run**

```bash
cd d:/be-yours-mylab/scripts/odoo && python step41_split_mail_identities.py --dry-run
```

Attendu : exit 0, aucune écriture, et un plan à 8 lignes. Contrôler point par point :

- tpl 34 → `[contact] via user_id.signature`
- tpl 20 → `[compta] via invoice_user_id.signature`
- tpl 18, 35, 36, 37, 38, 39 → `[compta] via signature en dur`
- Aucune ligne `ABANDON`.
- Les longueurs de corps varient de quelques centaines de caractères, pas d'un facteur 2 (un
  corps qui doublerait signalerait une injection en double plutôt qu'un remplacement).

Si un template sort en `ABANDON — aucun point d'ancrage`, ne pas contourner en relâchant la
regex : inspecter le corps réel avec `probe_template_signatures.py` et corriger l'ancrage.

- [ ] **Step 3: Vérifier que le dry-run n'a rien écrit**

```bash
cd d:/be-yours-mylab/scripts/odoo && python verify_mail_identities.py
```

Attendu : exit 1, mêmes échecs qu'en Task 2. Le dry-run doit être totalement inerte.

- [ ] **Step 4: Commit**

```bash
cd d:/be-yours-mylab
git add scripts/odoo/step41_split_mail_identities.py
git commit -m "feat(mail): script idempotent de séparation des identités d'envoi

Backup JSON préalable, puis email_from/reply_to et injection du bloc
signature encadré de marqueurs ML_SIG_START/END. Trois stratégies
d'ancrage par ordre de priorité (marqueurs, user_id.signature, table
en dur), échec explicite sans écriture si aucune ne matche.

--dry-run pour inspecter. Pas encore appliqué sur le live.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4 : Application sur le live

**Files:**
- Create: `scripts/odoo/backups/mail_templates_pre-identity-split_2026-07-15.json` (généré)

**Interfaces:**
- Consumes: `step41_split_mail_identities.py` (Task 3), `verify_mail_identities.py` (Task 2).
- Produces: les 8 templates dans leur état cible sur l'Odoo live.

**Gate :** ne pas exécuter sans validation explicite de Yoann. Écrit sur le live, et modifie
les templates que les crons de relance et le workflow n8n utilisent. À partir d'ici, tout
mail envoyé par ces flux porte la nouvelle identité.

- [ ] **Step 1: Confirmer qu'aucune édition UI n'est en cours**

Demander à Yoann de fermer tout formulaire de template mail ouvert dans Odoo. L'UID 8 est
partagé : une écriture concurrente pendant le script produit un état incohérent.

- [ ] **Step 2: Appliquer**

```bash
cd d:/be-yours-mylab/scripts/odoo && python step41_split_mail_identities.py
```

Attendu : `Backup ecrit : …json (8 templates)`, puis 8 lignes `ecrit tpl NN`, puis
`8 templates mis a jour.`

- [ ] **Step 3: Vérifier — le vérificateur DOIT passer**

```bash
cd d:/be-yours-mylab/scripts/odoo && python verify_mail_identities.py
```

Attendu : `OK — les 8 templates sont conformes`, exit 0.

- [ ] **Step 4: Vérifier l'idempotence**

```bash
cd d:/be-yours-mylab/scripts/odoo && python step41_split_mail_identities.py --dry-run
```

Attendu : les 8 templates sortent maintenant `via marqueurs` — c'est ce qui prouve que
l'ancrage est stable et qu'un rejeu ne peut plus toucher qu'au contenu entre marqueurs.

En revanche, **les longueurs ne seront pas identiques** (`body  2880 -> 2921 car.`), et c'est
normal : Odoo décode les entités HTML au stockage (`&eacute;` → `é`, `&rsquo;` → `’`,
`&mdash;` → `—`, `&middot;` → `·`), soit ~41 caractères de moins que ce qu'on envoie. Le
script relit donc une version normalisée et se croit toujours obligé de réécrire.

La bonne formulation : le script **converge** (l'état stocké est un point fixe — réécrire
produit exactement le même résultat) sans être **inerte** (il refait 8 écritures RPC à chaque
rejeu). C'est sans conséquence : le mail rendu est identique et les marqueurs survivent au
décodage. Ne pas « corriger » ce comportement en normalisant les entités côté client — ce
serait fragile pour un gain nul.

- [ ] **Step 5: Commit du backup**

```bash
cd d:/be-yours-mylab
git add scripts/odoo/backups/mail_templates_pre-identity-split_2026-07-15.json
git commit -m "chore(mail): backup des 8 templates avant séparation des identités

État pré-bascule (email_from en yoann@, signatures d'origine), pour
restauration si le canari révèle une réécriture Gmail.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5 : Canari — les en-têtes réellement reçus

**Files:**
- Create: `scripts/odoo/canary_mail_identities.py`

**Interfaces:**
- Consumes: l'état live produit par Task 4.
- Produces: trois mails dans la boîte `yoann@mylab-shop.com`, dont les en-têtes `From` sont
  relus manuellement. Aucun artefact Odoo persistant (nettoyage en fin de script).

**Gate :** envoie de vrais mails. Ne pas lancer sans validation explicite de Yoann.

C'est l'étape qui compte. Odoo peut afficher `email_from = comptabilite@…` tout en voyant
Gmail réécrire le From en `yoann@` au relais SMTP, silencieusement. Seul l'en-tête **reçu**
fait foi — ne jamais conclure depuis `mail.mail.email_from`, qui n'enregistre que l'intention.

- [ ] **Step 1: Écrire le canari**

Créer `scripts/odoo/canary_mail_identities.py` :

```python
"""Canari — envoie 1 devis + 1 facture + 1 relance de test vers yoann@mylab-shop.com.

Cree un partenaire et des brouillons dediés, envoie, puis nettoie. Aucun client reel
n'est destinataire : le partenaire de test porte l'adresse yoann@mylab-shop.com.
La facture reste en brouillon -> aucun numero de sequence consomme.

Usage :
    python canary_mail_identities.py           # envoie puis nettoie
    python canary_mail_identities.py --keep    # laisse les enregistrements pour inspection
"""
import argparse
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from _client import execute, search_read, create, unlink

TEST_EMAIL = "yoann@mylab-shop.com"
TEST_PARTNER_NAME = "ZZ Canari Identites Mail — NE PAS UTILISER"
COMPANY_ID = 3

# (tpl_id, libelle, identite attendue dans le From recu)
SENDS = [
    (34, "Devis", "contact@mylab-shop.com"),
    (18, "Facture", "comptabilite@mylab-shop.com"),
    (37, "Relance facture L1", "comptabilite@mylab-shop.com"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="ne pas supprimer les enregistrements")
    args = ap.parse_args()

    created = {"partner": [], "order": [], "move": []}
    try:
        partner_id = create("res.partner", {
            "name": TEST_PARTNER_NAME,
            "email": TEST_EMAIL,
            "company_id": COMPANY_ID,
        })
        created["partner"].append(partner_id)
        print(f"Partenaire de test : {partner_id} <{TEST_EMAIL}>")

        product = search_read("product.product", [("sale_ok", "=", True)], ["id", "name"], limit=1)
        if not product:
            print("ABANDON — aucun produit vendable trouve")
            return 1
        pid = product[0]["id"]

        order_id = create("sale.order", {
            "partner_id": partner_id,
            "company_id": COMPANY_ID,
            "order_line": [(0, 0, {"product_id": pid, "product_uom_qty": 1})],
        })
        created["order"].append(order_id)
        print(f"Devis de test : {order_id}")

        move_id = create("account.move", {
            "partner_id": partner_id,
            "company_id": COMPANY_ID,
            "move_type": "out_invoice",
            "invoice_line_ids": [(0, 0, {"product_id": pid, "quantity": 1, "price_unit": 10.0})],
        })
        created["move"].append(move_id)
        print(f"Facture de test (brouillon) : {move_id}")

        res_for = {34: order_id, 18: move_id, 37: move_id}
        for tpl_id, libelle, attendu in SENDS:
            execute("mail.template", "send_mail", [tpl_id, res_for[tpl_id]],
                    {"force_send": True})
            print(f"  envoye  tpl {tpl_id:>2} {libelle:<20} -> From attendu : {attendu}")
            time.sleep(2)

        print("\nEnvoi termine. Verifier maintenant les EN-TETES RECUS dans Gmail,")
        print("PAS mail.mail.email_from cote Odoo (qui ne reflete que l'intention).")
        return 0
    finally:
        # Aucun `return` dans ce finally : il avalerait l'exception en cours et
        # ferait sortir le script en code 0 alors que l'envoi a echoue.
        if args.keep:
            print(f"\n--keep : enregistrements conserves {created}")
        else:
            for model, ids in (("account.move", created["move"]),
                               ("sale.order", created["order"]),
                               ("res.partner", created["partner"])):
                for rid in ids:
                    try:
                        unlink(model, [rid])
                        print(f"  supprime {model} {rid}")
                    except Exception as exc:
                        print(f"  ATTENTION — {model} {rid} non supprime : {exc}")


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Lancer le canari**

```bash
cd d:/be-yours-mylab/scripts/odoo && python canary_mail_identities.py
```

Attendu : 3 lignes `envoye tpl …`, puis le nettoyage des 3 enregistrements.

- [ ] **Step 3: Lire les en-têtes RÉELLEMENT reçus**

Attendre ~1 min, puis relire les trois mails arrivés dans la boîte `yoann@mylab-shop.com` et
relever l'expéditeur affiché de chacun.

Critère d'acceptation :

| Mail | `From` reçu attendu |
|------|---------------------|
| Devis de test | `contact@mylab-shop.com` |
| Facture de test | `comptabilite@mylab-shop.com` |
| Relance facture L1 de test | `comptabilite@mylab-shop.com` |

**Si un From arrive en `yoann@mylab-shop.com`** : Gmail réécrit, l'alias n'est pas un « send as »
valide pour le chemin SMTP. Ne pas insister côté Odoo — le correctif est côté Gmail
(Paramètres → Comptes → *Ajouter une autre adresse e-mail*, puis vérification). Restaurer
l'état antérieur depuis le backup de Task 4 si Yoann veut annuler entre-temps.

- [ ] **Step 4: Consigner le résultat dans la spec**

Ajouter à `docs/superpowers/specs/2026-07-15-odoo-mail-identities-design.md`, sous une nouvelle
section `## Résultat du canari (2026-07-15)`, les trois From effectivement observés. Cette trace
évite de refaire le test au prochain doute.

- [ ] **Step 5: Commit**

```bash
cd d:/be-yours-mylab
git add scripts/odoo/canary_mail_identities.py docs/superpowers/specs/2026-07-15-odoo-mail-identities-design.md
git commit -m "test(mail): canari des identités d'envoi + résultat observé

Envoie 1 devis, 1 facture et 1 relance de test vers yoann@ via un
partenaire dédié (aucun client réel destinataire, facture laissée en
brouillon donc aucun numéro consommé), puis nettoie.

Consigne les en-têtes From réellement reçus dans la spec.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6 : Le chemin manuel « Envoyer & Imprimer »

**Files:**
- Modify: `docs/superpowers/specs/2026-07-15-odoo-mail-identities-design.md` (section résultat)

**Interfaces:**
- Consumes: le canari de Task 5 (qui couvre `send_mail`, pas le wizard).
- Produces: une conclusion documentée sur le comportement de `account.move.send`.

Les flux automatiques passent par `mail.template.send_mail()` et héritent de `email_from`.
L'envoi manuel d'une facture depuis l'UI passe par le wizard `account.move.send`, qui pourrait
recalculer le From. On l'inspecte par lecture de source plutôt que par un envoi réel : tester
ce chemin en vrai exigerait une facture **postée**, donc un numéro de séquence consommé pour rien.

- [ ] **Step 1: Inspecter la source du wizard dans le conteneur**

Se connecter au VPS (paramiko, cf. `reference_vps_ssh_python.md` — `sshpass` indisponible) et
chercher comment le wizard construit le From :

```bash
docker exec odoo grep -rn "email_from" /usr/lib/python3/dist-packages/odoo/addons/account/models/account_move_send.py
```

Si le chemin diffère, le localiser d'abord :

```bash
docker exec odoo find / -name "account_move_send.py" -not -path "*/node_modules/*" 2>/dev/null
```

- [ ] **Step 2: Conclure et documenter**

Deux issues possibles :

- Le wizard rend `email_from` depuis le template (typiquement via `_get_mail_params` /
  `mail_template_id._generate_template`) → le chemin manuel hérite, rien à faire. Le noter.
- Le wizard force une autre valeur (ex. `company_id.email` ou `invoice_user_id.email_formatted`)
  → le chemin manuel enverra encore depuis `yoann@`. Le noter comme limite connue **sans le
  corriger dans ce lot** : surcharger un wizard standard dépasse le périmètre de cette spec et
  mérite sa propre décision.

Renseigner la conclusion dans la section `## Résultat du canari` de la spec, en citant le
fichier et la ligne observés.

- [ ] **Step 3: Commit**

```bash
cd d:/be-yours-mylab
git add docs/superpowers/specs/2026-07-15-odoo-mail-identities-design.md
git commit -m "docs(mail): conclusion sur le chemin manuel account.move.send

Inspection de la source du wizard pour déterminer si l'envoi manuel
d'une facture depuis l'UI hérite de l'email_from du template.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7 : Signatures Gmail et mise à jour de la mémoire

**Files:**
- Modify: `C:\Users\startec\.claude\projects\d--be-yours-mylab\memory\feedback_gmail_signature.md`
- Modify: `C:\Users\startec\.claude\projects\d--be-yours-mylab\memory\MEMORY.md`

**Interfaces:**
- Consumes: les deux fichiers signature de Task 1.
- Produces: mémoire à jour ; Gmail configuré par Yoann (action manuelle).

- [ ] **Step 1: Fournir la procédure Gmail à Yoann**

L'API Gmail disponible ici ne couvre pas les paramètres « send as » — c'est manuel. Étapes,
à faire une fois par alias :

1. Gmail → Paramètres (roue dentée) → *Voir tous les paramètres*
2. Onglet *Comptes et importation* → section *Envoyer des e-mails en tant que*
3. `contact@mylab-shop.com` → *modifier les informations* → coller le contenu de
   `docs/signature-email-contact.html` dans le bloc signature
4. Idem pour `comptabilite@mylab-shop.com` avec `docs/signature-email-comptabilite.html`

Coller le HTML rendu (ouvrir le fichier dans un navigateur, tout sélectionner, copier) et non
le code source — l'éditeur de signature Gmail est WYSIWYG, il n'accepte pas le HTML brut.

- [ ] **Step 2: Mettre à jour la mémoire**

`feedback_gmail_signature.md` référence `docs/signature-email.html`, qui n'existe plus. Réécrire
le corps pour pointer vers les deux fichiers et expliquer la règle de choix :

```markdown
---
name: gmail-signature
description: Deux signatures MY.LAB — contact (Yoann/Dirigeant) et comptabilité (L'équipe MY.LAB), une par alias et par identité de template Odoo
metadata:
  type: feedback
---

Deux signatures HTML, sourcées dans le repo, à mettre au bas des mails :
`docs/signature-email-contact.html` (Yoann DURAND / Dirigeant / contact@) et
`docs/signature-email-comptabilite.html` (L'équipe MY.LAB / Comptabilité / comptabilite@).

**Why:** depuis le 2026-07-15, MY.LAB sépare l'avant-vente (devis, contact@) du recouvrement
(facture, avoir, relances, comptabilite@). Une seule signature ne peut pas couvrir les deux —
et un utilisateur Odoo n'ayant qu'un champ `signature`, les templates portent leur signature
en dur, encadrée des marqueurs `<!-- ML_SIG_START/END -->`.

**How to apply:** choisir la signature selon l'identité de l'expéditeur, pas selon le sujet.
Dans les templates Odoo, ne jamais réintroduire `user_id.signature` : ça casserait la
séparation. Voir [[odoo-mail-identities]].
```

Puis mettre à jour la ligne correspondante dans `MEMORY.md` pour refléter les deux fichiers.

- [ ] **Step 3: Écrire la mémoire projet**

Créer `odoo-mail-identities.md` dans le dossier mémoire :

```markdown
---
name: odoo-mail-identities
description: Routage des 8 templates mail Odoo vers contact@ (devis) ou comptabilite@ (facture, avoir, relances)
metadata:
  type: project
---

Depuis le 2026-07-15 : tpl 34 (devis) part de `"MY.LAB" <contact@mylab-shop.com>` ; tpl 18
(facture), 20 (avoir) et 35-39 (relances) partent de
`"MY.LAB – Comptabilité" <comptabilite@mylab-shop.com>`. Les deux alias sont des « send as »
du compte Gmail `yoann@mylab-shop.com`, donc les réponses arrivent dans la même boîte.

**Why:** le client recevait ses devis et ses mises en demeure de la même adresse personnelle.
Décision « compta large » de Yoann : seul le devis est de l'avant-vente.

**How to apply:** le serveur SMTP « Gmail Mylab » (id=2) a `from_filter = mylab-shop.com`, donc
aucune modif d'infra n'est nécessaire pour ajouter une identité `@mylab-shop.com` — il suffit
de poser `email_from` sur le template. Rejouer
`scripts/odoo/step41_split_mail_identities.py` (idempotent) après toute retouche de signature,
puis `verify_mail_identities.py`. Hors périmètre et toujours en `yoann@` : tpl 22, 23, 24, 27.
Voir [[gmail-signature]].
```

Ajouter la ligne correspondante dans `MEMORY.md`.

- [ ] **Step 4: Commit**

```bash
cd d:/be-yours-mylab
git add -A && git commit -m "docs(mail): procédure Gmail et mémoire des identités d'envoi

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

Les fichiers mémoire vivent hors du repo (`~/.claude/projects/…`) et ne seront pas capturés
par ce commit — c'est normal, ils sont versionnés séparément.

---

## Self-Review

**Couverture de la spec :**

| Exigence de la spec | Task |
|---------------------|------|
| Routage des 8 templates (email_from + reply_to) | 3, 4 |
| Deux fichiers signature sourcés dans `docs/` | 1 |
| Renommage `signature-email.html` → `-contact.html` | 1 |
| Script idempotent + marqueurs ML_SIG_START/END | 3, 4 (étape 4 = preuve d'idempotence) |
| Backup JSON avant écriture | 3 (code), 4 (exécution + commit) |
| Uniformisation `user_id.signature` → en dur (tpl 34, 20) | 3 (stratégie d'ancrage), 2 (assertion anti-résidu) |
| Échec explicite si ancrage introuvable | 3 |
| Canari + lecture des en-têtes reçus | 5 |
| Vérification du chemin `account.move.send` | 6 |
| Signatures Gmail (manuel) | 7 |
| Mise à jour mémoire `feedback_gmail_signature.md` | 7 |
| Hors périmètre (tpl 22, 23, 24, 27 ; `res.users(8).signature`) | non touchés ; consigné en mémoire (Task 7) |

**Cohérence des noms :** `MARK_START`/`MARK_END`, `CONTACT_FROM`/`COMPTA_FROM`,
`CONTACT_REPLY`/`COMPTA_REPLY` et le dict `ROUTING`/`EXPECTED` portent les mêmes valeurs dans
`step41_split_mail_identities.py` et `verify_mail_identities.py`. Les deux fichiers les
redéclarent au lieu de partager un module commun : c'est délibéré — un vérificateur qui
importerait les constantes du script vérifierait la cohérence interne du script, pas sa
conformité à la spec.

**Point de vigilance connu :** `RE_HARD_SIG` s'ancre sur `231 Avenue de la Voguette`. Si
l'adresse de MY.LAB change un jour, le script échouera franchement (`ABANDON — aucun point
d'ancrage`) plutôt que de corrompre un corps — c'est le comportement voulu, mais l'ancrage
devra alors être mis à jour. Après le premier passage, les marqueurs prennent le relais et
l'ancrage sur l'adresse n'est plus sollicité.
