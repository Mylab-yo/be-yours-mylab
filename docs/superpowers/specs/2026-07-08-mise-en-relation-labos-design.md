# Mise en relation labos partenaires — Design

**Date** : 2026-07-08
**Statut** : validé sur les choix structurants, en attente relecture finale Yoann

## Contexte & objectif

La home affiche une carte « Hors périmètre » (bloc `col_exclude` de la section `perimeter_columns`, `templates/index.json`) qui liste ce que MY.LAB ne fait pas (modification de formule, sur-mesure, formulation à façon, études cliniques) et renvoie vers le catalogue. C'est une impasse commerciale : le prospect sur-mesure repart sans rien.

Nouveau modèle : MY.LAB devient apporteur d'affaires. Le prospect décrit son projet via un formulaire ; MY.LAB le qualifie et le transmet à ses laboratoires partenaires ; MY.LAB prend un pourcentage du CA de chaque projet validé (accord commercial MY.LAB ↔ labo, invisible côté client).

## Décisions actées

| Décision | Choix |
|---|---|
| Circuit du lead | Lead → Yoann (mail + Airtable). Qualification et transmission au labo **manuelles**. Aucun envoi automatique à un tiers. |
| Formulaire | Page dédiée + section Liquid custom, **clone du pattern catalogue** (`ml-catalogue-request.liquid`) |
| URL | `/pages/projet-sur-mesure` |
| Niveau de qualification | ~10 champs (identité + projet) |
| Accusé de réception client | Oui, mail auto via n8n, promesse « retour sous 48 h » |
| Stockage leads | Nouvelle table **« Leads sur-mesure »** dans la base Airtable existante « Espace de travail mylab » (`appdWBkaxdGnJAqxU`) |
| Commission | Suivi manuel dans Airtable (colonnes pipeline). Aucune mention côté client. |

## Composant 1 — Carte home « Projet sur-mesure »

Modification du seul bloc `col_exclude` de `perimeter_columns` (`templates/index.json`) :

- **Titre** : `<em>Projet sur-mesure ?</em>` (remplace « Hors périmètre »)
- **Texte** : la liste des 4 items reste, précédée d'une phrase qui inverse le message, ex. : « Ces projets dépassent notre catalogue — nos laboratoires partenaires les réalisent. Nous vous mettons en relation gratuitement : » suivi de la liste existante.
- **CTA** : « Décrivez-nous votre projet » → `shopify://pages/projet-sur-mesure` (remplace « Voir le catalogue de formules »)

Contraintes maison : modification **chirurgicale** du bloc (jamais de full-PUT de `templates/index.json`, cf. gotcha Theme Editor), test sur **thème dev** (`--development --nodelete`), mise en live seulement sur « PUSH LIVE » explicite.

## Composant 2 — Page `/pages/projet-sur-mesure` + section `ml-partner-request.liquid`

Clone structurel de `ml-catalogue-request.liquid` : même DA (hero Cormorant Garamond italic + DM Sans, grid 2 colonnes contenu/formulaire, mêmes classes de champ), préfixe classes `ml-partner__`.

**Colonne gauche (contenu)** : promesse et déroulé — 1. Décrivez votre projet · 2. MY.LAB sélectionne le laboratoire partenaire adapté · 3. Mise en relation sous 48 h. Arguments : labos français, accompagnement MY.LAB, gratuit et sans engagement.

**Colonne droite (formulaire)** :

| Champ | Type | Requis |
|---|---|---|
| Prénom / Nom | text ×2 | oui |
| Email | email | oui |
| Téléphone | tel | non |
| Marque / société | text | non |
| Type de projet | select : Modification de formule existante · Création de formule sur-mesure · Formulation à façon · Études cliniques · Autre | oui |
| Catégorie produit | select : Capillaire · Soin visage · Corps · Hygiène · Autre | oui |
| Quantités envisagées | select : < 500 u · 500–1 000 · 1 000–5 000 · > 5 000 · Je ne sais pas encore | non |
| Échéance | select : < 3 mois · 3–6 mois · 6–12 mois · Pas de date | non |
| Description du projet | textarea | oui |
| Consentement | checkbox, requis : « J'accepte que MY.LAB transmette ces informations à ses laboratoires partenaires pour l'étude de mon projet. » + lien politique de confidentialité | oui |

**Mécanique** (identique au catalogue) : `submit` JS → POST JSON vers webhook n8n (URL en setting Theme Editor, vide par défaut) + **backup** POST `/contact` natif Shopify (filet si n8n down) + message succès inline. Payload : tous les champs + `source: "Shopify — page projet sur-mesure"` + `page_url`.

Le pourcentage de commission n'apparaît **nulle part** sur la page : mise en relation présentée comme gratuite (elle l'est, pour le client).

## Composant 3 — Workflow n8n « Mise en relation labos »

Nouveau workflow dédié (pas de mutualisation avec le workflow catalogue — parcours différents) :

1. **Webhook** (POST) — reçoit le payload du formulaire.
2. **Airtable create** — ligne dans « Leads sur-mesure » (statut initial « Nouveau »).
3. **Mail notification Yoann** (yoann@mylab-shop.com) — récap complet du lead, objet « 🧪 Nouveau projet sur-mesure — {marque ou nom} ».
4. **Mail AR client** — « Votre projet a bien été transmis, nous revenons vers vous sous 48 h avec le laboratoire adapté. » Signature MY.LAB.

Conventions maison : jsCode versionné dans `scripts/n8n/<wf>/`, secrets via `$env`, folder Yo, `this.helpers.httpRequest()`.

## Composant 4 — Table Airtable « Leads sur-mesure »

Base « Espace de travail mylab » (`appdWBkaxdGnJAqxU`). Champs formulaire : Prénom, Nom, Email, Téléphone, Marque/société, Type de projet (single select), Catégorie produit (single select), Quantités (single select), Échéance (single select), Description (long text), Date de soumission (dateTime), Source.

Champs pipeline (gestion Yoann) :

- **Statut** (single select) : Nouveau → Qualifié → Transmis labo → Devis en cours → Projet validé → Commission facturée · (+ Sans suite)
- **Labo partenaire** (single select, alimenté au fil de l'eau)
- **CA projet (€)** (currency), **% commission** (percent), **Commission due (€)** (formula = CA × %)
- **Notes** (long text)

## RGPD

Le partage de données client avec des tiers (labos) impose le consentement explicite → case dédiée au libellé transparent (composant 2). La transmission restant manuelle, Yoann contrôle chaque partage. Pas de données sensibles collectées.

## Hors scope v1

- Envoi automatique aux labos (routing par type de projet) — envisageable plus tard une fois le volume connu.
- Calcul/facturation automatique des commissions (Odoo) — le pipeline Airtable suffit au départ.
- Contrats d'apport d'affaires avec les labos — hors périmètre technique, à traiter par Yoann en parallèle.
- Espace labo partenaire (portail) — non.

## Critères de succès

- La carte home reformulée est en ligne (après validation sur thème dev) et pointe vers la page.
- Un formulaire soumis crée la ligne Airtable, notifie Yoann et envoie l'AR client en < 1 min.
- n8n down → la soumission arrive quand même dans Shopify admin (backup `/contact`).
- Zéro mention de commission côté client.

## Ordre d'implémentation

1. Table Airtable (MCP Airtable dispo dans la session).
2. Workflow n8n (webhook → Airtable → 2 mails), test avec payload factice.
3. Section `ml-partner-request.liquid` + page + template JSON, push thème dev, QA curl preview.
4. Modification carte home (bloc `col_exclude`), push thème dev, QA.
5. Validation Yoann sur dev → PUSH LIVE explicite.
