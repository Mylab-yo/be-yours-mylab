# Devis Manuel — Upload PDF/JPEG — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter au formulaire devis manuel un mode d'upload PDF/JPEG qui génère un devis Odoo via Gemini multimodal, avec attachement du fichier source au `sale.order` créé.

**Architecture:** Toggle either/or côté front (texte OU fichier). Webhook JSON unifié avec champs `file_base64/mime/name` optionnels. Node "Parse avec Gemini" modifié pour construire des `parts` adaptatives (texte seul OU image + texte). Node "Creer devis Odoo" modifié pour attacher l'`ir.attachment` au `sale.order` + poster note interne dans le chatter (subtype `mail.mt_note`).

**Tech Stack:** HTML/JS vanilla (formulaire statique), n8n REST API v1 (PUT workflow), Gemini 2.5 Flash multimodal (v1beta), Odoo XML-RPC (modèles `ir.attachment` + `sale.order`).

**Spec source:** `docs/superpowers/specs/2026-05-26-devis-manuel-upload-design.md`

**Workflow n8n cible:** `e0rRHlz61Ll807gX` — "MY.LAB - Devis Manuel (Formulaire)"

---

## Note importante sur l'approche de "test"

Ce repo Shopify n'a **pas de test runner** (cf. `CLAUDE.md`). Les "tests" sont des smoke tests manuels via `curl` ou via la vraie UI formulaire. Chaque tâche d'implémentation est suivie d'une vérification curl ou navigateur, pas d'un `pytest`.

---

## File Structure

**Files to create :**
- `scripts/n8n/devis_manuel/01_parse_gemini.js` — code complet du node "Parse avec Gemini" (remplace le jsCode existant)
- `scripts/n8n/devis_manuel/02_creer_devis_odoo.js` — code complet du node "Creer devis Odoo" (remplace le jsCode existant)
- `scripts/n8n/devis_manuel/patch_workflow.py` — script de déploiement (GET → patch jsCode → PUT via REST API)
- `scripts/n8n/devis_manuel/test_payloads/text_smoke.json` — fixture curl test #1
- `scripts/n8n/devis_manuel/test_payloads/build_file_payload.py` — helper pour générer JSON avec base64 d'un fichier
- `scripts/n8n/devis_manuel/README.md` — usage du dossier

**Files to modify :**
- `docs/devis-manuel.html` — toggle + file input + raw_ocr fallback UI
- `docs/n8n-devis-manuel.json` — re-export après PUT pour garder l'export local sync
- `C:\Users\startec\.claude\projects\d--be-yours-mylab\memory\project_devis_manuel_workflow.md` — documenter le nouveau mode

---

## Pre-flight checks

### Task 0: Vérifier l'environnement

**Files:** none

- [ ] **Step 0.1: Vérifier que `.env.local` contient `N8N_API_KEY`**

Run:
```bash
grep -c '^N8N_API_KEY=' .env.local
```
Expected: `1`. Si `0`, demander à Yoann la clé via la mémoire `reference_api_keys.md`.

- [ ] **Step 0.2: Vérifier que `curl` et `python3` sont disponibles**

Run:
```bash
curl --version | head -1 && python --version
```
Expected: les deux versions s'affichent.

- [ ] **Step 0.3: Vérifier l'accès au webhook**

Run:
```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://n8n.startec-paris.com/webhook/mylab-devis-manuel -H "Content-Type: application/json" -d '{}'
```
Expected: `200` (le node Parse renverra `{ error: true, message: "Le champ demande est requis." }`).

---

## Task 1: Frontend — CSS additions

**Files:**
- Modify: `docs/devis-manuel.html` (bloc `<style>`)

- [ ] **Step 1.1: Ajouter le CSS du toggle et du file mode**

Dans `docs/devis-manuel.html`, dans le bloc `<style>` juste avant `/* ── Loading ── */` (ligne ~119), ajouter :

```css
.mode-toggle {
  display: flex;
  gap: 20px;
  padding: 12px 14px;
  background: #fafafa;
  border: 1.5px solid #ddd;
  border-radius: 8px;
}
.mode-toggle label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  color: #444;
  text-transform: none;
  letter-spacing: 0;
  font-weight: 500;
  margin: 0;
}
.mode-toggle input[type="radio"] {
  accent-color: #1a1a1a;
  width: 16px;
  height: 16px;
  cursor: pointer;
}

input[type="file"] {
  width: 100%;
  padding: 12px 14px;
  border: 1.5px dashed #bbb;
  border-radius: 8px;
  background: #fafafa;
  font-family: 'DM Sans', sans-serif;
  font-size: 0.9rem;
  cursor: pointer;
}
input[type="file"]:hover { border-color: #1a1a1a; background: #fff; }

.file-preview {
  margin-top: 10px;
  padding: 12px 14px;
  background: #f0ede8;
  border-radius: 8px;
  font-size: 0.85rem;
  color: #444;
  display: none;
}
.file-preview.visible { display: block; }
.file-preview .file-meta { display: flex; justify-content: space-between; align-items: center; }
.file-preview .file-name { font-weight: 500; }
.file-preview .file-size { color: #777; }
.file-preview img { display: block; margin-top: 10px; max-width: 120px; max-height: 120px; border-radius: 6px; }

.raw-ocr-block {
  margin-top: 16px;
  padding: 12px 16px;
  background: #fef3c7;
  border-radius: 8px;
  font-size: 0.85rem;
  color: #92400e;
}
.raw-ocr-block strong { display: block; margin-bottom: 8px; }
.raw-ocr-block pre {
  background: #fff;
  border: 1px solid #fde68a;
  border-radius: 6px;
  padding: 10px 12px;
  margin: 8px 0;
  max-height: 300px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Courier New', monospace;
  font-size: 0.82rem;
  color: #333;
}
.raw-ocr-block button.btn-copy-text {
  display: inline-block;
  padding: 8px 14px;
  background: #1a1a1a;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  font-family: 'DM Sans', sans-serif;
}

.attach-warning {
  margin: -8px 0 16px 0;
  padding: 10px 14px;
  background: #fef3c7;
  border-radius: 8px;
  font-size: 0.82rem;
  color: #92400e;
}
```

- [ ] **Step 1.2: Smoke test visuel (rendu CSS sans logique)**

Ouvrir `docs/devis-manuel.html` dans le navigateur. Vérifier qu'aucun élément ne casse (le CSS ajouté n'est encore référencé nulle part). Si la page rend correctement comme avant, OK.

- [ ] **Step 1.3: Commit**

```bash
git add docs/devis-manuel.html
git commit -m "feat(devis-manuel): add CSS for upload toggle, file preview, raw_ocr fallback"
```

---

## Task 2: Frontend — Markup HTML (toggle + file mode)

**Files:**
- Modify: `docs/devis-manuel.html` (bloc `<form>`)

- [ ] **Step 2.1: Remplacer le bloc `<form>` actuel**

Dans `docs/devis-manuel.html`, remplacer :

```html
<form id="devisForm">
  <div class="row">
    <div class="field">
      <label for="email">Email client</label>
      <input type="email" id="email" name="email" placeholder="client@salon.fr">
    </div>
    <div class="field">
      <label for="clientName">Nom (optionnel)</label>
      <input type="text" id="clientName" name="client_name" placeholder="Salon XYZ">
    </div>
  </div>

  <div class="field">
    <label for="demande">Demande produits</label>
    <textarea id="demande" name="demande" required
      placeholder="Collez ici la demande du client, par exemple :&#10;&#10;12 shampoings nourrissants 200ml&#10;6 masques boucles 400ml&#10;24 cremes lissantes&#10;12 serums finition ultime"></textarea>
    <div class="hint">L'IA reconnait les noms de produits meme en langage naturel, avec ou sans accents.</div>
  </div>

  <button type="submit" id="submitBtn">Generer le devis</button>
</form>
```

par :

```html
<form id="devisForm">
  <div class="row">
    <div class="field">
      <label for="email">Email client</label>
      <input type="email" id="email" name="email" placeholder="client@salon.fr">
    </div>
    <div class="field">
      <label for="clientName">Nom (optionnel)</label>
      <input type="text" id="clientName" name="client_name" placeholder="Salon XYZ">
    </div>
  </div>

  <div class="field">
    <label>Source de la commande</label>
    <div class="mode-toggle">
      <label><input type="radio" name="mode" value="text" checked> Saisir le texte</label>
      <label><input type="radio" name="mode" value="file"> Deposer un document</label>
    </div>
  </div>

  <div class="field" id="textMode">
    <label for="demande">Demande produits</label>
    <textarea id="demande" name="demande"
      placeholder="Collez ici la demande du client, par exemple :&#10;&#10;12 shampoings nourrissants 200ml&#10;6 masques boucles 400ml&#10;24 cremes lissantes&#10;12 serums finition ultime"></textarea>
    <div class="hint">L'IA reconnait les noms de produits meme en langage naturel, avec ou sans accents.</div>
  </div>

  <div class="field" id="fileMode" style="display:none;">
    <label for="file">Document de commande</label>
    <input type="file" id="file" name="file" accept="application/pdf,image/jpeg,image/jpg">
    <div class="hint">PDF (toutes pages lues) ou JPEG. Max 10 Mo.</div>
    <div id="filePreview" class="file-preview"></div>
  </div>

  <button type="submit" id="submitBtn">Generer le devis</button>
</form>
```

Note : on a retiré l'attribut `required` du textarea (la validation est désormais dynamique en JS selon le mode).

- [ ] **Step 2.2: Smoke test visuel (toggle non câblé)**

Ouvrir `docs/devis-manuel.html`. Vérifier visuellement :
- Les 2 radios apparaissent dans une boîte gris clair.
- Le textarea est visible par défaut.
- Le bloc fileMode est caché.
- Cliquer une radio ne fait rien (pas encore de JS) — c'est attendu.

- [ ] **Step 2.3: Commit**

```bash
git add docs/devis-manuel.html
git commit -m "feat(devis-manuel): add mode toggle and file input markup"
```

---

## Task 3: Frontend — JS toggle + file handler

**Files:**
- Modify: `docs/devis-manuel.html` (bloc `<script>`)

- [ ] **Step 3.1: Ajouter les listeners toggle + file**

Dans `docs/devis-manuel.html`, juste après la ligne `const submitBtn = document.getElementById('submitBtn');` (vers ligne 297), ajouter :

```js
    const fileInput = document.getElementById('file');
    const filePreview = document.getElementById('filePreview');
    const textMode = document.getElementById('textMode');
    const fileMode = document.getElementById('fileMode');
    const demandeTextarea = document.getElementById('demande');

    // Etat du fichier upload (base64 strippé)
    let uploadedFile = null;  // { base64, mime, name, size }

    // Toggle mode texte / fichier
    document.querySelectorAll('input[name="mode"]').forEach(radio => {
      radio.addEventListener('change', (e) => {
        if (e.target.value === 'text') {
          textMode.style.display = '';
          fileMode.style.display = 'none';
        } else {
          textMode.style.display = 'none';
          fileMode.style.display = '';
        }
      });
    });

    // File input : validation + base64
    fileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      uploadedFile = null;
      filePreview.classList.remove('visible');
      filePreview.innerHTML = '';

      if (!file) return;

      const allowedMimes = ['application/pdf', 'image/jpeg', 'image/jpg'];
      if (!allowedMimes.includes(file.type)) {
        alert('Format non supporte. Utilisez PDF ou JPEG.');
        fileInput.value = '';
        return;
      }

      const MAX = 10 * 1024 * 1024;
      if (file.size > MAX) {
        alert('Fichier trop volumineux (max 10 Mo). Taille : ' + (file.size/1024/1024).toFixed(2) + ' Mo.');
        fileInput.value = '';
        return;
      }

      const reader = new FileReader();
      reader.onload = (ev) => {
        // ev.target.result = "data:application/pdf;base64,JVBERi..."
        const base64 = ev.target.result.split(',')[1] || '';
        uploadedFile = {
          base64,
          mime: file.type,
          name: file.name,
          size: file.size
        };
        renderFilePreview(file);
      };
      reader.onerror = () => {
        alert('Erreur de lecture du fichier.');
        fileInput.value = '';
      };
      reader.readAsDataURL(file);
    });

    function renderFilePreview(file) {
      const sizeMb = (file.size / 1024 / 1024).toFixed(2);
      let html = `
        <div class="file-meta">
          <span class="file-name">${esc(file.name)}</span>
          <span class="file-size">${sizeMb} Mo</span>
        </div>
      `;
      if (file.type.startsWith('image/')) {
        const url = URL.createObjectURL(file);
        html += `<img src="${url}" alt="apercu">`;
      }
      filePreview.innerHTML = html;
      filePreview.classList.add('visible');
    }
```

- [ ] **Step 3.2: Smoke test visuel — toggle + file**

Ouvrir `docs/devis-manuel.html` dans le navigateur.
1. Cliquer "Deposer un document" → le textarea disparaît, le file input apparaît.
2. Cliquer "Saisir le texte" → l'inverse.
3. En mode fichier, déposer un PDF quelconque → preview affiche le nom + taille.
4. Déposer une image JPEG → preview affiche nom + taille + thumbnail.
5. Tenter un .txt → alert "Format non supporte" + reset.
6. Tenter un fichier >10 Mo (ex: `dd if=/dev/zero of=/tmp/big.pdf bs=1M count=11` sur WSL/Linux, ou n'importe quel gros fichier) → alert "trop volumineux" + reset.

- [ ] **Step 3.3: Commit**

```bash
git add docs/devis-manuel.html
git commit -m "feat(devis-manuel): wire mode toggle and file validation/base64"
```

---

## Task 4: Frontend — JS submit + result rendering enrichi

**Files:**
- Modify: `docs/devis-manuel.html` (bloc `<script>`)

- [ ] **Step 4.1: Remplacer le submit handler et `renderResult`**

Dans `docs/devis-manuel.html`, **remplacer entièrement** le bloc submit handler `form.addEventListener('submit', ...)` actuel par :

```js
    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const email = document.getElementById('email').value.trim();
      const clientName = document.getElementById('clientName').value.trim();
      const mode = document.querySelector('input[name="mode"]:checked').value;

      let payload;
      if (mode === 'text') {
        const demande = demandeTextarea.value.trim();
        if (!demande) {
          alert('Veuillez saisir la demande produits.');
          return;
        }
        payload = { email, client_name: clientName, demande };
        loading.querySelector('p').textContent = 'Analyse de la demande et creation du devis dans Odoo...';
      } else {
        if (!uploadedFile) {
          alert('Veuillez deposer un fichier PDF ou JPEG.');
          return;
        }
        payload = {
          email,
          client_name: clientName,
          file_base64: uploadedFile.base64,
          file_mime: uploadedFile.mime,
          file_name: uploadedFile.name
        };
        loading.querySelector('p').textContent = 'Lecture du document et creation du devis dans Odoo...';
      }

      submitBtn.disabled = true;
      loading.classList.add('visible');
      resultDiv.classList.remove('visible');

      try {
        const resp = await fetch(WEBHOOK_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!resp.ok) {
          throw new Error(`Erreur HTTP ${resp.status}: ${resp.statusText}`);
        }

        const data = await resp.json();
        renderResult(data);
      } catch (err) {
        renderError(err.message);
      } finally {
        submitBtn.disabled = false;
        loading.classList.remove('visible');
      }
    });
```

- [ ] **Step 4.2: Remplacer la fonction `renderResult` pour gérer `raw_ocr` et `file_attached`**

Dans `docs/devis-manuel.html`, **remplacer entièrement** la fonction `renderResult(data)` actuelle par :

```js
    function renderResult(data) {
      if (data.error) {
        renderError(data.message || 'Erreur inconnue');
        return;
      }

      // Cas special : 0 produit extrait du fichier → afficher raw_ocr + bouton copier
      if (!data.success && data.raw_ocr) {
        renderRawOcrFallback(data.raw_ocr);
        return;
      }

      const isPartial = data.unmatched && data.unmatched.length > 0;
      const statusClass = data.success
        ? (isPartial ? 'result-partial' : 'result-success')
        : 'result-error';

      let html = `<div class="result-card ${statusClass}">`;

      if (data.success) {
        // Banner d'avertissement si attachement Odoo a echoue
        if (data.source === 'file' && data.file_attached === false) {
          const errMsg = data.attachment_error ? ` (${esc(data.attachment_error)})` : '';
          html += `<div class="attach-warning">Devis cree, mais l'attachement du fichier source a echoue${errMsg}. Le devis est valide ; verifie l'Odoo si besoin.</div>`;
        }

        html += `
          <div class="devis-number">${esc(data.devis)}</div>
          <div class="devis-client">Client : ${esc(data.client)}</div>
          <a href="${esc(data.devis_url)}" target="_blank" class="devis-link">
            Ouvrir dans Odoo
          </a>
        `;

        if (data.matched && data.matched.length > 0) {
          html += `
            <h3>Produits (${data.nb_produits})</h3>
            <table class="product-table">
              <thead>
                <tr><th>Produit</th><th>Qte</th><th>PU HT</th></tr>
              </thead>
              <tbody>
          `;
          for (const m of data.matched) {
            const pu = m.prix_unitaire != null ? m.prix_unitaire.toFixed(2) + ' €' : '-';
            html += `<tr>
              <td>${esc(m.name)}</td>
              <td>${m.quantity}</td>
              <td>${pu}</td>
            </tr>`;
          }
          html += '</tbody></table>';

          if (data.montant_ht != null) {
            html += `
              <div class="total-row">
                <span>Total HT</span>
                <span>${data.montant_ht.toFixed(2)} €</span>
              </div>
            `;
          }
          if (data.montant_total != null) {
            html += `
              <div class="total-row" style="border-top:none; padding-top:0; font-size:0.9rem; color:#666;">
                <span>Total TTC</span>
                <span>${data.montant_total.toFixed(2)} €</span>
              </div>
            `;
          }
        }
      } else {
        html += `
          <h3>Aucun produit reconnu</h3>
          <p class="error-msg">
            Aucun produit de la demande n'a pu etre matche dans Odoo.
            Verifiez les noms ou ajoutez les produits manquants dans le catalogue.
          </p>
        `;
      }

      if (data.unmatched && data.unmatched.length > 0) {
        html += `
          <div class="warnings">
            <strong>Produits non trouves (${data.nb_non_trouves})</strong>
            <ul>
              ${data.unmatched.map(u =>
                `<li>${esc(u.demande)}${u.search ? ` (recherche: "${esc(u.search)}")` : ''} — ${esc(u.raison)}</li>`
              ).join('')}
            </ul>
          </div>
        `;
      }

      html += `<button class="btn-reset" onclick="resetForm()">Nouveau devis</button>`;
      html += '</div>';

      resultDiv.innerHTML = html;
      resultDiv.classList.add('visible');
    }

    function renderRawOcrFallback(rawOcr) {
      const safeOcr = esc(rawOcr);
      const html = `
        <div class="result-card result-error">
          <h3>Document illisible par l'IA</h3>
          <p class="error-msg">Aucun produit n'a pu etre extrait du document. Voici la transcription brute :</p>
          <div class="raw-ocr-block">
            <strong>Transcription :</strong>
            <pre>${safeOcr}</pre>
            <button class="btn-copy-text" id="btnCopyToText">Copier vers mode texte</button>
          </div>
          <button class="btn-reset" onclick="resetForm()" style="margin-left:8px;">Nouveau devis</button>
        </div>
      `;
      resultDiv.innerHTML = html;
      resultDiv.classList.add('visible');

      document.getElementById('btnCopyToText').addEventListener('click', () => {
        // Basculer en mode texte
        document.querySelector('input[name="mode"][value="text"]').checked = true;
        textMode.style.display = '';
        fileMode.style.display = 'none';
        // Pre-remplir le textarea
        demandeTextarea.value = rawOcr;
        // Reset resultat + focus
        resultDiv.classList.remove('visible');
        resultDiv.innerHTML = '';
        demandeTextarea.focus();
        demandeTextarea.scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
    }
```

Note : la fonction `renderError` et `resetForm` existantes ne changent pas. Vérifier qu'elles sont toujours présentes après le `renderRawOcrFallback` et que `esc` est toujours définie en bas du script.

- [ ] **Step 4.3: Smoke test visuel — submit avec mode texte (sanity)**

Le workflow n8n n'est pas encore patché — il devrait toujours fonctionner en mode texte comme aujourd'hui.

Dans le navigateur, saisir "12 shampoings nourrissants 200ml" en mode texte avec un email valide, soumettre. Vérifier qu'un devis est créé comme avant (le node Parse actuel ne sait pas gérer `file_base64` mais ne le voit pas non plus en mode texte → comportement byte-identique).

- [ ] **Step 4.4: Commit**

```bash
git add docs/devis-manuel.html
git commit -m "feat(devis-manuel): submit handler + raw_ocr fallback rendering"
```

---

## Task 5: n8n — Code complet du node "Parse avec Gemini"

**Files:**
- Create: `scripts/n8n/devis_manuel/01_parse_gemini.js`

- [ ] **Step 5.1: Créer le dossier**

Run:
```bash
mkdir -p scripts/n8n/devis_manuel/test_payloads
```

- [ ] **Step 5.2: Écrire `01_parse_gemini.js` (code complet, incluant catalogue verbatim de l'existant)**

Créer le fichier `scripts/n8n/devis_manuel/01_parse_gemini.js` avec ce contenu **complet** (le catalogue et les règles 1-9 sont repris VERBATIM du jsCode actuel ; on ajoute uniquement Bloc 1, Bloc 2 adaptatif, Bloc 3 enrichi) :

```javascript
// Parse la demande client avec Gemini (text OR file mode)
const GEMINI_KEY = $env.GEMINI_API_KEY;

const input = $input.first().json;
const email = input.body?.email || '';
const clientName = input.body?.client_name || '';
const demande = input.body?.demande || '';
const fileB64 = input.body?.file_base64 || '';
const fileMime = input.body?.file_mime || '';
const fileName = input.body?.file_name || '';

const source = fileB64 ? 'file' : 'text';

// Validation entree
if (!demande && !fileB64) {
  return [{ json: { error: true, message: 'Demande ou fichier requis.' } }];
}
if (fileB64 && !['application/pdf', 'image/jpeg', 'image/jpg'].includes(fileMime)) {
  return [{ json: { error: true, message: 'Format non supporte (PDF ou JPEG uniquement).' } }];
}

const catalogue = `CATALOGUE PRODUITS MY.LAB (cosmetiques capillaires professionnels B2B) :

SHAMPOINGS - 200ml, 500ml, 1000ml :
nourrissant | boucles | lissant | HA repulpe | volume | purifiant | protecteur de couleur
Gloss (200ml et 1000ml uniquement)
Homme : shampoing gel douche (200ml/500ml/1000ml)

MASQUES CAPILLAIRES - 200ml, 400ml, 1000ml :
nourrissant | boucles | lissant | HA repulpe | volume | protecteur de couleur
Gloss (200ml et 1000ml uniquement)
Homme : masque intense (200ml seulement)

CREMES SANS RINCAGE - 200ml (boucles aussi en 500ml) :
boucles | HA repulpe | lissante | nourrissante | volume

SPRAYS - 200ml :
masque reparateur sans rincage | spray texturisant
ATTENTION : le nom Odoo est "masque reparateur sans rincage 200ml" SANS le prefixe "spray".

SERUMS - 50ml :
serum finition ultime | serum barbe (homme)

HUILES - 50ml :
bain miraculeux (NOM ODOO: "bain miraculeux", PAS "huile bain miraculeux") | huile a barbe (homme)

COLORISTEURS/DEJAUNISSEURS - shampoings ET masques - 200ml, 1000ml :
blond soleil | blond vanille | chocolat | cuivre | marron noisette | dejaunisseur platine
Tulipe noire : MASQUE uniquement (shampoing tulipe noire n'existe plus)
ATTENTION masque cuivre : nom Odoo = "masque coloristeur cuivre intense" (avec "intense"). Shampoing cuivre = "shampoing coloristeur cuivre" (sans "intense").

PRODUITS DISCONTINUES (TOUJOURS RETOURNER search_name = "INCONNU") :
- shampoing cerise (toutes contenances)
- masque cerise (toutes contenances)
- shampoing tulipe noire (toutes contenances)

NOMS COMMERCIAUX (alias utilises par les clients) :
- "brillance" ou "protecteur de couleur" = protecteur de couleur (shampoing/creme/masque)
- "blond polaire" ou "platine" = dejaunisseur platine
- "blond cuivre" ou "cuivre" = coloristeur cuivre
- "blond ble" ou "ble" = coloristeur blond soleil (shampoing ET masque)
- "roucou" = coloristeur cuivre (shampoing) / coloristeur cuivre intense (masque)
- "tulipe noire" = coloristeur tulipe noire (masque uniquement)
- "spray volume" ou "spray detox" ou "spray volume & detox" = spray texturisant
- "spray masque reparateur" = "masque reparateur sans rincage" (PAS de prefixe "spray" dans Odoo)
- "1L" ou "1 litre" = 1000ml
- "demi-litre" ou "0.5L" = 500ml

ATTENTION creme protectrice de couleur : le nom Odoo est "creme protectrice de couleur" (pas "creme protecteur")`;

const introText = fileB64
  ? `Le document joint (PDF ou photo) est une commande client MY.LAB. Lis-le integralement (toutes les pages si PDF), identifie les produits et quantites demandees, et extrais-les dans le format ci-dessous.`
  : `Analyse cette demande client MY.LAB et extrais les produits et quantites.`;

const extraRule = fileB64
  ? `\n10. Inclus aussi un champ "raw_ocr" en string contenant la transcription textuelle brute des elements de commande visibles dans le document (lignes produits, quantites, en-tete si present). Sert de fallback si aucun produit n'est extrait.`
  : '';

const prompt = `${introText}

${catalogue}

REGLES :
1. Retourne UNIQUEMENT du JSON valide, rien d autre
2. Format : { "products": [{ "search_name": "...", "display_name": "...", "quantity": N }] }
3. search_name = nom normalise minuscule pour Odoo, format EXACT : "type variante contenanceml"
   Exemples : "shampoing nourrissant 200ml", "masque boucles 400ml", "creme lissante 200ml",
   "serum finition ultime 50ml", "shampoing coloristeur blond soleil 200ml"
4. display_name = nom lisible avec majuscules
5. Contenance par defaut si non precisee : 200ml (50ml pour serums/huiles)
6. Quantite par defaut si non precisee : 6 (minimum B2B)
7. Si un produit demande n existe pas dans le catalogue, search_name = "INCONNU"
8. search_name doit etre le NOM EXACT tel que dans Odoo, SANS prefixe de type
   Correct: "bain miraculeux 50ml", "serum finition ultime 50ml"
   Incorrect: "huile bain miraculeux 50ml", "serum de finition ultime 50ml"
9. TOUJOURS traduire les noms commerciaux vers les noms Odoo
   "shampoing brillance" -> "shampoing protecteur de couleur 200ml"
   "creme brillance" -> "creme protectrice de couleur 200ml"
   "shampoing blond polaire" -> "shampoing dejaunisseur platine 200ml"
   "masque blond polaire 1L" -> "masque dejaunisseur platine 1000ml"
   "shampoing blond ble 1L" -> "shampoing coloristeur blond soleil 1000ml"
   "masque blond ble 1L" -> "masque coloristeur blond soleil 1000ml"
   "shampoing roucou 1L" -> "shampoing coloristeur cuivre 1000ml"
   "masque roucou 1L" -> "masque coloristeur cuivre intense 1000ml"
   "masque tulipe noire 1L" -> "masque coloristeur tulipe noire 1000ml"
   "spray masque reparateur sans rincage" -> "masque reparateur sans rincage 200ml"
   "spray volume & detox" -> "spray texturisant 200ml"${extraRule}

${demande ? 'DEMANDE :\n' + demande : ''}`;

const parts = [{ text: prompt }];
if (fileB64) {
  parts.unshift({ inlineData: { mimeType: fileMime, data: fileB64 } });
}

const response = await this.helpers.httpRequest({
  method: 'POST',
  url: 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=' + GEMINI_KEY,
  headers: { 'Content-Type': 'application/json' },
  body: {
    contents: [{ parts }],
    generationConfig: { temperature: 0.1, responseMimeType: 'application/json' }
  }
});

const text = response.candidates[0].content.parts[0].text;
const parsed = JSON.parse(text);

return [{
  json: {
    email,
    client_name: clientName,
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

- [ ] **Step 5.3: Sanity check — valider la syntaxe JS du fichier**

Run:
```bash
node --check scripts/n8n/devis_manuel/01_parse_gemini.js
```
Expected: pas d'output (= syntaxe OK). Si erreur, corriger avant de continuer.

Note : `$input`, `$env`, `this.helpers` sont des globals n8n donc Node hors n8n peut les flagger comme "undefined" — mais `node --check` vérifie uniquement la syntaxe, pas les références. OK.

- [ ] **Step 5.4: Commit**

```bash
git add scripts/n8n/devis_manuel/01_parse_gemini.js
git commit -m "feat(n8n): new Parse Gemini node code with multimodal upload support"
```

---

## Task 6: n8n — Code complet du node "Creer devis Odoo"

**Files:**
- Create: `scripts/n8n/devis_manuel/02_creer_devis_odoo.js`

- [ ] **Step 6.1: Écrire `02_creer_devis_odoo.js` (code complet)**

Créer le fichier `scripts/n8n/devis_manuel/02_creer_devis_odoo.js` avec ce contenu **complet** (le matching produits et la création `sale.order` sont VERBATIM du node actuel ; on ajoute le bloc attachement à la fin avant le `return`) :

```javascript
// Creer le devis dans Odoo (avec attachement fichier si mode upload)
const ODOO_URL = 'https://odoo.startec-paris.com';
const ODOO_DB = 'OdooYJ';
const ODOO_UID = 8;
const ODOO_KEY = 'e6d35b4261b948664841075e8fffc3510c8db437';
const COMPANY_ID = 3;
const PRICELIST_ID = 3;

const helpers = this.helpers;
const input = $input.first().json;

if (input.error) {
  return [{ json: input }];
}

const { email, client_name, products, raw_demande } = input;

async function odoo(model, method, args, kwargs) {
  const resp = await helpers.httpRequest({
    method: 'POST',
    url: ODOO_URL + '/jsonrpc',
    headers: { 'Content-Type': 'application/json' },
    body: {
      jsonrpc: '2.0',
      id: Date.now(),
      method: 'call',
      params: {
        service: 'object',
        method: 'execute_kw',
        args: [ODOO_DB, ODOO_UID, ODOO_KEY, model, method, args],
        kwargs: kwargs || {}
      }
    }
  });
  if (resp.error) throw new Error(JSON.stringify(resp.error));
  return resp.result;
}

const PRODUCT_ALIASES = {
  'shampoing brillance 200ml': 'shampoing protecteur de couleur 200ml',
  'shampoing brillance 500ml': 'shampoing protecteur de couleur 500ml',
  'shampoing brillance 1000ml': 'shampoing protecteur de couleur 1000ml',
  'creme brillance 200ml': 'creme protectrice de couleur 200ml',
  'masque brillance 200ml': 'masque protecteur de couleur 200ml',
  'masque brillance 400ml': 'masque protecteur de couleur 400ml',
  'masque brillance 1000ml': 'masque protecteur de couleur 1000ml',
  'shampoing blond polaire 200ml': 'shampoing dejaunisseur platine 200ml',
  'shampoing blond polaire 1000ml': 'shampoing dejaunisseur platine 1000ml',
  'masque blond polaire 200ml': 'masque dejaunisseur platine 200ml',
  'masque blond polaire 1000ml': 'masque dejaunisseur platine 1000ml',
  'masque blond cuivre 200ml': 'masque coloristeur cuivre 200ml',
  'masque blond cuivre 1000ml': 'masque coloristeur cuivre intense 1000ml',
  'shampoing blond cuivre 200ml': 'shampoing coloristeur cuivre 200ml',
  'shampoing blond cuivre 1000ml': 'shampoing coloristeur cuivre 1000ml',
  'spray volume 200ml': 'spray texturisant 200ml',
  'spray detox 200ml': 'spray texturisant 200ml',
  'spray volume detox 200ml': 'spray texturisant 200ml',
  'huile bain miraculeux 50ml': 'bain miraculeux 50ml',
  'shampoing blond ble 200ml': 'shampoing coloristeur blond soleil 200ml',
  'shampoing blond ble 1000ml': 'shampoing coloristeur blond soleil 1000ml',
  'masque blond ble 200ml': 'masque coloristeur blond soleil 200ml',
  'masque blond ble 1000ml': 'masque coloristeur blond soleil 1000ml',
  'shampoing roucou 200ml': 'shampoing coloristeur cuivre 200ml',
  'shampoing roucou 1000ml': 'shampoing coloristeur cuivre 1000ml',
  'masque roucou 200ml': 'masque coloristeur cuivre intense 200ml',
  'masque roucou 1000ml': 'masque coloristeur cuivre intense 1000ml',
  'masque tulipe noire 200ml': 'masque coloristeur tulipe noire 200ml',
  'masque tulipe noire 1000ml': 'masque coloristeur tulipe noire 1000ml',
  'spray masque reparateur sans rincage 200ml': 'masque reparateur sans rincage 200ml',
};

// 1. Chercher ou creer le client
let partnerId;
let partnerName = client_name || email || 'Client sans nom';

if (email) {
  const existing = await odoo('res.partner', 'search_read',
    [[['email', '=', email]]],
    { fields: ['id', 'name'], limit: 1 }
  );
  if (existing.length > 0) {
    partnerId = existing[0].id;
    partnerName = existing[0].name;
  }
}

if (!partnerId) {
  partnerId = await odoo('res.partner', 'create', [{
    name: partnerName,
    email: email || false,
    company_type: 'company',
    customer_rank: 1,
    company_id: COMPANY_ID
  }]);
}

// Validation email partner
const partnerFull = await odoo('res.partner', 'read', [[partnerId]], { fields: ['email', 'name'] });
const partnerEmail = partnerFull[0].email;
const emailRegex = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
if (!partnerEmail || !emailRegex.test(partnerEmail)) {
  return [{ json: {
    error: 'Email partner manquant ou invalide',
    error_code: 'PARTNER_EMAIL_MISSING',
    partner_id: partnerId,
    partner_name: partnerFull[0].name,
    partner_email: partnerEmail || null,
    details: "Le devis n'a pas ete cree : l'email du client dans Odoo est manquant ou invalide. Corrige-le dans Odoo puis resoumets le formulaire.",
    raw_demande: raw_demande || null
  }}];
}

// 2. Matcher les produits dans Odoo
const orderLines = [];
const matched = [];
const unmatched = [];

for (const p of products) {
  if (p.search_name === 'INCONNU') {
    unmatched.push({ demande: p.display_name, raison: 'Produit non reconnu par IA' });
    continue;
  }

  const searchName = PRODUCT_ALIASES[p.search_name] || p.search_name;

  let found = await odoo('product.product', 'search_read',
    [[['name', '=', searchName], ['sale_ok', '=', true]]],
    { fields: ['id', 'name', 'list_price', 'default_code'], limit: 1 }
  );

  if (found.length === 0) {
    found = await odoo('product.product', 'search_read',
      [[['name', 'ilike', searchName], ['sale_ok', '=', true]]],
      { fields: ['id', 'name', 'list_price', 'default_code'], limit: 3 }
    );
  }

  if (found.length === 0 && searchName.match(/\d+ml$/)) {
    const baseName = searchName.replace(/\s*\d+ml$/, '');
    found = await odoo('product.product', 'search_read',
      [[['name', 'ilike', baseName], ['sale_ok', '=', true]]],
      { fields: ['id', 'name', 'list_price', 'default_code'], limit: 5 }
    );
  }

  if (found.length > 0) {
    const prod = found[0];
    orderLines.push([0, 0, {
      product_id: prod.id,
      product_uom_qty: p.quantity
    }]);
    matched.push({
      name: prod.name,
      odoo_id: prod.id,
      sku: prod.default_code || '',
      quantity: p.quantity,
      prix_unitaire: prod.list_price
    });
  } else {
    unmatched.push({
      demande: p.display_name,
      search: p.search_name,
      raison: 'Non trouve dans Odoo'
    });
  }
}

// 3. Creer le devis
let result = {
  success: false,
  devis: null,
  devis_id: null,
  devis_url: null,
  client: partnerName,
  partner_id: partnerId,
  matched,
  unmatched,
  nb_produits: matched.length,
  nb_non_trouves: unmatched.length,
  montant_total: null
};

// 3b. Detecter la position fiscale automatiquement
let fiscalPositionId = false;
try {
  const fp = await odoo('account.fiscal.position', 'get_fiscal_position', [[partnerId]]);
  if (fp) fiscalPositionId = fp;
} catch(e) {
  try {
    const partner = await odoo('res.partner', 'read', [[partnerId]], { fields: ['country_id', 'vat'] });
    const countryId = partner[0].country_id ? partner[0].country_id[0] : false;
    const hasVat = !!partner[0].vat;
    if (countryId) {
      const fps = await odoo('account.fiscal.position', 'search_read',
        [[['auto_apply', '=', true]]],
        { fields: ['id', 'country_id', 'country_group_id', 'vat_required'], order: 'sequence' }
      );
      const groups = await odoo('res.country.group', 'search_read',
        [[['country_ids', 'in', [countryId]]]],
        { fields: ['id'] }
      );
      const groupIds = groups.map(g => g.id);
      for (const fp of fps) {
        const fpCountry = fp.country_id ? fp.country_id[0] : false;
        const fpGroup = fp.country_group_id ? fp.country_group_id[0] : false;
        if (fp.vat_required && !hasVat) continue;
        if (fpCountry && fpCountry === countryId) { fiscalPositionId = fp.id; break; }
        if (fpGroup && groupIds.includes(fpGroup)) { fiscalPositionId = fp.id; break; }
      }
    }
  } catch(e2) {}
}

if (orderLines.length > 0) {
  const orderId = await odoo('sale.order', 'create', [{
    partner_id: partnerId,
    pricelist_id: PRICELIST_ID,
    company_id: COMPANY_ID,
    order_line: orderLines,
    fiscal_position_id: fiscalPositionId || false,
  }]);

  const order = await odoo('sale.order', 'read', [[orderId]],
    { fields: ['name', 'amount_total', 'amount_untaxed'] }
  );

  result.success = true;
  result.devis = order[0].name;
  result.devis_id = orderId;
  result.devis_url = ODOO_URL + '/web#id=' + orderId + '&model=sale.order&view_type=form';
  result.montant_total = order[0].amount_total;
  result.montant_ht = order[0].amount_untaxed;
}

// 4. Attachement Odoo (mode fichier uniquement)
if (input.file_base64 && result.success && result.devis_id) {
  try {
    const attachmentName = input.file_name || `commande-${result.devis}.${input.file_mime === 'application/pdf' ? 'pdf' : 'jpg'}`;
    const attachmentId = await odoo('ir.attachment', 'create', [{
      name: attachmentName,
      type: 'binary',
      datas: input.file_base64,
      mimetype: input.file_mime,
      res_model: 'sale.order',
      res_id: result.devis_id,
      company_id: COMPANY_ID
    }]);

    await odoo('sale.order', 'message_post', [[result.devis_id]], {
      body: `<p>Devis genere automatiquement depuis un document uploade via le formulaire devis manuel.</p><p><b>Fichier source :</b> ${attachmentName}</p>`,
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
} else if (input.file_base64) {
  result.file_attached = false;
} 

result.source = input.source || (input.file_base64 ? 'file' : 'text');

// Cas special : 0 produit extrait + fichier present → exposer raw_ocr pour le front
if (input.file_base64 && matched.length === 0 && input.raw_ocr) {
  result.raw_ocr = input.raw_ocr;
}

return [{ json: result }];
```

- [ ] **Step 6.2: Sanity check syntaxe**

Run:
```bash
node --check scripts/n8n/devis_manuel/02_creer_devis_odoo.js
```
Expected: pas d'output.

- [ ] **Step 6.3: Commit**

```bash
git add scripts/n8n/devis_manuel/02_creer_devis_odoo.js
git commit -m "feat(n8n): new Creer devis Odoo node code with attachment + chatter"
```

---

## Task 7: Script de déploiement n8n (`patch_workflow.py`)

**Files:**
- Create: `scripts/n8n/devis_manuel/patch_workflow.py`
- Create: `scripts/n8n/devis_manuel/README.md`

- [ ] **Step 7.1: Écrire `patch_workflow.py`**

Créer le fichier `scripts/n8n/devis_manuel/patch_workflow.py` :

```python
"""Patch le workflow n8n 'MY.LAB - Devis Manuel (Formulaire)' avec le nouveau
code JS des nodes Parse Gemini et Creer Devis Odoo.

Usage:
    python scripts/n8n/devis_manuel/patch_workflow.py [--dry-run]

Lit:
    .env.local                           (variable N8N_API_KEY)
    01_parse_gemini.js                   (jsCode pour le node Parse)
    02_creer_devis_odoo.js               (jsCode pour le node Creer Devis)

Met a jour:
    n8n workflow id e0rRHlz61Ll807gX     (via PUT REST API)
    ../../../docs/n8n-devis-manuel.json  (export local re-genere)

Champs read-only a exclure du PUT (n8n 1.x) :
    updatedAt, createdAt, versionId, activeVersionId, triggerCount,
    isArchived, versionCounter, description, meta, pinData, staticData,
    shared, id, active, tags, activeVersion
"""
import json
import sys
import os
import urllib.request
import urllib.error
from pathlib import Path

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent.parent.parent
ENV_FILE = REPO_ROOT / ".env.local"
EXPORT_FILE = REPO_ROOT / "docs" / "n8n-devis-manuel.json"

WORKFLOW_ID = "e0rRHlz61Ll807gX"
N8N_BASE = "https://n8n.startec-paris.com"
PARSE_NODE_ID = "a1b2c3d4-0002-4000-8000-000000000002"
ODOO_NODE_ID = "a1b2c3d4-0003-4000-8000-000000000003"

READ_ONLY_FIELDS = {
    "updatedAt", "createdAt", "versionId", "activeVersionId", "triggerCount",
    "isArchived", "versionCounter", "description", "meta", "pinData",
    "staticData", "shared", "id", "active", "tags", "activeVersion"
}


def load_env_var(name: str) -> str:
    if not ENV_FILE.exists():
        sys.exit(f"ERROR: {ENV_FILE} missing")
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(name + "="):
            value = line.split("=", 1)[1].strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            return value
    sys.exit(f"ERROR: {name} not found in {ENV_FILE}")


def n8n_request(method: str, path: str, api_key: str, body: dict | None = None) -> dict:
    url = f"{N8N_BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-N8N-API-KEY", api_key)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        sys.exit(f"ERROR: HTTP {e.code} on {method} {path}\n{body_text}")


def patch_node_jscode(nodes: list, node_id: str, new_js: str, label: str) -> None:
    for node in nodes:
        if node.get("id") == node_id:
            old_len = len(node["parameters"].get("jsCode", ""))
            node["parameters"]["jsCode"] = new_js
            print(f"  [{label}] jsCode replaced: {old_len} -> {len(new_js)} chars")
            return
    sys.exit(f"ERROR: node id {node_id} ({label}) not found in workflow")


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    api_key = load_env_var("N8N_API_KEY")
    parse_js = (HERE / "01_parse_gemini.js").read_text(encoding="utf-8")
    odoo_js = (HERE / "02_creer_devis_odoo.js").read_text(encoding="utf-8")

    print(f"GET workflow {WORKFLOW_ID}")
    wf = n8n_request("GET", f"/api/v1/workflows/{WORKFLOW_ID}", api_key)
    print(f"  name: {wf.get('name')}")
    print(f"  active: {wf.get('active')}")
    print(f"  nodes count: {len(wf.get('nodes', []))}")

    patch_node_jscode(wf["nodes"], PARSE_NODE_ID, parse_js, "Parse avec Gemini")
    patch_node_jscode(wf["nodes"], ODOO_NODE_ID, odoo_js, "Creer devis Odoo")

    # Construire le payload PUT (exclure read-only)
    put_body = {k: v for k, v in wf.items() if k not in READ_ONLY_FIELDS}

    if dry_run:
        print("DRY RUN: not sending PUT")
        return

    print(f"PUT workflow {WORKFLOW_ID}")
    updated = n8n_request("PUT", f"/api/v1/workflows/{WORKFLOW_ID}", api_key, put_body)
    print(f"  versionId: {updated.get('versionId')}")
    print(f"  active: {updated.get('active')}")

    # Re-export local
    print(f"GET workflow (re-export) -> {EXPORT_FILE.relative_to(REPO_ROOT)}")
    fresh = n8n_request("GET", f"/api/v1/workflows/{WORKFLOW_ID}", api_key)
    EXPORT_FILE.write_text(json.dumps(fresh, ensure_ascii=False), encoding="utf-8")
    print(f"  size: {EXPORT_FILE.stat().st_size} bytes")

    print("\nDONE.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 7.2: Écrire `README.md` du dossier**

Créer `scripts/n8n/devis_manuel/README.md` :

```markdown
# Devis Manuel — n8n workflow patcher

Source de verite du jsCode des 2 Code nodes du workflow n8n :
- Workflow : `e0rRHlz61Ll807gX` ("MY.LAB - Devis Manuel (Formulaire)")
- Endpoint : `POST https://n8n.startec-paris.com/webhook/mylab-devis-manuel`

## Fichiers

| Fichier | Role |
|---|---|
| `01_parse_gemini.js` | jsCode du node "Parse avec Gemini" (validation, prompt, Gemini multimodal) |
| `02_creer_devis_odoo.js` | jsCode du node "Creer devis Odoo" (matching, sale.order, attachement) |
| `patch_workflow.py` | Deploie les .js vers le workflow n8n via REST API + re-export local |
| `test_payloads/text_smoke.json` | Fixture curl test #1 (mode texte) |
| `test_payloads/build_file_payload.py` | Helper pour generer un JSON avec base64 d'un fichier |

## Convention

**JAMAIS** editer le jsCode des nodes via l'UI n8n. Les fichiers .js de ce dossier sont la source de verite. Workflow:

1. Editer `01_*.js` ou `02_*.js`
2. `python patch_workflow.py --dry-run` pour valider la lecture
3. `python patch_workflow.py` pour deployer
4. Tester via le formulaire ou via curl avec les test payloads
5. Commiter les .js + l'export `docs/n8n-devis-manuel.json` re-genere

## Smoke tests

```bash
# Test 1 : mode texte (anti-regression)
curl -X POST https://n8n.startec-paris.com/webhook/mylab-devis-manuel \
  -H "Content-Type: application/json" \
  -d @test_payloads/text_smoke.json

# Test 2/3 : mode fichier (genere le payload depuis un PDF/JPEG local)
python test_payloads/build_file_payload.py /chemin/vers/commande.pdf > /tmp/file_payload.json
curl -X POST https://n8n.startec-paris.com/webhook/mylab-devis-manuel \
  -H "Content-Type: application/json" \
  -d @/tmp/file_payload.json
```
```

- [ ] **Step 7.3: Commit**

```bash
git add scripts/n8n/devis_manuel/patch_workflow.py scripts/n8n/devis_manuel/README.md
git commit -m "feat(n8n): patch script + README for devis manuel workflow"
```

---

## Task 8: Test payloads

**Files:**
- Create: `scripts/n8n/devis_manuel/test_payloads/text_smoke.json`
- Create: `scripts/n8n/devis_manuel/test_payloads/build_file_payload.py`

- [ ] **Step 8.1: Créer `text_smoke.json`**

Créer `scripts/n8n/devis_manuel/test_payloads/text_smoke.json` :

```json
{
  "email": "yoann@mylab-shop.com",
  "client_name": "TEST SMOKE - Mode texte",
  "demande": "12 shampoings nourrissants 200ml\n6 masques boucles 400ml"
}
```

- [ ] **Step 8.2: Créer `build_file_payload.py`**

Créer `scripts/n8n/devis_manuel/test_payloads/build_file_payload.py` :

```python
"""Helper : genere un JSON payload pour tester le webhook devis manuel en mode fichier.

Usage:
    python build_file_payload.py /chemin/vers/fichier.pdf > /tmp/payload.json
    python build_file_payload.py /chemin/vers/fichier.jpg --email client@salon.fr > /tmp/payload.json

Output sur stdout : JSON pret pour curl -d @-
"""
import argparse
import base64
import json
import mimetypes
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="PDF ou JPEG a inclure")
    parser.add_argument("--email", default="yoann@mylab-shop.com")
    parser.add_argument("--client-name", default="TEST SMOKE - Mode fichier")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        sys.exit(f"ERROR: {path} not found")

    mime, _ = mimetypes.guess_type(str(path))
    if mime not in {"application/pdf", "image/jpeg", "image/jpg"}:
        sys.exit(f"ERROR: unsupported mime {mime!r} (need PDF or JPEG)")

    data = path.read_bytes()
    if len(data) > 10 * 1024 * 1024:
        sys.exit(f"ERROR: file too large ({len(data)/1024/1024:.2f} Mo > 10 Mo)")

    payload = {
        "email": args.email,
        "client_name": args.client_name,
        "file_base64": base64.b64encode(data).decode("ascii"),
        "file_mime": mime,
        "file_name": path.name
    }
    json.dump(payload, sys.stdout)


if __name__ == "__main__":
    main()
```

- [ ] **Step 8.3: Commit**

```bash
git add scripts/n8n/devis_manuel/test_payloads/
git commit -m "feat(n8n): test payloads for devis manuel smoke tests"
```

---

## Task 9: Déploiement n8n (dry-run puis live)

**Files:** none (exécution scripts)

- [ ] **Step 9.1: Dry-run pour valider la lecture**

Run:
```bash
python scripts/n8n/devis_manuel/patch_workflow.py --dry-run
```
Expected output (exemple) :
```
GET workflow e0rRHlz61Ll807gX
  name: MY.LAB - Devis Manuel (Formulaire)
  active: True
  nodes count: 3
  [Parse avec Gemini] jsCode replaced: 3982 -> 4567 chars
  [Creer devis Odoo] jsCode replaced: 5821 -> 6534 chars
DRY RUN: not sending PUT
```

Si erreur "node id ... not found" : vérifier les `PARSE_NODE_ID` / `ODOO_NODE_ID` dans le script vs ceux du workflow réel (consulter `docs/n8n-devis-manuel.json` pour les vrais IDs des nodes Code).

- [ ] **Step 9.2: Deploy live**

Run:
```bash
python scripts/n8n/devis_manuel/patch_workflow.py
```
Expected: même output que dry-run + `PUT workflow ... versionId: <new-uuid>` + `GET workflow (re-export) -> docs/n8n-devis-manuel.json size: NNNN bytes`.

- [ ] **Step 9.3: Vérifier que le workflow est toujours actif**

Run:
```bash
curl -s -H "X-N8N-API-KEY: $(grep '^N8N_API_KEY=' .env.local | cut -d= -f2-)" \
  https://n8n.startec-paris.com/api/v1/workflows/e0rRHlz61Ll807gX | \
  python -c "import sys,json; w=json.load(sys.stdin); print('active:', w['active']); print('versionId:', w.get('versionId'))"
```
Expected: `active: True` + un versionId différent de celui d'avant.

Si `active: False` : ré-activer via l'UI n8n (le PUT ne devrait PAS désactiver, mais on vérifie).

- [ ] **Step 9.4: Commit l'export local re-généré**

```bash
git add docs/n8n-devis-manuel.json
git commit -m "chore(n8n): re-export devis manuel workflow after upload feature deploy"
```

---

## Task 10: Smoke test #1 — Mode texte (anti-régression)

**Files:** none (test curl)

- [ ] **Step 10.1: Appel webhook avec payload texte**

Run:
```bash
curl -s -X POST https://n8n.startec-paris.com/webhook/mylab-devis-manuel \
  -H "Content-Type: application/json" \
  -d @scripts/n8n/devis_manuel/test_payloads/text_smoke.json | \
  python -m json.tool
```

Expected: réponse JSON avec `"success": true`, `"devis": "S00XXX"`, `"source": "text"`, `"matched"` non vide, **pas de** `raw_ocr` ni `file_attached` ni `attachment_id` (sauf si `file_attached: false` via le `else if (input.file_base64)` qui ne s'exécute pas en mode texte → champ absent, correct).

- [ ] **Step 10.2: Vérifier le devis dans Odoo**

Ouvrir l'URL `devis_url` retournée par l'appel. Vérifier dans Odoo :
- Devis en état "Brouillon"
- Lignes : 12 shampoings nourrissants 200ml + 6 masques boucles 400ml
- Aucune pièce jointe dans l'onglet PJ
- Aucun message dans le chatter (à part les messages système habituels comme la création)

- [ ] **Step 10.3: Si OK, supprimer le devis test**

Dans Odoo, supprimer ce devis brouillon de test (clic droit → Supprimer, ou bouton corbeille). Note : si tu préfères le garder pour archivage, c'est OK aussi — il restera en brouillon, pas de risque.

---

## Task 11: Smoke test #2 — Mode fichier (PDF lisible, 5-10 Mo)

**Files:** none (test curl + Odoo UI)

- [ ] **Step 11.1: Choisir un PDF de bon de commande client**

Trouver un vrai bon de commande PDF (de préférence 5-10 Mo pour valider la latence sur gros fichier) dans l'historique email de Yoann ou dans les pièces jointes d'anciens devis Odoo. Sauvegarder vers `/tmp/test_bdc.pdf` (ou autre chemin local).

- [ ] **Step 11.2: Générer le payload JSON**

Run:
```bash
python scripts/n8n/devis_manuel/test_payloads/build_file_payload.py \
  /tmp/test_bdc.pdf \
  --client-name "TEST SMOKE - PDF lisible" > /tmp/file_payload.json
```
Expected: pas d'output (succès silencieux). Vérifier la taille :
```bash
wc -c /tmp/file_payload.json
```
Expected: environ 1.33× la taille du PDF original (overhead base64).

- [ ] **Step 11.3: Appel webhook avec timing**

Run:
```bash
time curl -s -X POST https://n8n.startec-paris.com/webhook/mylab-devis-manuel \
  -H "Content-Type: application/json" \
  -d @/tmp/file_payload.json | python -m json.tool
```
Expected: latence <30s. Réponse JSON avec :
- `"success": true`
- `"devis": "S00XXX"`
- `"source": "file"`
- `"file_attached": true`
- `"attachment_id": <int>`
- `"matched"` non vide (les produits extraits du PDF)

Si latence >30s, noter pour réévaluer le risque "Attachement Odoo lent" du spec §12.

- [ ] **Step 11.4: Vérifier l'attachement et le chatter dans Odoo**

Ouvrir `devis_url`. Dans Odoo :
1. Onglet pièces jointes (icône trombone à droite ou en bas) : voir le PDF, ouvrir → vérifier que le contenu est identique à l'original.
2. Chatter (en bas) : voir une note interne (icône note, **pas** message) avec "Devis genere automatiquement depuis un document uploade..." + lien vers la PJ.
3. **Vérifier dans Gmail de Yoann** : aucun email reçu de la part d'Odoo concernant ce devis (confirme que `subtype mail.mt_note` fait son job).

- [ ] **Step 11.5: Si OK, supprimer le devis test (ou garder pour archivage)**

Idem Step 10.3.

---

## Task 12: Smoke test #3 — Mode fichier (JPEG illisible, fallback raw_ocr)

**Files:** none (test curl + browser)

- [ ] **Step 12.1: Préparer une image difficile**

Choix :
- Photo smartphone très floue d'un document
- Photo d'un objet quelconque (pas une commande)
- Capture d'écran d'un mème ou d'une page web sans rapport

Sauvegarder vers `/tmp/test_illisible.jpg`.

- [ ] **Step 12.2: Générer le payload**

Run:
```bash
python scripts/n8n/devis_manuel/test_payloads/build_file_payload.py \
  /tmp/test_illisible.jpg \
  --client-name "TEST SMOKE - JPEG illisible" > /tmp/illisible_payload.json
```

- [ ] **Step 12.3: Appel webhook**

Run:
```bash
curl -s -X POST https://n8n.startec-paris.com/webhook/mylab-devis-manuel \
  -H "Content-Type: application/json" \
  -d @/tmp/illisible_payload.json | python -m json.tool
```

Expected (cas idéal) : réponse avec :
- `"success": false`
- `"source": "file"`
- `"raw_ocr": "..."` (transcription brute, peut être courte ou vide selon ce que Gemini "voit")
- `"matched": []` ou `"nb_produits": 0`
- **Aucun devis** créé dans Odoo (pas de `devis_id`)
- **Aucune PJ** créée (pas d'attachement orphelin)

Si Gemini hallucine des produits (le piège classique) : noter dans le journal de risques, mais ne pas bloquer — l'unmatched/matched logic d'Odoo absorbera (les produits hallucinés non-existants iront dans `unmatched`).

- [ ] **Step 12.4: Tester le fallback UI dans le navigateur**

Ouvrir `docs/devis-manuel.html` dans le navigateur, sélectionner mode "Deposer un document", uploader le même JPEG illisible, soumettre. Vérifier :
- Bloc d'erreur "Document illisible par l'IA" s'affiche
- Transcription brute visible dans le `<pre>` (peut être vide)
- Bouton "Copier vers mode texte" présent
- Cliquer le bouton : bascule en mode texte, textarea pré-rempli avec `raw_ocr`, focus sur textarea, scroll vers le textarea

- [ ] **Step 12.5: Documenter le résultat dans le commit suivant**

Si tout passe, continuer. Si comportement inattendu sur ce edge case, noter dans une issue interne / mémoire mais ne pas bloquer le déploiement (le path nominal mode fichier marche).

---

## Task 13: Déploiement frontend `docs/devis-manuel.html`

**Files:** dépend de l'hébergement actuel

- [ ] **Step 13.1: Identifier où est hébergé le formulaire**

Run:
```bash
git log --all --oneline -- docs/devis-manuel.html | head -10
```

Lire les messages de commit pour repérer un hint sur le déploiement (Vercel, Netlify, page Shopify, GitHub Pages, autre). Si rien de clair :

```bash
grep -rn "devis-manuel" --include="*.md" --include="*.json" --include="*.html" --include="*.liquid" -l . 2>/dev/null | head -10
```

Cela permet de voir si une page Shopify lie ce fichier, ou si c'est servi depuis un endpoint externe.

**Si pas trouvé** : demander à Yoann "où est hébergé `docs/devis-manuel.html` aujourd'hui ?" avant de continuer.

- [ ] **Step 13.2: Déployer selon l'hébergement**

Selon ce qui est trouvé :
- **Si Shopify page liquid** : copier le contenu HTML dans la page concernée (Theme Editor ou via Shopify CLI / Admin API).
- **Si Vercel/Netlify** : git push, le déploiement auto se déclenche.
- **Si GitHub Pages** : git push sur la branche pages.
- **Si hébergement custom (VPS)** : `scp` ou `rsync` vers le serveur.

Documenter le mécanisme retenu dans le commit suivant.

- [ ] **Step 13.3: Smoke test sur l'URL live**

Ouvrir l'URL publique du formulaire (pas `file://`). Refaire un test rapide :
1. Mode texte : "6 shampoings nourrissants 200ml" + email valide → devis créé
2. Mode fichier : uploader un PDF léger → devis créé + PJ visible

Si OK, le déploiement est complet.

- [ ] **Step 13.4: Commit final si non déjà fait**

Si la procédure de déploiement a impliqué un commit (cas Vercel/Netlify) :
```bash
git push origin feature/stock-mrp-setup  # ou la branche actuelle
```

---

## Task 14: Mise à jour mémoire

**Files:**
- Modify: `C:\Users\startec\.claude\projects\d--be-yours-mylab\memory\project_devis_manuel_workflow.md`

- [ ] **Step 14.1: Ajouter la section "Mode fichier (upload)" au memo existant**

Éditer `C:\Users\startec\.claude\projects\d--be-yours-mylab\memory\project_devis_manuel_workflow.md` : ajouter, après la section "Architecture (3 nodes)" et avant "Système d'alias", la section suivante :

```markdown
## Mode fichier (upload PDF/JPEG) — depuis 2026-05-26
Le formulaire accepte un upload PDF (multi-pages) ou JPEG (<10 Mo) en alternative au textarea.
Toggle either/or cote front : `source` = `"text"` ou `"file"` dans la reponse.

### Flux mode fichier
1. Front : FileReader → base64 strippe → POST `{email, client_name, file_base64, file_mime, file_name}`
2. Node Parse : construit `parts: [{inlineData}, {text}]` pour Gemini multimodal, ajoute regle 10 pour exiger `raw_ocr`
3. Node Odoo : matching produits standard, puis si `sale.order` cree → `ir.attachment.create` + `sale.order.message_post` (subtype `mail.mt_note` = note interne, pas notification email)
4. Si 0 produit extrait + fichier present → reponse contient `raw_ocr` (transcription brute), front affiche fallback + bouton "Copier vers mode texte"

### Source de verite du jsCode
Les fichiers `scripts/n8n/devis_manuel/01_parse_gemini.js` et `02_creer_devis_odoo.js` sont la source de verite. **JAMAIS** editer le jsCode des nodes via l'UI n8n. Pour deployer : `python scripts/n8n/devis_manuel/patch_workflow.py`.

### Champs additionnels dans la reponse webhook
- `source` : `"text"` | `"file"` (toujours present)
- `file_attached` : bool (si source=file, true si attachement Odoo reussi)
- `attachment_id` : int (si file_attached=true)
- `attachment_error` : string (si file_attached=false, cause)
- `raw_ocr` : string (UNIQUEMENT si source=file ET matched.length===0)
```

- [ ] **Step 14.2: Mettre à jour le MEMORY.md index si nécessaire**

Vérifier que la ligne d'index pointe bien vers le fichier mis à jour. Pas de changement requis ici (le nom du fichier est inchangé), mais la date "Updated" dans l'index peut être bumpée :

Run:
```bash
grep "project_devis_manuel_workflow" "C:\Users\startec\.claude\projects\d--be-yours-mylab\memory\MEMORY.md"
```

Si la ligne existe avec une date `2026-04-14`, la mettre à jour à `2026-05-26`. Sinon laisser tel quel.

- [ ] **Step 14.3: Pas de commit nécessaire**

Les fichiers de mémoire ne sont pas dans le repo git (ils sont sous `C:\Users\startec\.claude\projects\...`).

---

## Self-review (rappel pour l'exécutant)

Avant de marquer le plan complet :

1. **Coverage du spec** :
   - Section 3 architecture → Tasks 1-4 (front) + 5-7 (n8n)
   - Section 4 contrat webhook → validation Bloc 1 dans Task 5 + payload front Task 4
   - Section 5 frontend → Tasks 1-4
   - Section 6 Parse Gemini → Task 5
   - Section 7 Odoo → Task 6
   - Section 8 edge cases → couverts par validations dans Tasks 3, 5, 6 + tests 10-12
   - Section 9 plan de test → Tasks 10, 11, 12
   - Section 10 déploiement → Tasks 9 (n8n) + 13 (front)
   - Section 11 hors-scope → respecté (rien d'implémenté)
   - Section 12 risques → mitigés par try/catch, validations, tests

2. **Anti-régression mode texte** : Task 10 garantit que le path texte reste byte-identique.

3. **Rollback plan** : en cas de bug bloquant après Task 9, rollback rapide :
   ```bash
   git show HEAD~1:docs/n8n-devis-manuel.json > /tmp/prev.json
   # Patcher le script pour PUT /tmp/prev.json (ou re-PUT manuellement)
   ```
   Le workflow étant versionné côté n8n, on peut aussi revenir à un versionId précédent via l'UI n8n.

---

**Fin du plan.**
