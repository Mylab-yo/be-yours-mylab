# MY.LAB Studio V3 — Lot 3 (onboarding Studio) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L'onboarding Studio en 3 écrans (Brand DNA, photos produits, société/prix/domaine/histoire + éléments existants), débloqué à la gamme validée, sauvegardé écran par écran, avec notification admin à la soumission — la matière première du Lot 4 (génération).

**Architecture:** Tout dans l'app `mylab-configurateur`. Un modèle `Onboarding` (1/projet, champs Json par écran + `completedSteps`), une route API unique upsert-par-écran gardée propriétaire, un wizard client 3 écrans sous `/projet/onboarding/[projectId]`, la timeline `/projet` étendue au 3e jalon. Validation métier pure (SIRET Luhn, complétude d'écran) testée en TDD.

**Tech Stack:** identique Lots 1-2 (Next 16 App Router · TS strict · Prisma 7 · NextAuth · Cloudinary via `/api/upload` · Resend · vitest 4).

**Spec de référence :** `docs/superpowers/specs/2026-07-08-mylab-studio-v3-design.md` §4.4 + §5. État : Lot 2 en prod (demande BAT, `label_validated`, gardes, notifications).

## Global Constraints

- **Repo** : `d:\Projets mylab vs code\mylab-configurateur`, branche `feat/studio-v3-lot3-onboarding` (Task 0, depuis `main`).
- Conventions Lots 1-2 inchangées : TS strict, `@/`, client Prisma `@/generated/prisma/client`, singleton `@/lib/prisma`, pas de server actions (server page → client `fetch` → API route + garde), params async, grammaire visuelle CLIENT (`neutral-*`, `rounded-xl`) pour tout ce lot (aucune surface admin).
- **Migrations** : recette éprouvée des Lots 1-2 — `npx prisma migrate diff --from-schema <HEAD> --to-schema prisma/schema.prisma --script` (⚠️ Prisma 7 : PAS `--from-schema-datamodel` ; ne PAS utiliser `git stash --keep-index`), SQL écrit à la main dans `prisma/migrations/<ts>_add_onboarding/migration.sql`, **RLS invariant** (`ENABLE ROW LEVEL SECURITY` + policy `"Service role only" … USING (auth.role() = 'service_role')`) sur toute nouvelle table, appliqué par `migrate deploy` en Task 8 seulement.
- **Écrans de la spec §4.4 (verbatim)** : ① Brand DNA — 6 questions visuelles (palette, ambiance, ton, style, univers, cible) ; ② Photos produits — 1 à 3 photos par référence du vrai flacon étiqueté ; ③ société (raison sociale, forme juridique, SIRET, adresse, contact) + **prix publics par référence** + wizard domaine 3 chemins (A domaine existant / B achat Shopify / C conseil de nom) + 2-3 questions histoire de marque (pourquoi, pour qui, promesse) + **« Vos éléments existants » optionnel** (photos, vidéos, textes, logo…, priorisés sur le généré au Lot 4).
- **Déviations spec assumées (documentées ici, à rappeler dans la revue finale)** : (a) la palette n'est PAS pré-remplie depuis l'étiquette validée — le configurateur en mode embed ne persiste rien en DB, il n'y a pas de données couleur exploitables ; saisie manuelle (3 couleurs). (b) La suggestion de prix « B2B × coefficient » est remplacée par un champ libre avec texte d'aide — les prix B2B par référence ne sont pas en base.
- Déblocage : l'onboarding n'est accessible que si `project.status ∈ { label_validated, onboarding_submitted }` (lecture seule visuelle après soumission non requise — le wizard reste éditable jusqu'à soumission, verrouillé après).
- Uploads : réutiliser `POST /api/upload` existant (anonyme + rate-limité, FormData `file` + `folder`) — folders `onboarding-photos` et `onboarding-elements`. Pas de nouveau endpoint d'upload.
- Tests : vitest colocalisés, imports explicites. `npm test -- <fichier>`. Avant chaque commit : `npx tsc --noEmit` + `npm test`.
- Git : commits `feat(studio): …` français. Merge sur `main` en Task 8 après revue finale uniquement.

---

### Task 0: Branche de travail

**Files:** aucun

**Interfaces:**
- Produces: branche `feat/studio-v3-lot3-onboarding`.

- [ ] **Step 1: Créer la branche**

```bash
cd "d:\Projets mylab vs code\mylab-configurateur"
git checkout main && git pull origin main
git checkout -b feat/studio-v3-lot3-onboarding
```

---

### Task 1: Modèle Prisma `Onboarding` + statut + migration

**Files:**
- Modify: `prisma/schema.prisma`
- Create: `prisma/migrations/<timestamp>_add_onboarding/migration.sql`

**Interfaces:**
- Consumes: `Project`, enum `ProjectStatus`.
- Produces: `ProjectStatus` gagne `onboarding_submitted // onboarding soumis — prêt pour la génération (Lot 4)` ; modèle `Onboarding` ci-dessous ; relation inverse `Project.onboarding Onboarding?` ; accès `prisma.onboarding`.

- [ ] **Step 1: Schema**

Ajouter `onboarding_submitted` à `enum ProjectStatus` (après `label_validated`). Puis à la suite des modèles BAT :

```prisma
model Onboarding {
  id             String    @id @default(cuid())
  projectId      String    @unique
  project        Project   @relation(fields: [projectId], references: [id])
  brandDna       Json? // { palette: string[3], ambiance, ton, style, univers, cible }
  photos         Json? // [{ referenceId, urls: string[] (1-3) }]
  infos          Json? // { societe, prix: [{referenceId, prixPublic}], domaine: {mode, valeur}, histoire, elements: [{url, name}] }
  completedSteps String[]  @default([]) // "brand_dna" | "photos" | "infos"
  submittedAt    DateTime?
  createdAt      DateTime  @default(now())
  updatedAt      DateTime  @updatedAt
}
```

Relation inverse dans `Project` : `onboarding Onboarding?`.

- [ ] **Step 2: Migration SQL (recette Lots 1-2, sans l'appliquer)**

```bash
git show HEAD:prisma/schema.prisma > prisma/_schema_before.prisma
npx prisma migrate diff --from-schema prisma/_schema_before.prisma --to-schema prisma/schema.prisma --script > migration_draft.sql
```

Écrire `prisma/migrations/<YYYYMMDDHHmmss>_add_onboarding/migration.sql` (timestamp UTC > migrations existantes) = draft + bloc RLS :

```sql
-- RLS (invariant repo)
ALTER TABLE "Onboarding" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON "Onboarding" FOR ALL USING (auth.role() = 'service_role');
```

Supprimer les fichiers temporaires. Conserver l'`ALTER TYPE "ProjectStatus" ADD VALUE` généré.

- [ ] **Step 3: Vérifier**

Run: `npx prisma generate && npx tsc --noEmit`
Expected: OK, 0 erreur.

- [ ] **Step 4: Commit**

```bash
git add prisma/schema.prisma prisma/migrations
git commit -m "feat(studio): modele Onboarding + statut onboarding_submitted + migration RLS"
```

---

### Task 2: Lib pure `onboarding.ts` — validation + complétude (TDD)

**Files:**
- Create: `src/lib/studio/onboarding.ts`
- Test: `src/lib/studio/onboarding.test.ts`
- Modify: `src/lib/studio/bat.ts` (extension `projectDoneCount`)
- Modify: `src/lib/studio/bat.test.ts` (test du 3e jalon)

**Interfaces:**
- Consumes: rien (pur).
- Produces (consommé par Tasks 4-6) :
  - `ONBOARDING_STEPS = ["brand_dna", "photos", "infos"] as const` ; `type OnboardingStep = (typeof ONBOARDING_STEPS)[number]`
  - `validateSiret(siret: string): boolean` — 14 chiffres + somme de Luhn valide (espaces tolérés).
  - `type BrandDna = { palette: string[]; ambiance: string; ton: string; style: string; univers: string; cible: string }`
  - `type PhotosEntry = { referenceId: string; urls: string[] }`
  - `type Infos = { societe: { raisonSociale: string; formeJuridique: string; siret: string; adresse: string; codePostal: string; ville: string; email: string; telephone: string }; prix: { referenceId: string; prixPublic: number }[]; domaine: { mode: "existant" | "achat" | "conseil"; valeur: string }; histoire: { pourquoi: string; pourQui: string; promesse: string }; elements: { url: string; name: string }[] }`
  - `isStepComplete(step: OnboardingStep, data: unknown, referenceIds: string[]): boolean` — brand_dna : palette 3 couleurs hex + 5 champs non vides ; photos : 1-3 urls pour CHAQUE referenceId ; infos : société complète avec SIRET valide + un prix > 0 par référence + domaine.valeur non vide + histoire complète (elements optionnels).
  - `canSubmit(completedSteps: string[]): boolean` — les 3 étapes présentes.
  - Dans `bat.ts` : `projectDoneCount` gagne le 3e jalon — `onboarding_submitted` → 3.

- [ ] **Step 1: Tests (échouent)**

```ts
// src/lib/studio/onboarding.test.ts
import { describe, it, expect } from "vitest";
import { validateSiret, isStepComplete, canSubmit } from "./onboarding";

const brandDna = { palette: ["#aabbcc", "#112233", "#ffffff"], ambiance: "naturelle", ton: "chaleureux", style: "botanique", univers: "soins capillaires clean", cible: "femmes 25-45" };
const REFS = ["r1", "r2"];
const infos = {
  societe: { raisonSociale: "Néroli SAS", formeJuridique: "SAS", siret: "73282932000074", adresse: "1 rue des Fleurs", codePostal: "75011", ville: "Paris", email: "c@neroli.fr", telephone: "0601020304" },
  prix: [{ referenceId: "r1", prixPublic: 24.9 }, { referenceId: "r2", prixPublic: 19.9 }],
  domaine: { mode: "achat", valeur: "neroli-co.fr" },
  histoire: { pourquoi: "p", pourQui: "q", promesse: "r" },
  elements: [],
};

describe("validateSiret", () => {
  it("accepte un SIRET Luhn valide, avec ou sans espaces", () => {
    expect(validateSiret("73282932000074")).toBe(true);
    expect(validateSiret("732 829 320 00074")).toBe(true);
  });
  it("rejette longueur ou clé Luhn invalides", () => {
    expect(validateSiret("73282932000075")).toBe(false);
    expect(validateSiret("123")).toBe(false);
    expect(validateSiret("abcdefghijklmn")).toBe(false);
  });
});

describe("isStepComplete", () => {
  it("brand_dna complet / incomplet", () => {
    expect(isStepComplete("brand_dna", brandDna, REFS)).toBe(true);
    expect(isStepComplete("brand_dna", { ...brandDna, palette: ["#aabbcc"] }, REFS)).toBe(false);
    expect(isStepComplete("brand_dna", { ...brandDna, cible: " " }, REFS)).toBe(false);
    expect(isStepComplete("brand_dna", null, REFS)).toBe(false);
  });
  it("photos : 1-3 urls pour chaque référence", () => {
    expect(isStepComplete("photos", [{ referenceId: "r1", urls: ["u"] }, { referenceId: "r2", urls: ["u", "v"] }], REFS)).toBe(true);
    expect(isStepComplete("photos", [{ referenceId: "r1", urls: ["u"] }], REFS)).toBe(false);
    expect(isStepComplete("photos", [{ referenceId: "r1", urls: [] }, { referenceId: "r2", urls: ["u"] }], REFS)).toBe(false);
    expect(isStepComplete("photos", [{ referenceId: "r1", urls: ["a", "b", "c", "d"] }, { referenceId: "r2", urls: ["u"] }], REFS)).toBe(false);
  });
  it("infos : société+SIRET+prix par référence+domaine+histoire", () => {
    expect(isStepComplete("infos", infos, REFS)).toBe(true);
    expect(isStepComplete("infos", { ...infos, societe: { ...infos.societe, siret: "73282932000075" } }, REFS)).toBe(false);
    expect(isStepComplete("infos", { ...infos, prix: [{ referenceId: "r1", prixPublic: 24.9 }] }, REFS)).toBe(false);
    expect(isStepComplete("infos", { ...infos, prix: [{ referenceId: "r1", prixPublic: 0 }, { referenceId: "r2", prixPublic: 19.9 }] }, REFS)).toBe(false);
    expect(isStepComplete("infos", { ...infos, domaine: { mode: "achat", valeur: "" } }, REFS)).toBe(false);
  });
});

describe("canSubmit", () => {
  it("exige les 3 étapes", () => {
    expect(canSubmit(["brand_dna", "photos", "infos"])).toBe(true);
    expect(canSubmit(["brand_dna", "infos"])).toBe(false);
    expect(canSubmit([])).toBe(false);
  });
});
```

Dans `src/lib/studio/bat.test.ts`, describe `projectDoneCount`, ajouter :

```ts
  it("3 jalons après soumission de l'onboarding", () => {
    expect(projectDoneCount("onboarding_submitted")).toBe(3);
  });
```

- [ ] **Step 2: RED**

Run: `npm test -- src/lib/studio/onboarding.test.ts src/lib/studio/bat.test.ts`
Expected: FAIL (module introuvable + jalon 3 manquant).

- [ ] **Step 3: Implémenter**

```ts
// src/lib/studio/onboarding.ts
export const ONBOARDING_STEPS = ["brand_dna", "photos", "infos"] as const;
export type OnboardingStep = (typeof ONBOARDING_STEPS)[number];

export type BrandDna = { palette: string[]; ambiance: string; ton: string; style: string; univers: string; cible: string };
export type PhotosEntry = { referenceId: string; urls: string[] };
export type Infos = {
  societe: { raisonSociale: string; formeJuridique: string; siret: string; adresse: string; codePostal: string; ville: string; email: string; telephone: string };
  prix: { referenceId: string; prixPublic: number }[];
  domaine: { mode: "existant" | "achat" | "conseil"; valeur: string };
  histoire: { pourquoi: string; pourQui: string; promesse: string };
  elements: { url: string; name: string }[];
};

export function validateSiret(siret: string): boolean {
  const digits = siret.replace(/\s/g, "");
  if (!/^\d{14}$/.test(digits)) return false;
  let sum = 0;
  for (let i = 0; i < 14; i++) {
    let n = Number(digits[i]);
    if (i % 2 === 0) { n *= 2; if (n > 9) n -= 9; } // positions impaires depuis la droite sur 14 chiffres
    sum += n;
  }
  return sum % 10 === 0;
}

const filled = (s: unknown): boolean => typeof s === "string" && s.trim().length > 0;
const isHex = (s: unknown): boolean => typeof s === "string" && /^#[0-9a-fA-F]{6}$/.test(s);

export function isStepComplete(step: OnboardingStep, data: unknown, referenceIds: string[]): boolean {
  if (!data) return false;
  if (step === "brand_dna") {
    const d = data as Partial<BrandDna>;
    return Array.isArray(d.palette) && d.palette.length === 3 && d.palette.every(isHex) &&
      filled(d.ambiance) && filled(d.ton) && filled(d.style) && filled(d.univers) && filled(d.cible);
  }
  if (step === "photos") {
    const entries = Array.isArray(data) ? (data as PhotosEntry[]) : [];
    return referenceIds.every((id) => {
      const e = entries.find((x) => x.referenceId === id);
      return !!e && Array.isArray(e.urls) && e.urls.length >= 1 && e.urls.length <= 3;
    });
  }
  const d = data as Partial<Infos>;
  const s = d.societe;
  const societeOk = !!s && filled(s.raisonSociale) && filled(s.formeJuridique) && validateSiret(s.siret ?? "") &&
    filled(s.adresse) && filled(s.codePostal) && filled(s.ville) && filled(s.email) && filled(s.telephone);
  const prixOk = Array.isArray(d.prix) && referenceIds.every((id) => {
    const p = d.prix!.find((x) => x.referenceId === id);
    return !!p && typeof p.prixPublic === "number" && p.prixPublic > 0;
  });
  const domaineOk = !!d.domaine && filled(d.domaine.valeur);
  const h = d.histoire;
  const histoireOk = !!h && filled(h.pourquoi) && filled(h.pourQui) && filled(h.promesse);
  return societeOk && prixOk && domaineOk && histoireOk;
}

export function canSubmit(completedSteps: string[]): boolean {
  return ONBOARDING_STEPS.every((s) => completedSteps.includes(s));
}
```

Dans `src/lib/studio/bat.ts`, remplacer `projectDoneCount` :

```ts
export function projectDoneCount(projectStatus: string, requestStatus?: ReqStatus): number {
  if (projectStatus === "draft") return 0;
  if (projectStatus === "onboarding_submitted") return 3;
  if (projectStatus === "label_validated" || requestStatus === "validated") return 2;
  return 1;
}
```

- [ ] **Step 4: GREEN**

Run: `npm test -- src/lib/studio/onboarding.test.ts src/lib/studio/bat.test.ts`
Expected: PASS (11 nouveaux + existants).

- [ ] **Step 5: Commit**

```bash
git add src/lib/studio/onboarding.ts src/lib/studio/onboarding.test.ts src/lib/studio/bat.ts src/lib/studio/bat.test.ts
git commit -m "feat(studio): lib onboarding — SIRET Luhn, completude par ecran, 3e jalon timeline (TDD)"
```

---

### Task 3: Notification « onboarding soumis » (TDD)

**Files:**
- Modify: `src/lib/studio/notifications.ts`
- Modify: `src/lib/studio/notifications.test.ts`

**Interfaces:**
- Consumes: helpers existants (`wrap`, `escapeHtml`, `ADMIN_EMAIL` exporté).
- Produces (consommé par Task 4) : `buildOnboardingSubmittedEmail(p: { orderNumber: string; brandName: string | null }): StudioEmail` — subject `Onboarding soumis — commande n°<orderNumber>`, html contenant le nom de marque échappé (ou « (marque non renseignée) ») et un lien vers `https://mylab-configurateur.vercel.app/admin` (dashboard admin), text non vide.

- [ ] **Step 1: Tests (échouent)** — ajouter à `notifications.test.ts` :

```ts
describe("buildOnboardingSubmittedEmail", () => {
  it("subject, marque échappée, lien admin", () => {
    const m = buildOnboardingSubmittedEmail({ orderNumber: "1042", brandName: "Néroli <Co>" });
    expect(m.subject).toBe("Onboarding soumis — commande n°1042");
    expect(m.html).toContain("Néroli &lt;Co&gt;");
    expect(m.html).toContain("https://mylab-configurateur.vercel.app/admin");
    expect(m.text.length).toBeGreaterThan(20);
  });
  it("marque absente → mention neutre", () => {
    const m = buildOnboardingSubmittedEmail({ orderNumber: "1042", brandName: null });
    expect(m.html).toContain("(marque non renseignée)");
  });
});
```

(+ import de `buildOnboardingSubmittedEmail` en tête.)

- [ ] **Step 2: RED** — Run: `npm test -- src/lib/studio/notifications.test.ts` → FAIL (export manquant).

- [ ] **Step 3: Implémenter** — ajouter à `notifications.ts` :

```ts
export function buildOnboardingSubmittedEmail(p: { orderNumber: string; brandName: string | null }): StudioEmail {
  const marque = p.brandName ? escapeHtml(p.brandName) : "(marque non renseignée)";
  return {
    subject: `Onboarding soumis — commande n°${p.orderNumber}`,
    html: wrap(
      "Onboarding Studio soumis ✓",
      `<p>Le client <strong>${marque}</strong> a complété son onboarding : Brand DNA, photos produits, société, prix et domaine sont prêts pour la génération (Lot 4).</p>` +
        `<p><a href="https://mylab-configurateur.vercel.app/admin">Ouvrir le back-office</a></p>`
    ),
    text: `Onboarding soumis (commande n°${p.orderNumber}) — ${p.brandName ?? "(marque non renseignée)"}. Données prêtes pour la génération.`,
  };
}
```

- [ ] **Step 4: GREEN** — Run: `npm test -- src/lib/studio/notifications.test.ts` → PASS (10 tests).

- [ ] **Step 5: Commit**

```bash
git add src/lib/studio/notifications.ts src/lib/studio/notifications.test.ts
git commit -m "feat(studio): email onboarding soumis (TDD)"
```

---

### Task 4: API — GET/PUT onboarding par écran

**Files:**
- Create: `src/app/api/studio/onboarding/[projectId]/route.ts`

**Interfaces:**
- Consumes: Task 1 (`prisma.onboarding`), Task 2 (`isStepComplete`, `canSubmit`, `ONBOARDING_STEPS`), Task 3 (email), garde propriétaire (logique inline — `requireRequestOwner` est indexé sur requestId, pas projectId).
- Produces (consommé par Tasks 5-6) :
  - `GET /api/studio/onboarding/[projectId]` → 200 `{ onboarding: { brandDna, photos, infos, completedSteps, submittedAt } | null, references: { id, label }[] }` (références de la demande BAT, pour les écrans 2-3). Garde : propriétaire du projet ; 403 si `project.status` ∉ {label_validated, onboarding_submitted}.
  - `PUT /api/studio/onboarding/[projectId]` body `{ step: "brand_dna"|"photos"|"infos", data: unknown, submit?: boolean }` → 200 `{ completedSteps, submitted: boolean }`. Upsert le champ de l'écran ; recalcule `completedSteps` ; si `submit` : 409 si `!canSubmit`, sinon `submittedAt` + `project.status = "onboarding_submitted"` + email admin via `after()`. 409 si déjà soumis (`submittedAt` non nul) pour tout PUT.

- [ ] **Step 1: Implémenter la route**

```ts
// src/app/api/studio/onboarding/[projectId]/route.ts
import { NextResponse } from "next/server";
import { after } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { isStepComplete, canSubmit, ONBOARDING_STEPS, type OnboardingStep } from "@/lib/studio/onboarding";
import { buildOnboardingSubmittedEmail, sendStudioEmail, ADMIN_EMAIL } from "@/lib/studio/notifications";

async function loadOwnedProject(projectId: string) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.email) return NextResponse.json({ error: "Non authentifié" }, { status: 401 });
  const project = await prisma.project.findUnique({
    where: { id: projectId },
    include: { onboarding: true, labelRequest: { include: { references: { orderBy: { title: "asc" } } } } },
  });
  if (!project) return NextResponse.json({ error: "Projet introuvable" }, { status: 404 });
  const email = session.user.email.toLowerCase();
  if (project.userId !== session.user.id && project.email !== email)
    return NextResponse.json({ error: "Accès interdit" }, { status: 403 });
  if (project.status !== "label_validated" && project.status !== "onboarding_submitted")
    return NextResponse.json({ error: "L'onboarding s'ouvre après la validation de votre gamme d'étiquettes" }, { status: 403 });
  return project;
}

export async function GET(_req: Request, { params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const project = await loadOwnedProject(projectId);
  if (project instanceof NextResponse) return project;
  const o = project.onboarding;
  return NextResponse.json({
    onboarding: o
      ? { brandDna: o.brandDna, photos: o.photos, infos: o.infos, completedSteps: o.completedSteps, submittedAt: o.submittedAt }
      : null,
    references: (project.labelRequest?.references ?? []).map((r) => ({
      id: r.id,
      label: `${r.title}${r.variantTitle ? ` ${r.variantTitle}` : ""}`,
    })),
  });
}

export async function PUT(req: Request, { params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const project = await loadOwnedProject(projectId);
  if (project instanceof NextResponse) return project;
  if (project.onboarding?.submittedAt)
    return NextResponse.json({ error: "Onboarding déjà soumis" }, { status: 409 });

  const { step, data, submit } = (await req.json()) as { step?: OnboardingStep; data?: unknown; submit?: boolean };
  if (!step || !ONBOARDING_STEPS.includes(step))
    return NextResponse.json({ error: "step invalide" }, { status: 400 });

  const referenceIds = (project.labelRequest?.references ?? []).map((r) => r.id);
  const field = step === "brand_dna" ? "brandDna" : step;

  const result = await prisma.$transaction(async (tx) => {
    const current = await tx.onboarding.upsert({
      where: { projectId },
      update: { [field]: data ?? undefined },
      create: { projectId, [field]: data ?? undefined },
    });
    const stepData = { brand_dna: current.brandDna, photos: current.photos, infos: current.infos } as const;
    const completedSteps = ONBOARDING_STEPS.filter((s) => isStepComplete(s, stepData[s], referenceIds));
    let submitted = false;
    if (submit) {
      if (!canSubmit(completedSteps)) throw Object.assign(new Error("incomplet"), { code: "INCOMPLETE" });
      await tx.onboarding.update({ where: { projectId }, data: { completedSteps, submittedAt: new Date() } });
      await tx.project.update({ where: { id: projectId }, data: { status: "onboarding_submitted" } });
      submitted = true;
    } else {
      await tx.onboarding.update({ where: { projectId }, data: { completedSteps } });
    }
    return { completedSteps, submitted };
  }).catch((e) => (e?.code === "INCOMPLETE" ? "INCOMPLETE" : Promise.reject(e)));

  if (result === "INCOMPLETE")
    return NextResponse.json({ error: "Complétez les trois écrans avant de soumettre" }, { status: 409 });

  if (result.submitted) {
    after(async () => {
      await sendStudioEmail(
        ADMIN_EMAIL,
        buildOnboardingSubmittedEmail({ orderNumber: project.shopifyOrderNumber ?? "—", brandName: project.brandName })
      );
    });
  }

  return NextResponse.json(result);
}
```

- [ ] **Step 2: Vérifier**

Run: `npx tsc --noEmit && npm test`
Expected: 0 erreur, suite verte.

- [ ] **Step 3: Commit**

```bash
git add src/app/api/studio/onboarding
git commit -m "feat(studio): API onboarding — GET etat + PUT par ecran avec soumission transactionnelle"
```

---

### Task 5: Wizard — page serveur + shell + écran 1 (Brand DNA)

**Files:**
- Create: `src/app/projet/onboarding/[projectId]/page.tsx`
- Create: `src/components/projet/OnboardingWizard.tsx`
- Create: `src/components/projet/OnboardingStepBrandDna.tsx`

**Interfaces:**
- Consumes: Task 4 (GET/PUT), session/redirect pattern de `/projet`.
- Produces (consommé par Task 6) :
  - Page serveur : auth + fetch initial via Prisma (mêmes gardes que l'API), rend `<OnboardingWizard projectId initialOnboarding references submitted />`.
  - `OnboardingWizard` : état `stepIndex` (0-2), barre d'étapes (3 puces), délégation à un composant par écran via props communes `type StepProps = { value: unknown; references: { id: string; label: string }[]; saving: boolean; onSave: (data: unknown, opts?: { submit?: boolean }) => Promise<void>; error: string | null }` ; `onSave` fait `PUT { step, data, submit }` puis avance d'écran (`router.refresh()` sur submit final). Si `submitted` : bannière verte statique, wizard masqué.
  - `OnboardingStepBrandDna` : 3 `<input type="color">` + selects `ambiance` (naturelle/luxe/clinique/bohème/urbaine), `ton` (chaleureux/expert/complice/premium), `style` (minimaliste/botanique/audacieux/classique) + inputs texte `univers`, `cible`. Bouton « Enregistrer et continuer ».

- [ ] **Step 1: Page serveur**

```tsx
// src/app/projet/onboarding/[projectId]/page.tsx
import { getServerSession } from "next-auth";
import { redirect, notFound } from "next/navigation";
import Link from "next/link";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { OnboardingWizard } from "@/components/projet/OnboardingWizard";

export const dynamic = "force-dynamic";
export const metadata = { title: "Onboarding — MyLab Studio" };

export default async function OnboardingPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const session = await getServerSession(authOptions);
  if (!session?.user?.email) redirect(`/login?callbackUrl=/projet/onboarding/${projectId}`);

  const project = await prisma.project.findUnique({
    where: { id: projectId },
    include: { onboarding: true, labelRequest: { include: { references: { orderBy: { title: "asc" } } } } },
  });
  if (!project) notFound();
  const email = session.user.email.toLowerCase();
  if (project.userId !== session.user.id && project.email !== email) notFound();
  if (project.status !== "label_validated" && project.status !== "onboarding_submitted") redirect("/projet");

  return (
    <main className="mx-auto max-w-2xl px-4 py-12">
      <Link href="/projet" className="text-sm text-neutral-500 hover:text-neutral-800">← Mon projet</Link>
      <h1 className="mt-2 text-2xl font-semibold">Préparons votre site</h1>
      <p className="mt-1 text-neutral-600 text-sm">
        Commande n°{project.shopifyOrderNumber} — trois étapes rapides, vos réponses guident la création de vos visuels et de votre boutique.
      </p>
      <OnboardingWizard
        projectId={project.id}
        initialOnboarding={{
          brandDna: project.onboarding?.brandDna ?? null,
          photos: project.onboarding?.photos ?? null,
          infos: project.onboarding?.infos ?? null,
          completedSteps: project.onboarding?.completedSteps ?? [],
        }}
        references={(project.labelRequest?.references ?? []).map((r) => ({
          id: r.id,
          label: `${r.title}${r.variantTitle ? ` ${r.variantTitle}` : ""}`,
        }))}
        submitted={Boolean(project.onboarding?.submittedAt)}
      />
    </main>
  );
}
```

- [ ] **Step 2: Shell wizard (client)**

```tsx
// src/components/projet/OnboardingWizard.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { OnboardingStepBrandDna } from "@/components/projet/OnboardingStepBrandDna";
import { OnboardingStepPhotos } from "@/components/projet/OnboardingStepPhotos";
import { OnboardingStepInfos } from "@/components/projet/OnboardingStepInfos";

export type StepProps = {
  value: unknown;
  references: { id: string; label: string }[];
  saving: boolean;
  onSave: (data: unknown, opts?: { submit?: boolean }) => Promise<void>;
  error: string | null;
};

const STEP_DEFS = [
  { key: "brand_dna", label: "Votre marque" },
  { key: "photos", label: "Vos produits" },
  { key: "infos", label: "Votre boutique" },
] as const;

export function OnboardingWizard({ projectId, initialOnboarding, references, submitted }: {
  projectId: string;
  initialOnboarding: { brandDna: unknown; photos: unknown; infos: unknown; completedSteps: string[] };
  references: { id: string; label: string }[];
  submitted: boolean;
}) {
  const router = useRouter();
  const firstIncomplete = STEP_DEFS.findIndex((s) => !initialOnboarding.completedSteps.includes(s.key));
  const [stepIndex, setStepIndex] = useState(firstIncomplete === -1 ? 2 : firstIncomplete);
  const [values, setValues] = useState<Record<string, unknown>>({
    brand_dna: initialOnboarding.brandDna,
    photos: initialOnboarding.photos,
    infos: initialOnboarding.infos,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (submitted) {
    return (
      <div className="mt-8 rounded-xl bg-emerald-50 border border-emerald-200 px-5 py-4 text-emerald-800">
        🎉 Votre onboarding est soumis — nous préparons votre pack de lancement et votre site. Vous serez notifié par email.
      </div>
    );
  }

  const step = STEP_DEFS[stepIndex];

  async function save(data: unknown, opts?: { submit?: boolean }) {
    setSaving(true); setError(null);
    try {
      const res = await fetch(`/api/studio/onboarding/${projectId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ step: step.key, data, submit: opts?.submit ?? false }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || "Une erreur est survenue");
      setValues((v) => ({ ...v, [step.key]: data }));
      if (opts?.submit) { router.refresh(); return; }
      if (stepIndex < 2) setStepIndex(stepIndex + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    } finally {
      setSaving(false);
    }
  }

  const stepProps = { value: values[step.key], references, saving, onSave: save, error };

  return (
    <div className="mt-8">
      <ol className="flex items-center gap-2 text-sm" aria-label="Étapes de l'onboarding">
        {STEP_DEFS.map((s, i) => (
          <li key={s.key} className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setStepIndex(i)}
              className={`flex h-7 w-7 items-center justify-center rounded-full border text-xs font-medium transition-colors ${
                i === stepIndex ? "bg-neutral-900 text-white border-neutral-900" : "border-neutral-300 text-neutral-500 hover:border-neutral-500"
              }`}
              aria-current={i === stepIndex ? "step" : undefined}
            >
              {i + 1}
            </button>
            <span className={i === stepIndex ? "font-medium" : "text-neutral-400"}>{s.label}</span>
            {i < 2 && <span className="text-neutral-300">—</span>}
          </li>
        ))}
      </ol>

      <div className="mt-6 rounded-xl border border-neutral-200 p-6">
        {step.key === "brand_dna" && <OnboardingStepBrandDna {...stepProps} />}
        {step.key === "photos" && <OnboardingStepPhotos {...stepProps} />}
        {step.key === "infos" && <OnboardingStepInfos {...stepProps} />}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Écran 1 — Brand DNA (client)**

```tsx
// src/components/projet/OnboardingStepBrandDna.tsx
"use client";

import { useState } from "react";
import type { StepProps } from "@/components/projet/OnboardingWizard";

const AMBIANCES = ["naturelle", "luxe", "clinique", "bohème", "urbaine"];
const TONS = ["chaleureux", "expert", "complice", "premium"];
const STYLES = ["minimaliste", "botanique", "audacieux", "classique"];

type Dna = { palette: string[]; ambiance: string; ton: string; style: string; univers: string; cible: string };
const EMPTY: Dna = { palette: ["#1a1a1a", "#f5f0eb", "#c5a467"], ambiance: "", ton: "", style: "", univers: "", cible: "" };

export function OnboardingStepBrandDna({ value, saving, onSave, error }: StepProps) {
  const [dna, setDna] = useState<Dna>({ ...EMPTY, ...((value as Partial<Dna>) ?? {}) });
  const set = (k: keyof Dna, v: Dna[keyof Dna]) => setDna((d) => ({ ...d, [k]: v }));

  const Select = ({ k, label, options }: { k: "ambiance" | "ton" | "style"; label: string; options: string[] }) => (
    <div>
      <label className="block text-sm font-medium mb-1">{label} <span className="text-red-500">*</span></label>
      <select className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm" value={dna[k]} onChange={(e) => set(k, e.target.value)}>
        <option value="">Choisir…</option>
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  );

  return (
    <form onSubmit={(e) => { e.preventDefault(); void onSave(dna); }} className="space-y-5">
      <h2 className="font-medium">L’ADN de votre marque</h2>
      {error && <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>}

      <div>
        <label className="block text-sm font-medium mb-1">Votre palette (3 couleurs) <span className="text-red-500">*</span></label>
        <div className="flex gap-3">
          {dna.palette.map((c, i) => (
            <input key={i} type="color" value={c} aria-label={`Couleur ${i + 1}`}
              onChange={(e) => set("palette", dna.palette.map((x, j) => (j === i ? e.target.value : x)))}
              className="h-10 w-14 cursor-pointer rounded border border-neutral-300" />
          ))}
        </div>
        <p className="mt-1 text-xs text-neutral-500">Reprenez les couleurs de votre étiquette validée pour un site cohérent.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Select k="ambiance" label="Ambiance" options={AMBIANCES} />
        <Select k="ton" label="Ton" options={TONS} />
        <Select k="style" label="Style visuel" options={STYLES} />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Votre univers en une phrase <span className="text-red-500">*</span></label>
        <input className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm" value={dna.univers}
          onChange={(e) => set("univers", e.target.value)} placeholder="Ex. : soins capillaires clean aux actifs botaniques" />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Votre clientèle cible <span className="text-red-500">*</span></label>
        <input className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm" value={dna.cible}
          onChange={(e) => set("cible", e.target.value)} placeholder="Ex. : femmes 25-45 ans, cheveux texturés" />
      </div>

      <button type="submit" disabled={saving}
        className="rounded-full bg-neutral-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-neutral-700 transition-colors disabled:opacity-40">
        {saving ? "Enregistrement…" : "Enregistrer et continuer"}
      </button>
    </form>
  );
}
```

- [ ] **Step 4: Vérifier (compilation partielle)**

Les imports `OnboardingStepPhotos`/`OnboardingStepInfos` n'existent pas encore : créer des stubs minimaux TEMPORAIRES pour compiler (chacun : `"use client"; import type { StepProps } from "@/components/projet/OnboardingWizard"; export function OnboardingStepPhotos(_: StepProps) { return null; }` — idem Infos), qui seront remplacés en Task 6.

Run: `npx tsc --noEmit && npm run lint && npm test`
Expected: 0 erreur.

- [ ] **Step 5: Commit**

```bash
git add src/app/projet/onboarding src/components/projet/OnboardingWizard.tsx src/components/projet/OnboardingStepBrandDna.tsx src/components/projet/OnboardingStepPhotos.tsx src/components/projet/OnboardingStepInfos.tsx
git commit -m "feat(studio): wizard onboarding — page, shell 3 etapes, ecran Brand DNA (stubs ecrans 2-3)"
```

---

### Task 6: Wizard — écran 2 (photos) + écran 3 (société/prix/domaine/histoire/éléments)

**Files:**
- Modify (remplace les stubs): `src/components/projet/OnboardingStepPhotos.tsx`, `src/components/projet/OnboardingStepInfos.tsx`

**Interfaces:**
- Consumes: `StepProps` (Task 5), `POST /api/upload` existant (FormData `file` + `folder`, réponse `{ url }`), types de la lib Task 2.
- Produces: les deux écrans complets. Photos : par référence, 1-3 uploads (`folder: "onboarding-photos"`), vignettes + suppression. Infos : société (avec les champs exacts de la lib), prix par référence (€ TTC, `type="number" step="0.1" min="0"`), domaine (3 radios : `existant`/`achat`/`conseil` + input valeur), histoire (3 textareas), éléments existants (uploads multiples optionnels, `folder: "onboarding-elements"`, accept large). Bouton final « Soumettre mon onboarding » → `onSave(data, { submit: true })` ; bouton secondaire « Enregistrer » sans submit.

- [ ] **Step 1: Écran 2 — photos par référence**

```tsx
// src/components/projet/OnboardingStepPhotos.tsx
"use client";

import { useState } from "react";
import type { StepProps } from "@/components/projet/OnboardingWizard";

type Entry = { referenceId: string; urls: string[] };

async function uploadFile(file: File, folder: string): Promise<string> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("folder", folder);
  const res = await fetch("/api/upload", { method: "POST", body: fd });
  const json = await res.json();
  if (!res.ok) throw new Error(json.error || "Échec de l'upload");
  return json.url as string;
}

export function OnboardingStepPhotos({ value, references, saving, onSave, error }: StepProps) {
  const initial = (Array.isArray(value) ? (value as Entry[]) : []) ?? [];
  const [entries, setEntries] = useState<Entry[]>(
    references.map((r) => initial.find((e) => e.referenceId === r.id) ?? { referenceId: r.id, urls: [] })
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  async function addPhoto(refId: string, file: File) {
    setBusy(refId); setUploadError(null);
    try {
      const url = await uploadFile(file, "onboarding-photos");
      setEntries((es) => es.map((e) => (e.referenceId === refId && e.urls.length < 3 ? { ...e, urls: [...e.urls, url] } : e)));
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Erreur d'upload");
    } finally {
      setBusy(null);
    }
  }

  const removePhoto = (refId: string, url: string) =>
    setEntries((es) => es.map((e) => (e.referenceId === refId ? { ...e, urls: e.urls.filter((u) => u !== url) } : e)));

  const allOk = entries.every((e) => e.urls.length >= 1 && e.urls.length <= 3);

  return (
    <form onSubmit={(e) => { e.preventDefault(); void onSave(entries); }} className="space-y-5">
      <h2 className="font-medium">Vos produits en photo</h2>
      <p className="text-sm text-neutral-600">
        1 à 3 photos par produit, du <strong>vrai flacon étiqueté</strong>, bien éclairé sur fond simple — elles servent de référence pour générer vos visuels.
      </p>
      {(error || uploadError) && <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error || uploadError}</div>}

      {references.map((r) => {
        const entry = entries.find((e) => e.referenceId === r.id)!;
        return (
          <div key={r.id} className="rounded-lg border border-neutral-200 p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">{r.label}</span>
              <span className="text-xs text-neutral-500">{entry.urls.length}/3</span>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              {entry.urls.map((u) => (
                <div key={u} className="relative">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={u} alt={`Photo ${r.label}`} className="h-20 w-20 rounded-lg border border-neutral-200 object-cover" />
                  <button type="button" onClick={() => removePhoto(r.id, u)} aria-label="Supprimer la photo"
                    className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-neutral-900 text-white text-xs">×</button>
                </div>
              ))}
              {entry.urls.length < 3 && (
                <label className="flex h-20 w-20 cursor-pointer items-center justify-center rounded-lg border border-dashed border-neutral-300 text-2xl text-neutral-400 hover:border-neutral-500">
                  {busy === r.id ? "…" : "+"}
                  <input type="file" accept="image/png,image/jpeg,image/webp" className="hidden" disabled={busy !== null}
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) void addPhoto(r.id, f); e.target.value = ""; }} />
                </label>
              )}
            </div>
          </div>
        );
      })}

      <button type="submit" disabled={saving || !allOk}
        className="rounded-full bg-neutral-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-neutral-700 transition-colors disabled:opacity-40">
        {saving ? "Enregistrement…" : "Enregistrer et continuer"}
      </button>
      {!allOk && <p className="text-xs text-neutral-500">Ajoutez au moins une photo par produit pour continuer.</p>}
    </form>
  );
}
```

- [ ] **Step 2: Écran 3 — société, prix, domaine, histoire, éléments**

```tsx
// src/components/projet/OnboardingStepInfos.tsx
"use client";

import { useState } from "react";
import type { StepProps } from "@/components/projet/OnboardingWizard";
import type { Infos } from "@/lib/studio/onboarding";

const FORMES = ["SAS", "SASU", "SARL", "EURL", "EI", "Micro-entreprise", "Autre"];

const EMPTY: Infos = {
  societe: { raisonSociale: "", formeJuridique: "", siret: "", adresse: "", codePostal: "", ville: "", email: "", telephone: "" },
  prix: [],
  domaine: { mode: "existant", valeur: "" },
  histoire: { pourquoi: "", pourQui: "", promesse: "" },
  elements: [],
};

async function uploadFile(file: File): Promise<{ url: string; name: string }> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("folder", "onboarding-elements");
  const res = await fetch("/api/upload", { method: "POST", body: fd });
  const json = await res.json();
  if (!res.ok) throw new Error(json.error || "Échec de l'upload");
  return { url: json.url as string, name: file.name };
}

export function OnboardingStepInfos({ value, references, saving, onSave, error }: StepProps) {
  const v = (value as Partial<Infos>) ?? {};
  const [infos, setInfos] = useState<Infos>({
    ...EMPTY,
    ...v,
    societe: { ...EMPTY.societe, ...(v.societe ?? {}) },
    domaine: { ...EMPTY.domaine, ...(v.domaine ?? {}) },
    histoire: { ...EMPTY.histoire, ...(v.histoire ?? {}) },
    prix: references.map((r) => v.prix?.find((p) => p.referenceId === r.id) ?? { referenceId: r.id, prixPublic: 0 }),
    elements: v.elements ?? [],
  });
  const [busy, setBusy] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const setSoc = (k: keyof Infos["societe"], val: string) => setInfos((i) => ({ ...i, societe: { ...i.societe, [k]: val } }));
  const setHis = (k: keyof Infos["histoire"], val: string) => setInfos((i) => ({ ...i, histoire: { ...i.histoire, [k]: val } }));
  const setPrix = (refId: string, val: number) =>
    setInfos((i) => ({ ...i, prix: i.prix.map((p) => (p.referenceId === refId ? { ...p, prixPublic: val } : p)) }));

  async function addElement(file: File) {
    setBusy(true); setUploadError(null);
    try {
      const el = await uploadFile(file);
      setInfos((i) => ({ ...i, elements: [...i.elements, el] }));
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Erreur d'upload");
    } finally {
      setBusy(false);
    }
  }

  const Field = ({ k, label, placeholder }: { k: keyof Infos["societe"]; label: string; placeholder?: string }) => (
    <div>
      <label className="block text-sm font-medium mb-1">{label} <span className="text-red-500">*</span></label>
      <input className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm" value={infos.societe[k]}
        onChange={(e) => setSoc(k, e.target.value)} placeholder={placeholder} />
    </div>
  );

  return (
    <form onSubmit={(e) => { e.preventDefault(); void onSave(infos, { submit: true }); }} className="space-y-6">
      <h2 className="font-medium">Votre boutique</h2>
      {(error || uploadError) && <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error || uploadError}</div>}

      <fieldset className="space-y-4">
        <legend className="text-sm font-semibold">Votre société <span className="font-normal text-neutral-500">(mentions légales, CGV)</span></legend>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field k="raisonSociale" label="Raison sociale" />
          <div>
            <label className="block text-sm font-medium mb-1">Forme juridique <span className="text-red-500">*</span></label>
            <select className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm" value={infos.societe.formeJuridique}
              onChange={(e) => setSoc("formeJuridique", e.target.value)}>
              <option value="">Choisir…</option>
              {FORMES.map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          </div>
          <Field k="siret" label="SIRET" placeholder="14 chiffres" />
          <Field k="email" label="Email de contact" />
          <Field k="adresse" label="Adresse" />
          <Field k="telephone" label="Téléphone" />
          <Field k="codePostal" label="Code postal" />
          <Field k="ville" label="Ville" />
        </div>
      </fieldset>

      <fieldset className="space-y-3">
        <legend className="text-sm font-semibold">Vos prix de vente <span className="font-normal text-neutral-500">(€ TTC affichés sur votre site)</span></legend>
        {references.map((r) => {
          const p = infos.prix.find((x) => x.referenceId === r.id)!;
          return (
            <div key={r.id} className="flex items-center justify-between gap-4">
              <span className="text-sm">{r.label}</span>
              <div className="flex items-center gap-1">
                <input type="number" step="0.1" min="0" className="w-24 rounded-lg border border-neutral-300 px-3 py-2 text-sm text-right"
                  value={p.prixPublic || ""} onChange={(e) => setPrix(r.id, Number(e.target.value))} aria-label={`Prix ${r.label}`} />
                <span className="text-sm text-neutral-500">€</span>
              </div>
            </div>
          );
        })}
        <p className="text-xs text-neutral-500">Repère : la plupart des marques visent 2,5× à 4× leur coût d’achat par unité.</p>
      </fieldset>

      <fieldset className="space-y-3">
        <legend className="text-sm font-semibold">Votre domaine</legend>
        {([["existant", "J’ai déjà un domaine"], ["achat", "Je veux acheter ce domaine"], ["conseil", "J’hésite — voici mes idées"]] as const).map(([mode, label]) => (
          <label key={mode} className="flex items-center gap-2 text-sm">
            <input type="radio" name="domaine" checked={infos.domaine.mode === mode}
              onChange={() => setInfos((i) => ({ ...i, domaine: { ...i.domaine, mode } }))} />
            {label}
          </label>
        ))}
        <input className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm" value={infos.domaine.valeur}
          onChange={(e) => setInfos((i) => ({ ...i, domaine: { ...i.domaine, valeur: e.target.value } }))}
          placeholder={infos.domaine.mode === "conseil" ? "Vos idées de noms…" : "mondomaine.fr"} />
      </fieldset>

      <fieldset className="space-y-3">
        <legend className="text-sm font-semibold">Votre histoire <span className="font-normal text-neutral-500">(matière de votre page d’accueil)</span></legend>
        {([["pourquoi", "Pourquoi cette marque ?"], ["pourQui", "Pour qui ?"], ["promesse", "Votre promesse en une phrase"]] as const).map(([k, label]) => (
          <div key={k}>
            <label className="block text-sm font-medium mb-1">{label} <span className="text-red-500">*</span></label>
            <textarea className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm min-h-[60px]" value={infos.histoire[k]}
              onChange={(e) => setHis(k, e.target.value)} />
          </div>
        ))}
      </fieldset>

      <fieldset className="space-y-3">
        <legend className="text-sm font-semibold">Vos éléments existants <span className="font-normal text-neutral-500">(optionnel — photos, logo, textes, vidéos…)</span></legend>
        <p className="text-xs text-neutral-500">Tout ce que vous avez déjà : nous le privilégions sur le contenu généré.</p>
        <ul className="space-y-1 text-sm">
          {infos.elements.map((el) => (
            <li key={el.url} className="flex items-center justify-between">
              <span className="truncate">{el.name}</span>
              <button type="button" className="text-xs text-neutral-500 hover:text-red-600"
                onClick={() => setInfos((i) => ({ ...i, elements: i.elements.filter((x) => x.url !== el.url) }))}>Retirer</button>
            </li>
          ))}
        </ul>
        <label className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-neutral-300 px-4 py-2 text-sm hover:border-neutral-500">
          {busy ? "Envoi…" : "+ Ajouter un fichier"}
          <input type="file" accept="image/*,application/pdf" className="hidden" disabled={busy}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) void addElement(f); e.target.value = ""; }} />
        </label>
      </fieldset>

      <div className="flex items-center gap-3">
        <button type="submit" disabled={saving}
          className="rounded-full bg-neutral-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-neutral-700 transition-colors disabled:opacity-40">
          {saving ? "Envoi…" : "Soumettre mon onboarding"}
        </button>
        <button type="button" disabled={saving} onClick={() => void onSave(infos)}
          className="rounded-full border border-neutral-800 px-4 py-2 text-sm font-medium hover:bg-neutral-800 hover:text-white transition-colors disabled:opacity-40">
          Enregistrer sans soumettre
        </button>
      </div>
    </form>
  );
}
```

- [ ] **Step 3: Vérifier**

Run: `npx tsc --noEmit && npm run lint && npm test`
Expected: 0 erreur (note : `/api/upload` accepte png/jpeg/svg/webp/pdf — l'accept de l'écran 3 est cohérent ; les vidéos seront refusées par l'API : afficher l'erreur d'upload telle quelle, comportement accepté pour ce lot).

- [ ] **Step 4: Commit**

```bash
git add src/components/projet/OnboardingStepPhotos.tsx src/components/projet/OnboardingStepInfos.tsx
git commit -m "feat(studio): ecrans onboarding photos par reference + societe/prix/domaine/histoire/elements"
```

---

### Task 7: `/projet` — CTA onboarding + timeline à 3 jalons

**Files:**
- Modify: `src/app/projet/page.tsx`

**Interfaces:**
- Consumes: `projectDoneCount` étendu (Task 2), page onboarding (Task 5).
- Produces: sous la timeline, quand `project.status === "label_validated"` et pas d'onboarding soumis : carte CTA « Préparons votre site → Commencer » (lien `/projet/onboarding/[id]`) ; si onboarding entamé non soumis : « Reprendre mon onboarding » ; si soumis (`onboarding_submitted`) : bandeau « 🚀 Onboarding soumis — génération de votre pack en préparation ». Le hint du jalon `onboarding` reflète l'état.

- [ ] **Step 1: Étendre la page**

Dans `src/app/projet/page.tsx` :
1. Ajouter `onboarding: { select: { submittedAt: true, completedSteps: true } }` à l'`include` du `findMany`.
2. Après le bloc `{request?.status === "validated" && (…)}` existant, REMPLACER ce bloc par :

```tsx
              {project.status === "label_validated" && (
                <div className="mt-4 rounded-xl border border-neutral-200 bg-neutral-50 p-5">
                  <h3 className="font-medium">🎉 Votre gamme d’étiquettes est validée !</h3>
                  <p className="mt-1 text-sm text-neutral-600">
                    Prochaine étape : votre onboarding — trois écrans pour préparer vos visuels et votre boutique.
                  </p>
                  <a href={`/projet/onboarding/${project.id}`}
                    className="mt-3 inline-block rounded-full bg-neutral-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-neutral-700 transition-colors">
                    {(project.onboarding?.completedSteps?.length ?? 0) > 0 ? "Reprendre mon onboarding" : "Commencer mon onboarding"}
                  </a>
                </div>
              )}

              {project.status === "onboarding_submitted" && (
                <div className="mt-4 rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-800">
                  🚀 Onboarding soumis — nous préparons votre pack de lancement et votre site.
                </div>
              )}
```

3. Dans `ETIQUETTE_HINT`, rien ne change ; ajouter un hint pour le jalon `onboarding` : dans la boucle STEPS, à côté du hint étiquette existant, ajouter :

```tsx
                        {state === "current" && step.key === "onboarding" && project.status === "label_validated" && (
                          <span className="text-neutral-500"> — à vous de jouer, trois écrans rapides !</span>
                        )}
```

- [ ] **Step 2: Vérifier**

Run: `npx tsc --noEmit && npm run lint && npm test`
Expected: 0 erreur. (Le `projectDoneCount` étendu place `onboarding_submitted` → jalon 3 automatiquement.)

- [ ] **Step 3: Commit**

```bash
git add src/app/projet/page.tsx
git commit -m "feat(studio): /projet — CTA onboarding + bandeau soumis + hint jalon 3"
```

---

### Task 8: Déploiement + e2e (exécuté par le contrôleur après revue finale)

**Files:** aucun nouveau (opérations)

**Interfaces:**
- Consumes: tout le lot mergé ; `.env.vercel-prod` local pour `DATABASE_URL`/`DIRECT_URL`.
- Produces: Lot 3 en prod, vérifié.

- [ ] **Step 1: Merge + push (déclenche Vercel)**

```bash
git checkout main && git pull origin main
git merge --no-ff feat/studio-v3-lot3-onboarding -m "Merge feat/studio-v3-lot3-onboarding : Studio V3 Lot 3 (onboarding)"
npx tsc --noEmit && npm test
git push origin main
```

- [ ] **Step 2: Migration prod**

`npx prisma migrate status` (seule `_add_onboarding` en attente) puis `npx prisma migrate deploy` avec les env de `.env.vercel-prod`.

- [ ] **Step 3: E2e (recette éprouvée)**

Script jetable Prisma (même squelette que le Lot 2) : créer commande test signée via webhook (ordre 999000333, dossier + 2 produits) → simuler cycle BAT jusqu'à `label_validated` → PUT les 3 écrans via l'API en session… (l'API exige une session : à défaut, simuler les upserts `Onboarding` via Prisma et vérifier `isStepComplete`/`canSubmit` en conditions réelles + le passage `onboarding_submitted`) → vérifier la timeline (3 jalons) → nettoyage complet (Onboarding → BAT → refs → request → project).

- [ ] **Step 4: Vérification visuelle (Yoann)**

`/projet` avec un projet `label_validated` → CTA → wizard 3 écrans → soumission → email admin reçu → bandeau 🚀.

---

## Hors scope Lot 3 (assumé)

- Pré-remplissage palette depuis l'étiquette (pas de données couleur en DB — voir Global Constraints) ; suggestion de prix calculée (pas de prix B2B par référence en base).
- Upload vidéo (l'API `/api/upload` accepte images+PDF ; les vidéos remontent une erreur propre — élargir au Lot 4 si besoin).
- Édition post-soumission (verrouillé ; déverrouillage manuel admin si besoin via prisma studio).
- Écrans admin de consultation de l'onboarding (le Lot 4 les consommera ; en attendant : prisma studio).

## Critères de succès

- Un projet `label_validated` affiche le CTA dans `/projet` ; le wizard sauvegarde écran par écran et reprend où on s'est arrêté (reload compris).
- Impossible de soumettre incomplet (bouton + 409 serveur) ; impossible de modifier après soumission (409).
- SIRET invalide → écran 3 non complet ; chaque référence exige 1-3 photos et un prix > 0.
- À la soumission : projet `onboarding_submitted`, email admin, timeline 3 jalons ✅, bandeau 🚀.
- Un client ne peut pas toucher l'onboarding d'un autre projet (404/403).
