# MY.LAB Studio — Push Home (extension Lot 5) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nouveau target `home` du push livraison : remplace `templates/index.json` du thème `mylab-studio-theme` du dev store par une home curée — hero (visuel sélectionné du pack + textes IA validés), histoire de marque, intro + vitrine gamme (collection créée avec les produits poussés), 3 réassurances, galerie des autres visuels — et injecte la couleur d'accent du Brand DNA dans `settings_data.json`. Bouton « Pousser la home » dans la fiche admin.

**Architecture:** Lib `shopify-theme.ts` : builders purs TDD (`buildIndexTemplate`, `buildColorsPatch`) + fonctions API fines (thèmes, assets, GraphQL fileCreate pour les images, custom collection). Le target `home` s'ajoute au switch de `push/route.ts` (mêmes patterns : pushLog incrémental, checklist auto, idempotence). Le thème visé reste **unpublished** — la publication est un geste manuel (checklist « thème »).

**Tech Stack:** Admin REST 2025-01 (themes/assets/custom_collections) + Admin GraphQL 2025-01 (`fileCreate` — scope `write_files`), images sources = URLs Cloudinary des GenerationJobs sélectionnés.

**Dépôt :** `d:\Projets mylab vs code\mylab-configurateur`, branche `feat/studio-push-home` depuis `main` (`c68b624`).

## Global Constraints

- Mêmes contraintes que le Lot 5 : Prisma via `@/generated/prisma/client`, `requireAdmin` première ligne, token write-only, erreurs français U+2019, tests vitest libs pures `globals:false` (tests en relatif, sources en alias `@/`), pas de tests de routes, DA admin existante, pushLog incrémental + idempotence, `Prisma.InputJsonValue` pour les colonnes Json.
- **Schemas de sections relevés sur le thème réel** (fork Be Yours, thème id trouvé par nom contenant `mylab-studio-theme`) — utiliser EXACTEMENT ces ids de settings/blocks :
  - `image-banner` : settings `image`, `show_text_box` ; blocks `heading{heading}`, `text{text}`, `button{button_label,button_link}`
  - `image-with-text` : settings `image` ; blocks `subheading{subheading}`, `heading{heading}`, `text{text}`
  - `rich-text` : blocks `heading{heading}`, `text{text}`
  - `featured-collection` : settings `collection` (handle), `products_to_show`, `show_view_all`, `heading`
  - `multicolumn` : settings `columns_desktop`, `heading` ; block `column{title,text}`
  - `gallery` : settings `per_row` ; block `image{image}`
  - `config/settings_data.json` : `{ current: { colors_accent, colors_highlight, … } }` (si `current` est une string — nom de preset — ne PAS patcher)
- Références d'images dans les templates JSON : `shopify://shop_images/<filename>` ; liens : `shopify://collections/<handle>`.
- Le push home ne touche JAMAIS au thème publié si `mylab-studio-theme` est introuvable → 409 explicite (pas de fallback silencieux sur le main).

---

### Task 1: Lib `shopify-theme.ts` — builders purs (TDD) + API thèmes/images/collection

**Files:**
- Create: `src/lib/studio/shopify-theme.ts`
- Test: `src/lib/studio/shopify-theme.test.ts`

**Interfaces:**
- Consumes: `type DeliveryCopy` (`@/lib/studio/copy`), `type PushResult` (`@/lib/studio/shopify-store`).
- Produces (consommés par Task 2) :
  - `buildIndexTemplate(p: { copy: DeliveryCopy; heroImage: string | null; histoireImage: string | null; galleryImages: string[]; collectionHandle: string }): Record<string, unknown>`
  - `buildColorsPatch(settingsDataRaw: string, palette: string[]): string | null` (JSON string prêt à PUT, null si structure non patchable)
  - `imageRef(filename: string): string` → `shopify://shop_images/<filename>`
  - `findStudioTheme(domain: string, token: string): Promise<{ id: number; name: string } | null>`
  - `getAsset(domain, token, themeId, key): Promise<string | null>`
  - `putAsset(domain, token, themeId, key, value): Promise<PushResult>` (id = themeId si ok)
  - `uploadStoreImages(domain, token, images: { url: string; filename: string }[]): Promise<{ filename: string; ok: boolean; error?: string }[]>` (GraphQL `fileCreate`, poll `fileStatus` READY ≤ 20 s)
  - `createGammeCollection(domain, token, title: string, productIds: number[]): Promise<{ ok: boolean; id?: number; handle?: string; error?: string }>`

- [ ] **Step 1: Tests qui échouent** — `src/lib/studio/shopify-theme.test.ts` :

```ts
import { describe, it, expect } from "vitest";
import { buildIndexTemplate, buildColorsPatch, imageRef } from "./shopify-theme";
import type { DeliveryCopy } from "./copy";

const copy: DeliveryCopy = {
  hero: { title: "La nature, dosée", subtitle: "Des soins efficaces.", cta: "Découvrir" },
  histoire: { title: "Notre histoire", body: "Tout a commencé…" },
  gamme: { title: "La gamme", intro: "Trois essentiels." },
  reassurance: { items: [
    { title: "Fabrication française", text: "Conçu et fabriqué en France." },
    { title: "Formules douces", text: "Sans compromis." },
    { title: "Livraison suivie", text: "Expédié en 48 h." },
  ] },
  produits: [{ referenceId: "r1", title: "P", description: "D" }],
  domaines: [],
};

describe("imageRef", () => {
  it("construit la référence shop_images", () => {
    expect(imageRef("studio-x-1.jpg")).toBe("shopify://shop_images/studio-x-1.jpg");
  });
});

describe("buildIndexTemplate", () => {
  const tpl = buildIndexTemplate({
    copy,
    heroImage: "studio-p-hero.jpg",
    histoireImage: "studio-p-histoire.jpg",
    galleryImages: ["studio-p-g1.jpg", "studio-p-g2.jpg"],
    collectionHandle: "la-gamme",
  }) as { sections: Record<string, { type: string; settings?: Record<string, unknown>; blocks?: Record<string, { type: string; settings: Record<string, unknown> }>; block_order?: string[] }>; order: string[] };

  it("ordonne hero → histoire → intro gamme → collection → réassurance → galerie", () => {
    expect(tpl.order).toEqual(["hero", "histoire", "gamme_intro", "gamme", "reassurance", "galerie"]);
  });
  it("hero : image-banner avec image, textes IA et CTA vers la collection", () => {
    const hero = tpl.sections.hero;
    expect(hero.type).toBe("image-banner");
    expect(hero.settings?.image).toBe("shopify://shop_images/studio-p-hero.jpg");
    expect(hero.blocks?.heading.settings.heading).toBe("La nature, dosée");
    expect(hero.blocks?.button.settings.button_link).toBe("shopify://collections/la-gamme");
  });
  it("gamme : featured-collection pointe le handle, 8 produits, voir tout", () => {
    const g = tpl.sections.gamme;
    expect(g.settings?.collection).toBe("la-gamme");
    expect(g.settings?.products_to_show).toBe(8);
    expect(g.settings?.show_view_all).toBe(true);
  });
  it("réassurance : 3 colonnes title/text", () => {
    const r = tpl.sections.reassurance;
    expect(r.type).toBe("multicolumn");
    expect(Object.keys(r.blocks ?? {})).toHaveLength(3);
    expect(Object.values(r.blocks ?? {})[0].settings.title).toBe("Fabrication française");
  });
  it("galerie présente avec 2 images ; absente sous 2", () => {
    expect(Object.keys(tpl.sections.galerie.blocks ?? {})).toHaveLength(2);
    const sans = buildIndexTemplate({ copy, heroImage: null, histoireImage: null, galleryImages: [], collectionHandle: "h" }) as { order: string[] };
    expect(sans.order).not.toContain("galerie");
  });
  it("hero sans image : pas de setting image", () => {
    const sans = buildIndexTemplate({ copy, heroImage: null, histoireImage: null, galleryImages: [], collectionHandle: "h" }) as { sections: Record<string, { settings?: Record<string, unknown> }> };
    expect(sans.sections.hero.settings?.image).toBeUndefined();
  });
});

describe("buildColorsPatch", () => {
  it("patche colors_accent et colors_highlight en gardant le reste", () => {
    const raw = JSON.stringify({ current: { colors_accent: "#000000", colors_text: "#111111" }, presets: {} });
    const out = buildColorsPatch(raw, ["#aabbcc", "#112233", "#ffffff"]);
    const v = JSON.parse(out!);
    expect(v.current.colors_accent).toBe("#aabbcc");
    expect(v.current.colors_highlight).toBe("#112233");
    expect(v.current.colors_text).toBe("#111111");
    expect(v.presets).toEqual({});
  });
  it("null si current est un nom de preset ou JSON invalide", () => {
    expect(buildColorsPatch(JSON.stringify({ current: "Default" }), ["#aabbcc"])).toBeNull();
    expect(buildColorsPatch("not json", ["#aabbcc"])).toBeNull();
    expect(buildColorsPatch(JSON.stringify({ current: {} }), [])).toBeNull();
  });
});
```

- [ ] **Step 2: Vérifier l'échec** — `npx vitest run src/lib/studio/shopify-theme.test.ts` → FAIL (module inexistant).

- [ ] **Step 3: Implémenter `src/lib/studio/shopify-theme.ts`** :

```ts
import type { DeliveryCopy } from "@/lib/studio/copy";
import type { PushResult } from "@/lib/studio/shopify-store";

// Cible le thème Studio du dev store (fork Be Yours). Schemas relevés sur le thème réel —
// ne pas inventer d'ids de settings.
const API_VERSION = "2025-01";
export const STUDIO_THEME_NAME = "mylab-studio-theme";

export function imageRef(filename: string): string {
  return `shopify://shop_images/${filename}`;
}

export function buildIndexTemplate(p: {
  copy: DeliveryCopy;
  heroImage: string | null;
  histoireImage: string | null;
  galleryImages: string[];
  collectionHandle: string;
}): Record<string, unknown> {
  const c = p.copy;
  const sections: Record<string, unknown> = {
    hero: {
      type: "image-banner",
      blocks: {
        heading: { type: "heading", settings: { heading: c.hero.title } },
        text: { type: "text", settings: { text: c.hero.subtitle } },
        button: {
          type: "button",
          settings: { button_label: c.hero.cta, button_link: `shopify://collections/${p.collectionHandle}` },
        },
      },
      block_order: ["heading", "text", "button"],
      settings: {
        ...(p.heroImage ? { image: imageRef(p.heroImage) } : {}),
        show_text_box: true,
      },
    },
    histoire: {
      type: "image-with-text",
      blocks: {
        subheading: { type: "subheading", settings: { subheading: "Notre histoire" } },
        heading: { type: "heading", settings: { heading: c.histoire.title } },
        text: { type: "text", settings: { text: `<p>${c.histoire.body}</p>` } },
      },
      block_order: ["subheading", "heading", "text"],
      settings: { ...(p.histoireImage ? { image: imageRef(p.histoireImage) } : {}) },
    },
    gamme_intro: {
      type: "rich-text",
      blocks: {
        heading: { type: "heading", settings: { heading: c.gamme.title } },
        text: { type: "text", settings: { text: `<p>${c.gamme.intro}</p>` } },
      },
      block_order: ["heading", "text"],
      settings: {},
    },
    gamme: {
      type: "featured-collection",
      settings: { collection: p.collectionHandle, products_to_show: 8, show_view_all: true, heading: "" },
    },
    reassurance: {
      type: "multicolumn",
      blocks: Object.fromEntries(
        c.reassurance.items.slice(0, 3).map((item, i) => [
          `column_${i + 1}`,
          { type: "column", settings: { title: item.title, text: `<p>${item.text}</p>` } },
        ])
      ),
      block_order: c.reassurance.items.slice(0, 3).map((_, i) => `column_${i + 1}`),
      settings: { columns_desktop: 3, heading: "" },
    },
  };
  const order = ["hero", "histoire", "gamme_intro", "gamme", "reassurance"];
  if (p.galleryImages.length >= 2) {
    sections.galerie = {
      type: "gallery",
      blocks: Object.fromEntries(
        p.galleryImages.map((f, i) => [`image_${i + 1}`, { type: "image", settings: { image: imageRef(f) } }])
      ),
      block_order: p.galleryImages.map((_, i) => `image_${i + 1}`),
      settings: { per_row: Math.min(p.galleryImages.length, 4) },
    };
    order.push("galerie");
  }
  return { sections, order };
}

// Patch conservateur : accent + highlight seulement (le reste du scheme de couleurs du thème
// est laissé intact — contraste maîtrisé par le thème).
export function buildColorsPatch(settingsDataRaw: string, palette: string[]): string | null {
  if (palette.length < 2) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(settingsDataRaw);
  } catch {
    return null;
  }
  const data = parsed as { current?: unknown };
  if (!data || typeof data !== "object" || !data.current || typeof data.current !== "object") return null;
  const current = data.current as Record<string, unknown>;
  return JSON.stringify({ ...data, current: { ...current, colors_accent: palette[0], colors_highlight: palette[1] } });
}

async function rest(domain: string, token: string, method: string, path: string, body?: Record<string, unknown>): Promise<{ status: number; json: unknown }> {
  const res = await fetch(`https://${domain}/admin/api/${API_VERSION}/${path}`, {
    method,
    headers: { "X-Shopify-Access-Token": token, "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = await res.json().catch(() => null);
  return { status: res.status, json };
}

export async function findStudioTheme(domain: string, token: string): Promise<{ id: number; name: string } | null> {
  const { status, json } = await rest(domain, token, "GET", "themes.json");
  if (status !== 200) return null;
  const themes = (json as { themes?: { id: number; name: string; role: string }[] })?.themes ?? [];
  return themes.find((t) => t.name.toLowerCase().includes(STUDIO_THEME_NAME)) ?? null;
}

export async function getAsset(domain: string, token: string, themeId: number, key: string): Promise<string | null> {
  const { status, json } = await rest(domain, token, "GET", `themes/${themeId}/assets.json?asset%5Bkey%5D=${encodeURIComponent(key)}`);
  if (status !== 200) return null;
  return (json as { asset?: { value?: string } })?.asset?.value ?? null;
}

export async function putAsset(domain: string, token: string, themeId: number, key: string, value: string): Promise<PushResult> {
  try {
    const { status, json } = await rest(domain, token, "PUT", `themes/${themeId}/assets.json`, { asset: { key, value } });
    if (status === 200) return { ok: true, id: themeId };
    const errors = (json as { errors?: unknown } | null)?.errors;
    return { ok: false, error: `HTTP ${status}${errors ? ` — ${typeof errors === "string" ? errors : JSON.stringify(errors)}` : ""}` };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Erreur réseau" };
  }
}

async function graphql(domain: string, token: string, query: string, variables: Record<string, unknown>): Promise<unknown> {
  const res = await fetch(`https://${domain}/admin/api/${API_VERSION}/graphql.json`, {
    method: "POST",
    headers: { "X-Shopify-Access-Token": token, "Content-Type": "application/json" },
    body: JSON.stringify({ query, variables }),
  });
  return res.json().catch(() => null);
}

// Upload des visuels Cloudinary vers Files (référençables en shopify://shop_images/<filename>).
export async function uploadStoreImages(
  domain: string,
  token: string,
  images: { url: string; filename: string }[]
): Promise<{ filename: string; ok: boolean; error?: string }[]> {
  if (images.length === 0) return [];
  const create = (await graphql(
    domain,
    token,
    `mutation fileCreate($files: [FileCreateInput!]!) {
      fileCreate(files: $files) { files { id fileStatus } userErrors { field message } }
    }`,
    { files: images.map((i) => ({ originalSource: i.url, contentType: "IMAGE", filename: i.filename })) }
  )) as { data?: { fileCreate?: { files?: { id: string; fileStatus: string }[]; userErrors?: { message: string }[] } } } | null;
  const errs = create?.data?.fileCreate?.userErrors ?? [];
  if (errs.length > 0) return images.map((i) => ({ filename: i.filename, ok: false, error: errs.map((e) => e.message).join(", ") }));
  const ids = (create?.data?.fileCreate?.files ?? []).map((f) => f.id);
  if (ids.length !== images.length) return images.map((i) => ({ filename: i.filename, ok: false, error: "fileCreate incomplet" }));

  // Poll jusqu'à READY/FAILED (≤ 20 s)
  const status = new Map<string, string>(ids.map((id) => [id, "PROCESSING"]));
  for (let tour = 0; tour < 10; tour++) {
    const pending = ids.filter((id) => status.get(id) === "PROCESSING" || status.get(id) === "UPLOADED");
    if (pending.length === 0) break;
    await new Promise((r) => setTimeout(r, 2000));
    const q = (await graphql(
      domain,
      token,
      `query nodes($ids: [ID!]!) { nodes(ids: $ids) { ... on MediaImage { id fileStatus } ... on GenericFile { id fileStatus } } }`,
      { ids: pending }
    )) as { data?: { nodes?: ({ id: string; fileStatus: string } | null)[] } } | null;
    for (const n of q?.data?.nodes ?? []) if (n) status.set(n.id, n.fileStatus);
  }
  return images.map((img, i) => {
    const st = status.get(ids[i]);
    return st === "READY" ? { filename: img.filename, ok: true } : { filename: img.filename, ok: false, error: `fileStatus ${st ?? "inconnu"}` };
  });
}

export async function createGammeCollection(
  domain: string,
  token: string,
  title: string,
  productIds: number[]
): Promise<{ ok: boolean; id?: number; handle?: string; error?: string }> {
  try {
    const { status, json } = await rest(domain, token, "POST", "custom_collections.json", {
      custom_collection: { title, published: true, collects: productIds.map((id) => ({ product_id: id })) },
    });
    const col = (json as { custom_collection?: { id?: number; handle?: string } } | null)?.custom_collection;
    if (status === 201 && col?.id && col.handle) return { ok: true, id: col.id, handle: col.handle };
    const errors = (json as { errors?: unknown } | null)?.errors;
    return { ok: false, error: `HTTP ${status}${errors ? ` — ${typeof errors === "string" ? errors : JSON.stringify(errors)}` : ""}` };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Erreur réseau" };
  }
}
```

- [ ] **Step 4: Tests verts** — `npx vitest run src/lib/studio/shopify-theme.test.ts` → PASS.
- [ ] **Step 5: `npx tsc --noEmit` + eslint, commit** `feat(studio): lib shopify-theme — home générée + images + collection (push home)`

---

### Task 2: Target `home` dans la route push + bouton UI

**Files:**
- Modify: `src/app/api/studio/delivery/[projectId]/push/route.ts`
- Modify: `src/components/admin/delivery/DeliveryPushPanel.tsx`
- Modify: `src/app/admin/(dashboard)/delivery/[projectId]/page.tsx`

**Interfaces:**
- Consumes: lib Task 1 ; `GenerationJob` (selected/done/assetUrl, type image) ; `BrandDna` (`palette`) via `onboarding.brandDna` ; pushLog existant.
- Produces: `POST push { target: "home" }` → `{ home: { theme, collectionHandle, images: [...], indexOk, colorsOk, error? } }` ; `pushLog.home = { themeId, themeName, collectionId, collectionHandle, files: [{filename, ok, error?}], indexPushedAt?, colorsPushedAt?, error?, at }` ; checklist auto : `home: true` si index poussé, `theme: true` si couleurs aussi.

- [ ] **Step 1: Route — accepter `"home"`** dans la validation du body (`products | pages | home`), et ajouter la branche AVANT la branche products (après pages), gardes puis logique :

```ts
if (body.target === "home") {
  if (!delivery.copyValidatedAt)
    return NextResponse.json({ error: "Valider d'abord les textes" }, { status: 409 });
  const copy = delivery.copy as unknown as DeliveryCopy | null;
  if (!copy) return NextResponse.json({ error: "Générer d'abord les textes" }, { status: 409 });
  const productLog = (log.products ?? []).filter((r) => r.productId);
  const references = project.labelRequest?.references ?? [];
  if (productLog.length < references.length)
    return NextResponse.json({ error: "Pousser d'abord les produits (la home présente la gamme)" }, { status: 409 });
  const jobs = await prisma.generationJob.findMany({
    where: { projectId, type: "image", status: "done", selected: true, assetUrl: { not: null } },
    orderBy: { createdAt: "asc" },
  });
  if (jobs.length === 0)
    return NextResponse.json({ error: "Aucun visuel sélectionné — la home a besoin d'images du pack" }, { status: 409 });

  const theme = await findStudioTheme(delivery.storeDomain, delivery.adminToken);
  if (!theme)
    return NextResponse.json({ error: `Thème « ${STUDIO_THEME_NAME} » introuvable sur le dev store` }, { status: 409 });

  const home: HomeLog = (log.home ?? {}) as HomeLog;
  home.themeId = theme.id;
  home.themeName = theme.name;
  home.at = now();

  // 1. Collection gamme (réutilisée si déjà créée)
  if (!home.collectionHandle) {
    const col = await createGammeCollection(
      delivery.storeDomain, delivery.adminToken, copy.gamme.title,
      productLog.map((r) => r.productId!) 
    );
    if (!col.ok) {
      home.error = `Collection : ${col.error}`;
      await saveHome(projectId, log, home);
      return NextResponse.json({ home }, { status: 502 });
    }
    home.collectionId = col.id;
    home.collectionHandle = col.handle;
    await saveHome(projectId, log, home);
  }

  // 2. Upload des visuels (hero, histoire, galerie ≤ 4) — skip ceux déjà ok
  const wanted = jobs.slice(0, 6).map((j) => ({ url: j.assetUrl!, filename: `studio-${projectId}-${j.id}.jpg` }));
  const already = new Set((home.files ?? []).filter((f) => f.ok).map((f) => f.filename));
  const toUpload = wanted.filter((w) => !already.has(w.filename));
  if (toUpload.length > 0) {
    const uploaded = await uploadStoreImages(delivery.storeDomain, delivery.adminToken, toUpload);
    home.files = [...(home.files ?? []).filter((f) => f.ok), ...uploaded];
    await saveHome(projectId, log, home);
  }
  const okFiles = wanted.filter((w) => (home.files ?? []).some((f) => f.filename === w.filename && f.ok)).map((w) => w.filename);

  // 3. Couleurs Brand DNA (best effort — non bloquant)
  const palette = ((project.onboarding?.brandDna as unknown as BrandDna | null)?.palette ?? []) as string[];
  const settingsRaw = await getAsset(delivery.storeDomain, delivery.adminToken, theme.id, "config/settings_data.json");
  if (settingsRaw && palette.length >= 2) {
    const patched = buildColorsPatch(settingsRaw, palette);
    if (patched) {
      const rc = await putAsset(delivery.storeDomain, delivery.adminToken, theme.id, "config/settings_data.json", patched);
      if (rc.ok) home.colorsPushedAt = now();
    }
  }

  // 4. templates/index.json
  const tpl = buildIndexTemplate({
    copy,
    heroImage: okFiles[0] ?? null,
    histoireImage: okFiles[1] ?? null,
    galleryImages: okFiles.slice(2, 6),
    collectionHandle: home.collectionHandle!,
  });
  const ri = await putAsset(delivery.storeDomain, delivery.adminToken, theme.id, "templates/index.json", JSON.stringify(tpl, null, 2));
  if (!ri.ok) {
    home.error = `index.json : ${ri.error}`;
    await saveHome(projectId, log, home);
    return NextResponse.json({ home }, { status: 502 });
  }
  home.indexPushedAt = now();
  home.error = undefined;

  const fresh = await prisma.delivery.findUnique({ where: { projectId }, select: { checklist: true } });
  const checklist = {
    ...((fresh?.checklist ?? {}) as Record<string, boolean>),
    home: true,
    ...(home.colorsPushedAt ? { theme: true } : {}),
  };
  await prisma.delivery.update({
    where: { projectId },
    data: { pushLog: { ...log, home } as Prisma.InputJsonValue, checklist: checklist as Prisma.InputJsonValue },
  });
  return NextResponse.json({ home });
}
```

Avec en haut du fichier : imports depuis `@/lib/studio/shopify-theme` (`findStudioTheme`, `getAsset`, `putAsset`, `uploadStoreImages`, `createGammeCollection`, `buildIndexTemplate`, `buildColorsPatch`, `STUDIO_THEME_NAME`), `type BrandDna` depuis `@/lib/studio/onboarding`, extension du type `PushLog` :

```ts
type HomeLog = {
  themeId?: number; themeName?: string; collectionId?: number; collectionHandle?: string;
  files?: { filename: string; ok: boolean; error?: string }[];
  indexPushedAt?: string; colorsPushedAt?: string; error?: string; at?: string;
};
// PushLog gagne : home?: HomeLog
```

et le helper :

```ts
async function saveHome(projectId: string, log: PushLog, home: HomeLog): Promise<void> {
  await prisma.delivery.update({
    where: { projectId },
    data: { pushLog: { ...log, home } as Prisma.InputJsonValue },
  });
}
```

- [ ] **Step 2: UI — `DeliveryPushPanel`** : prop nouvelle `productsPushed: boolean` (passée par la page fiche : toutes les références ont un `productId` dans `pushLog.products`), type `PushLog` étendu (`home?`), bouton :

```tsx
<button type="button" className="btn-primary btn-sm" onClick={() => push("home")} disabled={busy !== null || !props.hasStore || !props.copyValidated || !props.productsPushed}>
  {busy === "home" ? "Push home…" : "Pousser la home"}
</button>
```

(le type de `busy` et de `push(target)` passe à `"products" | "pages" | "home"`), hint si `!productsPushed` : « La home se pousse après les produits (elle présente la gamme). », et sous la liste des résultats, l'état home :

```tsx
{props.pushLog?.home?.indexPushedAt && (
  <li className="flex items-center gap-2">
    <ResultDot ok />
    <span>
      Home poussée sur « {props.pushLog.home.themeName} » (collection /{props.pushLog.home.collectionHandle},
      {" "}{(props.pushLog.home.files ?? []).filter((f) => f.ok).length} visuels{props.pushLog.home.colorsPushedAt ? ", couleurs Brand DNA" : ""})
    </span>
  </li>
)}
{props.pushLog?.home?.error && (
  <li className="flex items-center gap-2"><ResultDot ok={false} /><span className="text-red-700">Home — {props.pushLog.home.error}</span></li>
)}
```

- [ ] **Step 3: Fiche serveur** — passer `productsPushed` :

```tsx
productsPushed={references.length > 0 && references.every((ref) =>
  ((d?.pushLog as { products?: { referenceId: string; productId?: number }[] } | null)?.products ?? []).some((r) => r.referenceId === ref.id && r.productId)
)}
```

- [ ] **Step 4: `npx tsc --noEmit` + `npx eslint src/app/api/studio/delivery src/components/admin/delivery src/app/admin` + `npx vitest run src/lib/studio`, commit** `feat(studio): push home — thème studio, collection gamme, visuels pack, couleurs Brand DNA`

---

### Task 3: Release + e2e réel sur test-mylab-studio (contrôleur)

- [ ] Suite complète + build (`npx vitest run && npx tsc --noEmit && npx next build`)
- [ ] Merge `feat/studio-push-home` → main, push, deploy Vercel Ready
- [ ] E2E réel (session admin forgée) sur le projet démo : POST push products → POST push pages → POST push home ; vérifier : collection créée avec 3 produits, fichiers images READY, `templates/index.json` du thème = 5-6 sections attendues, `settings_data` patché (accent = palette[0] du démo), checklist `home`/`theme` cochées ; contrôle visuel via l'URL de preview `https://test-mylab-studio.myshopify.com/?preview_theme_id=<id>` (thème non publié)
- [ ] Ledger + notification Yoann avec le lien de preview
