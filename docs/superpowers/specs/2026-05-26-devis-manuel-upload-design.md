# Devis Manuel — Upload PDF/JPEG pour génération de devis

**Date** : 2026-05-26
**Auteur** : Yoann Durand + Claude (brainstorming)
**Statut** : design validé, en attente du plan d'implémentation
**Workflow n8n cible** : `e0rRHlz61Ll807gX` — "MY.LAB - Devis Manuel (Formulaire)"
**Fichiers impactés** : `docs/devis-manuel.html`, workflow n8n (2 nodes modifiés), export local `docs/n8n-devis-manuel.json`

---

## 1. Objectif

Étendre le formulaire devis manuel pour qu'un utilisateur (Yoann, Laure, futurs commerciaux) puisse **uploader un PDF ou une photo JPEG d'un bon de commande client** et générer directement un devis Odoo, au lieu de retaper la commande dans le textarea.

Cas d'usage cible :
- Client envoie un bon de commande PDF par email → upload → devis créé en quelques secondes.
- Photo smartphone d'un carnet de commande pris au salon → upload → devis créé.
- Le fichier source est **attaché au sale.order** dans Odoo pour traçabilité (chatter + PJ).

## 2. Décisions clés (issues du brainstorming)

| Décision | Choix | Raison |
|---|---|---|
| UX du toggle | **Either/or** : texte OU fichier, pas les deux | Évite l'ambiguïté côté Gemini et côté UI. Cohérent avec l'existant texte-only. |
| Type/taille fichiers | **1 fichier**, PDF (multi-pages OK) ou JPEG, **<10 Mo** | Couvre 95% des cas (bon de commande typique). Gemini 2.5 Flash lit nativement PDF multi-pages jusqu'à 1000 pages. |
| Fallback extraction ratée | **Erreur claire + transcription brute** (`raw_ocr`) renvoyée au front, bouton "Copier vers mode texte" | Maximale transparence. L'utilisateur peut corriger sans retaper depuis zéro. |
| Attachement Odoo | **`ir.attachment` lié au sale.order + note interne dans le chatter** (subtype `mail.mt_note`) | Traçabilité complète, pas de spam email aux followers. |
| Architecture workflow | **Approche A** : node Gemini adaptatif (1 branche conditionnelle interne, pas de fork DAG) | Garde le workflow à 3 nodes. Une seule logique catalogue/alias à maintenir. |
| Transport HTTP | **base64 dans JSON** (pas multipart) | Webhook n8n reste JSON-only. ~13 Mo max (sous la limite 16 Mo par défaut). Gemini attend du base64 de toute façon. |

## 3. Architecture & flux de données

```
[Frontend devis-manuel.html]
  ├── Toggle radio : ○ Texte  ○ Document (PDF/JPEG)
  ├── Mode texte : textarea existant
  └── Mode fichier : <input type="file"> → FileReader.readAsDataURL → base64 (préfixe data: strippé)
                                  ↓
            POST JSON vers webhook (un seul endpoint, deux formes valides)
                                  ↓
[n8n Webhook]                     ← inchangé
                                  ↓
[Parse avec Gemini]               ← modifié (3 blocs ajoutés)
  ├── Validation entrée (text OR file requis, MIME whitelist)
  ├── Construction `parts` adaptative :
  │     - Mode texte : [{ text: catalogue+prompt+demande }]
  │     - Mode fichier : [{ inlineData: {mimeType, data} }, { text: catalogue+prompt }]
  │     - Mode fichier : règle prompt supplémentaire → renvoyer `raw_ocr` (transcription brute)
  └── Propage `file_base64/mime/name` au node suivant si présents
                                  ↓
[Creer devis Odoo]                ← modifié (bloc d'attachement ajouté en fin)
  ├── Matching produits + sale.order create (inchangé)
  └── Si file_base64 ET sale.order créé :
        1. ir.attachment.create (res_model=sale.order, res_id=devis_id, company_id=3)
        2. sale.order.message_post (subtype mail.mt_note, attachment_ids=[…])
        → Log non-bloquant en cas d'échec (file_attached=false + attachment_error)
                                  ↓
[Réponse JSON enrichie]
  ├── Tous les champs actuels (rétro-compat byte-identique pour mode texte)
  ├── + source: 'text'|'file'
  ├── + file_attached: bool (si source=file)
  └── + raw_ocr: string (présent UNIQUEMENT si source=file ET 0 produit extrait)
```

## 4. Contrat webhook

### Payload entrant

```jsonc
// Mode texte (inchangé)
{
  "email": "client@salon.fr",
  "client_name": "Salon XYZ",
  "demande": "12 shampoings nourrissants 200ml..."
}

// Mode fichier (nouveau)
{
  "email": "client@salon.fr",
  "client_name": "Salon XYZ",
  "file_base64": "JVBERi0xLjQK...",
  "file_mime": "application/pdf",
  "file_name": "commande-mars.pdf"
}
```

### Règles de validation (au début du node Parse)

1. `demande` OU `file_base64` doit être présent et non vide → sinon `{ error: true, message: "Demande ou fichier requis." }`.
2. Si les deux sont présents → **le fichier gagne** (cohérent UX, robustesse côté serveur).
3. Si `file_base64` présent → `file_mime` ∈ `{application/pdf, image/jpeg, image/jpg}` → sinon `{ error: true, message: "Format non supporté (PDF ou JPEG uniquement)." }`.
4. Taille : pas de check explicite côté n8n (front a déjà validé <10 Mo, webhook plante naturellement à >16 Mo).

### Réponse sortante

```jsonc
{
  // Champs existants (success path, inchangés) :
  "success": true, "devis": "S00xxx", "devis_id": 123, "devis_url": "...",
  "client": "...", "partner_id": ..., "matched": [...], "unmatched": [...],
  "nb_produits": N, "nb_non_trouves": M, "montant_ht": ..., "montant_total": ...,

  // Nouveaux champs :
  "source": "text" | "file",        // toujours présent
  "file_attached": true | false,    // si source=file
  "attachment_id": 456,             // si file_attached=true
  "attachment_error": "...",        // si file_attached=false (cause de l'échec)
  "raw_ocr": "..."                  // PRÉSENT UNIQUEMENT si source=file ET matched.length===0
}
```

**Rétro-compatibilité** : zéro champ existant supprimé ou renommé. Mode texte = byte-identique à aujourd'hui.

## 5. Frontend — `docs/devis-manuel.html`

### Modifications markup

- Toggle radio "Source de la commande" : `text` (default) | `file`.
- Bloc `#textMode` (actuel, wrappé dans un container) : visible si radio=text.
- Bloc `#fileMode` (nouveau) : visible si radio=file. Contient `<input type="file" accept="application/pdf,image/jpeg,image/jpg">` + zone preview (nom + taille, thumbnail JPEG).
- CSS additionnel ~30 lignes (mode-toggle inline, file-preview avec fond gris clair, `<pre>` scrollable pour `raw_ocr`).

### Modifications JS

- Listener `change` radios → toggle `display` des deux blocs + reset state inverse.
- Listener `change` input file :
  - Vérif `file.size > 10 * 1024 * 1024` → `alert("Fichier trop volumineux (max 10 Mo).")` + reset input.
  - Vérif MIME `application/pdf` OU `image/jpeg`/`image/jpg` → idem.
  - `FileReader.readAsDataURL(file)` → strip `data:...;base64,` → garder `file_base64` en mémoire.
  - Affiche `filePreview` : `${file.name} — ${(file.size/1024/1024).toFixed(2)} Mo` (+ `<img>` thumbnail pour JPEG).
- Submit handler :
  - Mode texte : body actuel `{ email, client_name, demande }` (byte-identique).
  - Mode fichier : `{ email, client_name, file_base64, file_mime, file_name }` (pas de `demande`).
  - Validation : mode texte impose `demande` non vide ; mode fichier impose `file_base64` non vide.
- Spinner adapté : `"Lecture du document et création du devis dans Odoo..."` en mode fichier.

### Rendu résultat — cas en plus

Si réponse contient `raw_ocr` (zéro produit extrait du fichier) :
- Bloc d'erreur enrichi (`result-error` ou nouveau `result-fallback`).
- Affiche la transcription brute dans un `<pre>` scrollable, max-height ~300px.
- Bouton **"Copier vers mode texte"** qui :
  1. Bascule le toggle radio vers `text`.
  2. Pré-remplit le textarea avec `raw_ocr`.
  3. Focus + scroll vers le textarea.
  4. Reset le bloc résultat.

### Affichage `file_attached: false` (devis créé mais PJ ratée)

Banner d'avertissement non-bloquant en haut du `result-card` succès :
> ⚠ Devis créé, mais l'attachement du fichier source a échoué (`attachment_error`). Le devis est valide. Vérifie l'Odoo si besoin.

## 6. n8n — Node "Parse avec Gemini"

### Bloc 1 — Validation entrée (remplace `if (!demande)`)

```js
const fileB64 = input.body?.file_base64 || '';
const fileMime = input.body?.file_mime || '';
const fileName = input.body?.file_name || '';
const demande = input.body?.demande || '';
const source = fileB64 ? 'file' : 'text';

if (!demande && !fileB64) {
  return [{ json: { error: true, message: 'Demande ou fichier requis.' } }];
}
if (fileB64 && !['application/pdf','image/jpeg','image/jpg'].includes(fileMime)) {
  return [{ json: { error: true, message: 'Format non supporté (PDF ou JPEG uniquement).' } }];
}
```

### Bloc 2 — Prompt et `parts` adaptatifs

Le **catalogue produits + alias** existant reste byte-identique. On varie uniquement :
- L'introduction du prompt selon le mode.
- Une règle additionnelle (n°10) en mode fichier pour exiger un champ `raw_ocr`.

```js
const introText = fileB64
  ? `Le document joint (PDF ou photo) est une commande client MY.LAB. Lis-le intégralement (toutes les pages si PDF), identifie les produits et quantités demandées, et extrais-les dans le format ci-dessous.`
  : `Analyse cette demande client MY.LAB et extrais les produits et quantités.`;

const extraRule = fileB64
  ? `\n10. Inclus aussi un champ "raw_ocr" en string contenant la transcription textuelle brute des éléments de commande visibles dans le document (lignes produits, quantités, en-tête si présent). Sert de fallback si aucun produit n'est extrait.`
  : '';

// Les règles 1-9 sont reprises VERBATIM du node actuel (search_name normalisé,
// contenance par défaut, INCONNU, traduction des noms commerciaux, etc.).
// On ne change QUE l'introText et on append extraRule (règle 10) en mode fichier.
const prompt = `${introText}\n\n${catalogue}\n\nREGLES :\n[<règles 1-9 verbatim du node actuel>]${extraRule}\n\n${demande ? 'DEMANDE :\n' + demande : ''}`;

const parts = [{ text: prompt }];
if (fileB64) {
  parts.unshift({ inlineData: { mimeType: fileMime, data: fileB64 } });
}
```

Note technique : `inlineData` est placé **avant** le prompt texte (best practice Gemini : média en premier, instruction texte en second).

### Bloc 3 — Sortie enrichie

```js
const parsed = JSON.parse(text);
return [{
  json: {
    email, client_name: clientName,
    products: parsed.products || [],
    raw_demande: demande || null,
    source,
    raw_ocr: parsed.raw_ocr || null,
    file_base64: fileB64 || null,
    file_mime: fileMime || null,
    file_name: fileName || null
  }
}];
```

## 7. n8n — Node "Creer devis Odoo"

Le code de matching et création `sale.order` ne change pas. Bloc ajouté **avant le `return` final** :

```js
// Attachement Odoo (mode fichier uniquement)
if (input.file_base64 && result.success && result.devis_id) {
  try {
    const attachmentId = await odoo('ir.attachment', 'create', [{
      name: input.file_name || `commande-${result.devis}.${input.file_mime === 'application/pdf' ? 'pdf' : 'jpg'}`,
      type: 'binary',
      datas: input.file_base64,
      mimetype: input.file_mime,
      res_model: 'sale.order',
      res_id: result.devis_id,
      company_id: COMPANY_ID
    }]);

    await odoo('sale.order', 'message_post', [[result.devis_id]], {
      body: `<p>Devis généré automatiquement depuis un document uploadé via le formulaire devis manuel.</p><p><b>Fichier source :</b> ${input.file_name || '(sans nom)'}</p>`,
      attachment_ids: [attachmentId],
      message_type: 'comment',
      subtype_xmlid: 'mail.mt_note'
    });

    result.file_attached = true;
    result.attachment_id = attachmentId;
  } catch (e) {
    result.file_attached = false;
    result.attachment_error = String(e.message || e);
  }
} else {
  result.file_attached = false;
}

result.source = input.source || (input.file_base64 ? 'file' : 'text');

if (input.file_base64 && matched.length === 0 && input.raw_ocr) {
  result.raw_ocr = input.raw_ocr;
}
```

### Détails techniques critiques

- **`subtype_xmlid: 'mail.mt_note'`** = note interne, **pas** notification email aux followers. Évite le spam de Yoann à chaque devis uploadé.
- **`datas` base64 sans préfixe** — Odoo XML-RPC attend le base64 nu. Le front strippe `data:...;base64,` avant l'envoi.
- **`company_id: COMPANY_ID` (3)** — garantit que l'attachement appartient à SARL STARTEC.
- **`try/catch` isolant** — l'attachement ne peut pas faire échouer le devis. Si Odoo refuse (droits, taille, etc.), `result.file_attached = false` + `attachment_error` exposé pour debug.
- **0 produit + fichier** → pas de `sale.order` créé (bloc `if (orderLines.length > 0)` existant), mais `raw_ocr` propagé pour fallback front.

## 8. Edge cases & robustesse

| Cas | Comportement attendu |
|---|---|
| Fichier 11 Mo | Bloqué côté front (alert + reset). Webhook ne reçoit jamais. |
| MIME `image/png` ou autre | Bloqué côté front ET côté serveur (Bloc 1 validation). |
| `file_base64` corrompu | Gemini renvoie erreur → bubble up via `try/catch` natif sur `httpRequest`. |
| PDF 50 pages | Gemini lit tout (limite native 1000 pages). Latence ~10-15s, le spinner suffit. |
| Email partner manquant Odoo | Bloc existant `PARTNER_EMAIL_MISSING` s'applique avant l'attachement. Pas de devis, pas d'attachement (cohérent). |
| Attachement Odoo échoue | `file_attached: false` + `attachment_error` — devis reste créé, banner d'avertissement front. |
| Client soumet texte + fichier (force JSON) | Serveur : fichier gagne. Front : toggle empêche déjà ce cas. |
| Réseau coupé pendant upload | Erreur fetch standard → bloc `renderError` existant. |
| Gemini quota dépassé | Erreur 429 propagée → `renderError`. Quota free 1500 req/jour largement suffisant. |

## 9. Plan de test (3 scénarios obligatoires avant push live)

1. **Anti-régression mode texte** — soumettre une demande texte. Vérifier `source: 'text'`, pas de `raw_ocr`, pas de `file_attached`, payload byte-identique à l'actuel.
2. **Mode fichier — PDF lisible** — vrai bon de commande client (depuis l'historique email). Vérifier : produits matchés, `sale.order` brouillon créé, PJ visible dans Odoo, note interne dans chatter, **pas d'email envoyé** aux followers. **Inclure dans ce test un PDF ~5-10 Mo** pour valider la latence d'attachement Odoo sur gros fichier (cf. §12 risque "Attachement Odoo lent").
3. **Mode fichier — JPEG difficile (fallback)** — photo smartphone illisible ou doc non-commande. Vérifier : `raw_ocr` présent dans la réponse, aucun `sale.order` créé, front affiche transcription + bouton "Copier vers mode texte" fonctionnel.

## 10. Déploiement

1. **`docs/devis-manuel.html`** — push direct sur l'hébergement statique du formulaire (à vérifier l'emplacement actuel au moment du déploiement).
2. **Workflow n8n `e0rRHlz61Ll807gX`** — modif via script Python `GET → patch jsCode des 2 nodes → PUT`. Pattern habituel (cf. `feedback_n8n_workflow_folder.md`, `feedback_n8n_db_internals.md`). Folder Yo (id `Z2t5yT17QDhgf2XO`, project `HUgJsuxI2uJxkLLk`).
3. **Export local `docs/n8n-devis-manuel.json`** — re-générer après le PUT pour garder l'export à jour.
4. **Aucune migration Odoo** — `ir.attachment` et `mail.thread.message_post` sont des APIs standard Odoo 18 Community.

## 11. Hors-scope (explicitement)

- ❌ OCR alternatif local (Tesseract) en backup si Gemini down — quota free suffisant pour le volume.
- ❌ Workflow batch (uploader N commandes d'un coup) — à voir si besoin opérationnel apparaît.
- ❌ Détection auto langue (commande en anglais) — prompt actuel suppose FR, à voir si problème réel.
- ❌ Persistance d'historique des uploads hors Odoo — Odoo est la source de vérité (`ir.attachment`).
- ❌ Refonte UI du formulaire — modifs minimales, on garde le look DA actuel.

## 12. Risques & mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Gemini hallucine des produits non présents sur le doc | Moyenne | Devis incorrect créé | Workflow actuel a déjà `unmatched` pour produits non trouvés Odoo. Vérification manuelle du brouillon par Yoann reste la garde-fou (devis = `state: draft`). |
| Coût Gemini explose | Faible | Coût €/mois | Volume estimé <100 uploads/mois × ~2k tokens = quelques € max. Free tier 1500 req/jour. |
| Webhook payload > 16 Mo (n8n default) | Faible | Webhook 413 | Front bloque à 10 Mo, base64 = ×1.33 → max ~13 Mo. Marge confortable. |
| Attachement Odoo lent (>30s) | Faible | UX dégradée | Test sur PDF 10 Mo à faire pendant le test #2. Si problème, basculer en async (fire-and-forget côté n8n). |
| Régression du path texte | Faible | Bug critique | Test #1 anti-régression obligatoire avant push live. |

## 13. Liens & dépendances

- Workflow n8n : `e0rRHlz61Ll807gX` (actif depuis 2026-04-14, version 45)
- Webhook : `POST https://n8n.startec-paris.com/webhook/mylab-devis-manuel`
- API Gemini : `gemini-2.5-flash` v1beta (multimodal natif)
- Odoo APIs utilisées : `ir.attachment.create`, `sale.order.message_post`
- Pricelist : `TARIFS DEGRESSIFS MYLAB` id=3
- Company : SARL STARTEC id=3

---

**Fin du design.** Prochaine étape : plan d'implémentation détaillé via skill `writing-plans`.
