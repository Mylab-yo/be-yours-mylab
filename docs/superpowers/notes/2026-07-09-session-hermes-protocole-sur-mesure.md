# Session 08–09/07/2026 — Protocole /mails Hermes, offre sur-mesure, fixes Bastien

Note de session (travail réalisé en grande partie hors de ce repo : skills Hermes locaux + VPS).

## 1. Post-mortem session Hermes du 08/07 (brouillons email)

La session `/mails` d'Hermes local a déraillé sur le brouillon Bintou (S00623) :

- **Faux diagnostic « brouillon vide »** : relecture du brouillon sans `--folder "[Gmail]/Brouillons"` → himalaya lit l'INBOX → sortie vide. Les brouillons étaient en réalité complets et correctement threadés (`In-Reply-To` exact).
- **Vrai constat mal interprété** : un brouillon déposé par IMAP n'apparaît pas *dans* la conversation Gmail web — limite Gmail (pas de threadId via IMAP), pas un bug. Le rattachement se fait à l'envoi.
- **Spirale** : RFC822/quoted-printable écrit à la main (`é` cassés, `€` → `©` dans un email de paiement), commandes identiques relancées en boucle, faux « Brouillon 3 créé » sans exécution, doublon Bintou.
- Hermes avait mis en attente un patch de skill institutionnalisant la mauvaise leçon → **supprimé**.

### Durcissements appliqués (skills Hermes locaux, hors repo)

- `draft-creator.py` : **garde anti-doublon mécanique** (refus exit 1 si un brouillon existe pour le destinataire ; `--replace` pour corriger). Testé.
- Skill `/mails` réécrit en **protocole verrouillé** : 7 interdictions absolues, cycle A→E par email (faits Odoo AVANT rédaction, création unique, preuve `[OK]`), vérification finale obligatoire du dossier Brouillons, STOP après 2 échecs identiques.
- `mylab-email-rules` + skill `email/himalaya` : recettes contradictoires purgées (plus de `message save`/RFC822 manuel), lecture brouillon documentée avec `--folder`.

## 2. Offre « Projet sur-mesure » (nouvelle section home)

MY.LAB met désormais en relation avec ses **laboratoires partenaires** pour : modification de la formule existante du client, création de formule sur-mesure, formulation à façon. Formulaire : `https://mylab-shop.com/pages/projet-sur-mesure`. Les formules du **catalogue** restent fixes (aucune modification). Zéro promesse tarifs/délais/MOQ pour le sur-mesure.

Propagé dans les **3 systèmes de réponse client** (chacun a sa propre copie des règles) :

1. **Hermes local** : `SOUL.md`, `mylab-email-rules` §2/§3, `references/infos-commerciales-b2b.md`.
2. **Chatbot Bastien** (VPS `/root/bastien/kb/`) : `40-conditions.md`, `60-faq.md`, `70-liens.md`.
3. **Répondeur email cron** (conteneur `hermes-gateway`, `/opt/data/email_responder_prompt.md`) — règle périmée « modif parfum/actifs dès 50L ≈ 3 000 € » supprimée (jamais validée).

Tests Bastien validés dans les deux sens : sur-mesure → formulaire ; modification formule catalogue → refus ferme puis bascule sur-mesure. Piège tarifaire : aucune invention.

## 3. Circuit du formulaire projet sur-mesure — vérifié bout en bout

Formulaire → webhook n8n `projet-sur-mesure` → workflow « MY.LAB — Projet sur-mesure (mise en relation) » (`c2jg5izEjB9o7fNq`, créé 08/07 15:45) → lead Airtable → notif Yoann → AR client. 3 soumissions de test = 3 notifs + 3 AR reçus. Chaîne linéaire : si Airtable échoue, aucun email ne part (cause de l'échec du 1ᵉʳ test de Yoann à 15:45).

## 4. Fixes Bastien

- **Reload KB** : `docker exec … reload_kb()` ne recharge PAS le serveur (process séparé, KB cachée en mémoire, pas de route HTTP). Seul `docker restart bastien-svc` applique une modif KB. Skill `mylab-chatbot-ops` corrigé. Attention aussi à l'**ancrage d'historique** par session (tester en session neuve).
- **Liens 404 (ponctuation collée à l'URL)** : sanitizer serveur `_strip_url_trailing_punct` dans `src/bastien/main.py` (commit `47ab684` sur le repo VPS `/root/bastien`, rebuildé, testé live) + regex linkify durcie dans `snippets/bastien-widget.liquid` (ce repo — **fix widget déployé avec ce commit côté code, à pousser sur le thème live via theme push**).
- **Liens RDV unifiés** sur `https://cal.com/yoann-durand-ry0bng/etude-projet-marque-capillaire` (l'ancien `cal.eu/yoann-durand-xyj75z` reste actif en ligne mais plus référencé nulle part).

## Reste à faire

- [ ] Pousser `snippets/bastien-widget.liquid` sur le thème live (theme push ou copier la ligne 349 dans l'admin).
- [ ] Nettoyer les 4 leads de test Airtable (`Claude-*` + 1 vide) et les emails 🧪 de test.
- [ ] Configurer le push GitHub du repo VPS `/root/bastien` (ahead 6 d'origin/main).
- [ ] Optionnel : filtre Gmail « 🧪 Nouveau projet sur-mesure » → label `Prospects`.
