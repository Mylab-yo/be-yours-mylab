# MY.LAB Studio V3 — Lot 2 (workflow BAT) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer les allers-retours email de création d'étiquette par un workflow BAT complet dans l'app Studio : back-office graphiste, validation par référence côté client, notifications automatiques.

**Architecture:** Tout vit dans l'app `mylab-configurateur` (aucun changement thème dans ce lot). Le webhook `orders/paid` (Lot 1) crée désormais aussi la demande d'étiquette (`LabelRequest` + une `LabelReference` par produit de la gamme). Le graphiste travaille dans `/admin/bat` (upload d'aperçus BAT via Cloudinary, filigrane par transformation d'URL) ; le client valide référence par référence dans `/projet`. Les transitions d'état notifient par Resend. Logique d'état = fonctions pures testées (TDD) ; routes = colle mince ; UI = trio établi du repo (server page → client form `fetch` → API route + garde).

**Tech Stack:** Next.js 16 App Router · TypeScript strict · Prisma 7 (client `@/generated/prisma/client`) · NextAuth v4 (magic link, rôles) · Cloudinary (aperçus + filigrane URL) · Resend · vitest 4.

**Spec de référence :** `docs/superpowers/specs/2026-07-08-mylab-studio-v3-design.md` §4.3 (workflow BAT), §5 (modèle de données), §6 (intégrations). État Lot 1 : modèle `Project` livré, webhook live (id 2395102183758), `/projet` minimal en prod.

## Global Constraints

- **Repo** : `d:\Projets mylab vs code\mylab-configurateur`, branche de travail `feat/studio-v3-lot2-bat` (créée en Task 0 depuis `main`).
- TypeScript `strict`, alias `@/` → `src/`, client Prisma via `@/generated/prisma/client` (JAMAIS `@prisma/client`), singleton `import { prisma } from "@/lib/prisma"`.
- **Pas de server actions, pas de lib de composants** : pattern unique du repo = server page (fetch Prisma direct + `export const dynamic = "force-dynamic"`) → client component (`fetch` + `router.refresh()`) → API route (`NextResponse.json`, garde en tête). Params Next : `params: Promise<{ id: string }>` puis `await params`.
- **Deux grammaires visuelles** : admin = classes globales `.card` / `.input` / `.btn-gold` / `.btn-secondary` + palette `mylab-*` + icônes lucide-react ; page client `/projet` = Tailwind neutre (`rounded-xl border border-neutral-200`). Ne pas mélanger.
- **Emails** : import dynamique `const { Resend } = await import("resend")`, from `"MyLab <noreply@mylab-shop.com>"`, admin `yoann@mylab-shop.com`, chaque email a `text:` ET `html:`, valeurs user-controlled échappées, envoi hors requête via `after()` de `next/server`.
- **Migrations** : AUCUN `prisma migrate dev` (base = Supabase de PROD, pas de base locale). SQL généré par `npx prisma migrate diff --from-schema-datamodel <avant> --to-schema-datamodel prisma/schema.prisma --script`, écrit dans `prisma/migrations/<timestamp>_<nom>/migration.sql`, appliqué par `prisma migrate deploy` en Task 9 uniquement. **Invariant repo : toute nouvelle table reçoit `ENABLE ROW LEVEL SECURITY` + policy `"Service role only" … USING (auth.role() = 'service_role')`** (pattern de `20260708220000_enable_rls_project`), y compris la table de jointure implicite.
- **Machine à états (spec §4.3, verbatim)** : demande `Demande reçue → En création (graphiste) → BAT vN envoyé → Gamme validée ✓` ; « Modifications demandées » sur un BAT renvoie en « En création » et incrémente la version au prochain envoi. **Validation par référence** ; demande « Gamme validée » quand TOUTES les références le sont ; bouton « Tout valider ». **Chaque transition notifie par email** : BAT envoyé → client ; modifications demandées → graphiste ; gamme validée → Yoann.
- **Fichiers** : le client ne voit que des aperçus basse définition **filigranés** ; les fichiers Illustrator de production restent hors app (hors scope, voir fin de plan).
- Rôles : `client`, `graphiste`, `admin`. Le graphiste n'accède qu'à `/admin/bat*` (pages) et aux API BAT.
- Tests : vitest, imports explicites (`globals: false`), colocalisés `*.test.ts`. Commande : `npm test -- <fichier>`. Avant chaque commit : `npx tsc --noEmit` + `npm test` complets.
- Git : commits conventionnels français `feat(studio): …`. Jamais de push sur `main` (merge en fin de lot après revue).

---

### Task 0: Branche de travail

**Files:** aucun (git uniquement)

**Interfaces:**
- Produces: branche `feat/studio-v3-lot2-bat` (app). Toutes les tâches committent dessus.

- [ ] **Step 1: Créer la branche**

```bash
cd "d:\Projets mylab vs code\mylab-configurateur"
git status   # doit être propre (hors dossiers untracked d'assets) ; sinon s'arrêter et demander
git checkout main && git pull origin main
git checkout -b feat/studio-v3-lot2-bat
```

---

### Task 1: Modèles Prisma BAT + rôle graphiste + migration SQL

**Files:**
- Modify: `prisma/schema.prisma`
- Create: `prisma/migrations/<timestamp>_add_bat_workflow/migration.sql` (SQL généré, non appliqué)

**Interfaces:**
- Consumes: modèles existants `Project`, `User` ; enums `UserRole`, `ProjectStatus`.
- Produces (noms exacts consommés par les Tasks 2-8) : enums `LabelRequestStatus { received, in_progress, bat_sent, validated }`, `LabelReferenceStatus { pending, bat_sent, changes_requested, validated }` ; `UserRole` gagne `graphiste` ; `ProjectStatus` gagne `label_validated` ; modèles `LabelRequest`, `LabelReference`, `BatVersion`, `LabelComment` (le « Comment » de la spec — renommé pour éviter la collision avec le mot réservé) avec les champs ci-dessous ; accès `prisma.labelRequest`, `prisma.labelReference`, `prisma.batVersion`, `prisma.labelComment`.

- [ ] **Step 1: Étendre les enums existants**

Dans `prisma/schema.prisma` : `enum UserRole { client admin }` → ajouter `graphiste` ; `enum ProjectStatus { draft paid }` → ajouter `label_validated // gamme d'étiquettes validée — débloque l'onboarding (Lot 3)`.

- [ ] **Step 2: Ajouter enums et modèles BAT**

À la suite des enums existants :

```prisma
enum LabelRequestStatus {
  received    // créée au paiement de la commande, pas encore prise en charge
  in_progress // graphiste au travail (création initiale ou retravail après modifications)
  bat_sent    // un BAT est chez le client, en attente de retours
  validated   // toutes les références validées — gamme validée
}

enum LabelReferenceStatus {
  pending           // pas encore couverte par un BAT
  bat_sent          // couverte par le dernier BAT, en attente du client
  changes_requested // le client a demandé des modifications
  validated         // référence validée par le client
}
```

À la suite du modèle `Project` :

```prisma
model LabelRequest {
  id              String             @id @default(cuid())
  projectId       String             @unique
  project         Project            @relation(fields: [projectId], references: [id])
  designReference String? // property "Référence design" du configurateur (copiée du Project)
  status          LabelRequestStatus @default(received)
  references      LabelReference[]
  batVersions     BatVersion[]
  comments        LabelComment[]
  createdAt       DateTime           @default(now())
  updatedAt       DateTime           @updatedAt
}

model LabelReference {
  id           String               @id @default(cuid())
  requestId    String
  request      LabelRequest         @relation(fields: [requestId], references: [id])
  title        String
  variantTitle String?
  quantity     Int
  sku          String?
  status       LabelReferenceStatus @default(pending)
  validatedAt  DateTime?
  batVersions  BatVersion[]
  comments     LabelComment[]

  @@index([requestId])
}

model BatVersion {
  id         String           @id @default(cuid())
  requestId  String
  request    LabelRequest     @relation(fields: [requestId], references: [id])
  version    Int
  previewUrl String // aperçu Cloudinary (filigrane appliqué à l'affichage, jamais stocké)
  note       String? // note du graphiste au client
  references LabelReference[] // références couvertes par cette version
  createdAt  DateTime         @default(now())

  @@unique([requestId, version])
}

model LabelComment {
  id          String          @id @default(cuid())
  requestId   String
  request     LabelRequest    @relation(fields: [requestId], references: [id])
  referenceId String?
  reference   LabelReference? @relation(fields: [referenceId], references: [id])
  authorRole  String // "client" | "graphiste" | "admin"
  body        String
  createdAt   DateTime        @default(now())

  @@index([requestId])
}
```

Ajouter la relation inverse dans `Project` : `labelRequest LabelRequest?`.

- [ ] **Step 3: Générer le SQL de migration (sans l'appliquer)**

```bash
git stash --keep-index 2>/dev/null # rien à stasher normalement
git show HEAD:prisma/schema.prisma > prisma/_schema_before.prisma
npx prisma migrate diff --from-schema-datamodel prisma/_schema_before.prisma --to-schema-datamodel prisma/schema.prisma --script > migration_draft.sql
```

Créer le dossier `prisma/migrations/<YYYYMMDDHHmmss>_add_bat_workflow/` (timestamp UTC actuel, postérieur à `20260708220000`) et y écrire `migration.sql` = contenu de `migration_draft.sql` **suivi du bloc RLS** (invariant repo — adapter la liste si la table de jointure générée porte un autre nom dans le draft) :

```sql
-- RLS (invariant repo : cf. 20260708220000_enable_rls_project)
ALTER TABLE "LabelRequest" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON "LabelRequest" FOR ALL USING (auth.role() = 'service_role');
ALTER TABLE "LabelReference" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON "LabelReference" FOR ALL USING (auth.role() = 'service_role');
ALTER TABLE "BatVersion" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON "BatVersion" FOR ALL USING (auth.role() = 'service_role');
ALTER TABLE "LabelComment" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON "LabelComment" FOR ALL USING (auth.role() = 'service_role');
ALTER TABLE "_BatVersionToLabelReference" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON "_BatVersionToLabelReference" FOR ALL USING (auth.role() = 'service_role');
```

Supprimer `prisma/_schema_before.prisma` et `migration_draft.sql`.

⚠️ Le draft contiendra des `ALTER TYPE "UserRole" ADD VALUE 'graphiste'` / `ALTER TYPE "ProjectStatus" ADD VALUE 'label_validated'` — les conserver tels quels en tête de fichier.

- [ ] **Step 4: Régénérer le client et vérifier le typage**

Run: `npx prisma generate && npx tsc --noEmit`
Expected: génération OK, 0 erreur TS.

- [ ] **Step 5: Commit**

```bash
git add prisma/schema.prisma prisma/migrations
git commit -m "feat(studio): modeles BAT (LabelRequest/Reference/BatVersion/LabelComment) + roles graphiste + migration SQL"
```

---

### Task 2: Lib pure `bat.ts` — filigrane + machine à états (TDD)

**Files:**
- Create: `src/lib/studio/bat.ts`
- Test: `src/lib/studio/bat.test.ts`

**Interfaces:**
- Consumes: rien (fonctions pures ; les types statuts sont des unions string locales, PAS d'import Prisma pour rester pur).
- Produces (consommé par Tasks 5-8) :
  - `type RefStatus = "pending" | "bat_sent" | "changes_requested" | "validated"`
  - `type ReqStatus = "received" | "in_progress" | "bat_sent" | "validated"`
  - `watermarkUrl(url: string): string` — insère la transformation Cloudinary filigrane+basse déf après `/upload/` ; retourne l'URL inchangée si le motif est absent.
  - `refStatusAfterBatSent(current: RefStatus, covered: boolean): RefStatus`
  - `computeRequestStatus(refs: RefStatus[]): ReqStatus`
  - `projectDoneCount(projectStatus: string, requestStatus?: ReqStatus): number` — jalons atteints pour la timeline `/projet` (0-2 dans ce lot).

- [ ] **Step 1: Écrire les tests (échouent)**

```ts
// src/lib/studio/bat.test.ts
import { describe, it, expect } from "vitest";
import {
  watermarkUrl,
  refStatusAfterBatSent,
  computeRequestStatus,
  projectDoneCount,
} from "./bat";

describe("watermarkUrl", () => {
  it("insère la transformation filigrane après /upload/", () => {
    const url = "https://res.cloudinary.com/demo/image/upload/v123/mylab-configurateur/bat/x.png";
    expect(watermarkUrl(url)).toBe(
      "https://res.cloudinary.com/demo/image/upload/w_1200,q_auto:low,l_text:Arial_70_bold:BAT%20MYLAB,o_25,a_-30/v123/mylab-configurateur/bat/x.png"
    );
  });
  it("laisse intacte une URL sans /upload/", () => {
    expect(watermarkUrl("https://exemple.com/x.png")).toBe("https://exemple.com/x.png");
  });
});

describe("refStatusAfterBatSent", () => {
  it("passe une référence couverte en bat_sent", () => {
    expect(refStatusAfterBatSent("pending", true)).toBe("bat_sent");
    expect(refStatusAfterBatSent("changes_requested", true)).toBe("bat_sent");
  });
  it("ne touche pas une référence validée ni une non couverte", () => {
    expect(refStatusAfterBatSent("validated", true)).toBe("validated");
    expect(refStatusAfterBatSent("pending", false)).toBe("pending");
  });
});

describe("computeRequestStatus", () => {
  it("validated quand toutes les références sont validées", () => {
    expect(computeRequestStatus(["validated", "validated"])).toBe("validated");
  });
  it("bat_sent si au moins une référence attend le client", () => {
    expect(computeRequestStatus(["validated", "bat_sent"])).toBe("bat_sent");
    expect(computeRequestStatus(["bat_sent", "changes_requested"])).toBe("bat_sent");
  });
  it("in_progress si retours demandés ou travail restant sans BAT en attente", () => {
    expect(computeRequestStatus(["changes_requested", "validated"])).toBe("in_progress");
    expect(computeRequestStatus(["pending"])).toBe("in_progress");
  });
  it("received pour une liste vide (jamais couverte)", () => {
    expect(computeRequestStatus([])).toBe("received");
  });
});

describe("projectDoneCount", () => {
  it("0 avant paiement, 1 payé, 2 gamme validée", () => {
    expect(projectDoneCount("draft")).toBe(0);
    expect(projectDoneCount("paid")).toBe(1);
    expect(projectDoneCount("paid", "bat_sent")).toBe(1);
    expect(projectDoneCount("label_validated", "validated")).toBe(2);
  });
});
```

- [ ] **Step 2: Vérifier l'échec**

Run: `npm test -- src/lib/studio/bat.test.ts`
Expected: FAIL — module `./bat` introuvable.

- [ ] **Step 3: Implémenter**

```ts
// src/lib/studio/bat.ts
export type RefStatus = "pending" | "bat_sent" | "changes_requested" | "validated";
export type ReqStatus = "received" | "in_progress" | "bat_sent" | "validated";

// Filigrane + basse définition appliqués À L'AFFICHAGE (l'original Cloudinary reste propre
// pour l'impression d'un aperçu net après validation si besoin).
const WATERMARK = "w_1200,q_auto:low,l_text:Arial_70_bold:BAT%20MYLAB,o_25,a_-30";

export function watermarkUrl(url: string): string {
  const marker = "/upload/";
  const i = url.indexOf(marker);
  if (i === -1) return url;
  return url.slice(0, i + marker.length) + WATERMARK + "/" + url.slice(i + marker.length);
}

export function refStatusAfterBatSent(current: RefStatus, covered: boolean): RefStatus {
  if (!covered || current === "validated") return current;
  return "bat_sent";
}

export function computeRequestStatus(refs: RefStatus[]): ReqStatus {
  if (refs.length === 0) return "received";
  if (refs.every((r) => r === "validated")) return "validated";
  if (refs.some((r) => r === "bat_sent")) return "bat_sent";
  return "in_progress";
}

export function projectDoneCount(projectStatus: string, requestStatus?: ReqStatus): number {
  if (projectStatus === "draft") return 0;
  if (projectStatus === "label_validated" || requestStatus === "validated") return 2;
  return 1;
}
```

- [ ] **Step 4: Vérifier le succès**

Run: `npm test -- src/lib/studio/bat.test.ts`
Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
git add src/lib/studio/bat.ts src/lib/studio/bat.test.ts
git commit -m "feat(studio): lib pure BAT — filigrane Cloudinary + machine a etats (TDD)"
```

---

### Task 3: Webhook — création de la demande d'étiquette au paiement

**Files:**
- Modify: `src/app/api/webhooks/shopify/orders-paid/route.ts`

**Interfaces:**
- Consumes: Task 1 (`prisma.labelRequest`), Lot 1 (`extractProject` fournit `designReference` et `gammeRefs: { title, variantTitle, quantity, sku }[]`).
- Produces: à chaque commande parcours payée, un `LabelRequest` (status `received`) + une `LabelReference` (status `pending`) par entrée de `gammeRefs`, rattachés au `Project`. Idempotent (relivraison webhook = pas de doublon).

- [ ] **Step 1: Étendre la route**

Dans `src/app/api/webhooks/shopify/orders-paid/route.ts`, remplacer le bloc upsert existant par :

```ts
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

  // Lot 2 : la demande d'étiquette naît avec le paiement. Idempotent via projectId @unique.
  const existingRequest = await prisma.labelRequest.findUnique({ where: { projectId: project.id } });
  if (!existingRequest) {
    await prisma.labelRequest.create({
      data: {
        projectId: project.id,
        designReference: data.designReference,
        references: {
          create: data.gammeRefs.map((g) => ({
            title: g.title,
            variantTitle: g.variantTitle,
            quantity: g.quantity,
            sku: g.sku,
          })),
        },
      },
    });
  }

  return NextResponse.json({ projectId: project.id });
```

- [ ] **Step 2: Vérifier**

Run: `npx tsc --noEmit && npm test`
Expected: 0 erreur TS, suite complète verte (la logique d'extraction reste couverte par les tests Lot 1 ; la création est de la colle Prisma, vérifiée en e2e à la Task 9).

- [ ] **Step 3: Commit**

```bash
git add src/app/api/webhooks/shopify/orders-paid/route.ts
git commit -m "feat(studio): le webhook orders/paid cree la demande d'etiquette (LabelRequest + references)"
```

---

### Task 4: Notifications — builders d'emails (TDD) + envoi

**Files:**
- Create: `src/lib/studio/notifications.ts`
- Test: `src/lib/studio/notifications.test.ts`

**Interfaces:**
- Consumes: env `RESEND_API_KEY`, `STUDIO_GRAPHISTE_EMAIL` (optionnelle, fallback `yoann@mylab-shop.com`).
- Produces (consommé par Task 5) :
  - `type StudioEmail = { subject: string; html: string; text: string }`
  - `buildBatSentEmail(p: { orderNumber: string; version: number; note: string | null }): StudioEmail`
  - `buildChangesRequestedEmail(p: { orderNumber: string; refTitle: string | null; commentBody: string }): StudioEmail`
  - `buildGammeValideeEmail(p: { orderNumber: string; refCount: number }): StudioEmail`
  - `sendStudioEmail(to: string, email: StudioEmail): Promise<void>` — no-op loggé si `RESEND_API_KEY` absente ; ne jette jamais (erreurs loggées).
  - `graphisteEmail(): string`
  - `escapeHtml(s: string): string` (exportée pour les tests)

- [ ] **Step 1: Écrire les tests (échouent)**

```ts
// src/lib/studio/notifications.test.ts
import { describe, it, expect } from "vitest";
import {
  buildBatSentEmail,
  buildChangesRequestedEmail,
  buildGammeValideeEmail,
  escapeHtml,
  graphisteEmail,
} from "./notifications";

describe("escapeHtml", () => {
  it("échappe les caractères dangereux", () => {
    expect(escapeHtml(`<img src=x onerror="a&b">'`)).toBe(
      "&lt;img src=x onerror=&quot;a&amp;b&quot;&gt;&#39;"
    );
  });
});

describe("buildBatSentEmail", () => {
  const mail = buildBatSentEmail({ orderNumber: "1042", version: 2, note: 'Fond <clair> "éclairci"' });
  it("subject avec n° de commande et version", () => {
    expect(mail.subject).toBe("Votre BAT v2 est prêt — commande n°1042");
  });
  it("html contient le lien /projet et la note échappée", () => {
    expect(mail.html).toContain("https://mylab-configurateur.vercel.app/projet");
    expect(mail.html).toContain("Fond &lt;clair&gt; &quot;éclairci&quot;");
    expect(mail.html).not.toContain("<clair>");
  });
  it("text non vide sans balises", () => {
    expect(mail.text.length).toBeGreaterThan(20);
    expect(mail.text).not.toContain("<div");
  });
});

describe("buildChangesRequestedEmail", () => {
  const mail = buildChangesRequestedEmail({ orderNumber: "1042", refTitle: "Shampoing 500ml", commentBody: "Logo <plus> grand" });
  it("subject et contenu", () => {
    expect(mail.subject).toBe("Modifications demandées — commande n°1042");
    expect(mail.html).toContain("Shampoing 500ml");
    expect(mail.html).toContain("Logo &lt;plus&gt; grand");
    expect(mail.html).toContain("/admin/bat");
  });
  it("refTitle null → mention gamme entière", () => {
    const m = buildChangesRequestedEmail({ orderNumber: "1042", refTitle: null, commentBody: "x" });
    expect(m.html).toContain("l’ensemble de la gamme");
  });
});

describe("buildGammeValideeEmail", () => {
  it("subject et compteur de références", () => {
    const m = buildGammeValideeEmail({ orderNumber: "1042", refCount: 4 });
    expect(m.subject).toBe("Gamme validée ✓ — commande n°1042");
    expect(m.html).toContain("4 référence(s)");
  });
});

describe("graphisteEmail", () => {
  it("fallback admin sans env", () => {
    const prev = process.env.STUDIO_GRAPHISTE_EMAIL;
    delete process.env.STUDIO_GRAPHISTE_EMAIL;
    expect(graphisteEmail()).toBe("yoann@mylab-shop.com");
    if (prev !== undefined) process.env.STUDIO_GRAPHISTE_EMAIL = prev;
  });
});
```

- [ ] **Step 2: Vérifier l'échec**

Run: `npm test -- src/lib/studio/notifications.test.ts`
Expected: FAIL — module `./notifications` introuvable.

- [ ] **Step 3: Implémenter**

```ts
// src/lib/studio/notifications.ts
const FROM = "MyLab <noreply@mylab-shop.com>";
const ADMIN_EMAIL = "yoann@mylab-shop.com";
const PROJET_URL = "https://mylab-configurateur.vercel.app/projet";
const ADMIN_BAT_URL = "https://mylab-configurateur.vercel.app/admin/bat";

export type StudioEmail = { subject: string; html: string; text: string };

export function escapeHtml(s: string): string {
  return s
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function graphisteEmail(): string {
  return process.env.STUDIO_GRAPHISTE_EMAIL || ADMIN_EMAIL;
}

const wrap = (title: string, body: string) =>
  `<div style="font-family: Montserrat, sans-serif; max-width: 560px; margin: 0 auto; padding: 32px 20px; color: #212326; font-size: 14px; line-height: 1.6;">` +
  `<h1 style="font-size:22px; font-weight:500;">${title}</h1>${body}</div>`;

export function buildBatSentEmail(p: { orderNumber: string; version: number; note: string | null }): StudioEmail {
  const note = p.note ? `<p style="background:#f7f5f2;padding:12px 16px;">💬 ${escapeHtml(p.note)}</p>` : "";
  return {
    subject: `Votre BAT v${p.version} est prêt — commande n°${p.orderNumber}`,
    html: wrap(
      `Votre BAT v${p.version} est prêt`,
      `${note}<p>Votre maquette d’étiquette vous attend : consultez-la, validez chaque référence ou demandez des modifications.</p>` +
        `<p><a href="${PROJET_URL}" style="display:inline-block;background:#212326;color:#fff;padding:12px 24px;text-decoration:none;">Voir mon BAT</a></p>`
    ),
    text: `Votre BAT v${p.version} est prêt (commande n°${p.orderNumber}).${p.note ? `\nNote du graphiste : ${p.note}` : ""}\nConsultez-le et validez : ${PROJET_URL}`,
  };
}

export function buildChangesRequestedEmail(p: { orderNumber: string; refTitle: string | null; commentBody: string }): StudioEmail {
  const cible = p.refTitle ? escapeHtml(p.refTitle) : "l’ensemble de la gamme";
  return {
    subject: `Modifications demandées — commande n°${p.orderNumber}`,
    html: wrap(
      "Le client demande des modifications",
      `<p>Sur : <strong>${cible}</strong></p><p style="background:#f7f5f2;padding:12px 16px;">💬 ${escapeHtml(p.commentBody)}</p>` +
        `<p><a href="${ADMIN_BAT_URL}" style="display:inline-block;background:#212326;color:#fff;padding:12px 24px;text-decoration:none;">Ouvrir la demande</a></p>`
    ),
    text: `Modifications demandées (commande n°${p.orderNumber}) sur ${p.refTitle ?? "l'ensemble de la gamme"} :\n${p.commentBody}\n${ADMIN_BAT_URL}`,
  };
}

export function buildGammeValideeEmail(p: { orderNumber: string; refCount: number }): StudioEmail {
  return {
    subject: `Gamme validée ✓ — commande n°${p.orderNumber}`,
    html: wrap(
      "Gamme validée ✓",
      `<p>Le client a validé ${p.refCount} référence(s). La demande d’étiquette est terminée — l’onboarding Studio est débloqué (Lot 3) et les fichiers de production peuvent partir à l’impression.</p>` +
        `<p><a href="${ADMIN_BAT_URL}">Voir la demande</a></p>`
    ),
    text: `Gamme validée (commande n°${p.orderNumber}) : ${p.refCount} référence(s). ${ADMIN_BAT_URL}`,
  };
}

export async function sendStudioEmail(to: string, email: StudioEmail): Promise<void> {
  if (!process.env.RESEND_API_KEY) {
    console.log(`[studio notifications] RESEND_API_KEY absente — email non envoyé : ${email.subject} → ${to}`);
    return;
  }
  try {
    const { Resend } = await import("resend");
    const resend = new Resend(process.env.RESEND_API_KEY);
    const r = await resend.emails.send({ from: FROM, to, subject: email.subject, text: email.text, html: email.html });
    if (r.error) console.error("[studio notifications] échec envoi:", r.error);
  } catch (e) {
    console.error("[studio notifications] exception envoi:", e);
  }
}
```

- [ ] **Step 4: Vérifier le succès**

Run: `npm test -- src/lib/studio/notifications.test.ts`
Expected: PASS (9 tests), sortie propre.

- [ ] **Step 5: Commit**

```bash
git add src/lib/studio/notifications.ts src/lib/studio/notifications.test.ts
git commit -m "feat(studio): notifications BAT Resend — builders testes + envoi tolerant aux pannes"
```

---

### Task 5: Gardes d'accès — rôle graphiste + propriété projet

**Files:**
- Modify: `src/types/next-auth.d.ts` (union des rôles)
- Modify: `src/middleware.ts`
- Create: `src/lib/studio/guards.ts`

**Interfaces:**
- Consumes: `getServerSession(authOptions)`, `prisma`.
- Produces (consommé par Tasks 6-8) :
  - Union de rôle session : `"client" | "admin" | "graphiste"`.
  - `requireBatStaff(): Promise<NextResponse | null>` — 401 non connecté, 403 si ni `admin` ni `graphiste`.
  - `requireRequestOwner(requestId: string): Promise<{ session: Session; request: LabelRequestWithProject } | NextResponse>` où `LabelRequestWithProject = Prisma LabelRequest & { project: Project; references: LabelReference[] }` — 401/403/404 en `NextResponse` sinon.
  - Middleware : `admin` accède à tout `/admin/*` ; `graphiste` uniquement à `/admin/bat*`.

- [ ] **Step 1: Étendre le typage de session**

Dans `src/types/next-auth.d.ts`, remplacer l'union : `role: "client" | "admin"` → `role: "client" | "admin" | "graphiste"` (les deux occurrences si Session ET JWT y sont déclarés).

- [ ] **Step 2: Middleware**

Dans `src/middleware.ts`, remplacer le callback `authorized` :

```ts
callbacks: {
  authorized: ({ token, req }) =>
    token?.role === "admin" ||
    (token?.role === "graphiste" && req.nextUrl.pathname.startsWith("/admin/bat")),
},
```

Le matcher existant ne change pas.

- [ ] **Step 3: Gardes serveur**

```ts
// src/lib/studio/guards.ts
import { getServerSession } from "next-auth";
import { NextResponse } from "next/server";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export async function requireBatStaff(): Promise<NextResponse | null> {
  const session = await getServerSession(authOptions);
  if (!session?.user) return NextResponse.json({ error: "Non authentifié" }, { status: 401 });
  const role = session.user.role;
  if (role !== "admin" && role !== "graphiste")
    return NextResponse.json({ error: "Accès interdit" }, { status: 403 });
  return null;
}

export async function requireRequestOwner(requestId: string) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.email) return NextResponse.json({ error: "Non authentifié" }, { status: 401 });
  const request = await prisma.labelRequest.findUnique({
    where: { id: requestId },
    include: { project: true, references: true },
  });
  if (!request) return NextResponse.json({ error: "Demande introuvable" }, { status: 404 });
  const email = session.user.email.toLowerCase();
  const owns = request.project.userId === session.user.id || request.project.email === email;
  if (!owns) return NextResponse.json({ error: "Accès interdit" }, { status: 403 });
  return { session, request };
}
```

- [ ] **Step 4: Vérifier**

Run: `npx tsc --noEmit && npm test`
Expected: 0 erreur, suite verte.

- [ ] **Step 5: Commit**

```bash
git add src/types/next-auth.d.ts src/middleware.ts src/lib/studio/guards.ts
git commit -m "feat(studio): role graphiste (middleware /admin/bat) + gardes staff et proprietaire"
```

---

### Task 6: API BAT — envoi de version, validation, commentaires

**Files:**
- Create: `src/app/api/studio/bat/route.ts` (POST — graphiste envoie un BAT)
- Create: `src/app/api/studio/references/[id]/validate/route.ts` (POST — client valide une référence)
- Create: `src/app/api/studio/requests/[id]/validate-all/route.ts` (POST — client « Tout valider »)
- Create: `src/app/api/studio/requests/[id]/comments/route.ts` (POST — commentaire ± demande de modifications)

**Interfaces:**
- Consumes: Task 1 (modèles), Task 2 (`refStatusAfterBatSent`, `computeRequestStatus`), Task 4 (builders + `sendStudioEmail`, `graphisteEmail`), Task 5 (gardes), `after` de `next/server`.
- Produces (consommé par Tasks 7-8, contrats exacts) :
  - `POST /api/studio/bat` body `{ requestId: string; previewUrl: string; note?: string; referenceIds: string[] }` → 201 `{ batVersionId, version, requestStatus }`. Garde `requireBatStaff`. Effets : `BatVersion` créée (version = max+1), refs couvertes non validées → `bat_sent`, statut demande recalculé, email « BAT envoyé » au client via `after()`.
  - `POST /api/studio/references/[id]/validate` body vide → 200 `{ refStatus: "validated", requestStatus }`. Garde propriétaire (via la demande parente). Si la demande passe `validated` : `project.status = "label_validated"` + email « gamme validée » à l'admin.
  - `POST /api/studio/requests/[id]/validate-all` body vide → 200 `{ requestStatus: "validated" }`. Même cascade.
  - `POST /api/studio/requests/[id]/comments` body `{ body: string; referenceId?: string; requestChanges?: boolean }` → 201 `{ commentId, requestStatus }`. Client propriétaire OU staff. Si client + `requestChanges` : réf ciblée (ou toutes les refs `bat_sent` si pas de `referenceId`) → `changes_requested`, demande → `in_progress`, email « modifications demandées » au graphiste.

- [ ] **Step 1: Route d'envoi de BAT**

```ts
// src/app/api/studio/bat/route.ts
import { NextResponse } from "next/server";
import { after } from "next/server";
import { prisma } from "@/lib/prisma";
import { requireBatStaff } from "@/lib/studio/guards";
import { refStatusAfterBatSent, computeRequestStatus, type RefStatus } from "@/lib/studio/bat";
import { buildBatSentEmail, sendStudioEmail } from "@/lib/studio/notifications";

export async function POST(req: Request) {
  const guard = await requireBatStaff();
  if (guard) return guard;

  const { requestId, previewUrl, note, referenceIds } = (await req.json()) as {
    requestId?: string; previewUrl?: string; note?: string; referenceIds?: string[];
  };
  if (!requestId || !previewUrl || !Array.isArray(referenceIds) || referenceIds.length === 0)
    return NextResponse.json({ error: "requestId, previewUrl et referenceIds requis" }, { status: 400 });

  const request = await prisma.labelRequest.findUnique({
    where: { id: requestId },
    include: { references: true, project: true, batVersions: { orderBy: { version: "desc" }, take: 1 } },
  });
  if (!request) return NextResponse.json({ error: "Demande introuvable" }, { status: 404 });

  const covered = new Set(referenceIds);
  const version = (request.batVersions[0]?.version ?? 0) + 1;

  const bat = await prisma.batVersion.create({
    data: {
      requestId,
      version,
      previewUrl,
      note: note || null,
      references: { connect: referenceIds.map((id) => ({ id })) },
    },
  });

  const newStatuses = request.references.map((r) => ({
    id: r.id,
    status: refStatusAfterBatSent(r.status as RefStatus, covered.has(r.id)),
  }));
  for (const s of newStatuses) {
    await prisma.labelReference.update({ where: { id: s.id }, data: { status: s.status } });
  }
  const requestStatus = computeRequestStatus(newStatuses.map((s) => s.status));
  await prisma.labelRequest.update({ where: { id: requestId }, data: { status: requestStatus } });

  after(async () => {
    await sendStudioEmail(
      request.project.email,
      buildBatSentEmail({ orderNumber: request.project.shopifyOrderNumber ?? "—", version, note: note || null })
    );
  });

  return NextResponse.json({ batVersionId: bat.id, version, requestStatus }, { status: 201 });
}
```

- [ ] **Step 2: Validation d'une référence**

```ts
// src/app/api/studio/references/[id]/validate/route.ts
import { NextResponse } from "next/server";
import { after } from "next/server";
import { prisma } from "@/lib/prisma";
import { requireRequestOwner } from "@/lib/studio/guards";
import { computeRequestStatus, type RefStatus } from "@/lib/studio/bat";
import { buildGammeValideeEmail, sendStudioEmail } from "@/lib/studio/notifications";

const ADMIN_EMAIL = "yoann@mylab-shop.com";

export async function POST(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const ref = await prisma.labelReference.findUnique({ where: { id } });
  if (!ref) return NextResponse.json({ error: "Référence introuvable" }, { status: 404 });

  const owner = await requireRequestOwner(ref.requestId);
  if (owner instanceof NextResponse) return owner;
  const { request } = owner;

  await prisma.labelReference.update({ where: { id }, data: { status: "validated", validatedAt: new Date() } });

  const statuses = request.references.map((r) => (r.id === id ? "validated" : (r.status as RefStatus)));
  const requestStatus = computeRequestStatus(statuses);
  await prisma.labelRequest.update({ where: { id: request.id }, data: { status: requestStatus } });

  if (requestStatus === "validated") {
    await prisma.project.update({ where: { id: request.projectId }, data: { status: "label_validated" } });
    after(async () => {
      await sendStudioEmail(
        ADMIN_EMAIL,
        buildGammeValideeEmail({ orderNumber: request.project.shopifyOrderNumber ?? "—", refCount: request.references.length })
      );
    });
  }

  return NextResponse.json({ refStatus: "validated", requestStatus });
}
```

- [ ] **Step 3: « Tout valider »**

```ts
// src/app/api/studio/requests/[id]/validate-all/route.ts
import { NextResponse } from "next/server";
import { after } from "next/server";
import { prisma } from "@/lib/prisma";
import { requireRequestOwner } from "@/lib/studio/guards";
import { buildGammeValideeEmail, sendStudioEmail } from "@/lib/studio/notifications";

const ADMIN_EMAIL = "yoann@mylab-shop.com";

export async function POST(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const owner = await requireRequestOwner(id);
  if (owner instanceof NextResponse) return owner;
  const { request } = owner;

  await prisma.labelReference.updateMany({
    where: { requestId: id, status: { not: "validated" } },
    data: { status: "validated", validatedAt: new Date() },
  });
  await prisma.labelRequest.update({ where: { id }, data: { status: "validated" } });
  await prisma.project.update({ where: { id: request.projectId }, data: { status: "label_validated" } });

  after(async () => {
    await sendStudioEmail(
      ADMIN_EMAIL,
      buildGammeValideeEmail({ orderNumber: request.project.shopifyOrderNumber ?? "—", refCount: request.references.length })
    );
  });

  return NextResponse.json({ requestStatus: "validated" });
}
```

- [ ] **Step 4: Commentaires ± demande de modifications**

```ts
// src/app/api/studio/requests/[id]/comments/route.ts
import { NextResponse } from "next/server";
import { after } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { requireRequestOwner } from "@/lib/studio/guards";
import { buildChangesRequestedEmail, sendStudioEmail, graphisteEmail } from "@/lib/studio/notifications";

export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { body, referenceId, requestChanges } = (await req.json()) as {
    body?: string; referenceId?: string; requestChanges?: boolean;
  };
  if (!body?.trim()) return NextResponse.json({ error: "body requis" }, { status: 400 });
  if (body.length > 4000) return NextResponse.json({ error: "commentaire trop long" }, { status: 400 });

  const session = await getServerSession(authOptions);
  const role = session?.user?.role;
  const isStaff = role === "admin" || role === "graphiste";

  let request;
  if (isStaff) {
    request = await prisma.labelRequest.findUnique({ where: { id }, include: { project: true, references: true } });
    if (!request) return NextResponse.json({ error: "Demande introuvable" }, { status: 404 });
  } else {
    const owner = await requireRequestOwner(id);
    if (owner instanceof NextResponse) return owner;
    request = owner.request;
  }

  if (referenceId && !request.references.some((r) => r.id === referenceId))
    return NextResponse.json({ error: "Référence hors demande" }, { status: 400 });

  const comment = await prisma.labelComment.create({
    data: { requestId: id, referenceId: referenceId || null, authorRole: isStaff ? (role as string) : "client", body: body.trim() },
  });

  let requestStatus = request.status as string;
  if (!isStaff && requestChanges) {
    await prisma.labelReference.updateMany({
      where: referenceId
        ? { id: referenceId, status: { not: "validated" } }
        : { requestId: id, status: "bat_sent" },
      data: { status: "changes_requested" },
    });
    requestStatus = "in_progress";
    await prisma.labelRequest.update({ where: { id }, data: { status: "in_progress" } });
    const refTitle = referenceId ? request.references.find((r) => r.id === referenceId)?.title ?? null : null;
    after(async () => {
      await sendStudioEmail(
        graphisteEmail(),
        buildChangesRequestedEmail({ orderNumber: request.project.shopifyOrderNumber ?? "—", refTitle, commentBody: body.trim() })
      );
    });
  }

  return NextResponse.json({ commentId: comment.id, requestStatus }, { status: 201 });
}
```

- [ ] **Step 5: Vérifier**

Run: `npx tsc --noEmit && npm test`
Expected: 0 erreur, suite verte (la logique d'état est couverte par la Task 2 ; les routes sont de la colle — vérification comportementale à la Task 9).

- [ ] **Step 6: Commit**

```bash
git add src/app/api/studio/bat src/app/api/studio/references src/app/api/studio/requests
git commit -m "feat(studio): API BAT — envoi de version, validation par reference, tout valider, commentaires"
```

---

### Task 7: Back-office `/admin/bat` — file + fiche demande

**Files:**
- Modify: `src/components/admin/AdminSidebar.tsx` (une entrée de nav)
- Create: `src/app/admin/(dashboard)/bat/page.tsx` (file des demandes)
- Create: `src/app/admin/(dashboard)/bat/[id]/page.tsx` (fiche)
- Create: `src/components/admin/BatUploadForm.tsx` (client)
- Create: `src/components/admin/BatCommentForm.tsx` (client)

**Interfaces:**
- Consumes: Task 6 (`POST /api/studio/bat`, `POST /api/studio/requests/[id]/comments`), composant existant `ImageUpload` (`src/components/admin/ImageUpload.tsx`, props `{ value, onChange, folder, label? }`), classes `.card`/`.input`/`.btn-gold`/`.btn-secondary`, pattern table admin (designs).
- Produces: `/admin/bat` (liste triée par `updatedAt` desc : commande, email, x/y réfs validées, badge statut) et `/admin/bat/[id]` (brief, tableau des références avec badges, historique des BAT avec aperçus, fil de commentaires, formulaire d'envoi de BAT, formulaire de commentaire staff). Accessible aux rôles `admin` et `graphiste` (middleware Task 5).

- [ ] **Step 1: Entrée sidebar**

Dans `src/components/admin/AdminSidebar.tsx`, importer `Stamp` de `lucide-react` et ajouter au tableau `links` (après « Designs ») : `{ href: "/admin/bat", label: "BAT Étiquettes", icon: Stamp },`

- [ ] **Step 2: File des demandes**

```tsx
// src/app/admin/(dashboard)/bat/page.tsx
import Link from "next/link";
import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

const STATUS_BADGE: Record<string, { label: string; cls: string }> = {
  received: { label: "Demande reçue", cls: "bg-blue-100 text-blue-700" },
  in_progress: { label: "En création", cls: "bg-amber-100 text-amber-700" },
  bat_sent: { label: "BAT chez le client", cls: "bg-purple-100 text-purple-700" },
  validated: { label: "Gamme validée ✓", cls: "bg-emerald-100 text-emerald-700" },
};

export default async function BatQueuePage() {
  const requests = await prisma.labelRequest.findMany({
    include: { project: true, references: true, batVersions: { orderBy: { version: "desc" }, take: 1 } },
    orderBy: { updatedAt: "desc" },
  });

  return (
    <div>
      <h1 className="text-2xl font-medium mb-6">BAT Étiquettes</h1>
      {requests.length === 0 ? (
        <div className="card text-center py-12 text-mylab-text/40">Aucune demande d’étiquette pour le moment.</div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50/50">
                <th className="text-left px-6 py-3 font-medium text-mylab-text/50">Commande</th>
                <th className="text-left px-6 py-3 font-medium text-mylab-text/50">Client</th>
                <th className="text-left px-6 py-3 font-medium text-mylab-text/50">Références</th>
                <th className="text-left px-6 py-3 font-medium text-mylab-text/50">Statut</th>
                <th className="text-left px-6 py-3 font-medium text-mylab-text/50">Dernier BAT</th>
                <th className="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {requests.map((r) => {
                const done = r.references.filter((x) => x.status === "validated").length;
                const badge = STATUS_BADGE[r.status] ?? STATUS_BADGE.received;
                return (
                  <tr key={r.id} className="border-b border-mylab-text/5 hover:bg-mylab-gold/5 transition-colors">
                    <td className="px-6 py-4">n°{r.project.shopifyOrderNumber}</td>
                    <td className="px-6 py-4">{r.project.email}</td>
                    <td className="px-6 py-4">{done}/{r.references.length} validées</td>
                    <td className="px-6 py-4"><span className={`text-xs px-2 py-0.5 ${badge.cls}`}>{badge.label}</span></td>
                    <td className="px-6 py-4">{r.batVersions[0] ? `v${r.batVersions[0].version}` : "—"}</td>
                    <td className="px-6 py-4"><Link href={`/admin/bat/${r.id}`} className="btn-secondary px-3 py-1.5 text-xs">Ouvrir</Link></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Fiche demande**

```tsx
// src/app/admin/(dashboard)/bat/[id]/page.tsx
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { prisma } from "@/lib/prisma";
import { BatUploadForm } from "@/components/admin/BatUploadForm";
import { BatCommentForm } from "@/components/admin/BatCommentForm";

export const dynamic = "force-dynamic";

const REF_BADGE: Record<string, { label: string; cls: string }> = {
  pending: { label: "En attente de BAT", cls: "bg-gray-100 text-gray-500" },
  bat_sent: { label: "Chez le client", cls: "bg-purple-100 text-purple-700" },
  changes_requested: { label: "Modifs demandées", cls: "bg-amber-100 text-amber-700" },
  validated: { label: "Validée ✓", cls: "bg-emerald-100 text-emerald-700" },
};

export default async function BatDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const request = await prisma.labelRequest.findUnique({
    where: { id },
    include: {
      project: true,
      references: { orderBy: { title: "asc" } },
      batVersions: { orderBy: { version: "desc" }, include: { references: true } },
      comments: { orderBy: { createdAt: "asc" }, include: { reference: true } },
    },
  });
  if (!request) notFound();

  return (
    <div>
      <Link href="/admin/bat" className="inline-flex items-center gap-2 text-sm text-mylab-text/50 hover:text-mylab-text mb-6">
        <ArrowLeft size={16} /> Toutes les demandes
      </Link>
      <h1 className="text-2xl font-medium mb-6">Commande n°{request.project.shopifyOrderNumber} — {request.project.email}</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-8">
          <div className="card p-6">
            <h2 className="text-sm font-medium mb-4 text-mylab-text/50 uppercase tracking-wider">Brief</h2>
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between"><dt className="text-mylab-text/50">Référence design</dt><dd>{request.designReference ?? "—"}</dd></div>
              <div className="flex justify-between"><dt className="text-mylab-text/50">Statut demande</dt><dd>{request.status}</dd></div>
            </dl>
          </div>

          <div className="card p-6">
            <h2 className="text-sm font-medium mb-4 text-mylab-text/50 uppercase tracking-wider">Références ({request.references.length})</h2>
            <ul className="space-y-2 text-sm">
              {request.references.map((r) => {
                const b = REF_BADGE[r.status] ?? REF_BADGE.pending;
                return (
                  <li key={r.id} className="flex items-center justify-between">
                    <span>{r.title}{r.variantTitle ? ` ${r.variantTitle}` : ""} ×{r.quantity}</span>
                    <span className={`text-xs px-2 py-0.5 ${b.cls}`}>{b.label}</span>
                  </li>
                );
              })}
            </ul>
          </div>

          <div className="card p-6">
            <h2 className="text-sm font-medium mb-4 text-mylab-text/50 uppercase tracking-wider">Commentaires</h2>
            <ul className="space-y-3 text-sm mb-4">
              {request.comments.map((c) => (
                <li key={c.id} className="bg-gray-50 p-3">
                  <div className="text-xs text-mylab-text/50 mb-1">
                    {c.authorRole === "client" ? "Client" : "MyLab"} · {c.createdAt.toLocaleDateString("fr-FR")}
                    {c.reference ? ` · ${c.reference.title}` : ""}
                  </div>
                  {c.body}
                </li>
              ))}
              {request.comments.length === 0 && <li className="text-mylab-text/40">Aucun commentaire.</li>}
            </ul>
            <BatCommentForm requestId={request.id} />
          </div>
        </div>

        <div className="space-y-8">
          <div className="card p-6">
            <h2 className="text-sm font-medium mb-4 text-mylab-text/50 uppercase tracking-wider">Envoyer un BAT</h2>
            <BatUploadForm
              requestId={request.id}
              references={request.references.map((r) => ({ id: r.id, label: `${r.title}${r.variantTitle ? ` ${r.variantTitle}` : ""}`, status: r.status }))}
              nextVersion={(request.batVersions[0]?.version ?? 0) + 1}
            />
          </div>

          <div className="card p-6">
            <h2 className="text-sm font-medium mb-4 text-mylab-text/50 uppercase tracking-wider">Historique des BAT</h2>
            <ul className="space-y-4 text-sm">
              {request.batVersions.map((b) => (
                <li key={b.id} className="border-b border-mylab-text/5 pb-4">
                  <div className="font-medium mb-1">v{b.version} · {b.createdAt.toLocaleDateString("fr-FR")}</div>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={b.previewUrl} alt={`BAT v${b.version}`} className="max-h-40 border border-mylab-text/10 mb-1" />
                  <div className="text-xs text-mylab-text/50">Couvre : {b.references.map((r) => r.title).join(", ")}</div>
                  {b.note && <div className="text-xs mt-1">💬 {b.note}</div>}
                </li>
              ))}
              {request.batVersions.length === 0 && <li className="text-mylab-text/40">Aucun BAT envoyé.</li>}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Formulaire d'envoi de BAT (client)**

```tsx
// src/components/admin/BatUploadForm.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ImageUpload } from "@/components/admin/ImageUpload";

type RefOption = { id: string; label: string; status: string };

export function BatUploadForm({ requestId, references, nextVersion }: { requestId: string; references: RefOption[]; nextVersion: number }) {
  const router = useRouter();
  const [previewUrl, setPreviewUrl] = useState("");
  const [note, setNote] = useState("");
  const [selected, setSelected] = useState<string[]>(references.filter((r) => r.status !== "validated").map((r) => r.id));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggle(id: string) {
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true); setError(null);
    try {
      const res = await fetch("/api/studio/bat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requestId, previewUrl, note: note || undefined, referenceIds: selected }),
      });
      if (!res.ok) { const data = await res.json(); throw new Error(data.error || "Échec de l'envoi"); }
      setPreviewUrl(""); setNote("");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 text-sm rounded-none">{error}</div>}
      <ImageUpload value={previewUrl} onChange={setPreviewUrl} folder="bat" label={`Aperçu BAT v${nextVersion} (PNG/JPG/PDF)`} />
      <div>
        <label className="block text-sm font-medium mb-1">Références couvertes <span className="text-red-500">*</span></label>
        <div className="space-y-1 text-sm">
          {references.map((r) => (
            <label key={r.id} className="flex items-center gap-2">
              <input type="checkbox" checked={selected.includes(r.id)} onChange={() => toggle(r.id)} disabled={r.status === "validated"} />
              <span className={r.status === "validated" ? "line-through text-mylab-text/40" : ""}>{r.label}</span>
            </label>
          ))}
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Note au client</label>
        <textarea className="input min-h-[80px]" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Ex. : logo agrandi, fond éclairci…" />
      </div>
      <button type="submit" className="btn-gold" disabled={loading || !previewUrl || selected.length === 0}>
        {loading ? "Envoi…" : `Envoyer le BAT v${nextVersion} au client`}
      </button>
    </form>
  );
}
```

- [ ] **Step 5: Formulaire de commentaire staff (client)**

```tsx
// src/components/admin/BatCommentForm.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function BatCommentForm({ requestId }: { requestId: string }) {
  const router = useRouter();
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true); setError(null);
    try {
      const res = await fetch(`/api/studio/requests/${requestId}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body }),
      });
      if (!res.ok) { const data = await res.json(); throw new Error(data.error || "Échec"); }
      setBody("");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      {error && <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 text-sm rounded-none">{error}</div>}
      <textarea className="input min-h-[60px]" value={body} onChange={(e) => setBody(e.target.value)} placeholder="Commentaire interne visible du client…" />
      <button type="submit" className="btn-secondary text-sm" disabled={loading || !body.trim()}>{loading ? "Envoi…" : "Commenter"}</button>
    </form>
  );
}
```

- [ ] **Step 6: Vérifier**

Run: `npx tsc --noEmit && npm run lint && npm test`
Expected: 0 erreur, lint OK, suite verte. Vérifier que l'export d'`ImageUpload` correspond (named vs default) — adapter l'import si besoin et le noter au rapport.

- [ ] **Step 7: Commit**

```bash
git add src/components/admin/AdminSidebar.tsx src/app/admin/(dashboard)/bat src/components/admin/BatUploadForm.tsx src/components/admin/BatCommentForm.tsx
git commit -m "feat(studio): back-office /admin/bat — file des demandes, fiche, envoi de BAT, commentaires"
```

---

### Task 8: Espace client `/projet` — suivi BAT et validation

**Files:**
- Modify: `src/app/projet/page.tsx`
- Create: `src/components/projet/BatPanel.tsx` (client)

**Interfaces:**
- Consumes: Task 2 (`watermarkUrl`, `projectDoneCount`, types), Task 6 (`POST /api/studio/references/[id]/validate`, `.../validate-all`, `.../comments`), modèles Task 1.
- Produces: `/projet` affiche par projet : timeline pilotée par `projectDoneCount`, et si un BAT est chez le client (`request.status === "bat_sent"`) le panneau BAT — aperçu filigrané de la dernière version, note du graphiste, liste des références avec bouton « Valider » individuel, bouton « Tout valider », formulaire « Demander une modification ». Grammaire visuelle NEUTRE (`neutral-*`, `rounded-xl`), pas les classes admin.

- [ ] **Step 1: Étendre la page serveur**

Remplacer `src/app/projet/page.tsx` par :

```tsx
// src/app/projet/page.tsx
import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { projectDoneCount, watermarkUrl, type ReqStatus } from "@/lib/studio/bat";
import { BatPanel } from "@/components/projet/BatPanel";

export const dynamic = "force-dynamic";
export const metadata = { title: "Mon projet — MyLab Studio" };

const STEPS = [
  { key: "commande", label: "Commande reçue" },
  { key: "etiquette", label: "Création de votre étiquette" },
  { key: "onboarding", label: "Préparation de votre site" },
  { key: "livraison", label: "Votre site en ligne" },
] as const;

const ETIQUETTE_HINT: Record<string, string> = {
  received: " — notre graphiste va prendre en charge votre demande",
  in_progress: " — notre graphiste travaille sur vos maquettes",
  bat_sent: " — un BAT vous attend ci-dessous !",
};

export default async function ProjetPage() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.email) redirect("/login?callbackUrl=/projet");

  const email = session.user.email.toLowerCase();
  const userId = session.user.id;

  await prisma.project.updateMany({ where: { email, userId: null }, data: { userId } });

  const projects = await prisma.project.findMany({
    where: { OR: [{ userId }, { email }] },
    include: {
      labelRequest: {
        include: {
          references: { orderBy: { title: "asc" } },
          batVersions: { orderBy: { version: "desc" }, take: 1 },
        },
      },
    },
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
          const request = project.labelRequest;
          const gamme = (project.gammeRefs ?? []) as { title: string; variantTitle: string | null; quantity: number }[];
          const doneCount = projectDoneCount(project.status, request?.status as ReqStatus | undefined);
          const latestBat = request?.batVersions[0];

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
                        <span className="sr-only">{state === "done" ? " (terminé)" : state === "current" ? " (en cours)" : " (à venir)"}</span>
                        {state === "current" && step.key === "etiquette" && request && (
                          <span className="text-neutral-500">{ETIQUETTE_HINT[request.status] ?? ""}</span>
                        )}
                      </span>
                    </li>
                  );
                })}
              </ol>

              {request && latestBat && request.status !== "validated" && (
                <BatPanel
                  requestId={request.id}
                  batVersion={latestBat.version}
                  batPreviewUrl={watermarkUrl(latestBat.previewUrl)}
                  batNote={latestBat.note}
                  references={request.references.map((r) => ({
                    id: r.id,
                    label: `${r.title}${r.variantTitle ? ` ${r.variantTitle}` : ""}`,
                    status: r.status,
                  }))}
                />
              )}

              {request?.status === "validated" && (
                <div className="mt-4 rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-800">
                  🎉 Votre gamme d’étiquettes est validée ! La préparation de votre site commence bientôt.
                </div>
              )}

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

- [ ] **Step 2: Panneau BAT (client)**

```tsx
// src/components/projet/BatPanel.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type Ref = { id: string; label: string; status: string };

export function BatPanel({ requestId, batVersion, batPreviewUrl, batNote, references }: {
  requestId: string; batVersion: number; batPreviewUrl: string; batNote: string | null; references: Ref[];
}) {
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [modif, setModif] = useState("");

  async function post(url: string, body?: object) {
    setLoading(url); setError(null);
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
      });
      if (!res.ok) { const data = await res.json(); throw new Error(data.error || "Une erreur est survenue"); }
      setModif("");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setLoading(null);
    }
  }

  const pending = references.filter((r) => r.status !== "validated");

  return (
    <div className="mt-6 rounded-xl border border-neutral-200 bg-neutral-50 p-5">
      <h3 className="font-medium">Votre BAT — version {batVersion}</h3>
      {batNote && <p className="mt-1 text-sm text-neutral-600">💬 {batNote}</p>}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={batPreviewUrl} alt={`Aperçu BAT version ${batVersion}`} className="mt-3 w-full rounded-lg border border-neutral-200" />

      {error && <div className="mt-3 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>}

      <ul className="mt-4 space-y-2">
        {references.map((r) => (
          <li key={r.id} className="flex items-center justify-between text-sm">
            <span className={r.status === "validated" ? "text-neutral-400 line-through" : ""}>
              {r.label}
              {r.status === "changes_requested" && <span className="ml-2 text-amber-600">(modifications demandées)</span>}
            </span>
            {r.status === "bat_sent" && (
              <button
                onClick={() => post(`/api/studio/references/${r.id}/validate`)}
                disabled={loading !== null}
                className="rounded-full border border-neutral-800 px-3 py-1 text-xs font-medium hover:bg-neutral-800 hover:text-white transition-colors"
              >
                ✓ Valider
              </button>
            )}
            {r.status === "validated" && <span className="text-emerald-600 text-xs">Validée ✓</span>}
          </li>
        ))}
      </ul>

      {pending.length > 1 && (
        <button
          onClick={() => post(`/api/studio/requests/${requestId}/validate-all`)}
          disabled={loading !== null}
          className="mt-4 w-full rounded-full bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-700 transition-colors"
        >
          Tout valider ({pending.length} références)
        </button>
      )}

      <details className="mt-4">
        <summary className="cursor-pointer text-sm text-neutral-600">Demander une modification…</summary>
        <div className="mt-2 space-y-2">
          <textarea
            className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm min-h-[80px]"
            value={modif}
            onChange={(e) => setModif(e.target.value)}
            placeholder="Décrivez la modification souhaitée (ex. : agrandir le logo sur le shampoing 500ml)…"
          />
          <button
            onClick={() => post(`/api/studio/requests/${requestId}/comments`, { body: modif, requestChanges: true })}
            disabled={loading !== null || !modif.trim()}
            className="rounded-full border border-neutral-800 px-4 py-2 text-sm font-medium hover:bg-neutral-800 hover:text-white transition-colors disabled:opacity-40"
          >
            Envoyer la demande
          </button>
        </div>
      </details>
    </div>
  );
}
```

- [ ] **Step 3: Vérifier**

Run: `npx tsc --noEmit && npm run lint && npm test`
Expected: 0 erreur, suite verte.

- [ ] **Step 4: Commit**

```bash
git add src/app/projet/page.tsx src/components/projet/BatPanel.tsx
git commit -m "feat(studio): /projet — panneau BAT (apercu filigrane, validation par reference, tout valider, demande de modification)"
```

---

### Task 9: Config, migration prod, test de bout en bout

**Files:**
- Modify: `.env.example`

**Interfaces:**
- Consumes: tout ce qui précède, mergé ; `.env.vercel-prod` (présent localement, gitignoré) pour `DATABASE_URL`/`DIRECT_URL` ; secret webhook déjà en place (Lot 1).
- Produces: migration appliquée en prod, env posée, chaîne complète vérifiée puis nettoyée.

- [ ] **Step 1: Documenter l'env**

Ajouter à `.env.example` sous le bloc Studio existant : `STUDIO_GRAPHISTE_EMAIL=   # notifications "modifications demandées" (défaut : yoann@mylab-shop.com)`

Commit : `git add .env.example && git commit -m "chore(studio): env STUDIO_GRAPHISTE_EMAIL (Lot 2)"`

- [ ] **Step 2: Merge + déploiement (après revue finale de branche)**

```bash
git checkout main && git pull origin main
git merge --no-ff feat/studio-v3-lot2-bat -m "Merge feat/studio-v3-lot2-bat : Studio V3 Lot 2 (workflow BAT)"
npx tsc --noEmit && npm test   # filet post-merge
git push origin main            # déclenche le deploy Vercel
```

- [ ] **Step 3: Migration prod**

```powershell
# charge DATABASE_URL/DIRECT_URL depuis .env.vercel-prod dans le process courant, puis :
npx prisma migrate status   # doit lister UNIQUEMENT <timestamp>_add_bat_workflow en attente
npx prisma migrate deploy
```

Expected: `All migrations have been successfully applied.`

- [ ] **Step 4: (Optionnel) poser STUDIO_GRAPHISTE_EMAIL sur Vercel**

Si un graphiste dédié existe : `"<email>" | vercel env add STUDIO_GRAPHISTE_EMAIL production` (+ preview), sinon skip (fallback admin). Redeployer si posée.

- [ ] **Step 5: Test de bout en bout signé (même recette que le Lot 1)**

1. POST signé (HMAC avec le secret prod) d'une fausse commande `id: 999000222` contenant le dossier + 2 produits → 200 `{ projectId }`.
2. Vérifier en base : `Project` créé ET `LabelRequest` (status `received`) avec 2 `LabelReference` (status `pending`).
3. Rejouer le même POST → même `projectId`, toujours 1 seule `LabelRequest` (idempotence).
4. Via Prisma (script jetable) : simuler le cycle — créer une `BatVersion` v1 couvrant les 2 refs (statuts → `bat_sent`), valider 1 réf, vérifier `computeRequestStatus` en base (`bat_sent`), valider la 2e, vérifier demande `validated` + projet `label_validated`.
5. Nettoyage : supprimer les `LabelComment`/`BatVersion`/`LabelReference`/`LabelRequest`/`Project` du test (ordre inverse des FK).

Expected: chaque étape conforme ; consigner les sorties dans le rapport.

- [ ] **Step 6: Vérification visuelle (Yoann)**

`/admin/bat` : la file s'affiche ; fiche : upload d'un BAT réel sur un projet de test, réception de l'email client ; `/projet` côté client : aperçu filigrané visible, boutons Valider/Tout valider/Demander une modification fonctionnels ; emails « modifications demandées » et « gamme validée » reçus.

---

## Hors scope Lot 2 (assumé)

- **Fichiers Illustrator de production** : restent hors app (échanges internes graphiste↔Yoann) ; la fiche `/admin/bat` ne les stocke pas. À revisiter si un besoin réel émerge.
- **Création du compte graphiste** : passer `role = "graphiste"` sur son `User` à la main (`npx prisma studio` ou SQL) après sa première connexion magic link — pas d'UI de gestion des rôles dans ce lot.
- **Rate-limiting des routes BAT client** : les routes exigent une session propriétaire ; pas de rate-limit dédié (le pattern `form-rate-limit` du repo protège les routes anonymes).
- Onboarding (Lot 3), génération fal.ai (Lot 4 — conditionné au GO du spike), provisioning site (Lot 5).

## Critères de succès (spec §4.3)

- Une commande parcours payée fait apparaître la demande dans `/admin/bat` sans aucune action manuelle.
- Le graphiste envoie un BAT v1 → le client reçoit l'email, voit l'aperçu **filigrané**, valide référence par référence ou demande une modification (qui repasse la demande « En création » et notifie le graphiste).
- La validation de la dernière référence passe le projet en `label_validated`, notifie Yoann, et la timeline `/projet` affiche 2 jalons ✅.
- Un `graphiste` connecté n'accède qu'à `/admin/bat*` ; un client n'accède qu'à ses propres demandes.
