# MY.LAB Studio V3 — Lot 0 (spike fal.ai) + Lot 1 (fondations) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Valider la fidélité étiquette de la génération API (GO/NO-GO) et poser les fondations du funnel V3 : parcours Shopify réordonné (produits avant étiquette), modèle `Project`, webhook `orders/paid`, espace client « Mon projet » minimal.

**Architecture:** Deux repos. Le thème Shopify `be-yours-mylab` (pas de build, Liquid + JS vanilla IIFE) porte les étapes ①-② et le stepper. L'app Next.js `mylab-configurateur` (App Router, Prisma 7/Postgres, NextAuth magic link, Vercel) devient l'app Studio : elle reçoit le webhook Shopify et expose « Mon projet ». Le spike fal.ai vit dans `scripts/spike-fal/` de l'app (la lib sera réutilisée au Lot 4).

**Tech Stack:** Liquid/JS vanilla (thème) · Next.js 16 App Router + TypeScript strict + Prisma 7 + vitest 4 (app) · `@fal-ai/client` (spike) · Shopify Admin (webhook manuel).

**Spec de référence :** `docs/superpowers/specs/2026-07-08-mylab-studio-v3-design.md` (repo be-yours-mylab).

## Global Constraints

- **Deux repos** — chaque tâche indique son repo. Thème : `d:\Projets mylab vs code\be-yours-mylab`. App : `d:\Projets mylab vs code\mylab-configurateur`.
- **Thème** : aucun bundler — éditer les fichiers `assets/` directement ; JS en IIFE `'use strict'` ; préfixe `ml-` pour toute classe CSS ; ne jamais réactiver le cart-drawer natif Be Yours.
- **App** : TypeScript `strict`, alias `@/` → `src/`, client Prisma importé depuis `@/generated/prisma/client` (JAMAIS `@prisma/client`), routes API avec `NextResponse.json` et params async, tests vitest colocalisés (`*.test.ts` à côté du code), imports vitest explicites (`globals: false`). ⚠️ AGENTS.md du repo : Next 16 a des breaking changes — consulter `node_modules/next/dist/docs/` en cas de doute sur une API Next.
- **Handles Shopify verbatim** : dossier = `creation-du-dossier-cosmetologique` · forfaits = `forfait-dimpression-standard` / `forfait-dimpression` · collections = `modeles-detiquettes` / `boutique-adherents`.
- **Nouvel ordre du parcours (spec §2.1)** : 01 Dossier → **02 Produits** → **03 Étiquette** → 04 Récap. Prix inchangés (dossier 389,90 €).
- **Lot 4 ne démarre pas sans GO du Lot 0** (spec §9). Lot 0 peut tourner en parallèle des tâches thème/app.
- **Git** : jamais de commit sur `master` ; branches dédiées créées en Task 0. Commits fréquents, messages conventionnels français (convention du repo : `feat(parcours): …`).

---

### Task 0: Branches de travail

**Files:** aucun (git uniquement)

**Interfaces:**
- Produces: branche `feat/studio-v3-lot1-parcours` (thème) et `feat/studio-v3-lot1-fondations` (app). Toutes les tâches suivantes committent dessus.

- [ ] **Step 1: Créer la branche thème**

```bash
cd "d:\Projets mylab vs code\be-yours-mylab"
git checkout -b feat/studio-v3-lot1-parcours
```

- [ ] **Step 2: Créer la branche app**

```bash
cd "d:\Projets mylab vs code\mylab-configurateur"
git status   # vérifier qu'on part d'un état propre ; si des modifs non commitées existent, s'arrêter et demander à Yoann
git checkout -b feat/studio-v3-lot1-fondations
```

---

### Task 1 (Lot 0): Spike fal.ai — fidélité étiquette + coûts

**Repo:** `mylab-configurateur`

**Files:**
- Create: `scripts/spike-fal/README.md`
- Create: `scripts/spike-fal/models.ts`
- Create: `scripts/spike-fal/generate-images.ts`
- Create: `scripts/spike-fal/generate-video.ts`
- Create: `scripts/spike-fal/RAPPORT.md`
- Modify: `package.json` (dépendances `@fal-ai/client`, `tsx`)

**Interfaces:**
- Consumes: rien (autonome). Prérequis humains : compte fal.ai + `FAL_KEY` dans `.env.local` ; 3-5 photos de vrais flacons étiquetés fournies par Yoann dans `scripts/spike-fal/photos/<nom-flacon>/*.jpg`.
- Produces: `scripts/spike-fal/out/` (visuels générés + `manifest.json`) et `RAPPORT.md` complété → décision **GO/NO-GO** qui conditionne le Lot 4.

> Note TDD : ce spike est exploratoire (sortie = jugement visuel humain), il n'a pas de tests automatisés. C'est l'exception assumée du plan.

- [ ] **Step 1: Installer les dépendances**

```bash
cd "d:\Projets mylab vs code\mylab-configurateur"
npm install @fal-ai/client
npm install -D tsx
```

- [ ] **Step 2: Identifier les IDs exacts des modèles sur fal.ai**

Ouvrir `https://fal.ai/models` et chercher « nano banana pro » puis « seedance ». Noter : l'ID exact du modèle image en mode **edit/référence** (celui qui accepte des images d'entrée, pas le text-to-image pur), l'ID du modèle vidéo Seedance 2.0 (image-to-video), et pour chacun le **schéma d'input** (nom exact du champ prompt et du champ images de référence) ainsi que le **prix par génération** affiché. Reporter ces valeurs dans `scripts/spike-fal/models.ts` :

```ts
// scripts/spike-fal/models.ts
// IDs et schémas relevés sur https://fal.ai/models le JJ/MM — à mettre à jour si fal change.
export const IMAGE_MODEL = {
  id: "fal-ai/nano-banana-pro/edit", // ← vérifier l'ID exact sur la page du modèle
  buildInput: (prompt: string, imageUrls: string[]) => ({
    prompt,
    image_urls: imageUrls, // ← vérifier le nom exact du champ sur la page du modèle
  }),
  pricePerCall: 0, // ← renseigner le prix affiché ($/image)
};

export const VIDEO_MODEL = {
  id: "fal-ai/bytedance/seedance/v2/image-to-video", // ← vérifier l'ID exact
  buildInput: (prompt: string, imageUrl: string) => ({
    prompt,
    image_url: imageUrl, // ← vérifier le nom exact du champ
  }),
  pricePerCall: 0, // ← renseigner le prix affiché ($/vidéo)
};
```

- [ ] **Step 3: Écrire le script images**

```ts
// scripts/spike-fal/generate-images.ts
// Usage : npx tsx scripts/spike-fal/generate-images.ts
// Prérequis : FAL_KEY dans .env.local ; photos dans scripts/spike-fal/photos/<flacon>/*.jpg
import { fal } from "@fal-ai/client";
import { readdir, readFile, mkdir, writeFile } from "node:fs/promises";
import { join, basename } from "node:path";
import { config } from "dotenv";

config({ path: ".env.local" });
fal.config({ credentials: process.env.FAL_KEY });

import { IMAGE_MODEL } from "./models";

const PHOTOS_DIR = "scripts/spike-fal/photos";
const OUT_DIR = "scripts/spike-fal/out";

// 3 compositions représentatives du pack de lancement (spec §4.5) :
// une facile (packshot), une moyenne (mise en scène), une dure (lifestyle chargé).
const PROMPTS: Record<string, string> = {
  packshot:
    "Packshot e-commerce professionnel de ce flacon cosmétique, exactement le même flacon avec la même étiquette parfaitement lisible, fond crème uni, éclairage studio doux, ombre portée légère",
  scene:
    "Ce flacon cosmétique posé sur une tablette de salle de bain en pierre claire, ambiance bohème épurée, lumière naturelle du matin, l'étiquette du flacon reste identique et parfaitement lisible",
  lifestyle:
    "Ce flacon cosmétique dans une composition flatlay avec serviette en lin, feuilles d'eucalyptus et savon artisanal, vue de dessus, l'étiquette du flacon reste strictement identique à la photo",
};

async function uploadPhotos(flaconDir: string): Promise<string[]> {
  const files = (await readdir(flaconDir)).filter((f) => /\.(jpe?g|png|webp)$/i.test(f));
  const urls: string[] = [];
  for (const f of files) {
    const buf = await readFile(join(flaconDir, f));
    const url = await fal.storage.upload(new Blob([buf]));
    urls.push(url);
  }
  return urls;
}

async function main() {
  const flacons = await readdir(PHOTOS_DIR);
  const manifest: object[] = [];
  await mkdir(OUT_DIR, { recursive: true });

  for (const flacon of flacons) {
    const refUrls = await uploadPhotos(join(PHOTOS_DIR, flacon));
    console.log(`\n=== ${flacon} — ${refUrls.length} photo(s) de référence ===`);

    for (const [key, prompt] of Object.entries(PROMPTS)) {
      const t0 = Date.now();
      const result = await fal.subscribe(IMAGE_MODEL.id, {
        input: IMAGE_MODEL.buildInput(prompt, refUrls),
      });
      const data = result.data as { images?: { url: string }[]; image?: { url: string } };
      const imageUrl = data.images?.[0]?.url ?? data.image?.url;
      if (!imageUrl) throw new Error(`Pas d'image dans la réponse: ${JSON.stringify(result.data).slice(0, 500)}`);

      const outName = `${flacon}--${key}.png`;
      const img = await fetch(imageUrl).then((r) => r.arrayBuffer());
      await writeFile(join(OUT_DIR, outName), Buffer.from(img));
      const entry = {
        flacon, prompt: key, file: outName,
        durationMs: Date.now() - t0,
        estimatedCostUsd: IMAGE_MODEL.pricePerCall,
        requestId: result.requestId,
      };
      manifest.push(entry);
      console.log(`  ✓ ${key} (${entry.durationMs} ms) → out/${outName}`);
    }
  }
  await writeFile(join(OUT_DIR, "manifest.json"), JSON.stringify(manifest, null, 2));
  console.log(`\nTerminé : ${manifest.length} visuels. Coût estimé total: $${(manifest.length * IMAGE_MODEL.pricePerCall).toFixed(2)} (vérifier le réel sur fal.ai/dashboard/usage)`);
}

main().catch((e) => { console.error(e); process.exit(1); });
```

Remarque : `basename` importé est inutilisé si le linter râle — le retirer.

- [ ] **Step 4: Écrire le script vidéo**

```ts
// scripts/spike-fal/generate-video.ts
// Usage : npx tsx scripts/spike-fal/generate-video.ts scripts/spike-fal/out/<meilleur-visuel>.png
import { fal } from "@fal-ai/client";
import { readFile, writeFile } from "node:fs/promises";
import { config } from "dotenv";

config({ path: ".env.local" });
fal.config({ credentials: process.env.FAL_KEY });

import { VIDEO_MODEL } from "./models";

async function main() {
  const src = process.argv[2];
  if (!src) throw new Error("Usage: npx tsx scripts/spike-fal/generate-video.ts <image.png>");
  const buf = await readFile(src);
  const url = await fal.storage.upload(new Blob([buf]));

  const result = await fal.subscribe(VIDEO_MODEL.id, {
    input: VIDEO_MODEL.buildInput(
      "Lent travelling circulaire autour du flacon, lumière chaude, ambiance spa, le flacon et son étiquette restent parfaitement nets et identiques",
      url
    ),
  });
  const data = result.data as { video?: { url: string } };
  if (!data.video?.url) throw new Error(`Pas de vidéo: ${JSON.stringify(result.data).slice(0, 500)}`);
  const vid = await fetch(data.video.url).then((r) => r.arrayBuffer());
  await writeFile("scripts/spike-fal/out/test-video.mp4", Buffer.from(vid));
  console.log("✓ scripts/spike-fal/out/test-video.mp4");
}

main().catch((e) => { console.error(e); process.exit(1); });
```

- [ ] **Step 5: Écrire le template de rapport GO/NO-GO**

```markdown
<!-- scripts/spike-fal/RAPPORT.md -->
# Spike fal.ai — Rapport GO/NO-GO (Lot 0)

Date : ____ · Modèles testés : image = ____ · vidéo = ____

## Grille de notation (par visuel généré)
Pour chaque fichier de `out/`, zoomer à 200 % sur l'étiquette et noter :

| Fichier | Texte étiquette lisible et EXACT (0-5) | Logo intact (0-5) | Géométrie flacon (0-5) | Verdict |
|---|---|---|---|---|
| exemple--packshot.png | | | | OK / KO |

## Critère de décision (spec §7 R1)
- **GO** : ≥ 80 % des visuels `packshot` + `scene` sans AUCUNE altération visible du texte d'étiquette (note 5/5 colonne texte). Le prompt `lifestyle` est informatif (il borne le répertoire de templates, pas le GO).
- **NO-GO image** : texte altéré sur les packshots → plan B spec §7 R1 (compositions sûres uniquement + photos réelles client) et re-scoper le Lot 4 avant de le lancer.
- **Vidéo (R2)** : la vidéo test conserve-t-elle l'étiquette nette ? Si non → fallback reels = montage animé des visuels validés (spec §7 R2).

## Coûts relevés
- Prix par image : $____ · par vidéo : $____ (fal.ai/dashboard/usage)
- Coût pack de lancement estimé (12 images + 2 reels) : $____
- Latence moyenne image : ____ ms · vidéo : ____ s

## Décision
- [ ] GO — Lot 4 tel que spécifié
- [ ] GO restreint — templates limités à : ____
- [ ] NO-GO — actions : ____
```

- [ ] **Step 6: Écrire le README du spike**

```markdown
<!-- scripts/spike-fal/README.md -->
# Spike fal.ai (Lot 0 — MY.LAB Studio V3)

1. Compte sur https://fal.ai → clé API → `FAL_KEY=...` dans `.env.local`
2. Déposer 3-5 dossiers de photos dans `scripts/spike-fal/photos/<nom-flacon>/` (1-3 photos par flacon, le vrai flacon étiqueté, bien éclairé)
3. Vérifier/compléter `models.ts` (IDs + schémas + prix depuis fal.ai/models)
4. `npx tsx scripts/spike-fal/generate-images.ts`
5. `npx tsx scripts/spike-fal/generate-video.ts scripts/spike-fal/out/<meilleur>.png`
6. Remplir `RAPPORT.md` (grille + décision GO/NO-GO)

`photos/` et `out/` ne sont pas commités (voir .gitignore).
```

Ajouter au `.gitignore` du repo app :

```
# spike fal.ai — assets locaux
scripts/spike-fal/photos/
scripts/spike-fal/out/
```

- [ ] **Step 7: Exécuter (avec Yoann)**

Run: `npx tsx scripts/spike-fal/generate-images.ts` puis le script vidéo.
Expected: 9-15 PNG dans `out/` + `manifest.json` + `test-video.mp4`, sans erreur. Yoann remplit la grille de `RAPPORT.md`.

- [ ] **Step 8: Commit**

```bash
git add scripts/spike-fal package.json package-lock.json .gitignore
git commit -m "feat(spike): scripts de test fidelite etiquette fal.ai (Lot 0 Studio V3)"
```

---

### Task 2 (Lot 1): Interversion des étapes 02↔03 du parcours Shopify

**Repo:** `be-yours-mylab`

**Files:**
- Modify: `assets/ml-parcours.js:78` (stepOrder) et `:242` (texte dialogue)
- Modify: `snippets/ml-parcours-shell.liquid:48-68` (pastilles) et `:108-109` (CTA mobile)
- Modify: `sections/ml-parcours-etiquette.liquid:13,91,95`
- Modify: `sections/ml-parcours-produits.liquid:10,35,39`
- Modify: `sections/ml-parcours-dossier.liquid:43`
- Modify: `sections/ml-parcours-recap.liquid:45`
- Modify: `templates/page.creons-ensemble-votre-marque.json` (ordre/kickers des blocks step_card)

**Interfaces:**
- Consumes: rien.
- Produces: nouvel ordre 01 Dossier → 02 Produits → 03 Étiquette → 04 Récap, cohérent sur les 12 points d'encodage. Le gate checkout (`hasDossier && hasEtiquette && hasProduits`, ordre-indépendant) et l'auto-forfait (déclenché par le panier) ne changent pas.

> Pas de test runner sur le thème : la vérification est un walkthrough manuel sur le thème de développement (Step 5). Ne PAS pousser en live dans cette tâche.

- [ ] **Step 1: JS — ordre et textes**

Dans `assets/ml-parcours.js` :
- l.78 : `const stepOrder = ['dossier', 'etiquette', 'produits', 'recap'];` → `const stepOrder = ['dossier', 'produits', 'etiquette', 'recap'];`
- l.242 : remplacer la phrase mentionnant « l'étape 03 » pour les produits par : `Les produits ajoutés à l'étape 02 restent dans votre panier.`

- [ ] **Step 2: Shell — pastilles et CTA mobile**

Dans `snippets/ml-parcours-shell.liquid` :
- Intervertir les deux blocs `<button>` du stepper (l.48-57 étiquette et l.59-68 produits) pour obtenir l'ordre DOM : dossier, **produits**, **étiquette**, recap. Puis corriger dans les blocs déplacés : produits → digit `2`, kicker `Étape 02` ; étiquette → digit `3`, kicker `Étape 03`. Les `data-go` restent `produits`/`etiquette` (la navigation passe par `CONFIG.paths`, pas par la position).
- l.108-109 (le `case page.handle` du CTA mobile) : `parcours-produits` → `Étape 02/04` + label `Produits` ; `parcours-etiquette` → `Étape 03/04` + label `Étiquette & impression`.

- [ ] **Step 3: Sections — kickers et navigation linéaire**

- `sections/ml-parcours-dossier.liquid` l.43 : lien « suivant » `/pages/parcours-etiquette` → `/pages/parcours-produits`, texte du bouton → `Valider et choisir mes produits`.
- `sections/ml-parcours-produits.liquid` : l.10 kicker → `Étape 02 / 04 — Produits` ; l.35 retour `/pages/parcours-etiquette` → `/pages/parcours-dossier` ; l.39 suivant `/pages/parcours-recap` → `/pages/parcours-etiquette`, texte → `Valider et créer mon étiquette`.
- `sections/ml-parcours-etiquette.liquid` : l.13 kicker → `Étape 03 / 04 — Étiquette & impression` ; l.91 retour `/pages/parcours-dossier` → `/pages/parcours-produits` ; l.95 suivant `/pages/parcours-produits` → `/pages/parcours-recap`, texte → `Voir le récap final`.
- `sections/ml-parcours-recap.liquid` l.45 : retour `/pages/parcours-produits` → `/pages/parcours-etiquette`.

- [ ] **Step 4: Landing — blocks step_card**

Ouvrir `templates/page.creons-ensemble-votre-marque.json`, repérer les blocks `step_card` (les kickers/titres sont des settings). Intervertir les blocks Étiquette/Produits dans le tableau `order` des blocks ET corriger leurs settings kicker : produits → `Étape 02`, étiquette → `Étape 03`. Mettre aussi à jour le preset de `sections/ml-parcours-landing.liquid` (l.75-80) pour cohérence future.

- [ ] **Step 5: Vérifier sur le thème de développement**

```bash
cd "d:\Projets mylab vs code\be-yours-mylab"
shopify theme push --store mylab-shop-3.myshopify.com --development
```

Walkthrough complet (checklist) :
1. Landing : cartes dans l'ordre Dossier / Produits / Étiquette / Récap avec les bons kickers.
2. « Démarrer mon projet » → dossier ajouté → page dossier (Étape 01), bouton suivant → **parcours-produits**.
3. Page produits : kicker Étape 02, ajouter 1 produit → pastille 2 passe done ; suivant → **parcours-etiquette**.
4. Page étiquette : kicker Étape 03, ajouter une étiquette via configurateur → forfait auto-ajouté (couplage panier intact) ; suivant → récap.
5. Récap : bouton « Valider votre projet » actif (3 conditions remplies) ; « Quitter le parcours » → le dialogue mentionne « l'étape 02 » pour les produits.
6. Stepper : recharger chaque page → les états done/current/locked tombent sur les BONNES pastilles (c'est le risque n°1 : mapping par index).

- [ ] **Step 6: Commit**

```bash
git add assets/ml-parcours.js snippets/ml-parcours-shell.liquid sections/ml-parcours-dossier.liquid sections/ml-parcours-etiquette.liquid sections/ml-parcours-produits.liquid sections/ml-parcours-recap.liquid sections/ml-parcours-landing.liquid templates/page.creons-ensemble-votre-marque.json
git commit -m "feat(parcours): produits avant etiquette (Studio V3 Lot 1) — swap etapes 02/03"
```

---

### Task 3 (Lot 1): Chip « Votre projet » vers l'app Studio dans le stepper

**Repo:** `be-yours-mylab`

**Files:**
- Modify: `snippets/ml-parcours-shell.liquid` (après la pastille recap, l.70-79)
- Modify: `assets/ml-parcours.css` (styles du chip)

**Interfaces:**
- Consumes: URL de l'espace projet (Task 7) : `https://mylab-configurateur.vercel.app/projet`.
- Produces: lien discret et permanent vers l'app depuis le parcours. Classe volontairement DIFFÉRENTE de `ml-parcours__step` pour ne pas casser le mapping par index de `stepOrder` (4 éléments).

- [ ] **Step 1: Ajouter le chip dans le shell**

Après le bloc de la pastille recap (l.79) dans `snippets/ml-parcours-shell.liquid` :

```liquid
<a class="ml-parcours__step-ext" href="https://mylab-configurateur.vercel.app/projet" target="_blank" rel="noopener">
  <span class="ml-parcours__step-ext-kicker">Suivi</span>
  <span class="ml-parcours__step-ext-name">Votre projet ↗</span>
</a>
```

- [ ] **Step 2: Styles**

Dans `assets/ml-parcours.css`, à la suite des styles du stepper :

```css
.ml-parcours__step-ext {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  margin-left: 1rem;
  padding: 0.4rem 0.9rem;
  border: 1px solid rgba(26, 26, 26, 0.25);
  border-radius: 999px;
  text-decoration: none;
  color: #1a1a1a;
}
.ml-parcours__step-ext-kicker {
  font-family: 'DM Mono', monospace;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  opacity: 0.6;
}
.ml-parcours__step-ext-name { font-size: 1.2rem; font-weight: 600; }
@media screen and (max-width: 749px) {
  .ml-parcours__step-ext { display: none; }
}
```

- [ ] **Step 3: Vérifier**

Run: `shopify theme push --store mylab-shop-3.myshopify.com --development`
Expected: chip visible à droite du stepper sur desktop, absent sur mobile, ouvre l'app dans un nouvel onglet ; les 4 pastilles gardent leurs états corrects (le chip est ignoré par le JS).

- [ ] **Step 4: Commit**

```bash
git add snippets/ml-parcours-shell.liquid assets/ml-parcours.css
git commit -m "feat(parcours): chip 'Votre projet' vers l'app Studio dans le stepper"
```

---

### Task 4 (Lot 1): Modèle Prisma `Project` + migration

**Repo:** `mylab-configurateur`

**Files:**
- Modify: `prisma/schema.prisma`
- Create: migration générée par `prisma migrate dev`

**Interfaces:**
- Consumes: modèles existants `User`, `Configuration`.
- Produces: modèle `Project` et enum `ProjectStatus { draft, paid }` — consommés par Tasks 5/6/7. Champs exacts ci-dessous ; accès via `prisma.project` (singleton `@/lib/prisma`).

- [ ] **Step 1: Ajouter enum + modèle au schema**

Dans `prisma/schema.prisma`, à la suite des enums existants :

```prisma
enum ProjectStatus {
  draft // avant paiement (réservé aux lots suivants — Lot 1 crée directement en paid)
  paid  // commande parcours payée — demande d'étiquette à traiter (statuts BAT au Lot 2)
}
```

À la suite des modèles existants :

```prisma
model Project {
  id                 String        @id @default(cuid())
  email              String
  userId             String?
  user               User?         @relation(fields: [userId], references: [id])
  configurationId    String?       @unique
  configuration      Configuration? @relation(fields: [configurationId], references: [id])
  shopifyOrderId     String        @unique
  shopifyOrderNumber String?
  brandName          String?
  designReference    String? // line item property "Référence design" posée par le configurateur
  gammeRefs          Json? // [{ title, variantTitle, quantity, sku }] — les produits de la gamme
  status             ProjectStatus @default(paid)
  createdAt          DateTime      @default(now())
  updatedAt          DateTime      @updatedAt

  @@index([email])
  @@index([userId])
}
```

Ajouter la relation inverse dans `User` : `projects Project[]` ; et dans `Configuration` : `project Project?`.

- [ ] **Step 2: Migrer et régénérer le client**

Run: `npx prisma migrate dev --name add_project`
Expected: migration créée et appliquée, client régénéré dans `src/generated/prisma` sans erreur.

- [ ] **Step 3: Vérifier le typage**

Run: `npx tsc --noEmit`
Expected: 0 erreur (le modèle est typé, rien ne le consomme encore).

- [ ] **Step 4: Commit**

```bash
git add prisma/schema.prisma prisma/migrations
git commit -m "feat(studio): modele Project + enum ProjectStatus (Lot 1)"
```

---

### Task 5 (Lot 1): Lib pure `shopify-order` — HMAC + détection + extraction (TDD)

**Repo:** `mylab-configurateur`

**Files:**
- Create: `src/lib/studio/shopify-order.ts`
- Test: `src/lib/studio/shopify-order.test.ts`

**Interfaces:**
- Consumes: rien (fonctions pures, `node:crypto`).
- Produces (consommé par Task 6) :
  - `verifyShopifyHmac(rawBody: string, hmacHeader: string | null, secret: string): boolean`
  - `type ShopifyLineItem = { product_id: number; variant_id: number; title: string; variant_title: string | null; quantity: number; sku: string | null; properties: { name: string; value: string }[] }`
  - `type ShopifyOrderPayload = { id: number; order_number: number; email: string | null; contact_email?: string | null; line_items: ShopifyLineItem[] }`
  - `isParcoursOrder(order: ShopifyOrderPayload, dossierProductId: number): boolean`
  - `extractProject(order: ShopifyOrderPayload, opts: { dossierProductId: number; forfaitProductIds: number[] }): { email: string; shopifyOrderId: string; shopifyOrderNumber: string; designReference: string | null; brandName: string | null; gammeRefs: { title: string; variantTitle: string | null; quantity: number; sku: string | null }[] } | null` — retourne `null` si pas d'email ou pas une commande parcours.

⚠️ Le payload `orders/paid` de Shopify ne contient PAS le handle produit dans les line items — la détection se fait par `product_id` (fournis en env, voir Task 8).

- [ ] **Step 1: Écrire les tests (échouent)**

```ts
// src/lib/studio/shopify-order.test.ts
import { describe, it, expect } from "vitest";
import { createHmac } from "node:crypto";
import {
  verifyShopifyHmac,
  isParcoursOrder,
  extractProject,
  type ShopifyOrderPayload,
} from "./shopify-order";

const SECRET = "shpss_test_secret";
const sign = (body: string) => createHmac("sha256", SECRET).update(body, "utf8").digest("base64");

const DOSSIER_ID = 111;
const FORFAIT_IDS = [222, 223];

const order = (overrides: Partial<ShopifyOrderPayload> = {}): ShopifyOrderPayload => ({
  id: 5001,
  order_number: 1042,
  email: "cliente@marque.fr",
  line_items: [
    { product_id: DOSSIER_ID, variant_id: 1, title: "Création du dossier cosmétologique", variant_title: null, quantity: 1, sku: null, properties: [] },
    { product_id: 333, variant_id: 2, title: "Modèle Botanique", variant_title: null, quantity: 1, sku: null,
      properties: [{ name: "Référence design", value: "DC-EMB-A1B2C3D4" }, { name: "Gammes", value: "Nourrissante, Réparatrice" }] },
    { product_id: 222, variant_id: 3, title: "Forfait d'impression", variant_title: null, quantity: 1, sku: null, properties: [] },
    { product_id: 444, variant_id: 4, title: "Shampoing nourrissant", variant_title: "500ml", quantity: 48, sku: "SH-N-500", properties: [] },
  ],
  ...overrides,
});

describe("verifyShopifyHmac", () => {
  it("accepte une signature valide", () => {
    const body = JSON.stringify(order());
    expect(verifyShopifyHmac(body, sign(body), SECRET)).toBe(true);
  });
  it("rejette une signature invalide", () => {
    expect(verifyShopifyHmac(JSON.stringify(order()), sign("autre"), SECRET)).toBe(false);
  });
  it("rejette un header absent", () => {
    expect(verifyShopifyHmac("{}", null, SECRET)).toBe(false);
  });
});

describe("isParcoursOrder", () => {
  it("vraie si le dossier est dans la commande", () => {
    expect(isParcoursOrder(order(), DOSSIER_ID)).toBe(true);
  });
  it("fausse sinon", () => {
    const o = order();
    o.line_items = o.line_items.filter((li) => li.product_id !== DOSSIER_ID);
    expect(isParcoursOrder(o, DOSSIER_ID)).toBe(false);
  });
});

describe("extractProject", () => {
  const opts = { dossierProductId: DOSSIER_ID, forfaitProductIds: FORFAIT_IDS };
  it("extrait email, ids, référence design et gamme (sans dossier/forfait/étiquette)", () => {
    const p = extractProject(order(), opts);
    expect(p).toEqual({
      email: "cliente@marque.fr",
      shopifyOrderId: "5001",
      shopifyOrderNumber: "1042",
      designReference: "DC-EMB-A1B2C3D4",
      brandName: null,
      gammeRefs: [{ title: "Shampoing nourrissant", variantTitle: "500ml", quantity: 48, sku: "SH-N-500" }],
    });
  });
  it("null si pas une commande parcours", () => {
    const o = order();
    o.line_items = o.line_items.filter((li) => li.product_id !== DOSSIER_ID);
    expect(extractProject(o, opts)).toBeNull();
  });
  it("null si pas d'email, fallback contact_email accepté", () => {
    expect(extractProject(order({ email: null }), opts)).toBeNull();
    const p = extractProject(order({ email: null, contact_email: "c2@marque.fr" }), opts);
    expect(p?.email).toBe("c2@marque.fr");
  });
});
```

- [ ] **Step 2: Vérifier l'échec**

Run: `npm test -- src/lib/studio/shopify-order.test.ts`
Expected: FAIL — module `./shopify-order` introuvable.

- [ ] **Step 3: Implémenter**

```ts
// src/lib/studio/shopify-order.ts
import { createHmac, timingSafeEqual } from "node:crypto";

export type ShopifyLineItem = {
  product_id: number;
  variant_id: number;
  title: string;
  variant_title: string | null;
  quantity: number;
  sku: string | null;
  properties: { name: string; value: string }[];
};

export type ShopifyOrderPayload = {
  id: number;
  order_number: number;
  email: string | null;
  contact_email?: string | null;
  line_items: ShopifyLineItem[];
};

export function verifyShopifyHmac(rawBody: string, hmacHeader: string | null, secret: string): boolean {
  if (!hmacHeader) return false;
  const digest = createHmac("sha256", secret).update(rawBody, "utf8").digest();
  let header: Buffer;
  try {
    header = Buffer.from(hmacHeader, "base64");
  } catch {
    return false;
  }
  return header.length === digest.length && timingSafeEqual(digest, header);
}

export function isParcoursOrder(order: ShopifyOrderPayload, dossierProductId: number): boolean {
  return order.line_items.some((li) => li.product_id === dossierProductId);
}

const prop = (li: ShopifyLineItem, name: string): string | null =>
  li.properties.find((p) => p.name === name)?.value ?? null;

export function extractProject(
  order: ShopifyOrderPayload,
  opts: { dossierProductId: number; forfaitProductIds: number[] }
) {
  if (!isParcoursOrder(order, opts.dossierProductId)) return null;
  const email = order.email ?? order.contact_email ?? null;
  if (!email) return null;

  const etiquetteLine = order.line_items.find((li) => prop(li, "Référence design") !== null);
  const excluded = new Set([opts.dossierProductId, ...opts.forfaitProductIds, etiquetteLine?.product_id ?? -1]);

  return {
    email,
    shopifyOrderId: String(order.id),
    shopifyOrderNumber: String(order.order_number),
    designReference: etiquetteLine ? prop(etiquetteLine, "Référence design") : null,
    brandName: null, // renseigné au Lot 3 (onboarding) — pas d'info marque dans la commande
    gammeRefs: order.line_items
      .filter((li) => !excluded.has(li.product_id))
      .map((li) => ({ title: li.title, variantTitle: li.variant_title, quantity: li.quantity, sku: li.sku })),
  };
}
```

- [ ] **Step 4: Vérifier le succès**

Run: `npm test -- src/lib/studio/shopify-order.test.ts`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add src/lib/studio/shopify-order.ts src/lib/studio/shopify-order.test.ts
git commit -m "feat(studio): lib pure webhook Shopify — HMAC, detection parcours, extraction Project (TDD)"
```

---

### Task 6 (Lot 1): Route webhook `orders/paid`

**Repo:** `mylab-configurateur`

**Files:**
- Create: `src/app/api/webhooks/shopify/orders-paid/route.ts`

**Interfaces:**
- Consumes: Task 5 (`verifyShopifyHmac`, `extractProject`, `ShopifyOrderPayload`), Task 4 (`prisma.project`), env `SHOPIFY_WEBHOOK_SECRET`, `STUDIO_DOSSIER_PRODUCT_ID`, `STUDIO_FORFAIT_PRODUCT_IDS` (Task 8).
- Produces: `POST /api/webhooks/shopify/orders-paid` → 401 si HMAC invalide ; 200 `{ ignored: true }` si commande hors parcours ; 200 `{ projectId }` sinon (upsert idempotent par `shopifyOrderId` — Shopify relivre les webhooks).

- [ ] **Step 1: Implémenter la route**

```ts
// src/app/api/webhooks/shopify/orders-paid/route.ts
import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import {
  verifyShopifyHmac,
  extractProject,
  type ShopifyOrderPayload,
} from "@/lib/studio/shopify-order";

export async function POST(req: Request) {
  const secret = process.env.SHOPIFY_WEBHOOK_SECRET;
  const dossierProductId = Number(process.env.STUDIO_DOSSIER_PRODUCT_ID);
  const forfaitProductIds = (process.env.STUDIO_FORFAIT_PRODUCT_IDS ?? "")
    .split(",").map((s) => Number(s.trim())).filter((n) => Number.isFinite(n) && n > 0);

  if (!secret || !Number.isFinite(dossierProductId) || dossierProductId <= 0) {
    console.error("[webhook orders-paid] configuration manquante (SHOPIFY_WEBHOOK_SECRET / STUDIO_DOSSIER_PRODUCT_ID)");
    return NextResponse.json({ error: "misconfigured" }, { status: 500 });
  }

  const rawBody = await req.text();
  if (!verifyShopifyHmac(rawBody, req.headers.get("x-shopify-hmac-sha256"), secret)) {
    return NextResponse.json({ error: "invalid hmac" }, { status: 401 });
  }

  let order: ShopifyOrderPayload;
  try {
    order = JSON.parse(rawBody) as ShopifyOrderPayload;
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }

  const data = extractProject(order, { dossierProductId, forfaitProductIds });
  if (!data) return NextResponse.json({ ignored: true });

  const project = await prisma.project.upsert({
    where: { shopifyOrderId: data.shopifyOrderId },
    update: {}, // relivraison webhook : ne pas écraser un projet existant
    create: {
      email: data.email.toLowerCase(),
      shopifyOrderId: data.shopifyOrderId,
      shopifyOrderNumber: data.shopifyOrderNumber,
      designReference: data.designReference,
      gammeRefs: data.gammeRefs,
      status: "paid",
    },
  });

  return NextResponse.json({ projectId: project.id });
}
```

- [ ] **Step 2: Vérifier le typage et les tests existants**

Run: `npx tsc --noEmit && npm test`
Expected: 0 erreur TS, tous les tests passent (la logique risquée est déjà couverte en Task 5 ; la route est une colle mince sans test dédié — cohérent avec le repo qui ne teste pas les routes).

- [ ] **Step 3: Test manuel local avec HMAC réel**

Lancer `npm run dev`, puis dans un second terminal (adapter `STUDIO_DOSSIER_PRODUCT_ID` de `.env.local` dans le payload) :

```bash
node -e '
const { createHmac } = require("node:crypto");
const body = JSON.stringify({ id: 999001, order_number: 9001, email: "test@mylab-shop.com",
  line_items: [
    { product_id: Number(process.env.DOSSIER_ID), variant_id: 1, title: "Dossier", variant_title: null, quantity: 1, sku: null, properties: [] },
    { product_id: 444, variant_id: 4, title: "Shampoing nourrissant", variant_title: "500ml", quantity: 48, sku: "SH-N-500", properties: [] }
  ]});
const hmac = createHmac("sha256", process.env.SECRET).update(body, "utf8").digest("base64");
fetch("http://localhost:3000/api/webhooks/shopify/orders-paid", {
  method: "POST", body,
  headers: { "content-type": "application/json", "x-shopify-hmac-sha256": hmac },
}).then(async r => console.log(r.status, await r.text()));
' # avec SECRET=<valeur .env.local> DOSSIER_ID=<valeur .env.local> en variables d'env
```

Expected: `200 {"projectId":"..."}` au premier appel ; le MÊME `projectId` au second (idempotence) ; `401` si on altère le body sans recalculer le HMAC.

- [ ] **Step 4: Commit**

```bash
git add src/app/api/webhooks/shopify/orders-paid/route.ts
git commit -m "feat(studio): webhook Shopify orders/paid -> creation Project idempotente"
```

---

### Task 7 (Lot 1): Espace client « Mon projet » minimal

**Repo:** `mylab-configurateur`

**Files:**
- Create: `src/app/projet/page.tsx`

**Interfaces:**
- Consumes: `getServerSession(authOptions)` (`@/lib/auth`), `prisma.project` (Task 4).
- Produces: page `/projet` (server component) : liste des projets du client (match par `userId` OU `email` de session, avec revendication du projet au passage), timeline statique des étapes du funnel. C'est la cible du chip Task 3 et la base des Lots 2/3.

- [ ] **Step 1: Implémenter la page**

```tsx
// src/app/projet/page.tsx
import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export const metadata = { title: "Mon projet — MyLab Studio" };

const STEPS = [
  { key: "commande", label: "Commande reçue" },
  { key: "etiquette", label: "Création de votre étiquette" },
  { key: "onboarding", label: "Préparation de votre site" },
  { key: "livraison", label: "Votre site en ligne" },
] as const;

export default async function ProjetPage() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.email) redirect("/login?callbackUrl=/projet");

  const email = session.user.email.toLowerCase();
  const userId = session.user.id;

  // Revendication : rattache au compte les projets créés par webhook avant la 1re connexion
  await prisma.project.updateMany({ where: { email, userId: null }, data: { userId } });

  const projects = await prisma.project.findMany({
    where: { OR: [{ userId }, { email }] },
    orderBy: { createdAt: "desc" },
  });

  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-2xl font-semibold">Mon projet</h1>

      {projects.length === 0 ? (
        <p className="mt-6 text-neutral-600">
          Aucun projet pour le moment. Votre projet apparaîtra ici après le paiement de votre
          commande du parcours «&nbsp;Créons ensemble votre marque&nbsp;» sur mylab-shop.com.
        </p>
      ) : (
        projects.map((project) => {
          const gamme = (project.gammeRefs ?? []) as { title: string; variantTitle: string | null; quantity: number }[];
          // Lot 1 : seul le jalon "commande" est atteignable (status paid) ; les suivants arrivent aux Lots 2-5.
          const doneCount = project.status === "paid" ? 1 : 0;
          return (
            <section key={project.id} className="mt-8 rounded-xl border border-neutral-200 p-6">
              <div className="flex items-baseline justify-between">
                <h2 className="font-medium">Commande n°{project.shopifyOrderNumber}</h2>
                {project.designReference && (
                  <span className="text-sm text-neutral-500">Design {project.designReference}</span>
                )}
              </div>

              <ol className="mt-4 space-y-2">
                {STEPS.map((step, i) => {
                  const state = i < doneCount ? "done" : i === doneCount ? "current" : "locked";
                  return (
                    <li key={step.key} className="flex items-center gap-3 text-sm">
                      <span aria-hidden>{state === "done" ? "✅" : state === "current" ? "🟡" : "○"}</span>
                      <span className={state === "locked" ? "text-neutral-400" : ""}>
                        {step.label}
                        {state === "current" && step.key === "etiquette" && (
                          <span className="text-neutral-500"> — notre graphiste prépare votre BAT, vous serez notifié par email</span>
                        )}
                      </span>
                    </li>
                  );
                })}
              </ol>

              {gamme.length > 0 && (
                <div className="mt-4 border-t border-neutral-100 pt-4 text-sm text-neutral-600">
                  <span className="font-medium text-neutral-800">Votre gamme :</span>{" "}
                  {gamme.map((g) => `${g.title}${g.variantTitle ? ` ${g.variantTitle}` : ""} ×${g.quantity}`).join(" · ")}
                </div>
              )}
            </section>
          );
        })
      )}
    </main>
  );
}
```

- [ ] **Step 2: Vérifier**

Run: `npx tsc --noEmit && npm run dev`
Expected: 0 erreur TS. Manuel : `/projet` sans session → redirect `/login` ; se connecter par magic link avec l'email du projet de test (Task 6 Step 3) → le projet s'affiche, jalon 1 ✅, jalon 2 🟡, gamme listée. Vérifier en DB que `userId` a été revendiqué (`npx prisma studio`, table Project).

- [ ] **Step 3: Commit**

```bash
git add src/app/projet/page.tsx
git commit -m "feat(studio): espace client /projet minimal (timeline + gamme + revendication par email)"
```

---

### Task 8 (Lot 1): Configuration — env, webhook Shopify réel, déploiement

**Repo:** `mylab-configurateur` (+ admin Shopify)

**Files:**
- Modify: `.env.example`

**Interfaces:**
- Consumes: routes des Tasks 6/7 déployées sur Vercel.
- Produces: webhook `orders/paid` actif en production, variables d'env documentées et posées.

- [ ] **Step 1: Documenter les variables**

Ajouter à `.env.example` (sans valeurs) :

```
# --- MyLab Studio (Lot 1) ---
SHOPIFY_WEBHOOK_SECRET=        # admin Shopify > Notifications > Webhooks > signing secret (shpss_...)
STUDIO_DOSSIER_PRODUCT_ID=     # product id du dossier cosmetologique (voir README étape ci-dessous)
STUDIO_FORFAIT_PRODUCT_IDS=    # ids des 2 forfaits impression, séparés par des virgules
# --- Spike Lot 0 ---
FAL_KEY=
```

- [ ] **Step 2: Relever les product ids réels**

```bash
curl -s https://mylab-shop.com/products/creation-du-dossier-cosmetologique.js | python -c "import json,sys; print(json.load(sys.stdin)['id'])"
curl -s https://mylab-shop.com/products/forfait-dimpression-standard.js | python -c "import json,sys; print(json.load(sys.stdin)['id'])"
curl -s https://mylab-shop.com/products/forfait-dimpression.js | python -c "import json,sys; print(json.load(sys.stdin)['id'])"
```

Expected: 3 entiers → renseigner `.env.local` et les env Vercel (Production + Preview).

- [ ] **Step 3: Déployer et créer le webhook (manuel, avec Yoann)**

1. Merger/déployer la branche sur Vercel (ou `vercel deploy` de test).
2. Admin Shopify (`mylab-shop-3.myshopify.com`) → Paramètres → Notifications → Webhooks → « Créer un webhook » : événement **Paiement de la commande** (`orders/paid`), format JSON, URL `https://mylab-configurateur.vercel.app/api/webhooks/shopify/orders-paid`, dernière version d'API stable. (Même procédure que `docs/shopify-webhook-setup.md` du repo thème — c'est un webhook DISTINCT de celui de n8n, ne pas toucher à `mylab-shopify-order`.)
3. Copier le **signing secret** (`shpss_…`) affiché → `SHOPIFY_WEBHOOK_SECRET` sur Vercel → redéployer.
4. Bouton « Envoyer une notification de test » → la commande de test ne contient pas le dossier → vérifier dans les logs Vercel une réponse `200 {"ignored":true}` (HMAC OK, filtrage OK).

- [ ] **Step 4: Test de bout en bout**

Passer une commande de test réelle du parcours (mode test de la boutique ou commande à 0 € via draft order contenant le dossier). Expected: une ligne `Project` apparaît (vérifier via `npx prisma studio` sur la DB de prod ou une route admin future), puis `/projet` l'affiche après connexion avec l'email de la commande.

- [ ] **Step 5: Commit**

```bash
git add .env.example
git commit -m "chore(studio): variables d'env Lot 1 (webhook Shopify, product ids, FAL_KEY)"
```

---

## Ce que ce plan ne couvre PAS (lots suivants, plans dédiés)

- **Lot 2** : workflow BAT complet (modèles `LabelRequest`/`LabelReference`/`BatVersion`/`Comment`, back-office graphiste, notifications Resend, statuts riches remplaçant l'enum minimal `ProjectStatus`).
- **Lot 3** : onboarding 3 écrans (+ upload éléments existants). **Lot 4** : intégration fal.ai produit (queue, galerie, revue admin) — conditionné au GO du Lot 0. **Lot 5** : provisioning + livraison.
- La création du `Project` dès la soumission du configurateur (spec §4.2) est volontairement différée au Lot 2 : en mode embed l'app n'écrit rien en DB aujourd'hui ; au Lot 1 le webhook est l'unique point de création (statut `draft` réservé à cet usage futur).
