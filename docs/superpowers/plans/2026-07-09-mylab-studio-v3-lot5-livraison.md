# MY.LAB Studio V3 — Lot 5 : Livraison du site — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Après `pack_selected`, l'admin pilote la livraison du site client depuis `/admin/delivery` : saisie du dev store Shopify (provisionné semi-manuellement sur le compte Partner de Yoann), génération des textes IA (home + descriptions produits + suggestions de domaine) via l'API Claude avec revue/édition obligatoire, push des produits (prix onboarding, photos client) et des 4 pages légales FR pré-remplies vers le dev store, checklist de livraison (spec §4.6), puis « Marquer livré » → email client. Le client voit l'avancement sur `/projet`.

**Architecture:** Nouveau modèle `Delivery` (1-1 avec `Project`) + 2 statuts projet (`site_in_progress`, `delivered`). Libs pures TDD (`delivery.ts` : checklist + templates légaux ; `copy.ts` : prompt + schéma + validation ; `shopify-store.ts` : payloads Admin REST du dev store) + wrapper Claude (`claude.ts`, streaming + structured output). 4 routes API admin (CRUD delivery / génération copy / push / deliver). UI admin liste + fiche. Le provisioning du dev store lui-même reste manuel (Yoann crée le store + une custom app avec scopes `write_products`, `write_content`, et colle domaine + token dans la fiche).

**Tech Stack:** Next.js 16 App Router, React 19, TS strict, Prisma 7 (client généré `@/generated/prisma/client`), Supabase Postgres (RLS), `@anthropic-ai/sdk` (déjà en deps — `claude-opus-4-8`), Shopify Admin REST API (dev store client), Resend, vitest.

**Dépôt de travail :** `d:\Projets mylab vs code\mylab-configurateur` (branche `feat/studio-lot5-livraison` depuis `main`).

## Global Constraints

- Prisma : import UNIQUEMENT depuis `@/generated/prisma/client` via le singleton `@/lib/prisma` — JAMAIS `@prisma/client`.
- Migration sans DB locale : `git show HEAD:prisma/schema.prisma > prisma/_schema_before.prisma` puis `npx prisma migrate diff --from-schema prisma/_schema_before.prisma --to-schema prisma/schema.prisma --script` (Prisma 7 : PAS `--from-schema-datamodel`) ; migration.sql écrite à la main ensuite ; **chaque nouvelle table reçoit** : `ALTER TABLE "X" ENABLE ROW LEVEL SECURITY; CREATE POLICY "Service role only" ON "X" FOR ALL USING (auth.role() = 'service_role');` ; application UNIQUEMENT via `npx prisma migrate deploy` avec l'env de `.env.vercel-prod` (secrets — jamais affichés/commités).
- Pas de server actions. Pattern : page serveur (`prisma` direct, `export const dynamic = "force-dynamic"`, `params` async `Promise<{...}>`) → composant client (`fetch` + `router.refresh()`) → route API (guard en première ligne, `NextResponse.json`).
- Guards : `requireAdmin` depuis `@/lib/require-admin` (toutes les routes delivery sont admin-only — PAS `requireBatStaff`, le graphiste n'y a pas accès).
- Messages d'erreur et UI en français, apostrophes typographiques (U+2019 « ' ») dans les textes utilisateur.
- DA : tokens `--ml-*`, classes globales `.card`/`.btn-primary`/`.btn-secondary`/`.btn-sm`/`.kicker`/`.ml-dot`, valeurs arbitraires Tailwind `bg-[var(--ml-cream-2)]` (les utilitaires `mylab-*` du @theme ont d'autres valeurs — ne pas les utiliser pour la DA parcours). Pas d'emojis dans l'UI admin. Interdits : Cormorant, italique décoratif, or `#c5a467`.
- Lint `react-hooks/static-components` (error) : aucun sous-composant défini dans un corps de rendu — hoister au niveau module avec props.
- Tests : vitest colocalisés `*.test.ts`, `globals:false` (importer `describe/it/expect` depuis `"vitest"`), libs pures uniquement (pas de tests de routes).
- Emails : builders purs dans `notifications.ts` + envoi via `sendStudioEmail` (ne throw jamais) dans `after()` de `next/server`.
- API Claude : modèle **`claude-opus-4-8`** exactement, `thinking: { type: "adaptive" }`, streaming + `finalMessage()`, structured output via `output_config.format` (json_schema). Les textes générés ne sont JAMAIS exposés au client sans validation admin (`copyValidatedAt`).
- Token Admin API du dev store : write-only — le PUT l'accepte, aucun GET/JSON de réponse ne le renvoie (renvoyer `hasToken: boolean`), jamais loggé.
- `.filter(Boolean)`, claims atomiques `updateMany` count-gated pour toute transition de statut (pattern des routes pack).

---

### Task 1: Schéma Prisma — modèle Delivery + statuts `site_in_progress`/`delivered` + migration prod

**Files:**
- Modify: `prisma/schema.prisma`
- Create: `prisma/migrations/<timestamp>_lot5_delivery/migration.sql`

**Interfaces:**
- Consumes: modèles `Project`, enum `ProjectStatus` existants.
- Produces: modèle `Delivery` (champs ci-dessous) + valeurs d'enum `site_in_progress`, `delivered` — utilisés par toutes les tâches suivantes. Relation `Project.delivery Delivery?`.

- [ ] **Step 1: Éditer le schéma**

Dans `enum ProjectStatus`, ajouter après `pack_selected` :

```prisma
  site_in_progress // livraison en cours (Delivery créée) — Lot 5
  delivered        // site livré au client — Lot 5
```

Dans `model Project`, ajouter la relation (après `generationJobs`) :

```prisma
  delivery           Delivery?
```

En fin de fichier, ajouter :

```prisma
model Delivery {
  id              String    @id @default(cuid())
  projectId       String    @unique
  project         Project   @relation(fields: [projectId], references: [id])
  storeDomain     String? // ex. mylab-neroli.myshopify.com (dev store Partner)
  adminToken      String? // token Admin API custom app du dev store — write-only côté API
  copy            Json? // DeliveryCopy (lib copy.ts) — brouillon IA puis éditions admin
  copyValidatedAt DateTime? // revue Yoann des textes — requis avant push produits
  checklist       Json? // { [ChecklistKey]: boolean } (lib delivery.ts)
  pushLog         Json? // { products: [{referenceId, productId?, error?, at}], pages: [{key, pageId?, error?, at}] }
  visioAt         DateTime? // visio de livraison planifiée
  deliveredAt     DateTime?
  createdAt       DateTime  @default(now())
  updatedAt       DateTime  @updatedAt
}
```

- [ ] **Step 2: Générer le diff SQL**

```bash
git show HEAD:prisma/schema.prisma > prisma/_schema_before.prisma
npx prisma migrate diff --from-schema prisma/_schema_before.prisma --to-schema prisma/schema.prisma --script
rm prisma/_schema_before.prisma
```

- [ ] **Step 3: Écrire la migration à la main**

Créer `prisma/migrations/<timestamp>_lot5_delivery/migration.sql` (timestamp format `YYYYMMDDHHMMSS`) à partir du diff, complétée par le bloc RLS :

```sql
-- Lot 5 : livraison du site
ALTER TYPE "ProjectStatus" ADD VALUE 'site_in_progress';
ALTER TYPE "ProjectStatus" ADD VALUE 'delivered';

CREATE TABLE "Delivery" (
    "id" TEXT NOT NULL,
    "projectId" TEXT NOT NULL,
    "storeDomain" TEXT,
    "adminToken" TEXT,
    "copy" JSONB,
    "copyValidatedAt" TIMESTAMP(3),
    "checklist" JSONB,
    "pushLog" JSONB,
    "visioAt" TIMESTAMP(3),
    "deliveredAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Delivery_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "Delivery_projectId_key" ON "Delivery"("projectId");

ALTER TABLE "Delivery" ADD CONSTRAINT "Delivery_projectId_fkey" FOREIGN KEY ("projectId") REFERENCES "Project"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- Invariant Supabase : RLS service-role only sur toute nouvelle table
ALTER TABLE "Delivery" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON "Delivery" FOR ALL USING (auth.role() = 'service_role');
```

Note : les `ALTER TYPE ... ADD VALUE` sont sûrs dans la même migration tant qu'aucune ligne n'utilise les nouvelles valeurs dans la même transaction (c'est le cas : migration purement additive).

- [ ] **Step 4: Régénérer le client + vérifier**

```bash
npx prisma generate
npx tsc --noEmit
```
Expected: 0 erreur.

- [ ] **Step 5: Appliquer en prod**

```bash
bash -c 'set -a; source .env.vercel-prod; set +a; npx prisma migrate deploy'
```
Expected: `1 migration applied` (additive — aucun code déployé ne référence encore ces colonnes, sans risque).

- [ ] **Step 6: Commit**

```bash
git add prisma/schema.prisma prisma/migrations
git commit -m "feat(studio): modele Delivery + statuts site_in_progress/delivered (lot 5)"
```

---

### Task 2: Lib `delivery.ts` — checklist, domaine store, garde de livraison, pages légales FR (TDD)

**Files:**
- Create: `src/lib/studio/delivery.ts`
- Test: `src/lib/studio/delivery.test.ts`

**Interfaces:**
- Consumes: `escapeHtml` exporté par `@/lib/studio/notifications` ; type `Infos` exporté par `@/lib/studio/onboarding`.
- Produces (consommés par Tasks 5-6) :
  - `CHECKLIST_ITEMS: readonly { key: string; label: string }[]` et `type ChecklistKey`
  - `checklistComplete(checklist: unknown): boolean`
  - `normalizeStoreDomain(input: string): string | null`
  - `canDeliver(status: string, checklist: unknown): boolean`
  - `type LegalPage = { key: string; title: string; bodyHtml: string }`
  - `buildLegalPages(p: { societe: Infos["societe"]; brandName: string; siteUrl: string }): LegalPage[]` (4 pages)

- [ ] **Step 1: Écrire les tests qui échouent**

`src/lib/studio/delivery.test.ts` :

```ts
import { describe, it, expect } from "vitest";
import {
  CHECKLIST_ITEMS,
  checklistComplete,
  normalizeStoreDomain,
  canDeliver,
  buildLegalPages,
} from "./delivery";

const societe = {
  raisonSociale: "Néroli & Co",
  formeJuridique: "SASU",
  siret: "12345678901234",
  adresse: "12 rue des Fleurs",
  codePostal: "75011",
  ville: "Paris",
  email: "contact@neroli.fr",
  telephone: "0612345678",
};

describe("normalizeStoreDomain", () => {
  it("accepte un domaine myshopify nu", () => {
    expect(normalizeStoreDomain("mylab-neroli.myshopify.com")).toBe("mylab-neroli.myshopify.com");
  });
  it("nettoie protocole, casse, slash et chemin", () => {
    expect(normalizeStoreDomain("https://MyLab-Neroli.myshopify.com/admin")).toBe("mylab-neroli.myshopify.com");
  });
  it("rejette un domaine non myshopify", () => {
    expect(normalizeStoreDomain("neroli.fr")).toBeNull();
    expect(normalizeStoreDomain("")).toBeNull();
  });
});

describe("checklistComplete / canDeliver", () => {
  const full = Object.fromEntries(CHECKLIST_ITEMS.map((i) => [i.key, true]));
  it("complete uniquement si toutes les cases sont vraies", () => {
    expect(checklistComplete(full)).toBe(true);
    expect(checklistComplete({ ...full, theme: false })).toBe(false);
    expect(checklistComplete(null)).toBe(false);
    expect(checklistComplete({})).toBe(false);
  });
  it("canDeliver exige le statut site_in_progress ET la checklist complète", () => {
    expect(canDeliver("site_in_progress", full)).toBe(true);
    expect(canDeliver("pack_selected", full)).toBe(false);
    expect(canDeliver("site_in_progress", {})).toBe(false);
  });
});

describe("buildLegalPages", () => {
  const pages = buildLegalPages({ societe, brandName: "Néroli & Co", siteUrl: "https://mylab-neroli.myshopify.com" });
  it("produit les 4 pages dans l'ordre attendu", () => {
    expect(pages.map((p) => p.key)).toEqual([
      "mentions-legales",
      "cgv",
      "politique-de-confidentialite",
      "retours-et-remboursements",
    ]);
    for (const p of pages) {
      expect(p.title.length).toBeGreaterThan(0);
      expect(p.bodyHtml).toContain("<h2>");
    }
  });
  it("remplit les infos société", () => {
    const mentions = pages[0].bodyHtml;
    expect(mentions).toContain("Néroli &amp; Co");
    expect(mentions).toContain("12345678901234");
    expect(mentions).toContain("75011 Paris");
  });
  it("échappe le HTML des données société", () => {
    const evil = buildLegalPages({
      societe: { ...societe, raisonSociale: "<script>x</script>" },
      brandName: "M",
      siteUrl: "https://x.myshopify.com",
    });
    expect(evil[0].bodyHtml).not.toContain("<script>");
    expect(evil[0].bodyHtml).toContain("&lt;script&gt;");
  });
});
```

- [ ] **Step 2: Lancer les tests — vérifier l'échec**

Run: `npx vitest run src/lib/studio/delivery.test.ts`
Expected: FAIL (module inexistant).

- [ ] **Step 3: Implémenter `src/lib/studio/delivery.ts`**

```ts
import { escapeHtml } from "@/lib/studio/notifications";
import type { Infos } from "@/lib/studio/onboarding";

// Checklist du site livré — spec V3 §4.6
export const CHECKLIST_ITEMS = [
  { key: "theme", label: "Thème configuré (Brand DNA : couleurs, typos, logo)" },
  { key: "home", label: "Home complète (hero, histoire de marque, gamme, réassurance)" },
  { key: "products", label: "Boutique prête (produits, prix, descriptions, photos)" },
  { key: "legal", label: "Pages légales FR (mentions légales, CGV, confidentialité, retours)" },
  { key: "shipping", label: "Zones et tarifs de livraison configurés" },
  { key: "emails", label: "Emails transactionnels aux couleurs de la marque" },
  { key: "domain", label: "Domaine branché (ou branchement acté avec le client)" },
] as const;

export type ChecklistKey = (typeof CHECKLIST_ITEMS)[number]["key"];

export function checklistComplete(checklist: unknown): boolean {
  if (!checklist || typeof checklist !== "object") return false;
  const c = checklist as Record<string, unknown>;
  return CHECKLIST_ITEMS.every((i) => c[i.key] === true);
}

export function canDeliver(status: string, checklist: unknown): boolean {
  return status === "site_in_progress" && checklistComplete(checklist);
}

// Accepte "x.myshopify.com", "https://x.myshopify.com/admin", etc. → domaine nu ou null.
export function normalizeStoreDomain(input: string): string | null {
  const cleaned = input
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .split("/")[0];
  return /^[a-z0-9][a-z0-9-]*\.myshopify\.com$/.test(cleaned) ? cleaned : null;
}

export type Societe = Infos["societe"];
export type LegalPage = { key: string; title: string; bodyHtml: string };

// Templates légaux FR pré-remplis (base e-commerce cosmétiques) — relus/ajustés par l'admin
// dans le dev store avant transfer. Toute donnée société est échappée.
export function buildLegalPages(p: { societe: Societe; brandName: string; siteUrl: string }): LegalPage[] {
  const e = escapeHtml;
  const s = p.societe;
  const marque = e(p.brandName);
  const identite = `${e(s.raisonSociale)} (${e(s.formeJuridique)}), SIRET ${e(s.siret)}, ${e(s.adresse)}, ${e(s.codePostal)} ${e(s.ville)}`;
  const contact = `${e(s.email)}${s.telephone ? ` — ${e(s.telephone)}` : ""}`;
  const site = e(p.siteUrl);

  const mentionsLegales: LegalPage = {
    key: "mentions-legales",
    title: "Mentions légales",
    bodyHtml: [
      `<h2>Éditeur du site</h2><p>Le site ${site} est édité par ${identite}.</p>`,
      `<p>Contact : ${contact}.</p>`,
      `<h2>Hébergement</h2><p>Le site est hébergé par Shopify International Ltd., Victoria Buildings, 2nd Floor, 1-2 Haddington Road, Dublin 4, D04 XN32, Irlande — www.shopify.com.</p>`,
      `<h2>Propriété intellectuelle</h2><p>L'ensemble des contenus du site (textes, visuels, logos, marque ${marque}) est la propriété exclusive de ${e(s.raisonSociale)} ou de ses partenaires. Toute reproduction sans autorisation préalable est interdite.</p>`,
    ].join("\n"),
  };

  const cgv: LegalPage = {
    key: "cgv",
    title: "Conditions générales de vente",
    bodyHtml: [
      `<h2>Article 1 — Objet</h2><p>Les présentes conditions régissent les ventes de produits cosmétiques de la marque ${marque} conclues sur le site ${site} entre ${identite} (le « Vendeur ») et tout consommateur (le « Client »).</p>`,
      `<h2>Article 2 — Prix</h2><p>Les prix sont indiqués en euros, toutes taxes comprises, hors frais de livraison. Le Vendeur se réserve le droit de modifier ses prix à tout moment ; les produits sont facturés au tarif en vigueur au moment de la commande.</p>`,
      `<h2>Article 3 — Commande et paiement</h2><p>La commande est validée après acceptation du paiement. Le paiement s'effectue en ligne par carte bancaire via une solution de paiement sécurisée. La commande est confirmée par email.</p>`,
      `<h2>Article 4 — Livraison</h2><p>Les produits sont livrés à l'adresse indiquée lors de la commande, dans les délais précisés à la validation du panier. En cas de retard, le Client peut contacter le Vendeur à ${e(s.email)}.</p>`,
      `<h2>Article 5 — Droit de rétractation</h2><p>Conformément aux articles L.221-18 et suivants du Code de la consommation, le Client dispose de 14 jours à compter de la réception pour exercer son droit de rétractation, sans motif. Par exception (article L.221-28 5°), les produits descellés après la livraison ne pouvant être renvoyés pour des raisons d'hygiène ne peuvent faire l'objet d'une rétractation.</p>`,
      `<h2>Article 6 — Garanties légales</h2><p>Les produits bénéficient de la garantie légale de conformité (articles L.217-3 et suivants du Code de la consommation) et de la garantie contre les vices cachés (articles 1641 et suivants du Code civil).</p>`,
      `<h2>Article 7 — Données personnelles</h2><p>Les données du Client sont traitées conformément à la Politique de confidentialité disponible sur le site.</p>`,
      `<h2>Article 8 — Litiges et médiation</h2><p>Les présentes conditions sont soumises au droit français. Conformément aux articles L.612-1 et suivants du Code de la consommation, le Client peut recourir gratuitement à un médiateur de la consommation. À défaut de résolution amiable, les tribunaux français sont compétents.</p>`,
    ].join("\n"),
  };

  const confidentialite: LegalPage = {
    key: "politique-de-confidentialite",
    title: "Politique de confidentialité",
    bodyHtml: [
      `<h2>Responsable de traitement</h2><p>${identite}. Contact : ${contact}.</p>`,
      `<h2>Données collectées</h2><p>Dans le cadre des commandes et de la gestion du compte client : identité, coordonnées, adresse de livraison, historique d'achats et données de paiement (traitées par le prestataire de paiement, jamais stockées par le Vendeur).</p>`,
      `<h2>Finalités</h2><p>Traitement des commandes, livraison, facturation, service client, et, avec consentement, communications commerciales.</p>`,
      `<h2>Sous-traitants</h2><p>Le site est opéré via la plateforme Shopify ; les données y sont hébergées et traitées conformément à sa politique de confidentialité.</p>`,
      `<h2>Durées de conservation</h2><p>Les données clients sont conservées pendant la durée de la relation commerciale, augmentée des durées de prescription légales.</p>`,
      `<h2>Vos droits</h2><p>Conformément au RGPD, vous disposez de droits d'accès, de rectification, d'effacement, d'opposition, de limitation et de portabilité. Exercez-les en écrivant à ${e(s.email)}. Vous pouvez introduire une réclamation auprès de la CNIL (www.cnil.fr).</p>`,
    ].join("\n"),
  };

  const retours: LegalPage = {
    key: "retours-et-remboursements",
    title: "Retours et remboursements",
    bodyHtml: [
      `<h2>Droit de rétractation</h2><p>Vous disposez de 14 jours à compter de la réception de votre commande pour changer d'avis, sans justification.</p>`,
      `<h2>Produits concernés</h2><p>Pour des raisons d'hygiène, seuls les produits non descellés et dans leur emballage d'origine peuvent être retournés (article L.221-28 5° du Code de la consommation).</p>`,
      `<h2>Procédure</h2><p>Écrivez-nous à ${e(s.email)} en précisant votre numéro de commande. Nous vous indiquerons l'adresse de retour. Les frais de retour restent à votre charge.</p>`,
      `<h2>Remboursement</h2><p>Le remboursement intervient dans les 14 jours suivant la réception du retour, via le moyen de paiement utilisé pour la commande.</p>`,
    ].join("\n"),
  };

  return [mentionsLegales, cgv, confidentialite, retours];
}
```

- [ ] **Step 4: Lancer les tests — vérifier le succès**

Run: `npx vitest run src/lib/studio/delivery.test.ts`
Expected: PASS (tous les tests).

- [ ] **Step 5: Vérifier tsc + lint, commit**

```bash
npx tsc --noEmit && npx eslint src/lib/studio/delivery.ts src/lib/studio/delivery.test.ts
git add src/lib/studio/delivery.ts src/lib/studio/delivery.test.ts
git commit -m "feat(studio): lib delivery — checklist, domaine store, pages legales FR (lot 5)"
```

---

### Task 3: Lib `copy.ts` (prompt + schéma + validation, TDD) + wrapper Claude `claude.ts`

**Files:**
- Create: `src/lib/studio/copy.ts`
- Create: `src/lib/studio/claude.ts`
- Test: `src/lib/studio/copy.test.ts`

**Interfaces:**
- Consumes: types `BrandDna`, `Infos` de `@/lib/studio/onboarding`.
- Produces (consommés par Tasks 5-6) :
  - `type DeliveryCopy = { hero: { title; subtitle; cta }; histoire: { title; body }; gamme: { title; intro }; reassurance: { items: { title; text }[] }; produits: { referenceId; title; description }[]; domaines: string[] }` (tous champs `string`)
  - `COPY_SCHEMA: Record<string, unknown>` (JSON Schema strict)
  - `buildCopyPrompt(p: { brandName: string; brandDna: BrandDna; histoire: Infos["histoire"]; references: { id: string; title: string; variantTitle: string | null }[]; domaineMode: "existant" | "achat" | "conseil"; domaineValeur: string }): string`
  - `validateCopy(raw: unknown, referenceIds: string[]): DeliveryCopy` (throw `Error` message français si couverture produits incomplète ou shape invalide)
  - `claude.ts` : `generateCopyRaw(prompt: string): Promise<unknown>` (appel API — non testé unitairement)

- [ ] **Step 1: Mettre à jour le SDK Anthropic**

```bash
npm install @anthropic-ai/sdk@latest
```
(0.91.1 peut ne pas typer `output_config` ; la dernière version le supporte.)

- [ ] **Step 2: Écrire les tests qui échouent**

`src/lib/studio/copy.test.ts` :

```ts
import { describe, it, expect } from "vitest";
import { buildCopyPrompt, validateCopy, COPY_SCHEMA, type DeliveryCopy } from "./copy";

const brandDna = { palette: ["#aabbcc", "#112233", "#ffffff"], ambiance: "botanique", ton: "chaleureux", style: "épuré", univers: "slow cosmétique", cible: "femmes 25-45" };
const histoire = { pourquoi: "Des soins simples", pourQui: "Peaux sensibles", promesse: "Le naturel qui tient ses promesses" };
const references = [
  { id: "ref1", title: "Shampoing nourrissant", variantTitle: "200ml" },
  { id: "ref2", title: "Baume corps", variantTitle: null },
];

function validCopy(): DeliveryCopy {
  return {
    hero: { title: "T", subtitle: "S", cta: "Découvrir" },
    histoire: { title: "Notre histoire", body: "B" },
    gamme: { title: "La gamme", intro: "I" },
    reassurance: { items: [{ title: "a", text: "x" }, { title: "b", text: "y" }, { title: "c", text: "z" }] },
    produits: [
      { referenceId: "ref1", title: "P1", description: "D1" },
      { referenceId: "ref2", title: "P2", description: "D2" },
    ],
    domaines: [],
  };
}

describe("buildCopyPrompt", () => {
  const prompt = buildCopyPrompt({ brandName: "Néroli & Co", brandDna, histoire, references, domaineMode: "conseil", domaineValeur: "" });
  it("contient la marque, le brand DNA et chaque référence avec son id", () => {
    expect(prompt).toContain("Néroli & Co");
    expect(prompt).toContain("chaleureux");
    expect(prompt).toContain("ref1");
    expect(prompt).toContain("Shampoing nourrissant");
    expect(prompt).toContain("ref2");
  });
  it("demande des suggestions de domaine uniquement en mode conseil", () => {
    expect(prompt).toContain("suggestions de nom de domaine");
    const sans = buildCopyPrompt({ brandName: "M", brandDna, histoire, references, domaineMode: "existant", domaineValeur: "neroli.fr" });
    expect(sans).toContain("tableau vide");
  });
});

describe("validateCopy", () => {
  it("accepte une copy valide", () => {
    expect(validateCopy(validCopy(), ["ref1", "ref2"])).toBeTruthy();
  });
  it("rejette si une référence n'a pas de texte produit", () => {
    const c = validCopy();
    c.produits = c.produits.slice(0, 1);
    expect(() => validateCopy(c, ["ref1", "ref2"])).toThrow(/référence/i);
  });
  it("rejette une shape invalide", () => {
    expect(() => validateCopy(null, ["ref1"])).toThrow();
    expect(() => validateCopy({ hero: {} }, ["ref1"])).toThrow();
  });
});

describe("COPY_SCHEMA", () => {
  it("est strict (additionalProperties false à la racine)", () => {
    expect((COPY_SCHEMA as { additionalProperties?: boolean }).additionalProperties).toBe(false);
  });
});
```

- [ ] **Step 3: Lancer les tests — vérifier l'échec**

Run: `npx vitest run src/lib/studio/copy.test.ts`
Expected: FAIL (module inexistant).

- [ ] **Step 4: Implémenter `src/lib/studio/copy.ts`**

```ts
import type { BrandDna, Infos } from "@/lib/studio/onboarding";

export type DeliveryCopy = {
  hero: { title: string; subtitle: string; cta: string };
  histoire: { title: string; body: string };
  gamme: { title: string; intro: string };
  reassurance: { items: { title: string; text: string }[] };
  produits: { referenceId: string; title: string; description: string }[];
  domaines: string[];
};

const str = { type: "string" } as const;

export const COPY_SCHEMA: Record<string, unknown> = {
  type: "object",
  additionalProperties: false,
  required: ["hero", "histoire", "gamme", "reassurance", "produits", "domaines"],
  properties: {
    hero: {
      type: "object",
      additionalProperties: false,
      required: ["title", "subtitle", "cta"],
      properties: { title: str, subtitle: str, cta: str },
    },
    histoire: {
      type: "object",
      additionalProperties: false,
      required: ["title", "body"],
      properties: { title: str, body: str },
    },
    gamme: {
      type: "object",
      additionalProperties: false,
      required: ["title", "intro"],
      properties: { title: str, intro: str },
    },
    reassurance: {
      type: "object",
      additionalProperties: false,
      required: ["items"],
      properties: {
        items: {
          type: "array",
          items: {
            type: "object",
            additionalProperties: false,
            required: ["title", "text"],
            properties: { title: str, text: str },
          },
        },
      },
    },
    produits: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["referenceId", "title", "description"],
        properties: { referenceId: str, title: str, description: str },
      },
    },
    domaines: { type: "array", items: str },
  },
};

export function buildCopyPrompt(p: {
  brandName: string;
  brandDna: BrandDna;
  histoire: Infos["histoire"];
  references: { id: string; title: string; variantTitle: string | null }[];
  domaineMode: "existant" | "achat" | "conseil";
  domaineValeur: string;
}): string {
  const d = p.brandDna;
  const refs = p.references
    .map((r) => `- referenceId "${r.id}" : ${r.title}${r.variantTitle ? ` ${r.variantTitle}` : ""}`)
    .join("\n");
  const domaines =
    p.domaineMode === "conseil"
      ? "domaines : 5 suggestions de nom de domaine disponibles-plausibles en .com ou .fr, en minuscules, sans accents ni espaces (ex. \"neroli-cosmetiques.fr\")."
      : `domaines : tableau vide [] (le client a déjà son domaine${p.domaineValeur ? ` : ${p.domaineValeur}` : ""}).`;

  return `Tu écris les textes d'une boutique en ligne Shopify pour une marque française de cosmétiques.

Marque : ${p.brandName}
Ambiance : ${d.ambiance} · Ton : ${d.ton} · Style : ${d.style} · Univers : ${d.univers} · Cible : ${d.cible}
Histoire de la marque — pourquoi : ${p.histoire.pourquoi} · pour qui : ${p.histoire.pourQui} · promesse : ${p.histoire.promesse}

Gamme (références produits) :
${refs}

Produis un JSON conforme au schéma demandé :
- hero : title court et mémorable (8 mots max), subtitle une phrase qui reprend la promesse, cta un appel à l'action de 2 à 4 mots.
- histoire : title + body de 80 à 120 mots, à la première personne de la marque, fidèle au « pourquoi » ci-dessus.
- gamme : title + intro de 30 à 50 mots qui présente la collection.
- reassurance : exactement 3 items (title 2-4 mots + text une phrase) adaptés à cette marque (ex. fabrication française, formules douces, livraison suivie).
- produits : une entrée pour CHAQUE référence listée ci-dessus, en recopiant exactement son referenceId ; title commercial court ; description de 60 à 100 mots orientée bénéfices et gestes d'utilisation.
- ${domaines}

Contraintes : écris en français, sans emojis, sans superlatifs creux. N'invente ni certification, ni composition INCI, ni chiffre précis. Ton : ${d.ton}.`;
}

export function validateCopy(raw: unknown, referenceIds: string[]): DeliveryCopy {
  if (!raw || typeof raw !== "object") throw new Error("Réponse IA invalide (objet attendu)");
  const c = raw as DeliveryCopy;
  const filled = (s: unknown): s is string => typeof s === "string" && s.trim().length > 0;
  if (!c.hero || !filled(c.hero.title) || !filled(c.hero.subtitle) || !filled(c.hero.cta))
    throw new Error("Réponse IA invalide (hero incomplet)");
  if (!c.histoire || !filled(c.histoire.title) || !filled(c.histoire.body))
    throw new Error("Réponse IA invalide (histoire incomplète)");
  if (!c.gamme || !filled(c.gamme.title) || !filled(c.gamme.intro))
    throw new Error("Réponse IA invalide (gamme incomplète)");
  const items = c.reassurance?.items;
  if (!Array.isArray(items) || items.length < 3 || !items.every((i) => filled(i?.title) && filled(i?.text)))
    throw new Error("Réponse IA invalide (réassurance : 3 items requis)");
  if (!Array.isArray(c.produits)) throw new Error("Réponse IA invalide (produits manquants)");
  for (const id of referenceIds) {
    const prod = c.produits.find((x) => x?.referenceId === id);
    if (!prod || !filled(prod.title) || !filled(prod.description))
      throw new Error(`Texte produit manquant pour la référence ${id}`);
  }
  if (!Array.isArray(c.domaines) || !c.domaines.every((x) => typeof x === "string"))
    throw new Error("Réponse IA invalide (domaines)");
  return c;
}
```

- [ ] **Step 5: Lancer les tests — vérifier le succès**

Run: `npx vitest run src/lib/studio/copy.test.ts`
Expected: PASS.

- [ ] **Step 6: Implémenter `src/lib/studio/claude.ts`**

```ts
import Anthropic from "@anthropic-ai/sdk";
import { COPY_SCHEMA } from "@/lib/studio/copy";

// Génère les textes du site via l'API Claude (structured output).
// Streaming obligatoire : la génération peut durer plusieurs minutes.
export async function generateCopyRaw(prompt: string): Promise<unknown> {
  const client = new Anthropic(); // ANTHROPIC_API_KEY (déjà dans l'env Vercel prod)
  const stream = client.messages.stream({
    model: "claude-opus-4-8",
    max_tokens: 16000,
    thinking: { type: "adaptive" },
    output_config: { format: { type: "json_schema", schema: COPY_SCHEMA } },
    messages: [{ role: "user", content: prompt }],
  });
  const msg = await stream.finalMessage();
  if (msg.stop_reason === "refusal") throw new Error("Génération refusée par le modèle — réessayer");
  if (msg.stop_reason === "max_tokens") throw new Error("Réponse IA tronquée — réessayer");
  const text = msg.content.find((b) => b.type === "text");
  if (!text || text.type !== "text") throw new Error("Réponse IA vide");
  return JSON.parse(text.text);
}
```

Note implémenteur : si `output_config` n'est pas typé par la version installée du SDK, ne PAS caster en `any` global — utiliser le paramètre tel quel après upgrade (Step 1) ; en dernier recours `// @ts-expect-error output_config (SDK types en retard)` sur la seule ligne concernée.

- [ ] **Step 7: Vérifier tsc + lint, commit**

```bash
npx tsc --noEmit && npx eslint src/lib/studio/copy.ts src/lib/studio/copy.test.ts src/lib/studio/claude.ts
git add package.json package-lock.json src/lib/studio/copy.ts src/lib/studio/copy.test.ts src/lib/studio/claude.ts
git commit -m "feat(studio): lib copy — prompt/schema/validation + wrapper Claude opus 4.8 (lot 5)"
```

---

### Task 4: Lib `shopify-store.ts` — client Admin REST du dev store (payloads TDD)

**Files:**
- Create: `src/lib/studio/shopify-store.ts`
- Test: `src/lib/studio/shopify-store.test.ts`

**Interfaces:**
- Consumes: `type LegalPage` de `@/lib/studio/delivery`.
- Produces (consommés par Task 5) :
  - `buildProductPayload(p: { title: string; variantTitle: string | null; descriptionHtml: string; priceEur: number; sku: string | null; images: string[] }): Record<string, unknown>`
  - `buildPagePayload(p: LegalPage): Record<string, unknown>`
  - `type PushResult = { ok: boolean; id?: number; error?: string }`
  - `createProduct(domain: string, token: string, payload: Record<string, unknown>): Promise<PushResult>`
  - `createPage(domain: string, token: string, payload: Record<string, unknown>): Promise<PushResult>`

- [ ] **Step 1: Écrire les tests qui échouent**

`src/lib/studio/shopify-store.test.ts` :

```ts
import { describe, it, expect } from "vitest";
import { buildProductPayload, buildPagePayload } from "./shopify-store";

describe("buildProductPayload", () => {
  const payload = buildProductPayload({
    title: "Shampoing nourrissant",
    variantTitle: "200ml",
    descriptionHtml: "<p>Doux</p>",
    priceEur: 24.9,
    sku: "SH-200",
    images: ["https://res.cloudinary.com/x/a.jpg", "https://res.cloudinary.com/x/b.jpg"],
  }) as { product: Record<string, unknown> };

  it("compose le titre avec la variante et formate le prix à 2 décimales", () => {
    expect(payload.product.title).toBe("Shampoing nourrissant 200ml");
    const variants = payload.product.variants as { price: string; sku: string }[];
    expect(variants[0].price).toBe("24.90");
    expect(variants[0].sku).toBe("SH-200");
  });
  it("mappe les images en {src} et publie le produit", () => {
    expect(payload.product.images).toEqual([
      { src: "https://res.cloudinary.com/x/a.jpg" },
      { src: "https://res.cloudinary.com/x/b.jpg" },
    ]);
    expect(payload.product.status).toBe("active");
    expect(payload.product.body_html).toBe("<p>Doux</p>");
  });
  it("gère variante et sku absents", () => {
    const p = buildProductPayload({ title: "Baume", variantTitle: null, descriptionHtml: "", priceEur: 10, sku: null, images: [] }) as { product: Record<string, unknown> };
    expect(p.product.title).toBe("Baume");
    const variants = p.product.variants as { price: string; sku?: string }[];
    expect(variants[0].price).toBe("10.00");
    expect(variants[0].sku).toBeUndefined();
  });
});

describe("buildPagePayload", () => {
  it("mappe une LegalPage en page Shopify publiée avec handle", () => {
    const p = buildPagePayload({ key: "cgv", title: "Conditions générales de vente", bodyHtml: "<h2>Article 1</h2>" }) as { page: Record<string, unknown> };
    expect(p.page.title).toBe("Conditions générales de vente");
    expect(p.page.handle).toBe("cgv");
    expect(p.page.body_html).toBe("<h2>Article 1</h2>");
    expect(p.page.published).toBe(true);
  });
});
```

- [ ] **Step 2: Lancer les tests — vérifier l'échec**

Run: `npx vitest run src/lib/studio/shopify-store.test.ts`
Expected: FAIL.

- [ ] **Step 3: Implémenter `src/lib/studio/shopify-store.ts`**

```ts
import type { LegalPage } from "@/lib/studio/delivery";

// Client Admin REST minimal pour le DEV STORE CLIENT (≠ SHOPIFY_STORE_DOMAIN qui est
// la boutique MyLab). Domaine + token viennent de la fiche Delivery (custom app du
// dev store, scopes requis : write_products, write_content).
const API_VERSION = "2025-01";

export type PushResult = { ok: boolean; id?: number; error?: string };

export function buildProductPayload(p: {
  title: string;
  variantTitle: string | null;
  descriptionHtml: string;
  priceEur: number;
  sku: string | null;
  images: string[];
}): Record<string, unknown> {
  return {
    product: {
      title: `${p.title}${p.variantTitle ? ` ${p.variantTitle}` : ""}`,
      body_html: p.descriptionHtml,
      status: "active",
      variants: [
        {
          price: p.priceEur.toFixed(2),
          ...(p.sku ? { sku: p.sku } : {}),
          inventory_management: null,
        },
      ],
      images: p.images.map((src) => ({ src })),
    },
  };
}

export function buildPagePayload(p: LegalPage): Record<string, unknown> {
  return { page: { title: p.title, handle: p.key, body_html: p.bodyHtml, published: true } };
}

async function storePost(domain: string, token: string, path: string, body: Record<string, unknown>): Promise<{ status: number; json: unknown }> {
  const res = await fetch(`https://${domain}/admin/api/${API_VERSION}/${path}`, {
    method: "POST",
    headers: { "X-Shopify-Access-Token": token, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const json = await res.json().catch(() => null);
  return { status: res.status, json };
}

function extractError(status: number, json: unknown): string {
  const errors = (json as { errors?: unknown } | null)?.errors;
  const detail = errors ? (typeof errors === "string" ? errors : JSON.stringify(errors)) : "";
  return `HTTP ${status}${detail ? ` — ${detail}` : ""}`;
}

export async function createProduct(domain: string, token: string, payload: Record<string, unknown>): Promise<PushResult> {
  try {
    const { status, json } = await storePost(domain, token, "products.json", payload);
    const id = (json as { product?: { id?: number } } | null)?.product?.id;
    if (status === 201 && id) return { ok: true, id };
    return { ok: false, error: extractError(status, json) };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Erreur réseau" };
  }
}

export async function createPage(domain: string, token: string, payload: Record<string, unknown>): Promise<PushResult> {
  try {
    const { status, json } = await storePost(domain, token, "pages.json", payload);
    const id = (json as { page?: { id?: number } } | null)?.page?.id;
    if (status === 201 && id) return { ok: true, id };
    return { ok: false, error: extractError(status, json) };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Erreur réseau" };
  }
}
```

- [ ] **Step 4: Lancer les tests — vérifier le succès**

Run: `npx vitest run src/lib/studio/shopify-store.test.ts`
Expected: PASS.

- [ ] **Step 5: Vérifier tsc + lint, commit**

```bash
npx tsc --noEmit && npx eslint src/lib/studio/shopify-store.ts src/lib/studio/shopify-store.test.ts
git add src/lib/studio/shopify-store.ts src/lib/studio/shopify-store.test.ts
git commit -m "feat(studio): client Admin REST dev store — payloads produits/pages (lot 5)"
```

---

### Task 5: Routes API delivery — CRUD, génération copy, push, deliver + email livraison

**Files:**
- Modify: `src/lib/studio/notifications.ts` (ajouter `buildSiteDeliveredEmail`)
- Create: `src/app/api/studio/delivery/[projectId]/route.ts` (PUT — pas de GET : les pages serveur lisent Prisma directement et les composants font `router.refresh()`)
- Create: `src/app/api/studio/delivery/[projectId]/copy/route.ts` (POST)
- Create: `src/app/api/studio/delivery/[projectId]/push/route.ts` (POST)
- Create: `src/app/api/studio/delivery/[projectId]/deliver/route.ts` (POST)

**Interfaces:**
- Consumes: `requireAdmin` (`@/lib/require-admin`), libs Tasks 2-4, `generateCopyRaw` (Task 3), `sendStudioEmail`/`escapeHtml` (`notifications.ts`), types `Infos`/`PhotosEntry` (`onboarding.ts`).
- Produces:
  - GET → `{ project: {...}, delivery: { storeDomain, hasToken, copy, copyValidatedAt, checklist, pushLog, visioAt, deliveredAt } | null }` — **jamais `adminToken`**.
  - PUT body partiel `{ storeDomain?, adminToken?, checklist?, visioAt?, copy?, copyValidated? }` → upsert + flip `pack_selected → site_in_progress`.
  - POST copy → `{ copy }` (généré + sauvegardé, `copyValidatedAt` remis à null).
  - POST push body `{ target: "products" | "pages" }` → `{ results: [...] }`.
  - POST deliver → `{ status: "delivered" }` + email client.

- [ ] **Step 1: Ajouter le builder d'email dans `notifications.ts`**

Après `buildPackSelectedEmail`, ajouter :

```ts
export function buildSiteDeliveredEmail(p: { orderNumber: string; siteUrl: string | null }): StudioEmail {
  const subject = "Votre boutique en ligne est prête";
  const lien = p.siteUrl
    ? `<p><a href="${escapeHtml(p.siteUrl)}">Découvrir votre boutique</a></p>`
    : "";
  const html = `<p>Bonne nouvelle !</p>
<p>Votre site est en ligne : votre marque a désormais sa boutique. Nous venons de finaliser la livraison de votre commande n°${escapeHtml(p.orderNumber)}.</p>
${lien}
<p>Vous recevrez séparément les accès et les prochaines étapes vues ensemble en visio.</p>
<p>L'équipe MyLab</p>`;
  const text = `Bonne nouvelle ! Votre site est en ligne (commande n°${p.orderNumber}).${p.siteUrl ? ` Découvrez-le : ${p.siteUrl}` : ""} Vous recevrez séparément les accès et les prochaines étapes.`;
  return { subject, html, text };
}
```

- [ ] **Step 2: Route GET/PUT `src/app/api/studio/delivery/[projectId]/route.ts`**

```ts
import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { requireAdmin } from "@/lib/require-admin";
import { normalizeStoreDomain } from "@/lib/studio/delivery";
import { validateCopy } from "@/lib/studio/copy";
import type { Prisma } from "@/generated/prisma/client";

type Params = { params: Promise<{ projectId: string }> };

function serializeDelivery(d: {
  storeDomain: string | null;
  adminToken: string | null;
  copy: unknown;
  copyValidatedAt: Date | null;
  checklist: unknown;
  pushLog: unknown;
  visioAt: Date | null;
  deliveredAt: Date | null;
} | null) {
  if (!d) return null;
  return {
    storeDomain: d.storeDomain,
    hasToken: !!d.adminToken,
    copy: d.copy,
    copyValidatedAt: d.copyValidatedAt,
    checklist: d.checklist,
    pushLog: d.pushLog,
    visioAt: d.visioAt,
    deliveredAt: d.deliveredAt,
  };
}

export async function GET(_req: Request, { params }: Params) {
  const guard = await requireAdmin();
  if (guard) return guard;
  const { projectId } = await params;
  const project = await prisma.project.findUnique({ where: { id: projectId }, include: { delivery: true } });
  if (!project) return NextResponse.json({ error: "Projet introuvable" }, { status: 404 });
  return NextResponse.json({
    project: { id: project.id, status: project.status, email: project.email, brandName: project.brandName, orderNumber: project.shopifyOrderNumber },
    delivery: serializeDelivery(project.delivery),
  });
}

export async function PUT(req: Request, { params }: Params) {
  const guard = await requireAdmin();
  if (guard) return guard;
  const { projectId } = await params;

  const project = await prisma.project.findUnique({ where: { id: projectId }, include: { labelRequest: { include: { references: true } } } });
  if (!project) return NextResponse.json({ error: "Projet introuvable" }, { status: 404 });
  const allowed = ["pack_selected", "site_in_progress", "delivered"];
  if (!allowed.includes(project.status))
    return NextResponse.json({ error: "La livraison s'ouvre après la sélection du pack" }, { status: 409 });

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Corps JSON invalide" }, { status: 400 });
  }

  const data: Prisma.DeliveryUncheckedUpdateInput = {};
  if (typeof body.storeDomain === "string") {
    if (body.storeDomain.trim() === "") {
      data.storeDomain = null;
    } else {
      const domain = normalizeStoreDomain(body.storeDomain);
      if (!domain) return NextResponse.json({ error: "Domaine invalide — attendu : xxx.myshopify.com" }, { status: 400 });
      data.storeDomain = domain;
    }
  }
  if (typeof body.adminToken === "string" && body.adminToken.trim().length > 0) data.adminToken = body.adminToken.trim();
  if (body.checklist && typeof body.checklist === "object") data.checklist = body.checklist as Prisma.InputJsonValue;
  if (typeof body.visioAt === "string") {
    const d = new Date(body.visioAt);
    if (Number.isNaN(d.getTime())) return NextResponse.json({ error: "Date de visio invalide" }, { status: 400 });
    data.visioAt = d;
  }
  if (body.copy !== undefined) {
    const refIds = project.labelRequest?.references.map((r) => r.id) ?? [];
    try {
      data.copy = validateCopy(body.copy, refIds) as unknown as Prisma.InputJsonValue;
      data.copyValidatedAt = null; // toute édition invalide la validation
    } catch (e) {
      return NextResponse.json({ error: e instanceof Error ? e.message : "Textes invalides" }, { status: 400 });
    }
  }
  if (body.copyValidated === true) data.copyValidatedAt = new Date();

  const delivery = await prisma.delivery.upsert({
    where: { projectId },
    create: { projectId, ...(data as Prisma.DeliveryUncheckedCreateInput) },
    update: data,
  });

  await prisma.project.updateMany({ where: { id: projectId, status: "pack_selected" }, data: { status: "site_in_progress" } });

  return NextResponse.json({ delivery: serializeDelivery(delivery) });
}
```

Note : `body.copy` + `body.copyValidated: true` dans le même PUT → l'ordre des affectations fait que la validation gagne (édition puis validation immédiate est un geste volontaire de l'admin).

- [ ] **Step 3: Route POST `src/app/api/studio/delivery/[projectId]/copy/route.ts`**

```ts
import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { requireAdmin } from "@/lib/require-admin";
import { buildCopyPrompt, validateCopy } from "@/lib/studio/copy";
import { generateCopyRaw } from "@/lib/studio/claude";
import type { BrandDna, Infos } from "@/lib/studio/onboarding";
import type { Prisma } from "@/generated/prisma/client";

export const maxDuration = 300; // la génération opus peut durer plusieurs minutes

export async function POST(_req: Request, { params }: { params: Promise<{ projectId: string }> }) {
  const guard = await requireAdmin();
  if (guard) return guard;
  const { projectId } = await params;

  const project = await prisma.project.findUnique({
    where: { id: projectId },
    include: { onboarding: true, labelRequest: { include: { references: true } } },
  });
  if (!project) return NextResponse.json({ error: "Projet introuvable" }, { status: 404 });
  const onboarding = project.onboarding;
  if (!onboarding?.submittedAt || !onboarding.brandDna || !onboarding.infos)
    return NextResponse.json({ error: "Onboarding non soumis — impossible de générer les textes" }, { status: 409 });
  const references = project.labelRequest?.references ?? [];
  if (references.length === 0)
    return NextResponse.json({ error: "Aucune référence produit sur ce projet" }, { status: 409 });

  const infos = onboarding.infos as unknown as Infos;
  const prompt = buildCopyPrompt({
    brandName: project.brandName ?? infos.societe.raisonSociale,
    brandDna: onboarding.brandDna as unknown as BrandDna,
    histoire: infos.histoire,
    references: references.map((r) => ({ id: r.id, title: r.title, variantTitle: r.variantTitle })),
    domaineMode: infos.domaine.mode,
    domaineValeur: infos.domaine.valeur,
  });

  let copy;
  try {
    const raw = await generateCopyRaw(prompt);
    copy = validateCopy(raw, references.map((r) => r.id));
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "Échec de la génération" }, { status: 502 });
  }

  await prisma.delivery.upsert({
    where: { projectId },
    create: { projectId, copy: copy as unknown as Prisma.InputJsonValue },
    update: { copy: copy as unknown as Prisma.InputJsonValue, copyValidatedAt: null },
  });
  await prisma.project.updateMany({ where: { id: projectId, status: "pack_selected" }, data: { status: "site_in_progress" } });

  return NextResponse.json({ copy });
}
```

- [ ] **Step 4: Route POST `src/app/api/studio/delivery/[projectId]/push/route.ts`**

```ts
import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { requireAdmin } from "@/lib/require-admin";
import { buildLegalPages } from "@/lib/studio/delivery";
import type { DeliveryCopy } from "@/lib/studio/copy";
import { buildProductPayload, buildPagePayload, createProduct, createPage } from "@/lib/studio/shopify-store";
import type { Infos, PhotosEntry } from "@/lib/studio/onboarding";
import type { Prisma } from "@/generated/prisma/client";

export const maxDuration = 120;

type PushLog = {
  products?: { referenceId: string; productId?: number; error?: string; at: string }[];
  pages?: { key: string; pageId?: number; error?: string; at: string }[];
};

export async function POST(req: Request, { params }: { params: Promise<{ projectId: string }> }) {
  const guard = await requireAdmin();
  if (guard) return guard;
  const { projectId } = await params;

  let body: { target?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Corps JSON invalide" }, { status: 400 });
  }
  if (body.target !== "products" && body.target !== "pages")
    return NextResponse.json({ error: "target attendu : products ou pages" }, { status: 400 });

  const project = await prisma.project.findUnique({
    where: { id: projectId },
    include: { delivery: true, onboarding: true, labelRequest: { include: { references: true } } },
  });
  if (!project) return NextResponse.json({ error: "Projet introuvable" }, { status: 404 });
  const delivery = project.delivery;
  if (!delivery?.storeDomain || !delivery.adminToken)
    return NextResponse.json({ error: "Renseigner d'abord le domaine et le token du dev store" }, { status: 409 });
  const infos = project.onboarding?.infos as unknown as Infos | undefined;
  if (!infos) return NextResponse.json({ error: "Onboarding manquant" }, { status: 409 });

  const log = (delivery.pushLog ?? {}) as PushLog;
  const now = () => new Date().toISOString();

  if (body.target === "pages") {
    const pages = buildLegalPages({
      societe: infos.societe,
      brandName: project.brandName ?? infos.societe.raisonSociale,
      siteUrl: `https://${delivery.storeDomain}`,
    });
    const done = new Set((log.pages ?? []).filter((p) => p.pageId).map((p) => p.key));
    const results: NonNullable<PushLog["pages"]> = log.pages ?? [];
    for (const page of pages) {
      if (done.has(page.key)) continue;
      const r = await createPage(delivery.storeDomain, delivery.adminToken, buildPagePayload(page));
      results.push({ key: page.key, ...(r.ok ? { pageId: r.id } : { error: r.error }), at: now() });
    }
    const allOk = pages.every((p) => results.some((r) => r.key === p.key && r.pageId));
    const checklist = { ...((delivery.checklist ?? {}) as Record<string, boolean>), ...(allOk ? { legal: true } : {}) };
    await prisma.delivery.update({
      where: { projectId },
      data: { pushLog: { ...log, pages: results } as Prisma.InputJsonValue, checklist: checklist as Prisma.InputJsonValue },
    });
    return NextResponse.json({ results });
  }

  // target === "products"
  if (!delivery.copyValidatedAt)
    return NextResponse.json({ error: "Valider d'abord les textes (descriptions produits)" }, { status: 409 });
  const copy = delivery.copy as unknown as DeliveryCopy | null;
  if (!copy) return NextResponse.json({ error: "Générer d'abord les textes" }, { status: 409 });
  const references = project.labelRequest?.references ?? [];
  const photos = (project.onboarding?.photos ?? []) as unknown as PhotosEntry[];
  const done = new Set((log.products ?? []).filter((p) => p.productId).map((p) => p.referenceId));
  const results: NonNullable<PushLog["products"]> = log.products ?? [];

  for (const ref of references) {
    if (done.has(ref.id)) continue;
    const prix = infos.prix.find((x) => x.referenceId === ref.id)?.prixPublic;
    const texte = copy.produits.find((x) => x.referenceId === ref.id);
    if (!prix || !texte) {
      results.push({ referenceId: ref.id, error: "Prix ou texte manquant pour cette référence", at: now() });
      continue;
    }
    const images = photos.find((x) => x.referenceId === ref.id)?.urls ?? [];
    const payload = buildProductPayload({
      title: texte.title || ref.title,
      variantTitle: ref.variantTitle,
      descriptionHtml: `<p>${texte.description}</p>`,
      priceEur: prix,
      sku: ref.sku,
      images,
    });
    const r = await createProduct(delivery.storeDomain, delivery.adminToken, payload);
    results.push({ referenceId: ref.id, ...(r.ok ? { productId: r.id } : { error: r.error }), at: now() });
  }

  const allOk = references.every((ref) => results.some((r) => r.referenceId === ref.id && r.productId));
  const checklist = { ...((delivery.checklist ?? {}) as Record<string, boolean>), ...(allOk ? { products: true } : {}) };
  await prisma.delivery.update({
    where: { projectId },
    data: { pushLog: { ...log, products: results } as Prisma.InputJsonValue, checklist: checklist as Prisma.InputJsonValue },
  });
  return NextResponse.json({ results });
}
```

- [ ] **Step 5: Route POST `src/app/api/studio/delivery/[projectId]/deliver/route.ts`**

```ts
import { NextResponse } from "next/server";
import { after } from "next/server";
import { prisma } from "@/lib/prisma";
import { requireAdmin } from "@/lib/require-admin";
import { canDeliver } from "@/lib/studio/delivery";
import { buildSiteDeliveredEmail, sendStudioEmail } from "@/lib/studio/notifications";
import type { Infos } from "@/lib/studio/onboarding";

export async function POST(_req: Request, { params }: { params: Promise<{ projectId: string }> }) {
  const guard = await requireAdmin();
  if (guard) return guard;
  const { projectId } = await params;

  const project = await prisma.project.findUnique({
    where: { id: projectId },
    include: { delivery: true, onboarding: true },
  });
  if (!project) return NextResponse.json({ error: "Projet introuvable" }, { status: 404 });
  if (!project.delivery) return NextResponse.json({ error: "Fiche de livraison manquante" }, { status: 409 });
  if (!canDeliver(project.status, project.delivery.checklist))
    return NextResponse.json({ error: "Checklist incomplète — toutes les cases doivent être cochées" }, { status: 409 });

  const flipped = await prisma.project.updateMany({
    where: { id: projectId, status: "site_in_progress" },
    data: { status: "delivered" },
  });
  if (flipped.count === 0) return NextResponse.json({ error: "Le projet n'est plus en livraison" }, { status: 409 });
  await prisma.delivery.update({ where: { projectId }, data: { deliveredAt: new Date() } });

  const infos = project.onboarding?.infos as unknown as Infos | undefined;
  const domaineClient = infos?.domaine.mode !== "conseil" && infos?.domaine.valeur ? infos.domaine.valeur : null;
  const siteUrl = domaineClient
    ? `https://${domaineClient.replace(/^https?:\/\//, "")}`
    : project.delivery.storeDomain
      ? `https://${project.delivery.storeDomain}`
      : null;
  after(async () => {
    await sendStudioEmail(project.email, buildSiteDeliveredEmail({ orderNumber: project.shopifyOrderNumber ?? "—", siteUrl }));
  });
  return NextResponse.json({ status: "delivered" });
}
```

- [ ] **Step 6: Vérifier + commit**

```bash
npx tsc --noEmit && npx eslint src/app/api/studio/delivery src/lib/studio/notifications.ts && npx vitest run src/lib/studio
git add src/lib/studio/notifications.ts "src/app/api/studio/delivery"
git commit -m "feat(studio): routes API livraison — CRUD, copy IA, push dev store, deliver (lot 5)"
```

---

### Task 6: UI admin — liste `/admin/delivery` + fiche projet (store, textes, push, checklist)

**Files:**
- Modify: `src/components/admin/AdminSidebar.tsx` (lien « Livraisons »)
- Create: `src/app/admin/(dashboard)/delivery/page.tsx` (liste, serveur)
- Create: `src/app/admin/(dashboard)/delivery/[projectId]/page.tsx` (fiche, serveur)
- Create: `src/components/admin/delivery/DeliveryStoreForm.tsx` (client)
- Create: `src/components/admin/delivery/DeliveryCopyPanel.tsx` (client)
- Create: `src/components/admin/delivery/DeliveryPushPanel.tsx` (client)
- Create: `src/components/admin/delivery/DeliveryChecklist.tsx` (client)

**Interfaces:**
- Consumes: routes Task 5 (shapes exactes ci-dessus), `CHECKLIST_ITEMS`/`checklistComplete` (Task 2), `DeliveryCopy` (Task 3), DA globale (`.card`, `.kicker`, `.btn-primary`, `.btn-secondary`, `.btn-sm`, `.input`).
- Produces: pages admin fonctionnelles ; le graphiste ne voit pas le lien (filtre rôle existant : seuls les liens `/admin/bat` lui sont montrés — aucun changement nécessaire).

- [ ] **Step 1: Sidebar**

Dans `src/components/admin/AdminSidebar.tsx`, importer `Rocket` depuis `lucide-react` et insérer après la ligne « Packs visuels » :

```ts
  { href: "/admin/delivery", label: "Livraisons", icon: Rocket },
```

- [ ] **Step 2: Liste `src/app/admin/(dashboard)/delivery/page.tsx`**

Suivre le pattern de `/admin/bat` (table `hidden sm:table` + cartes `sm:hidden`) :

```tsx
import Link from "next/link";
import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

const STATUS_BADGE: Record<string, { label: string; cls: string }> = {
  pack_selected: { label: "À démarrer", cls: "bg-gray-100 text-gray-500" },
  site_in_progress: { label: "En cours", cls: "bg-amber-100 text-amber-700" },
  delivered: { label: "Livré", cls: "bg-emerald-100 text-emerald-700" },
};

export default async function DeliveryListPage() {
  const projects = await prisma.project.findMany({
    where: { status: { in: ["pack_selected", "site_in_progress", "delivered"] } },
    include: { delivery: { select: { storeDomain: true, deliveredAt: true } } },
    orderBy: { updatedAt: "desc" },
  });

  return (
    <div>
      <h1 className="text-lg sm:text-2xl font-medium mb-6">Livraisons</h1>
      {projects.length === 0 && <p className="text-sm text-[color:var(--ml-muted)]">Aucun projet prêt pour la livraison.</p>}

      <table className="hidden sm:table w-full text-sm card">
        <thead>
          <tr className="text-left">
            <th className="p-4 kicker">Commande</th>
            <th className="p-4 kicker">Marque</th>
            <th className="p-4 kicker">Dev store</th>
            <th className="p-4 kicker">Statut</th>
          </tr>
        </thead>
        <tbody>
          {projects.map((p) => {
            const b = STATUS_BADGE[p.status] ?? STATUS_BADGE.pack_selected;
            return (
              <tr key={p.id} className="border-t border-[color:var(--ml-line)]">
                <td className="p-4">
                  <Link href={`/admin/delivery/${p.id}`} className="font-medium underline-offset-2 hover:underline">
                    n°{p.shopifyOrderNumber}
                  </Link>
                  <div className="text-xs text-[color:var(--ml-muted)]">{p.email}</div>
                </td>
                <td className="p-4">{p.brandName ?? "—"}</td>
                <td className="p-4 break-all">{p.delivery?.storeDomain ?? "—"}</td>
                <td className="p-4"><span className={`rounded-full px-2.5 py-0.5 text-[11px] font-[family-name:var(--font-dm-mono)] ${b.cls}`}>{b.label}</span></td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <ul className="sm:hidden space-y-3">
        {projects.map((p) => {
          const b = STATUS_BADGE[p.status] ?? STATUS_BADGE.pack_selected;
          return (
            <li key={p.id} className="card p-4">
              <Link href={`/admin/delivery/${p.id}`} className="flex items-center justify-between gap-2">
                <span className="min-w-0">
                  <span className="block font-medium">n°{p.shopifyOrderNumber} · {p.brandName ?? "—"}</span>
                  <span className="block text-xs text-[color:var(--ml-muted)] break-all">{p.email}</span>
                </span>
                <span className={`whitespace-nowrap rounded-full px-2.5 py-0.5 text-[11px] font-[family-name:var(--font-dm-mono)] ${b.cls}`}>{b.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
```

- [ ] **Step 3: Fiche `src/app/admin/(dashboard)/delivery/[projectId]/page.tsx`**

```tsx
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { prisma } from "@/lib/prisma";
import type { DeliveryCopy } from "@/lib/studio/copy";
import { DeliveryStoreForm } from "@/components/admin/delivery/DeliveryStoreForm";
import { DeliveryCopyPanel } from "@/components/admin/delivery/DeliveryCopyPanel";
import { DeliveryPushPanel } from "@/components/admin/delivery/DeliveryPushPanel";
import { DeliveryChecklist } from "@/components/admin/delivery/DeliveryChecklist";

export const dynamic = "force-dynamic";

export default async function DeliveryDetailPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const project = await prisma.project.findUnique({
    where: { id: projectId },
    include: {
      delivery: true,
      onboarding: { select: { submittedAt: true } },
      labelRequest: { include: { references: { orderBy: { title: "asc" } } } },
    },
  });
  if (!project) notFound();
  if (!["pack_selected", "site_in_progress", "delivered"].includes(project.status)) notFound();

  const d = project.delivery;
  const references = project.labelRequest?.references.map((r) => ({
    id: r.id,
    label: `${r.title}${r.variantTitle ? ` ${r.variantTitle}` : ""}`,
  })) ?? [];

  return (
    <div>
      <Link href="/admin/delivery" className="inline-flex items-center gap-2 text-sm text-[color:var(--ml-muted)] hover:text-[color:var(--ml-ink)] mb-6">
        <ArrowLeft size={16} /> Toutes les livraisons
      </Link>
      <h1 className="text-lg sm:text-2xl font-medium mb-6 break-words">
        Livraison — n°{project.shopifyOrderNumber} · {project.brandName ?? project.email}
      </h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-8">
          <DeliveryStoreForm
            projectId={project.id}
            storeDomain={d?.storeDomain ?? null}
            hasToken={!!d?.adminToken}
          />
          <DeliveryCopyPanel
            projectId={project.id}
            copy={(d?.copy as unknown as DeliveryCopy | null) ?? null}
            copyValidatedAt={d?.copyValidatedAt?.toISOString() ?? null}
            references={references}
            canGenerate={!!project.onboarding?.submittedAt}
          />
        </div>
        <div className="space-y-8">
          <DeliveryPushPanel
            projectId={project.id}
            hasStore={!!d?.storeDomain && !!d?.adminToken}
            copyValidated={!!d?.copyValidatedAt}
            pushLog={(d?.pushLog as { products?: { referenceId: string; productId?: number; error?: string }[]; pages?: { key: string; pageId?: number; error?: string }[] } | null) ?? null}
            references={references}
          />
          <DeliveryChecklist
            projectId={project.id}
            status={project.status}
            checklist={(d?.checklist as Record<string, boolean> | null) ?? null}
            visioAt={d?.visioAt?.toISOString() ?? null}
            deliveredAt={d?.deliveredAt?.toISOString() ?? null}
          />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: `DeliveryStoreForm.tsx`**

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function DeliveryStoreForm(props: { projectId: string; storeDomain: string | null; hasToken: boolean }) {
  const router = useRouter();
  const [domain, setDomain] = useState(props.storeDomain ?? "");
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setBusy(true);
    setError(null);
    const body: Record<string, string> = { storeDomain: domain };
    if (token.trim()) body.adminToken = token.trim();
    const res = await fetch(`/api/studio/delivery/${props.projectId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setBusy(false);
    if (!res.ok) {
      const j = await res.json().catch(() => null);
      setError(j?.error ?? "Erreur lors de l'enregistrement");
      return;
    }
    setToken("");
    router.refresh();
  }

  return (
    <div className="card p-6">
      <h2 className="kicker mb-1">Dev store Shopify</h2>
      <p className="text-xs text-[color:var(--ml-muted)] mb-4">
        Créer le dev store sur le compte Partner, puis une custom app avec les scopes
        write_products et write_content, et coller le token ici.
      </p>
      <label className="block text-sm mb-1" htmlFor="store-domain">Domaine myshopify</label>
      <input id="store-domain" className="input w-full" placeholder="ma-marque.myshopify.com" value={domain} onChange={(e) => setDomain(e.target.value)} />
      <label className="block text-sm mb-1 mt-3" htmlFor="store-token">Token Admin API</label>
      <input
        id="store-token"
        className="input w-full"
        type="password"
        placeholder={props.hasToken ? "•••••••• (déjà enregistré — coller pour remplacer)" : "shpat_…"}
        value={token}
        onChange={(e) => setToken(e.target.value)}
      />
      {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
      <button type="button" className="btn-primary btn-sm mt-4" onClick={save} disabled={busy}>
        {busy ? "Enregistrement…" : "Enregistrer"}
      </button>
    </div>
  );
}
```

- [ ] **Step 5: `DeliveryCopyPanel.tsx`**

Panneau client : bouton « Générer les textes » (POST `/copy`, état d'attente explicite « Génération en cours — jusqu'à 2-3 minutes »), champs éditables pour chaque bloc, « Enregistrer les textes » (PUT `{copy}`), « Valider les textes » (PUT `{copyValidated:true}`) avec badge « Textes validés le … » si `copyValidatedAt`. Sous-composants hoistés au niveau module (lint `react-hooks/static-components`).

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { DeliveryCopy } from "@/lib/studio/copy";

type Ref = { id: string; label: string };

function Field(props: { label: string; value: string; onChange: (v: string) => void; multiline?: boolean }) {
  return (
    <label className="block text-sm">
      <span className="text-xs text-[color:var(--ml-muted)]">{props.label}</span>
      {props.multiline ? (
        <textarea className="input w-full mt-1 min-h-24" value={props.value} onChange={(e) => props.onChange(e.target.value)} />
      ) : (
        <input className="input w-full mt-1" value={props.value} onChange={(e) => props.onChange(e.target.value)} />
      )}
    </label>
  );
}

export function DeliveryCopyPanel(props: {
  projectId: string;
  copy: DeliveryCopy | null;
  copyValidatedAt: string | null;
  references: Ref[];
  canGenerate: boolean;
}) {
  const router = useRouter();
  const [copy, setCopy] = useState<DeliveryCopy | null>(props.copy);
  const [busy, setBusy] = useState<"generate" | "save" | "validate" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setBusy("generate");
    setError(null);
    const res = await fetch(`/api/studio/delivery/${props.projectId}/copy`, { method: "POST" });
    setBusy(null);
    const j = await res.json().catch(() => null);
    if (!res.ok) {
      setError(j?.error ?? "Échec de la génération");
      return;
    }
    setCopy(j.copy);
    router.refresh();
  }

  async function put(body: Record<string, unknown>, kind: "save" | "validate") {
    setBusy(kind);
    setError(null);
    const res = await fetch(`/api/studio/delivery/${props.projectId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setBusy(null);
    if (!res.ok) {
      const j = await res.json().catch(() => null);
      setError(j?.error ?? "Erreur");
      return;
    }
    router.refresh();
  }

  const set = (fn: (c: DeliveryCopy) => DeliveryCopy) => setCopy((c) => (c ? fn(structuredClone(c)) : c));

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between gap-2 flex-wrap mb-4">
        <h2 className="kicker">Textes du site (IA + revue)</h2>
        {props.copyValidatedAt && (
          <span className="rounded-full bg-emerald-100 text-emerald-700 px-2.5 py-0.5 text-[11px] font-[family-name:var(--font-dm-mono)]">
            Validés le {new Date(props.copyValidatedAt).toLocaleDateString("fr-FR")}
          </span>
        )}
      </div>

      <button type="button" className="btn-secondary btn-sm" onClick={generate} disabled={busy !== null || !props.canGenerate}>
        {busy === "generate" ? "Génération en cours — jusqu'à 2-3 minutes…" : copy ? "Régénérer les textes" : "Générer les textes"}
      </button>
      {!props.canGenerate && <p className="mt-2 text-xs text-[color:var(--ml-muted)]">Disponible après soumission de l'onboarding.</p>}
      {error && <p className="mt-2 text-sm text-red-700">{error}</p>}

      {copy && (
        <div className="mt-5 space-y-4">
          <Field label="Hero — titre" value={copy.hero.title} onChange={(v) => set((c) => ({ ...c, hero: { ...c.hero, title: v } }))} />
          <Field label="Hero — sous-titre" value={copy.hero.subtitle} onChange={(v) => set((c) => ({ ...c, hero: { ...c.hero, subtitle: v } }))} />
          <Field label="Hero — bouton" value={copy.hero.cta} onChange={(v) => set((c) => ({ ...c, hero: { ...c.hero, cta: v } }))} />
          <Field label="Histoire — titre" value={copy.histoire.title} onChange={(v) => set((c) => ({ ...c, histoire: { ...c.histoire, title: v } }))} />
          <Field label="Histoire — texte" multiline value={copy.histoire.body} onChange={(v) => set((c) => ({ ...c, histoire: { ...c.histoire, body: v } }))} />
          <Field label="Gamme — titre" value={copy.gamme.title} onChange={(v) => set((c) => ({ ...c, gamme: { ...c.gamme, title: v } }))} />
          <Field label="Gamme — intro" multiline value={copy.gamme.intro} onChange={(v) => set((c) => ({ ...c, gamme: { ...c.gamme, intro: v } }))} />

          {copy.reassurance.items.map((item, i) => (
            <div key={i} className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <Field label={`Réassurance ${i + 1} — titre`} value={item.title} onChange={(v) => set((c) => { c.reassurance.items[i].title = v; return c; })} />
              <Field label={`Réassurance ${i + 1} — texte`} value={item.text} onChange={(v) => set((c) => { c.reassurance.items[i].text = v; return c; })} />
            </div>
          ))}

          {props.references.map((ref) => {
            const idx = copy.produits.findIndex((p) => p.referenceId === ref.id);
            if (idx === -1) return null;
            return (
              <div key={ref.id} className="border-t border-[color:var(--ml-line)] pt-3">
                <p className="text-xs font-medium mb-2">{ref.label}</p>
                <Field label="Titre produit" value={copy.produits[idx].title} onChange={(v) => set((c) => { c.produits[idx].title = v; return c; })} />
                <Field label="Description" multiline value={copy.produits[idx].description} onChange={(v) => set((c) => { c.produits[idx].description = v; return c; })} />
              </div>
            );
          })}

          {copy.domaines.length > 0 && (
            <div className="border-t border-[color:var(--ml-line)] pt-3 text-sm">
              <span className="kicker">Suggestions de domaine</span>
              <p className="mt-1 text-[color:var(--ml-muted)]">{copy.domaines.join(" · ")}</p>
            </div>
          )}

          <div className="flex flex-wrap gap-2 pt-2">
            <button type="button" className="btn-secondary btn-sm" onClick={() => put({ copy }, "save")} disabled={busy !== null}>
              {busy === "save" ? "Enregistrement…" : "Enregistrer les textes"}
            </button>
            <button type="button" className="btn-primary btn-sm" onClick={() => put({ copy, copyValidated: true }, "validate")} disabled={busy !== null}>
              {busy === "validate" ? "Validation…" : "Valider les textes"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 6: `DeliveryPushPanel.tsx`**

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type Ref = { id: string; label: string };
type PushLog = {
  products?: { referenceId: string; productId?: number; error?: string }[];
  pages?: { key: string; pageId?: number; error?: string }[];
};

const PAGE_LABELS: Record<string, string> = {
  "mentions-legales": "Mentions légales",
  cgv: "CGV",
  "politique-de-confidentialite": "Confidentialité",
  "retours-et-remboursements": "Retours",
};

function ResultDot(props: { ok: boolean }) {
  return <span aria-hidden className={props.ok ? "ml-dot ml-dot--done" : "ml-dot ml-dot--locked"} />;
}

export function DeliveryPushPanel(props: {
  projectId: string;
  hasStore: boolean;
  copyValidated: boolean;
  pushLog: PushLog | null;
  references: Ref[];
}) {
  const router = useRouter();
  const [busy, setBusy] = useState<"products" | "pages" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function push(target: "products" | "pages") {
    setBusy(target);
    setError(null);
    const res = await fetch(`/api/studio/delivery/${props.projectId}/push`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target }),
    });
    setBusy(null);
    if (!res.ok) {
      const j = await res.json().catch(() => null);
      setError(j?.error ?? "Échec du push");
    }
    router.refresh();
  }

  const products = props.pushLog?.products ?? [];
  const pages = props.pushLog?.pages ?? [];

  return (
    <div className="card p-6">
      <h2 className="kicker mb-4">Push vers le dev store</h2>
      {!props.hasStore && <p className="text-sm text-[color:var(--ml-muted)] mb-3">Renseigner d'abord le domaine et le token du dev store.</p>}

      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn-primary btn-sm" onClick={() => push("products")} disabled={busy !== null || !props.hasStore || !props.copyValidated}>
          {busy === "products" ? "Push produits…" : "Pousser les produits"}
        </button>
        <button type="button" className="btn-secondary btn-sm" onClick={() => push("pages")} disabled={busy !== null || !props.hasStore}>
          {busy === "pages" ? "Push pages…" : "Pousser les pages légales"}
        </button>
      </div>
      {!props.copyValidated && props.hasStore && (
        <p className="mt-2 text-xs text-[color:var(--ml-muted)]">Le push produits demande des textes validés.</p>
      )}
      {error && <p className="mt-2 text-sm text-red-700">{error}</p>}

      {(products.length > 0 || pages.length > 0) && (
        <ul className="mt-4 space-y-2 text-sm">
          {props.references.map((ref) => {
            const r = products.filter((x) => x.referenceId === ref.id).at(-1);
            if (!r) return null;
            return (
              <li key={ref.id} className="flex items-center gap-2">
                <ResultDot ok={!!r.productId} />
                <span className="min-w-0 break-words">
                  {ref.label} {r.productId ? `— produit #${r.productId}` : ""}
                  {r.error && <span className="text-red-700"> — {r.error}</span>}
                </span>
              </li>
            );
          })}
          {pages.map((p) => (
            <li key={p.key} className="flex items-center gap-2">
              <ResultDot ok={!!p.pageId} />
              <span>
                {PAGE_LABELS[p.key] ?? p.key} {p.pageId ? `— page #${p.pageId}` : ""}
                {p.error && <span className="text-red-700"> — {p.error}</span>}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 7: `DeliveryChecklist.tsx`**

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CHECKLIST_ITEMS, checklistComplete } from "@/lib/studio/delivery";

export function DeliveryChecklist(props: {
  projectId: string;
  status: string;
  checklist: Record<string, boolean> | null;
  visioAt: string | null;
  deliveredAt: string | null;
}) {
  const router = useRouter();
  const [checklist, setChecklist] = useState<Record<string, boolean>>(props.checklist ?? {});
  const [visio, setVisio] = useState(props.visioAt ? props.visioAt.slice(0, 16) : "");
  const [busy, setBusy] = useState<"save" | "deliver" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setBusy("save");
    setError(null);
    const body: Record<string, unknown> = { checklist };
    if (visio) body.visioAt = new Date(visio).toISOString();
    const res = await fetch(`/api/studio/delivery/${props.projectId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setBusy(null);
    if (!res.ok) {
      const j = await res.json().catch(() => null);
      setError(j?.error ?? "Erreur");
      return;
    }
    router.refresh();
  }

  async function deliver() {
    setBusy("deliver");
    setError(null);
    const res = await fetch(`/api/studio/delivery/${props.projectId}/deliver`, { method: "POST" });
    setBusy(null);
    if (!res.ok) {
      const j = await res.json().catch(() => null);
      setError(j?.error ?? "Impossible de marquer livré");
      return;
    }
    router.refresh();
  }

  if (props.deliveredAt) {
    return (
      <div className="card p-6">
        <h2 className="kicker mb-2">Livraison</h2>
        <p className="text-sm">Site livré le {new Date(props.deliveredAt).toLocaleDateString("fr-FR")}.</p>
      </div>
    );
  }

  return (
    <div className="card p-6">
      <h2 className="kicker mb-4">Checklist du site livré</h2>
      <ul className="space-y-2 text-sm">
        {CHECKLIST_ITEMS.map((item) => (
          <li key={item.key}>
            <label className="flex items-start gap-2">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={checklist[item.key] === true}
                onChange={(e) => setChecklist((c) => ({ ...c, [item.key]: e.target.checked }))}
              />
              <span>{item.label}</span>
            </label>
          </li>
        ))}
      </ul>

      <label className="block text-sm mt-4">
        <span className="text-xs text-[color:var(--ml-muted)]">Visio de livraison</span>
        <input type="datetime-local" className="input w-full mt-1" value={visio} onChange={(e) => setVisio(e.target.value)} />
      </label>

      {error && <p className="mt-2 text-sm text-red-700">{error}</p>}

      <div className="flex flex-wrap gap-2 mt-4">
        <button type="button" className="btn-secondary btn-sm" onClick={save} disabled={busy !== null}>
          {busy === "save" ? "Enregistrement…" : "Enregistrer"}
        </button>
        <button
          type="button"
          className="btn-primary btn-sm"
          onClick={deliver}
          disabled={busy !== null || props.status !== "site_in_progress" || !checklistComplete(checklist)}
        >
          {busy === "deliver" ? "…" : "Marquer livré"}
        </button>
      </div>
      {props.status === "site_in_progress" && !checklistComplete(checklist) && (
        <p className="mt-2 text-xs text-[color:var(--ml-muted)]">« Marquer livré » s'active quand toutes les cases sont cochées (et enregistrées).</p>
      )}
    </div>
  );
}
```

Note : le bouton se base sur l'état local ; le serveur re-vérifie via `canDeliver` sur la checklist **enregistrée** (409 sinon) — cocher puis « Enregistrer » avant « Marquer livré ».

- [ ] **Step 8: Vérifier + commit**

```bash
npx tsc --noEmit && npx eslint src/app/admin src/components/admin
git add src/components/admin/AdminSidebar.tsx "src/app/admin/(dashboard)/delivery" src/components/admin/delivery
git commit -m "feat(studio): UI admin livraisons — fiche store/textes/push/checklist (lot 5)"
```

---

### Task 7: Côté client `/projet` — jalons site en préparation / site livré + `projectDoneCount`

**Files:**
- Modify: `src/lib/studio/bat.ts` (+ test `src/lib/studio/bat.test.ts`)
- Modify: `src/app/projet/page.tsx`

**Interfaces:**
- Consumes: statuts `site_in_progress`/`delivered`, `Project.delivery` (`storeDomain`, `deliveredAt`).
- Produces: timeline correcte (jalon 4 « Votre site en ligne » : current pendant la livraison, done à `delivered`) + bandeaux de statut.

- [ ] **Step 1: Test qui échoue — `projectDoneCount`**

Dans `src/lib/studio/bat.test.ts`, ajouter au `describe` de `projectDoneCount` :

```ts
  it("retourne 3 pendant la livraison et 4 une fois livré", () => {
    expect(projectDoneCount("site_in_progress")).toBe(3);
    expect(projectDoneCount("delivered")).toBe(4);
  });
```

Run: `npx vitest run src/lib/studio/bat.test.ts` — Expected: FAIL (site_in_progress retourne 1).

- [ ] **Step 2: Implémenter dans `bat.ts`**

Remplacer le corps de `projectDoneCount` :

```ts
export function projectDoneCount(projectStatus: string, requestStatus?: ReqStatus): number {
  if (projectStatus === "draft") return 0;
  if (projectStatus === "delivered") return 4;
  if (projectStatus === "onboarding_submitted" || projectStatus === "site_in_progress" || PACK_STATUSES.has(projectStatus)) return 3;
  if (projectStatus === "label_validated" || requestStatus === "validated") return 2;
  return 1;
}
```

Run: `npx vitest run src/lib/studio/bat.test.ts` — Expected: PASS.

- [ ] **Step 3: `/projet` — inclure la delivery et afficher les nouveaux états**

Dans `src/app/projet/page.tsx` :

1. Dans la requête `prisma.project.findMany`, ajouter dans `include` :

```ts
      delivery: { select: { storeDomain: true, deliveredAt: true } },
```

2. Étendre la grille des visuels sélectionnés aux statuts de livraison — remplacer la condition du bloc `pack_selected` (ligne `{project.status === "pack_selected" && (`) par :

```tsx
{["pack_selected", "site_in_progress", "delivered"].includes(project.status) && (
```

et rendre le bandeau interne conditionnel : remplacer le `<div className="rounded-lg bg-emerald-50 …">Sélection enregistrée…</div>` par :

```tsx
{project.status === "pack_selected" && (
  <div className="rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-800">
    <span className="kicker text-emerald-700">Sélection enregistrée</span>
    <span className="block mt-0.5">Place à la mise en ligne de votre site !</span>
  </div>
)}
{project.status === "site_in_progress" && (
  <div className="rounded-lg border border-[color:var(--ml-line)] bg-[var(--ml-cream-2)] px-4 py-3 text-sm text-[color:var(--ml-ink)]">
    <span className="kicker">Mise en ligne en cours</span>
    <span className="block mt-0.5">Nous préparons votre boutique — nous vous contactons très vite pour la visio de livraison.</span>
  </div>
)}
{project.status === "delivered" && (
  <div className="rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-800">
    <span className="kicker text-emerald-700">Site livré</span>
    <span className="block mt-0.5">
      Votre boutique est en ligne{project.delivery?.deliveredAt ? ` depuis le ${project.delivery.deliveredAt.toLocaleDateString("fr-FR")}` : ""}.
      {project.delivery?.storeDomain && (
        <>
          {" "}
          <a className="underline underline-offset-2" href={`https://${project.delivery.storeDomain}`} target="_blank" rel="noreferrer">
            Voir ma boutique
          </a>
        </>
      )}
    </span>
  </div>
)}
```

(La grille des visuels sélectionnés reste sous ces bandeaux, inchangée.)

- [ ] **Step 4: Vérifier + commit**

```bash
npx tsc --noEmit && npx eslint src/app/projet/page.tsx src/lib/studio/bat.ts && npx vitest run src/lib/studio
git add src/app/projet/page.tsx src/lib/studio/bat.ts src/lib/studio/bat.test.ts
git commit -m "feat(studio): /projet — jalons livraison (site en cours / livré) (lot 5)"
```

---

### Task 8: Merge, déploiement, e2e prod sur le projet démo

**Files:** aucun nouveau — opérations de release (exécutées par le contrôleur, pas par un subagent).

- [ ] **Step 1: Suite complète + build local**

```bash
npx vitest run && npx tsc --noEmit && npx next build
```
Expected: tests verts, build OK.

- [ ] **Step 2: Merge + deploy**

```bash
git checkout main && git pull && git merge --no-ff feat/studio-lot5-livraison -m "feat(studio): lot 5 — livraison du site (delivery, copy IA, push dev store)"
git push
```
Attendre le deploy Vercel READY (`vercel ls` / inspect).

- [ ] **Step 3: E2E prod sur le projet démo 999000999** (id `cmrda3plf0002t8gbp741fxgz`, statut `pack_selected`)

Via script Prisma + fetch authentifié admin (pattern e2e des lots précédents) :
1. PUT delivery `{ storeDomain: "" }` vide → vérifier création `Delivery` + statut `site_in_progress`.
2. POST `/copy` → vérifier : `copy` non nul, `produits` couvre toutes les références, `domaines` cohérent avec le mode du projet démo, `copyValidatedAt` null. (Appel Claude réel — coût négligeable.)
3. PUT `{ copyValidated: true }` → `copyValidatedAt` non nul.
4. POST `/push` `{ target: "products" }` sans token → 409 « Renseigner d'abord… » (comportement attendu tant que Yoann n'a pas créé le dev store).
5. Vérifier `/projet` (statut « Mise en ligne en cours ») et `/admin/delivery` (fiche visible, textes éditables).
6. Nettoyage : PAS de rollback du statut (le projet démo reste en `site_in_progress`, substrat pour la suite : push réel dès qu'un dev store + token existent).

- [ ] **Step 4: Notifier Yoann**

Notification push : Lot 5 déployé, ce qui est prêt (fiche livraison, textes IA générés sur le démo), ce qui l'attend (créer un dev store Partner + custom app `write_products`/`write_content`, coller domaine + token dans `/admin/delivery`, pousser produits + pages, dérouler la checklist).

---

## Notes de scope (rappel spec §4.6 / §8)

- **Semi-manuel assumé au MVP** : la création du dev store, l'installation/config du thème, les zones de livraison, les emails de marque et le branchement du domaine se font à la main dans l'admin Shopify — la checklist les trace. L'app automatise : textes IA, produits (prix/descriptions/photos), pages légales, statuts, notifications.
- **Transfer de propriété** : action Partner dashboard + visio (R5 : jamais promettre 100 % auto) — hors app, tracé par la case « domaine » + `visioAt` + « Marquer livré ».
- Hors scope V3 (spec §8) : paiement en ligne du setup, provisioning 100 % auto, multi-langue.
