# MY.LAB Studio V3 — Lot 4 (génération du pack) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** À la soumission de l'onboarding, générer automatiquement le pack de lancement (12 visuels Nano Banana Pro + 2 reels Seedance 2.0) via la queue fal.ai, avec revue admin obligatoire puis galerie de sélection client (8 favoris).

**Architecture:** Event-driven sans worker : la soumission de l'onboarding crée 12 `GenerationJob` image et les soumet à la **queue fal.ai avec webhook** ; le webhook (token en URL, **jamais confiance au corps** — le handler re-fetche le résultat chez fal) rapatrie chaque asset sur Cloudinary ; quand les images sont terminées il soumet les 2 vidéos depuis les 2 premiers packshots ; quand tout est terminal → `pack_review` + email admin. L'admin écarte/relance/publie (`/admin/pack`) → `pack_ready` + email client ; le client sélectionne 8 visuels dans `/projet` → `pack_selected` + email admin. Prompts = 6 templates paramétrés par le Brand DNA (lib pure TDD).

**Tech Stack:** identique Lots 1-3 + `@fal-ai/client` (déjà en dependencies depuis le spike Lot 0).

**Spec de référence :** `docs/superpowers/specs/2026-07-08-mylab-studio-v3-design.md` §4.5 + §6. Modèles actés au GO du Lot 0 (`scripts/spike-fal/RAPPORT.md`) : image `fal-ai/nano-banana-pro/edit` (0,15 $/img, ~25 s), vidéo `bytedance/seedance-2.0/image-to-video` (720p 5s ≈ 1,52 $, ~2 min).

## Global Constraints

- **Repo** : `d:\Projets mylab vs code\mylab-configurateur`, branche `feat/studio-v3-lot4-generation` (Task 0, depuis `main`).
- Conventions Lots 1-3 inchangées (TS strict, `@/`, client Prisma généré, pattern server page → client fetch → API route + garde, grammaire admin `.card`/`.btn-gold`/`mylab-*` vs client `neutral-*`, migrations manuscrites recette éprouvée + **RLS invariant**, `after()` pour les emails, vitest colocalisé).
- **Spec §4.5 (verbatim)** : « **~12 visuels** (Nano Banana Pro ; prompts = templates × Brand DNA, photos produit en référence) — le client en sélectionne **8** dans une galerie "Mon projet". **2 reels courts** (Seedance 2.0). Assets stockés sur Cloudinary ; **coûts par asset tracés** (colonne coût sur le job). **Revue Yoann obligatoire avant exposition au client** : écran admin pour écarter/relancer les ratés. »
- **Webhook fal** : livré avec retries (10× sur 2 h, timeout 15 s) → le handler DOIT être **idempotent** et répondre 200 vite. Sécurité : token secret en query (`?token=$FAL_WEBHOOK_TOKEN`) + le corps n'est JAMAIS cru — le handler relit le statut/résultat via `fal.queue.result()` avec nos credentials. Un webhook pour un `request_id` inconnu → 200 `{ignored:true}`.
- Statuts projet ajoutés : `pack_generating → pack_review → pack_ready → pack_selected` (enum `ProjectStatus`). `projectDoneCount` : ces 4 statuts restent au jalon 3 (« livraison » = current).
- Coûts constants tracés : `COST_IMAGE_USD = 0.15`, `COST_VIDEO_USD = 1.52`.
- Env nouvelles : `FAL_KEY` (déjà en .env.local, à poser sur Vercel), `FAL_WEBHOOK_TOKEN` (chaîne aléatoire ≥ 32 chars), `APP_URL` (défaut codé `https://mylab-configurateur.vercel.app`).
- Publication client : possible seulement si ≥ 8 images `done` non écartées. Sélection client : exactement `min(8, images disponibles)` ; les 2 vidéos sont incluses d'office.
- Git : commits `feat(studio): …`, merge en Task 9 après revue finale uniquement.

---

### Task 0: Branche

**Files:** aucun

**Interfaces:**
- Produces: branche `feat/studio-v3-lot4-generation`.

- [ ] **Step 1:**

```bash
cd "d:\Projets mylab vs code\mylab-configurateur"
git checkout main && git pull origin main
git checkout -b feat/studio-v3-lot4-generation
```

---

### Task 1: Modèle Prisma `GenerationJob` + statuts pack + migration

**Files:**
- Modify: `prisma/schema.prisma`
- Create: `prisma/migrations/<timestamp>_add_generation_jobs/migration.sql`

**Interfaces:**
- Consumes: `Project`, `ProjectStatus`.
- Produces: enums `GenerationJobType { image, video }`, `GenerationJobStatus { queued, done, failed, discarded }` ; `ProjectStatus` gagne `pack_generating`, `pack_review`, `pack_ready`, `pack_selected` ; modèle `GenerationJob` ci-dessous ; relation inverse `Project.generationJobs GenerationJob[]` ; accès `prisma.generationJob`.

- [ ] **Step 1: Schema**

`enum ProjectStatus` : ajouter après `onboarding_submitted` :

```prisma
  pack_generating // jobs fal en cours
  pack_review     // pack généré — revue admin obligatoire avant exposition client
  pack_ready      // publié au client — sélection des favoris ouverte
  pack_selected   // sélection client faite — prêt pour la livraison (Lot 5)
```

Nouveaux enums + modèle à la suite d'`Onboarding` :

```prisma
enum GenerationJobType {
  image
  video
}

enum GenerationJobStatus {
  queued    // soumis à la queue fal, en attente du webhook
  done      // asset rapatrié sur Cloudinary
  failed    // erreur fal (relançable par l'admin)
  discarded // écarté par l'admin à la revue
}

model GenerationJob {
  id           String              @id @default(cuid())
  projectId    String
  project      Project             @relation(fields: [projectId], references: [id])
  type         GenerationJobType
  templateKey  String // clé du template de prompt (lib generation.ts)
  prompt       String
  referenceIds String[]            @default([]) // LabelReference sources des photos
  falRequestId String?             @unique
  status       GenerationJobStatus @default(queued)
  assetUrl     String? // Cloudinary (jamais l'URL fal, qui expire)
  costUsd      Float?
  error        String?
  selected     Boolean             @default(false) // choix client (galerie)
  createdAt    DateTime            @default(now())
  updatedAt    DateTime            @updatedAt

  @@index([projectId])
}
```

Relation inverse dans `Project` : `generationJobs GenerationJob[]`.

- [ ] **Step 2: Migration (recette éprouvée : `prisma migrate diff --from-schema <HEAD> --to-schema … --script`, timestamp UTC > existants, SANS l'appliquer)** — ajouter le bloc RLS :

```sql
ALTER TABLE "GenerationJob" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON "GenerationJob" FOR ALL USING (auth.role() = 'service_role');
```

- [ ] **Step 3: Vérifier** — Run: `npx prisma generate && npx tsc --noEmit` → 0 erreur.

- [ ] **Step 4: Commit**

```bash
git add prisma/schema.prisma prisma/migrations
git commit -m "feat(studio): modele GenerationJob + statuts pack + migration RLS"
```

---

### Task 2: Lib pure `generation.ts` — plan du pack, prompts, règles (TDD)

**Files:**
- Create: `src/lib/studio/generation.ts`
- Test: `src/lib/studio/generation.test.ts`
- Modify: `src/lib/studio/bat.ts` + `src/lib/studio/bat.test.ts` (`projectDoneCount` : statuts pack → 3)

**Interfaces:**
- Consumes: type `BrandDna` de `@/lib/studio/onboarding`.
- Produces (consommé par Tasks 4-8) :
  - `COST_IMAGE_USD = 0.15`, `COST_VIDEO_USD = 1.52`
  - `IMAGE_MODEL_ID = "fal-ai/nano-banana-pro/edit"`, `VIDEO_MODEL_ID = "bytedance/seedance-2.0/image-to-video"`
  - `PACK_IMAGE_COUNT = 12`, `PACK_VIDEO_COUNT = 2`, `PACK_SELECT_COUNT = 8`
  - `type ImageSpec = { templateKey: string; referenceIds: string[]; prompt: string }`
  - `buildPackPlan(references: { id: string; title: string }[], dna: BrandDna): ImageSpec[]` — exactement 12 specs, 6 templates × 2 tours, références en round-robin (le template `duo-gamme` prend 2 références si possible), déterministe.
  - `buildVideoPrompt(dna: BrandDna): string`
  - `packStatusAfterJobs(jobs: { type: string; status: string }[]): "generating" | "review"` — `review` quand plus AUCUN job `queued`.
  - `canPublish(jobs: { type: string; status: string }[]): boolean` — ≥ 8 images `done` non écartées.
  - `selectableImageCount(jobs: …): number` et `requiredSelection(available: number): number` = `min(8, available)`.
  - `projectDoneCount` (bat.ts) : `pack_generating|pack_review|pack_ready|pack_selected` → 3.

- [ ] **Step 1: Tests (échouent)**

```ts
// src/lib/studio/generation.test.ts
import { describe, it, expect } from "vitest";
import {
  buildPackPlan, buildVideoPrompt, packStatusAfterJobs, canPublish,
  selectableImageCount, requiredSelection, PACK_IMAGE_COUNT,
} from "./generation";

const DNA = { palette: ["#1a3a2a", "#f5f0eb", "#c5a467"], ambiance: "naturelle", ton: "chaleureux", style: "botanique", univers: "soins capillaires clean", cible: "femmes 25-45" };
const REFS = [
  { id: "r1", title: "Shampoing nourrissant" },
  { id: "r2", title: "Masque réparateur" },
  { id: "r3", title: "Huile brillance" },
];

describe("buildPackPlan", () => {
  const plan = buildPackPlan(REFS, DNA);
  it("produit exactement 12 specs, 6 templates × 2", () => {
    expect(plan).toHaveLength(PACK_IMAGE_COUNT);
    const byTemplate = new Map<string, number>();
    plan.forEach((s) => byTemplate.set(s.templateKey, (byTemplate.get(s.templateKey) ?? 0) + 1));
    expect([...byTemplate.values()].every((n) => n === 2)).toBe(true);
    expect(byTemplate.size).toBe(6);
  });
  it("distribue les références en round-robin et duo-gamme en prend 2", () => {
    const duo = plan.filter((s) => s.templateKey === "duo-gamme");
    expect(duo[0].referenceIds).toHaveLength(2);
    const singles = plan.filter((s) => s.templateKey !== "duo-gamme");
    expect(singles.every((s) => s.referenceIds.length === 1)).toBe(true);
    expect(new Set(plan.flatMap((s) => s.referenceIds)).size).toBe(3); // toutes les refs servent
  });
  it("injecte le Brand DNA et la clause de fidélité dans chaque prompt", () => {
    for (const s of plan) {
      expect(s.prompt).toContain("étiquette");
      expect(s.prompt.toLowerCase()).toContain("identique");
      expect(s.prompt).toContain(DNA.ambiance);
    }
    expect(plan.find((s) => s.templateKey === "packshot-palette")!.prompt).toContain("#1a3a2a");
    expect(plan.find((s) => s.templateKey === "scene-univers")!.prompt).toContain(DNA.univers);
  });
  it("gère 1 seule référence (duo-gamme dégrade en 1)", () => {
    const solo = buildPackPlan([REFS[0]], DNA);
    expect(solo).toHaveLength(12);
    expect(solo.every((s) => s.referenceIds.every((id) => id === "r1"))).toBe(true);
  });
  it("déterministe", () => {
    expect(buildPackPlan(REFS, DNA)).toEqual(buildPackPlan(REFS, DNA));
  });
});

describe("buildVideoPrompt", () => {
  it("contient l'ambiance et la clause de netteté", () => {
    const p = buildVideoPrompt(DNA);
    expect(p).toContain(DNA.ambiance);
    expect(p).toContain("nets");
  });
});

describe("packStatusAfterJobs", () => {
  it("generating tant qu'un job est queued", () => {
    expect(packStatusAfterJobs([{ type: "image", status: "done" }, { type: "video", status: "queued" }])).toBe("generating");
  });
  it("review quand tout est terminal (done/failed/discarded)", () => {
    expect(packStatusAfterJobs([{ type: "image", status: "done" }, { type: "image", status: "failed" }])).toBe("review");
  });
});

describe("canPublish / selection", () => {
  const img = (status: string) => ({ type: "image", status });
  it("publiable à 8 images done non écartées", () => {
    expect(canPublish(Array.from({ length: 8 }, () => img("done")))).toBe(true);
    expect(canPublish([...Array.from({ length: 7 }, () => img("done")), img("failed")])).toBe(false);
  });
  it("selectableImageCount ignore vidéos/failed/discarded ; requiredSelection = min(8, dispo)", () => {
    const jobs = [...Array.from({ length: 10 }, () => img("done")), img("discarded"), { type: "video", status: "done" }];
    expect(selectableImageCount(jobs)).toBe(10);
    expect(requiredSelection(10)).toBe(8);
    expect(requiredSelection(6)).toBe(6);
  });
});
```

Dans `bat.test.ts`, describe `projectDoneCount`, ajouter :

```ts
  it("statuts pack → jalon 3 (livraison en cours)", () => {
    for (const s of ["pack_generating", "pack_review", "pack_ready", "pack_selected"]) {
      expect(projectDoneCount(s)).toBe(3);
    }
  });
```

- [ ] **Step 2: RED** — Run: `npm test -- src/lib/studio/generation.test.ts src/lib/studio/bat.test.ts` → FAIL.

- [ ] **Step 3: Implémenter**

```ts
// src/lib/studio/generation.ts
import type { BrandDna } from "@/lib/studio/onboarding";

export const COST_IMAGE_USD = 0.15;
export const COST_VIDEO_USD = 1.52;
export const IMAGE_MODEL_ID = "fal-ai/nano-banana-pro/edit";
export const VIDEO_MODEL_ID = "bytedance/seedance-2.0/image-to-video";
export const PACK_IMAGE_COUNT = 12;
export const PACK_VIDEO_COUNT = 2;
export const PACK_SELECT_COUNT = 8;

export type ImageSpec = { templateKey: string; referenceIds: string[]; prompt: string };

const FIDELITE = "le flacon et son étiquette restent strictement identiques à la photo de référence, texte parfaitement lisible";

const TEMPLATES: { key: string; duo?: boolean; build: (dna: BrandDna, titles: string[]) => string }[] = [
  { key: "packshot-studio", build: (d) => `Packshot e-commerce professionnel de ce produit cosmétique, fond crème uni, éclairage studio doux, ambiance ${d.ambiance}, style ${d.style}, ${FIDELITE}` },
  { key: "packshot-palette", build: (d) => `Packshot premium de ce produit cosmétique sur fond uni de couleur ${d.palette[0]}, éclairage éditorial, ambiance ${d.ambiance}, ${FIDELITE}` },
  { key: "scene-salle-de-bain", build: (d) => `Ce produit cosmétique posé sur une tablette de salle de bain élégante, ambiance ${d.ambiance}, style ${d.style}, lumière naturelle du matin, ${FIDELITE}` },
  { key: "flatlay-botanique", build: (d) => `Composition flatlay vue de dessus avec ce produit cosmétique, éléments naturels assortis au style ${d.style}, ambiance ${d.ambiance}, ${FIDELITE}` },
  { key: "scene-univers", build: (d) => `Ce produit cosmétique mis en scène dans son univers : ${d.univers}, pensé pour ${d.cible}, ton ${d.ton}, ambiance ${d.ambiance}, ${FIDELITE}` },
  { key: "duo-gamme", duo: true, build: (d, t) => `Composition duo avec ${t.join(" et ")} côte à côte, harmonie de la gamme, ambiance ${d.ambiance}, style ${d.style}, ${FIDELITE}` },
];

export function buildPackPlan(references: { id: string; title: string }[], dna: BrandDna): ImageSpec[] {
  const specs: ImageSpec[] = [];
  let cursor = 0;
  const next = () => references[cursor++ % references.length];
  for (let round = 0; round < 2; round++) {
    for (const tpl of TEMPLATES) {
      if (tpl.duo) {
        const a = next();
        const b = references.length > 1 ? next() : a;
        const ids = a.id === b.id ? [a.id] : [a.id, b.id];
        specs.push({ templateKey: tpl.key, referenceIds: ids, prompt: tpl.build(dna, ids.length === 2 ? [a.title, b.title] : [a.title]) });
      } else {
        const r = next();
        specs.push({ templateKey: tpl.key, referenceIds: [r.id], prompt: tpl.build(dna, [r.title]) });
      }
    }
  }
  return specs;
}

export function buildVideoPrompt(dna: BrandDna): string {
  return `Lent travelling circulaire autour du produit, lumière chaude, ambiance ${dna.ambiance} haut de gamme, rendu publicitaire, le produit et son étiquette restent parfaitement nets et identiques`;
}

export function packStatusAfterJobs(jobs: { type: string; status: string }[]): "generating" | "review" {
  return jobs.some((j) => j.status === "queued") ? "generating" : "review";
}

const doneImages = (jobs: { type: string; status: string }[]) =>
  jobs.filter((j) => j.type === "image" && j.status === "done").length;

export function canPublish(jobs: { type: string; status: string }[]): boolean {
  return doneImages(jobs) >= PACK_SELECT_COUNT;
}

export function selectableImageCount(jobs: { type: string; status: string }[]): number {
  return doneImages(jobs);
}

export function requiredSelection(available: number): number {
  return Math.min(PACK_SELECT_COUNT, available);
}
```

Dans `bat.ts`, `projectDoneCount` :

```ts
const PACK_STATUSES = new Set(["pack_generating", "pack_review", "pack_ready", "pack_selected"]);

export function projectDoneCount(projectStatus: string, requestStatus?: ReqStatus): number {
  if (projectStatus === "draft") return 0;
  if (projectStatus === "onboarding_submitted" || PACK_STATUSES.has(projectStatus)) return 3;
  if (projectStatus === "label_validated" || requestStatus === "validated") return 2;
  return 1;
}
```

- [ ] **Step 4: GREEN** — Run: `npm test -- src/lib/studio/generation.test.ts src/lib/studio/bat.test.ts` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lib/studio/generation.ts src/lib/studio/generation.test.ts src/lib/studio/bat.ts src/lib/studio/bat.test.ts
git commit -m "feat(studio): lib generation — plan du pack 12 visuels, prompts Brand DNA, regles publication/selection (TDD)"
```

---

### Task 3: Lib `fal-queue.ts` — soumission + rapatriement (colle mince)

**Files:**
- Create: `src/lib/studio/fal-queue.ts`

**Interfaces:**
- Consumes: `@fal-ai/client`, `uploadToCloudinary` (`@/lib/cloudinary`), env `FAL_KEY`, `FAL_WEBHOOK_TOKEN`, `APP_URL?`.
- Produces (consommé par Tasks 4-5) :
  - `submitImageJob(prompt: string, imageUrls: string[]): Promise<string>` — `fal.queue.submit(IMAGE_MODEL_ID, { input: { prompt, image_urls }, webhookUrl: webhookUrl() })`, retourne `request_id`.
  - `submitVideoJob(prompt: string, imageUrl: string): Promise<string>` — idem avec `{ prompt, image_url, resolution: "720p", duration: "5" }` sur `VIDEO_MODEL_ID`.
  - `fetchResultUrl(type: "image" | "video", requestId: string): Promise<string>` — `fal.queue.result(modelId, { requestId })`, extrait `images[0].url` ou `video.url`, throw si absent.
  - `mirrorToCloudinary(url: string, jobId: string, type: "image" | "video"): Promise<string>` — fait ingérer l'URL fal par Cloudinary (folder `studio-packs`, public_id = jobId, `resource_type` selon le type — Cloudinary ingère une URL distante directement).
  - `webhookUrl(): string` — `${process.env.APP_URL ?? "https://mylab-configurateur.vercel.app"}/api/webhooks/fal?token=${process.env.FAL_WEBHOOK_TOKEN}`.

- [ ] **Step 1: Implémenter**

```ts
// src/lib/studio/fal-queue.ts
import { fal } from "@fal-ai/client";
import { v2 as cloudinary } from "cloudinary";
import { IMAGE_MODEL_ID, VIDEO_MODEL_ID } from "@/lib/studio/generation";

let configured = false;
function ensureConfigured() {
  if (configured) return;
  if (!process.env.FAL_KEY) throw new Error("FAL_KEY manquante");
  fal.config({ credentials: process.env.FAL_KEY });
  configured = true;
}

export function webhookUrl(): string {
  const base = process.env.APP_URL ?? "https://mylab-configurateur.vercel.app";
  return `${base}/api/webhooks/fal?token=${process.env.FAL_WEBHOOK_TOKEN ?? ""}`;
}

export async function submitImageJob(prompt: string, imageUrls: string[]): Promise<string> {
  ensureConfigured();
  const { request_id } = await fal.queue.submit(IMAGE_MODEL_ID, {
    input: { prompt, image_urls: imageUrls },
    webhookUrl: webhookUrl(),
  });
  return request_id;
}

export async function submitVideoJob(prompt: string, imageUrl: string): Promise<string> {
  ensureConfigured();
  const { request_id } = await fal.queue.submit(VIDEO_MODEL_ID, {
    input: { prompt, image_url: imageUrl, resolution: "720p", duration: "5" },
    webhookUrl: webhookUrl(),
  });
  return request_id;
}

export async function fetchResultUrl(type: "image" | "video", requestId: string): Promise<string> {
  ensureConfigured();
  const modelId = type === "image" ? IMAGE_MODEL_ID : VIDEO_MODEL_ID;
  const r = await fal.queue.result(modelId, { requestId });
  const data = r.data as { images?: { url: string }[]; image?: { url: string }; video?: { url: string } };
  const url = type === "image" ? data.images?.[0]?.url ?? data.image?.url : data.video?.url;
  if (!url) throw new Error(`Résultat fal sans asset (${requestId})`);
  return url;
}

export async function mirrorToCloudinary(url: string, jobId: string, type: "image" | "video"): Promise<string> {
  const r = await cloudinary.uploader.upload(url, {
    folder: "mylab-configurateur/studio-packs",
    public_id: jobId,
    resource_type: type === "video" ? "video" : "image",
    overwrite: true,
  });
  return r.secure_url as string;
}
```

Note : `cloudinary.config()` est déjà appelé par `@/lib/cloudinary` importé ailleurs ; ici on importe `v2` directement — vérifier que la config module (`src/lib/cloudinary.ts`) est bien exécutée en l'important : ajouter en tête `import "@/lib/cloudinary";` si sa config est un effet de module (à vérifier dans le fichier, adapter minimalement et le noter au rapport).

- [ ] **Step 2: Vérifier** — Run: `npx tsc --noEmit && npm test` → 0 erreur (pas de test dédié : I/O pur vers fal/Cloudinary, exercé en e2e Task 9 ; signatures verrouillées par les consommateurs typés).

- [ ] **Step 3: Commit**

```bash
git add src/lib/studio/fal-queue.ts
git commit -m "feat(studio): lib fal-queue — soumission webhook + rapatriement Cloudinary"
```

---

### Task 4: Déclencheur — la soumission d'onboarding lance le pack

**Files:**
- Modify: `src/app/api/studio/onboarding/[projectId]/route.ts`

**Interfaces:**
- Consumes: Tasks 1-3 (`prisma.generationJob`, `buildPackPlan`, `submitImageJob`), données onboarding (photos par référence), `after`.
- Produces: au submit réussi (dans le `after()` existant, APRÈS l'email admin) : création des 12 `GenerationJob` image + soumission fal + `project.status = "pack_generating"`. Idempotent : si des jobs existent déjà pour le projet → skip.

- [ ] **Step 1: Étendre le `after()` de soumission**

Dans la route, remplacer le bloc `if (result.submitted) { after(...) }` par :

```ts
  if (result.submitted) {
    after(async () => {
      await sendStudioEmail(
        ADMIN_EMAIL,
        buildOnboardingSubmittedEmail({ orderNumber: project.shopifyOrderNumber ?? "—", brandName: project.brandName })
      );
      await launchPackGeneration(projectId);
    });
  }
```

Et ajouter en bas du fichier (imports en tête : `buildPackPlan` de `@/lib/studio/generation`, `submitImageJob` de `@/lib/studio/fal-queue`, type `BrandDna` et `PhotosEntry` de `@/lib/studio/onboarding`) :

```ts
async function launchPackGeneration(projectId: string) {
  try {
    const existing = await prisma.generationJob.count({ where: { projectId } });
    if (existing > 0) return; // idempotence (retry after(), resoumission)

    const project = await prisma.project.findUnique({
      where: { id: projectId },
      include: { onboarding: true, labelRequest: { include: { references: { orderBy: { title: "asc" } } } } },
    });
    const dna = project?.onboarding?.brandDna as BrandDna | null | undefined;
    const photos = (project?.onboarding?.photos ?? []) as PhotosEntry[];
    const references = project?.labelRequest?.references ?? [];
    if (!project || !dna || references.length === 0) {
      console.error(`[pack] données onboarding incomplètes pour ${projectId} — génération non lancée`);
      return;
    }

    const photosByRef = new Map(photos.map((p) => [p.referenceId, p.urls]));
    const plan = buildPackPlan(references.map((r) => ({ id: r.id, title: r.title })), dna);

    for (const spec of plan) {
      const imageUrls = spec.referenceIds.flatMap((id) => photosByRef.get(id) ?? []);
      if (imageUrls.length === 0) continue;
      const job = await prisma.generationJob.create({
        data: { projectId, type: "image", templateKey: spec.templateKey, prompt: spec.prompt, referenceIds: spec.referenceIds },
      });
      try {
        const falRequestId = await submitImageJob(spec.prompt, imageUrls);
        await prisma.generationJob.update({ where: { id: job.id }, data: { falRequestId } });
      } catch (e) {
        await prisma.generationJob.update({
          where: { id: job.id },
          data: { status: "failed", error: e instanceof Error ? e.message.slice(0, 500) : "échec soumission fal" },
        });
      }
    }
    await prisma.project.update({ where: { id: projectId }, data: { status: "pack_generating" } });
    console.log(`[pack] ${plan.length} jobs image soumis pour ${projectId}`);
  } catch (e) {
    console.error("[pack] échec du lancement:", e);
  }
}
```

- [ ] **Step 2: Vérifier** — Run: `npx tsc --noEmit && npm test` → 0 erreur, suite verte.

- [ ] **Step 3: Commit**

```bash
git add src/app/api/studio/onboarding
git commit -m "feat(studio): la soumission d'onboarding lance la generation du pack (12 jobs fal, idempotent)"
```

---

### Task 5: Webhook fal — rapatriement, enchaînement vidéos, bascule en revue

**Files:**
- Create: `src/app/api/webhooks/fal/route.ts`

**Interfaces:**
- Consumes: Tasks 1-3 (`fetchResultUrl`, `mirrorToCloudinary`, `submitVideoJob`, `buildVideoPrompt`, `packStatusAfterJobs`, coûts), `buildPackReviewEmail` (Task 6), env `FAL_WEBHOOK_TOKEN`.
- Produces: `POST /api/webhooks/fal?token=…` → 401 token invalide ; 200 `{ignored:true}` request_id inconnu ; sinon : re-fetch du résultat chez fal (JAMAIS confiance au corps), mirror Cloudinary, job `done` + coût (ou `failed` + error) ; **idempotent** (job déjà terminal → 200 sans effet) ; si plus aucun job image `queued` et aucune vidéo n'existe → soumission des `PACK_VIDEO_COUNT` vidéos depuis les 2 premiers packshots `done` ; si plus AUCUN job `queued` du tout → `project.status = "pack_review"` + email admin.

- [ ] **Step 1: Implémenter**

```ts
// src/app/api/webhooks/fal/route.ts
import { NextResponse } from "next/server";
import { after } from "next/server";
import { prisma } from "@/lib/prisma";
import { fetchResultUrl, mirrorToCloudinary, submitVideoJob } from "@/lib/studio/fal-queue";
import { buildVideoPrompt, packStatusAfterJobs, COST_IMAGE_USD, COST_VIDEO_USD, PACK_VIDEO_COUNT } from "@/lib/studio/generation";
import { buildPackReviewEmail, sendStudioEmail, ADMIN_EMAIL } from "@/lib/studio/notifications";
import type { BrandDna } from "@/lib/studio/onboarding";

export async function POST(req: Request) {
  const url = new URL(req.url);
  if (!process.env.FAL_WEBHOOK_TOKEN || url.searchParams.get("token") !== process.env.FAL_WEBHOOK_TOKEN)
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  let body: { request_id?: string; status?: string };
  try {
    body = (await req.json()) as typeof body;
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }
  if (!body.request_id) return NextResponse.json({ ignored: true });

  const job = await prisma.generationJob.findUnique({ where: { falRequestId: body.request_id }, include: { project: true } });
  if (!job) return NextResponse.json({ ignored: true });
  if (job.status !== "queued") return NextResponse.json({ ok: true, idempotent: true }); // retry fal — déjà traité

  try {
    // Le corps du webhook n'est PAS cru : on relit le résultat chez fal avec nos credentials.
    const falUrl = await fetchResultUrl(job.type, body.request_id);
    const assetUrl = await mirrorToCloudinary(falUrl, job.id, job.type);
    await prisma.generationJob.update({
      where: { id: job.id },
      data: { status: "done", assetUrl, costUsd: job.type === "image" ? COST_IMAGE_USD : COST_VIDEO_USD },
    });
  } catch (e) {
    await prisma.generationJob.update({
      where: { id: job.id },
      data: { status: "failed", error: e instanceof Error ? e.message.slice(0, 500) : "échec récupération" },
    });
  }

  const jobs = await prisma.generationJob.findMany({ where: { projectId: job.projectId } });
  const images = jobs.filter((j) => j.type === "image");
  const videos = jobs.filter((j) => j.type === "video");

  // Enchaînement : toutes les images terminales, pas encore de vidéos → on les soumet.
  if (videos.length === 0 && images.every((j) => j.status !== "queued")) {
    const sources = images.filter((j) => j.status === "done" && j.templateKey.startsWith("packshot") && j.assetUrl).slice(0, PACK_VIDEO_COUNT);
    const fallback = images.filter((j) => j.status === "done" && j.assetUrl).slice(0, PACK_VIDEO_COUNT);
    const chosen = sources.length >= PACK_VIDEO_COUNT ? sources : fallback;
    const onboarding = await prisma.onboarding.findUnique({ where: { projectId: job.projectId } });
    const dna = onboarding?.brandDna as BrandDna | null;
    for (const src of chosen) {
      const v = await prisma.generationJob.create({
        data: { projectId: job.projectId, type: "video", templateKey: "reel-travelling", prompt: dna ? buildVideoPrompt(dna) : "Lent travelling circulaire autour du produit, le produit et son étiquette restent parfaitement nets", referenceIds: src.referenceIds },
      });
      try {
        const rid = await submitVideoJob(v.prompt, src.assetUrl!);
        await prisma.generationJob.update({ where: { id: v.id }, data: { falRequestId: rid } });
      } catch (e) {
        await prisma.generationJob.update({ where: { id: v.id }, data: { status: "failed", error: e instanceof Error ? e.message.slice(0, 500) : "échec soumission" } });
      }
    }
    return NextResponse.json({ ok: true, videosSubmitted: chosen.length });
  }

  // Fin de pack : plus aucun job queued (vidéos incluses, si elles existent) → revue admin.
  if (videos.length > 0 && packStatusAfterJobs(jobs) === "review" && job.project.status === "pack_generating") {
    await prisma.project.update({ where: { id: job.projectId }, data: { status: "pack_review" } });
    after(async () => {
      const doneCount = jobs.filter((j) => j.status === "done").length;
      await sendStudioEmail(ADMIN_EMAIL, buildPackReviewEmail({ orderNumber: job.project.shopifyOrderNumber ?? "—", doneCount, totalCount: jobs.length }));
    });
  }

  return NextResponse.json({ ok: true });
}
```

- [ ] **Step 2: Vérifier** — Run: `npx tsc --noEmit && npm test` → 0 erreur (Task 6 doit fournir `buildPackReviewEmail` — si tu exécutes les tâches dans l'ordre, implémente Task 6 Step 1 d'abord OU committe les deux ensemble ; l'ordre recommandé du plan place les emails en Task 6 : dans ce cas fais Task 6 AVANT Task 5 et note-le).

- [ ] **Step 3: Commit**

```bash
git add src/app/api/webhooks/fal
git commit -m "feat(studio): webhook fal — rapatriement Cloudinary, enchainement videos, bascule pack_review (idempotent)"
```

---

### Task 6: Notifications pack (TDD) — 3 builders

**Files:**
- Modify: `src/lib/studio/notifications.ts` + test

**Interfaces:**
- Consumes: helpers existants.
- Produces (consommé par Tasks 5, 7, 8) :
  - `buildPackReviewEmail({ orderNumber, doneCount, totalCount })` → admin : « Pack généré — à revoir » (subject `Pack généré — commande n°X`), compteur `N/M réussis`, lien `/admin/pack`.
  - `buildPackReadyEmail({ orderNumber })` → client : « Vos visuels sont prêts ! » (subject `Vos visuels de lancement sont prêts — commande n°X`), lien `/projet`.
  - `buildPackSelectedEmail({ orderNumber, selectedCount })` → admin : subject `Pack validé par le client — commande n°X`, lien `/admin/pack`.

- [ ] **Step 1: Tests (échouent)** — ajouter au fichier de test (import des 3 builders) :

```ts
describe("emails pack", () => {
  it("buildPackReviewEmail — admin, compteur, lien /admin/pack", () => {
    const m = buildPackReviewEmail({ orderNumber: "1042", doneCount: 13, totalCount: 14 });
    expect(m.subject).toBe("Pack généré — commande n°1042");
    expect(m.html).toContain("13/14");
    expect(m.html).toContain("/admin/pack");
  });
  it("buildPackReadyEmail — client, lien /projet", () => {
    const m = buildPackReadyEmail({ orderNumber: "1042" });
    expect(m.subject).toBe("Vos visuels de lancement sont prêts — commande n°1042");
    expect(m.html).toContain("https://mylab-configurateur.vercel.app/projet");
  });
  it("buildPackSelectedEmail — admin, compteur", () => {
    const m = buildPackSelectedEmail({ orderNumber: "1042", selectedCount: 8 });
    expect(m.subject).toBe("Pack validé par le client — commande n°1042");
    expect(m.html).toContain("8 visuel(s)");
  });
});
```

- [ ] **Step 2: RED** — Run: `npm test -- src/lib/studio/notifications.test.ts` → FAIL.

- [ ] **Step 3: Implémenter** (dans `notifications.ts`, réutilise `wrap`) :

```ts
const ADMIN_PACK_URL = "https://mylab-configurateur.vercel.app/admin/pack";

export function buildPackReviewEmail(p: { orderNumber: string; doneCount: number; totalCount: number }): StudioEmail {
  return {
    subject: `Pack généré — commande n°${p.orderNumber}`,
    html: wrap("Pack de lancement généré", `<p>${p.doneCount}/${p.totalCount} assets réussis. Revue obligatoire avant publication au client.</p><p><a href="${ADMIN_PACK_URL}">Ouvrir la revue du pack</a></p>`),
    text: `Pack généré (commande n°${p.orderNumber}) : ${p.doneCount}/${p.totalCount} réussis. Revue : ${ADMIN_PACK_URL}`,
  };
}

export function buildPackReadyEmail(p: { orderNumber: string }): StudioEmail {
  return {
    subject: `Vos visuels de lancement sont prêts — commande n°${p.orderNumber}`,
    html: wrap("Vos visuels sont prêts ✨", `<p>Votre pack de lancement vous attend : découvrez vos visuels et choisissez vos favoris.</p><p><a href="${PROJET_URL}" style="display:inline-block;background:#212326;color:#fff;padding:12px 24px;text-decoration:none;">Voir mes visuels</a></p>`),
    text: `Vos visuels de lancement sont prêts (commande n°${p.orderNumber}). Choisissez vos favoris : ${PROJET_URL}`,
  };
}

export function buildPackSelectedEmail(p: { orderNumber: string; selectedCount: number }): StudioEmail {
  return {
    subject: `Pack validé par le client — commande n°${p.orderNumber}`,
    html: wrap("Sélection client faite ✓", `<p>Le client a choisi ${p.selectedCount} visuel(s). Prêt pour la livraison du site (Lot 5).</p><p><a href="${ADMIN_PACK_URL}">Voir le pack</a></p>`),
    text: `Pack validé (commande n°${p.orderNumber}) : ${p.selectedCount} visuel(s) choisis. ${ADMIN_PACK_URL}`,
  };
}
```

(`PROJET_URL` existe déjà dans le module.)

- [ ] **Step 4: GREEN** — Run: `npm test -- src/lib/studio/notifications.test.ts` → PASS (13 tests).

- [ ] **Step 5: Commit**

```bash
git add src/lib/studio/notifications.ts src/lib/studio/notifications.test.ts
git commit -m "feat(studio): emails pack — revue admin, pack pret client, selection faite (TDD)"
```

---

### Task 7: API pack — actions admin + sélection client

**Files:**
- Create: `src/app/api/studio/pack/jobs/[id]/route.ts` (POST admin : `{ action: "discard" | "regenerate" }`)
- Create: `src/app/api/studio/pack/[projectId]/publish/route.ts` (POST admin)
- Create: `src/app/api/studio/pack/[projectId]/select/route.ts` (POST client : `{ jobIds: string[] }`)

**Interfaces:**
- Consumes: gardes existantes (`requireBatStaff` pour admin — le graphiste n'a PAS accès au pack : utiliser un nouveau check inline `role === "admin"`… non : réutiliser `require-admin.ts::requireAdmin()` existant), garde propriétaire (pattern `loadOwnedProject` — inline), libs Tasks 2-3, emails Task 6.
- Produces :
  - `POST /api/studio/pack/jobs/[id]` admin. `discard` : job `done` → `discarded` (200 `{status}`) ; `regenerate` : job `failed|discarded|done` → nouveau `falRequestId` via resoumission (`submitImageJob`/`submitVideoJob` selon type — pour une vidéo, re-source depuis le premier packshot done du projet), statut → `queued`, `selected=false`, projet → `pack_generating` s'il était `pack_review` (le webhook refera la bascule). 409 si projet `pack_ready|pack_selected` (publié = figé sauf retour arrière manuel).
  - `POST /api/studio/pack/[projectId]/publish` admin : 409 si `!canPublish(jobs)` ou statut projet ≠ `pack_review` ; sinon `pack_ready` + email client via `after()`.
  - `POST /api/studio/pack/[projectId]/select` client propriétaire : body `jobIds` ; 409 si statut ≠ `pack_ready` ; valide que chaque id est un job image `done` non `discarded` du projet et que `jobIds.length === requiredSelection(selectableImageCount(jobs))` ; transaction : reset `selected=false` sur les images du projet puis `selected=true` sur les choisis ; projet → `pack_selected` + email admin. 200 `{selectedCount}`.

- [ ] **Step 1: Route actions job (admin)**

```ts
// src/app/api/studio/pack/jobs/[id]/route.ts
import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { requireAdmin } from "@/lib/require-admin";
import { submitImageJob, submitVideoJob } from "@/lib/studio/fal-queue";

export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const guard = await requireAdmin();
  if (guard) return guard;
  const { id } = await params;
  const { action } = (await req.json()) as { action?: "discard" | "regenerate" };
  if (action !== "discard" && action !== "regenerate")
    return NextResponse.json({ error: "action invalide" }, { status: 400 });

  const job = await prisma.generationJob.findUnique({ where: { id }, include: { project: true } });
  if (!job) return NextResponse.json({ error: "Job introuvable" }, { status: 404 });
  if (job.project.status === "pack_ready" || job.project.status === "pack_selected")
    return NextResponse.json({ error: "Pack déjà publié" }, { status: 409 });

  if (action === "discard") {
    if (job.status !== "done") return NextResponse.json({ error: "Seul un asset généré peut être écarté" }, { status: 409 });
    await prisma.generationJob.update({ where: { id }, data: { status: "discarded", selected: false } });
    return NextResponse.json({ status: "discarded" });
  }

  // regenerate
  try {
    let falRequestId: string;
    if (job.type === "image") {
      const onboarding = await prisma.onboarding.findUnique({ where: { projectId: job.projectId } });
      const photos = (onboarding?.photos ?? []) as { referenceId: string; urls: string[] }[];
      const urls = job.referenceIds.flatMap((rid) => photos.find((p) => p.referenceId === rid)?.urls ?? []);
      if (urls.length === 0) return NextResponse.json({ error: "Photos de référence introuvables" }, { status: 409 });
      falRequestId = await submitImageJob(job.prompt, urls);
    } else {
      const src = await prisma.generationJob.findFirst({
        where: { projectId: job.projectId, type: "image", status: "done", assetUrl: { not: null } },
        orderBy: { createdAt: "asc" },
      });
      if (!src?.assetUrl) return NextResponse.json({ error: "Aucune image source disponible" }, { status: 409 });
      falRequestId = await submitVideoJob(job.prompt, src.assetUrl);
    }
    await prisma.$transaction(async (tx) => {
      await tx.generationJob.update({
        where: { id },
        data: { falRequestId, status: "queued", assetUrl: null, error: null, selected: false },
      });
      if (job.project.status === "pack_review")
        await tx.project.update({ where: { id: job.projectId }, data: { status: "pack_generating" } });
    });
    return NextResponse.json({ status: "queued" });
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message.slice(0, 300) : "échec resoumission" }, { status: 502 });
  }
}
```

- [ ] **Step 2: Route publish (admin)**

```ts
// src/app/api/studio/pack/[projectId]/publish/route.ts
import { NextResponse } from "next/server";
import { after } from "next/server";
import { prisma } from "@/lib/prisma";
import { requireAdmin } from "@/lib/require-admin";
import { canPublish } from "@/lib/studio/generation";
import { buildPackReadyEmail, sendStudioEmail } from "@/lib/studio/notifications";

export async function POST(_req: Request, { params }: { params: Promise<{ projectId: string }> }) {
  const guard = await requireAdmin();
  if (guard) return guard;
  const { projectId } = await params;
  const project = await prisma.project.findUnique({ where: { id: projectId }, include: { generationJobs: true } });
  if (!project) return NextResponse.json({ error: "Projet introuvable" }, { status: 404 });
  if (project.status !== "pack_review") return NextResponse.json({ error: "Le pack n'est pas en revue" }, { status: 409 });
  if (!canPublish(project.generationJobs)) return NextResponse.json({ error: "Il faut au moins 8 images réussies non écartées" }, { status: 409 });

  await prisma.project.update({ where: { id: projectId }, data: { status: "pack_ready" } });
  after(async () => {
    await sendStudioEmail(project.email, buildPackReadyEmail({ orderNumber: project.shopifyOrderNumber ?? "—" }));
  });
  return NextResponse.json({ status: "pack_ready" });
}
```

- [ ] **Step 3: Route select (client)**

```ts
// src/app/api/studio/pack/[projectId]/select/route.ts
import { NextResponse } from "next/server";
import { after } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { selectableImageCount, requiredSelection } from "@/lib/studio/generation";
import { buildPackSelectedEmail, sendStudioEmail, ADMIN_EMAIL } from "@/lib/studio/notifications";

export async function POST(req: Request, { params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const session = await getServerSession(authOptions);
  if (!session?.user?.email) return NextResponse.json({ error: "Non authentifié" }, { status: 401 });

  const project = await prisma.project.findUnique({ where: { id: projectId }, include: { generationJobs: true } });
  if (!project) return NextResponse.json({ error: "Projet introuvable" }, { status: 404 });
  const email = session.user.email.toLowerCase();
  if (project.userId !== session.user.id && project.email !== email)
    return NextResponse.json({ error: "Accès interdit" }, { status: 403 });
  if (project.status !== "pack_ready") return NextResponse.json({ error: "La sélection n'est pas ouverte" }, { status: 409 });

  const { jobIds } = (await req.json()) as { jobIds?: string[] };
  const selectable = new Set(
    project.generationJobs.filter((j) => j.type === "image" && j.status === "done").map((j) => j.id)
  );
  const required = requiredSelection(selectableImageCount(project.generationJobs));
  if (!Array.isArray(jobIds) || jobIds.length !== required || jobIds.some((id) => !selectable.has(id)))
    return NextResponse.json({ error: `Sélectionnez exactement ${required} visuel(s)` }, { status: 400 });

  await prisma.$transaction(async (tx) => {
    await tx.generationJob.updateMany({ where: { projectId, type: "image" }, data: { selected: false } });
    await tx.generationJob.updateMany({ where: { id: { in: jobIds } }, data: { selected: true } });
    await tx.project.update({ where: { id: projectId }, data: { status: "pack_selected" } });
  });
  after(async () => {
    await sendStudioEmail(ADMIN_EMAIL, buildPackSelectedEmail({ orderNumber: project.shopifyOrderNumber ?? "—", selectedCount: jobIds.length }));
  });
  return NextResponse.json({ selectedCount: jobIds.length });
}
```

- [ ] **Step 4: Vérifier** — Run: `npx tsc --noEmit && npm test` → 0 erreur, suite verte.

- [ ] **Step 5: Commit**

```bash
git add src/app/api/studio/pack
git commit -m "feat(studio): API pack — discard/regenerate, publish (>=8 done), selection client exacte"
```

---

### Task 8: UIs — revue admin `/admin/pack` + galerie client `/projet`

**Files:**
- Modify: `src/components/admin/AdminSidebar.tsx` (entrée `{ href: "/admin/pack", label: "Packs visuels", icon: Sparkles }` — import `Sparkles` de lucide-react, après « BAT Étiquettes »)
- Create: `src/app/admin/(dashboard)/pack/page.tsx` (liste des projets avec jobs, statut, compteurs)
- Create: `src/app/admin/(dashboard)/pack/[projectId]/page.tsx` (grille assets + actions)
- Create: `src/components/admin/PackReviewGrid.tsx` (client : cartes asset avec Écarter/Relancer + bouton Publier)
- Modify: `src/app/projet/page.tsx` (bloc pack : bandeau `pack_generating`/`pack_review`, galerie si `pack_ready`, confirmation si `pack_selected`)
- Create: `src/components/projet/PackGallery.tsx` (client : sélection exacte de N favoris + vidéos en lecture)

**Interfaces:**
- Consumes: routes Task 7, `requiredSelection`/`selectableImageCount` (Task 2), grammaires visuelles respectives.
- Produces: parcours complet visible. Détails d'implémentation imposés :
  - **Admin liste** : `prisma.project.findMany({ where: { generationJobs: { some: {} } }, include: { generationJobs: true } })`, table pattern « designs » : commande, email, `X done / Y failed / Z écartés`, badge statut projet (`pack_generating` ambre / `pack_review` violet / `pack_ready` bleu / `pack_selected` vert), lien Ouvrir.
  - **Admin détail** : grille `grid grid-cols-2 lg:grid-cols-3 gap-4` de cartes : `<img>` (ou `<video controls>` pour type video), templateKey + coût, badge statut, boutons « Écarter » (si done) / « Relancer » (toujours, sauf pack publié) via `PackReviewGrid` (fetch POST + `router.refresh()`, pattern ProductForm). En tête : compteur `canPublish` et bouton « Publier au client » (disabled si non publiable), POST publish, bandeau si déjà publié.
  - **Client `/projet`** : après le bloc onboarding existant — `pack_generating|pack_review` : bandeau neutre « 🎨 Vos visuels sont en cours de création — vous serez notifié » ; `pack_ready` : `<PackGallery jobs={imagesDone} videos={videosDone} required={N} projectId=… />` — cartes cliquables (ring de sélection), compteur `sélectionnés/N`, bouton « Valider ma sélection » disabled tant que ≠ N, POST select + refresh ; vidéos affichées en dessous (lecture seule, incluses d'office) ; `pack_selected` : bandeau vert « ✅ Sélection enregistrée — place à la mise en ligne de votre site ! » + galerie figée des choisis.
  - Les `<img>` de la galerie client utilisent l'URL Cloudinary avec transformation `w_600,q_auto,f_auto` (insertion après `/upload/` — helper local inline, PAS `watermarkUrl` : le pack publié n'est pas filigrané, le client l'a payé).

- [ ] **Step 1: Sidebar + pages admin + PackReviewGrid** (suivre les détails imposés ci-dessus ; reprendre les patterns exacts de `/admin/bat` Task 7 Lot 2 : `export const dynamic = "force-dynamic"`, badges span, `.card p-0 overflow-hidden` pour la table, fiche avec retour `ArrowLeft`).

- [ ] **Step 2: Bloc pack dans `/projet` + PackGallery** (grammaire neutre ; inclure les jobs dans l'`include` du `findMany` existant : `generationJobs: true`).

- [ ] **Step 3: Vérifier** — Run: `npx tsc --noEmit && npm run lint && npm test` → 0 erreur sur les fichiers touchés. ⚠️ Leçon récurrente : AUCUN sous-composant défini dans un corps de render (règle `react-hooks/static-components`) — hoister à la portée module avec props.

- [ ] **Step 4: Commit**

```bash
git add src/components/admin/AdminSidebar.tsx src/app/admin/(dashboard)/pack src/components/admin/PackReviewGrid.tsx src/app/projet/page.tsx src/components/projet/PackGallery.tsx
git commit -m "feat(studio): revue admin /admin/pack + galerie de selection client dans /projet"
```

---

### Task 9: Env, déploiement, e2e (contrôleur, après revue finale)

**Files:**
- Modify: `.env.example` (+`FAL_WEBHOOK_TOKEN=`, `APP_URL=` commentées)

**Interfaces:**
- Produces: Lot 4 en prod vérifié bout en bout.

- [ ] **Step 1:** `.env.example` : ajouter sous le bloc Studio :

```
FAL_WEBHOOK_TOKEN=   # chaîne aléatoire >=32 chars — authentifie /api/webhooks/fal
APP_URL=             # optionnel, défaut https://mylab-configurateur.vercel.app
```

Commit `chore(studio): env Lot 4 (FAL_WEBHOOK_TOKEN, APP_URL)`.

- [ ] **Step 2:** Merge sur main + tsc/tests post-merge + push (deploy Vercel).

- [ ] **Step 3:** Env Vercel : `FAL_KEY` (depuis .env.local) + `FAL_WEBHOOK_TOKEN` (générer : `[Convert]::ToHex((1..32 | % { Get-Random -Max 256 }))` ou équivalent) en production+preview ; redeploy ; `npx prisma migrate deploy` (une seule migration en attente : `_add_generation_jobs`).

- [ ] **Step 4: E2e réel en prod** — réutiliser le projet DÉMO (`shopifyOrderId 999000999`, email yoann@mylab-shop.com, gamme validée). L'API de soumission exige une session client, non scriptable : le script Prisma jetable reproduit donc le déclencheur côté serveur — (1) compléter l'`Onboarding` du projet démo (Brand DNA réaliste + les 3 photos réalisations du spike comme photos produit, `submittedAt` posé, statut `onboarding_submitted`) ; (2) créer les 12 jobs via `buildPackPlan` et les soumettre via `submitImageJob` réels (≈ 1,80 $) ; (3) laisser les webhooks de prod tourner et vérifier en base la progression : `queued→done`, mirror Cloudinary, enchaînement des 2 vidéos (≈ 3 $), bascule `pack_review`, email admin reçu. Puis dérouler la fin à la main : publish via `/admin/pack`, sélection par Yoann sur `/projet` (il est le propriétaire du projet démo). Budget e2e ≈ 5 $. NE PAS nettoyer : le pack démo sert de vitrine.
- [ ] **Step 5: Vérification visuelle (Yoann)** : `/admin/pack` et la galerie `/projet` du projet démo.

---

## Hors scope Lot 4 (assumé)

- Textes IA (home, descriptions produits) → Lot 5 avec la livraison du site.
- Quotas/facturation à l'usage (Phase 2). Régénération en masse ; galerie publique ; filigrane sur le pack (le pack publié appartient au client).
- Vérification de signature ed25519 des webhooks fal (le handler re-fetche le résultat avec nos credentials — le corps n'est jamais cru ; token URL secret en plus).

## Critères de succès (spec §4.5)

- La soumission d'un onboarding déclenche seule les 12 générations ; les assets arrivent sur Cloudinary sans intervention ; les 2 reels s'enchaînent automatiquement ; le projet bascule en `pack_review` avec email admin.
- L'admin peut écarter/relancer n'importe quel asset et ne peut publier qu'avec ≥ 8 images réussies ; le client ne voit RIEN avant la publication.
- Le client sélectionne exactement min(8, disponibles) visuels ; la sélection est enregistrée (`selected`) et notifiée ; les vidéos sont incluses d'office.
- Chaque job porte son coût ; un pack complet ≈ 4,84 $.
- Un webhook rejoué (retry fal) ne crée ni doublon ni régression d'état.
