# MY.LAB Studio — Plan d'implémentation Sprint 0 — v1.1

**Date** : 2026-05-25
**Auteur** : Yoann Durand + Claude (review)
**Réf. spec** : MY.LAB Studio Spec v2.1
**Durée cible** : ~1,5 sem de setup + boucle d'itération qualité (durée contrôlée par Yoann)
**Statut** : prêt à exécuter

---

## 0. Changelog

### 0.1 v1 → v1.1 (cette révision — review du plan Sprint 0)

10 ajouts intégrés à la v1 de Yoann. Aucun pivot, des précisions chirurgicales pour fiabiliser l'exécution.

| # | Précision | Section |
|---|---|---|
| **B1** *(décidé)* | **OS : WSL2 sur Windows + Ubuntu LTS** — garde Windows pour env MY.LAB habituel, ComfyUI/Docker tournent sous WSL2. Setup détaillé (driver NVIDIA Windows, CUDA WSL2, Docker Desktop backend WSL2, NVIDIA Container Toolkit, .wslconfig 24 Go) | §3.1 |
| **B2** *(décidé)* | **Containerisation Docker dès Sprint 0** confirmée — Docker Desktop avec backend WSL2 + NVIDIA Container Toolkit. Même image conteneur réutilisée SP2 pour worker cloud failover, zéro rework | §3.2, §4.1 |
| **B3** *(important)* | **Configuration `extra_model_paths.yaml`** pour que l'arborescence par rôle marche sans symlinks ni surprise | §4.2 |
| **B4** *(important)* | **Budget temps par passe complète <45 min**, ajouté au DoD. Réduire la matrice si dépassement | §1.2, §6.4 |
| **B5** *(important)* | **Juges multiples** pour la grille §9.1 (toi + Laure + 2-3 pilotes en aveugle), pas toi seul | §9.1 |
| **B6** | **Stratégie warm/cold** explicite : grouper jobs par étape pour minimiser I/O de chargement | §5, §7 |
| **B7** | **Filename pattern** avec timestamp + config hash pour préserver l'historique des passes | §7.1 |
| **B8** | **Tokens HuggingFace gated** (IC-Light, FLUX, certains Hunyuan) à anticiper avant Jour 1 | §2 |
| **B9** | **WebSocket /ws** plutôt que polling /history pour le banc d'essai (plus propre, plus rapide) | §7.2 |
| **B10** | **Mesurer aussi le temps de chargement** par étape, pas que VRAM + inference | §7.1 |

### 0.2 Reports vers la spec V2.2

À intégrer au prochain tour de spec :
- **Plan B §9.3 revu** (restreindre répertoire templates au lieu de "fallback LoRA") → spec §10 R1b mitigation, §13
- **D-vidéo-fidélité** (a/b/c, le compositing résout l'image mais pas la vidéo) → spec §12 D12

---

## 1. Objectifs et critères de sortie

### 1.1 Objectif
Monter le poste de génération local, établir l'**architecture en étapes** du pipeline compositing, et produire une **décision GO / NO-GO argumentée** sur le compositing-first, sans rien construire de l'infra aval (pas de dashboard, pas de VPS gateway, pas de Stripe/Shopify).

### 1.2 Critères de sortie (Definition of Done)
Sprint 0 est terminé quand **tous** les points suivants sont vrais :

- [ ] Le PC génère un visuel compositing **bout-en-bout en local** (scène → insertion produit → relight → upscale) sur la batterie de test.
- [ ] Le **headroom VRAM est mesuré et connu** par étape (A4), pas estimé.
- [ ] La **qualité de détourage est mesurée** sur photos cosmétiques réelles (D1c) avec un taux de validation auto chiffré.
- [ ] Le **banc d'essai est opérationnel** : changer un modèle + relancer la batterie = une commande.
- [ ] **Une passe complète de la matrice tourne en <45 min** *(B4)*. Si dépassement, réduire la matrice (5×4×1 seed = 20 images) en itération préliminaire.
- [ ] Le **smoke test cloud** passe : un output est poussé sur R2, supprimé en local, re-téléchargé via URL signée.
- [ ] La **porte A1 est tranchée** contre des critères écrits *avant* d'avoir vu les images, donnant GO (on enchaîne Sprint 1) ou NO-GO (plan B, §9).
- [ ] **Notation effectuée par 3+ juges** dont au moins 1 pilote en aveugle *(B5)*.

---

## 2. Pré-requis matériel et accès (à préparer en amont)

| Élément | Détail | Statut |
|---|---|---|
| Onduleur UPS | Eaton 5E ou APC Back-UPS (~120 €) — protège un job/training en cours d'une micro-coupure (pas un rôle serveur, cf. spec C2) | À acheter |
| Espace disque | Prévoir ~150-300 Go libres sur le NVMe pour les checkpoints/modèles testés (plusieurs candidats coexistent pendant l'itération) | À vérifier |
| Photos produit de test | 5 flacons réels **délibérément variés** (voir §6) — idéalement de vrais produits clients MY.LAB | À réunir |
| Compte Cloudflare R2 | Bucket de test + clés API (S3-compatible) pour le smoke test cloud | À créer |
| **Token HuggingFace** *(B8)* | Compte HF + token write/read + acceptation des licences gated **avant Jour 1** : IC-Light, FLUX (si testé), HunyuanVideo. Sans ça, les téléchargements bloquent en silence pendant l'install | **À créer** |
| **Juges pour notation** *(B5)* | Toi + Laure + 2-3 pilotes MY.LAB recrutés tôt pour noter en aveugle la 1ère passe convergée | **À recruter** |

---

## 3. Tâche 1 — Socle système (Jour 1)

But : un environnement GPU propre, reproductible, versionné.

### 3.1 B1 — OS retenu : **WSL2 sur Windows** *(B1 — décidé)*

Tu gardes Windows comme environnement principal pour ton workflow MY.LAB habituel (Odoo scripts, Shopify CLI, IDE, etc.), et tu fais tourner ComfyUI + Docker dans Ubuntu sous WSL2.

**Stack WSL2 à installer Jour 1 :**

1. **WSL2 + Ubuntu LTS** : `wsl --install -d Ubuntu-24.04` (ou 22.04 LTS si tu préfères la stabilité éprouvée)
2. **Pilote NVIDIA Windows à jour** : depuis Windows (pas dans WSL2). Le driver Windows expose CUDA à WSL2 via le passthrough natif Microsoft. **Pas besoin d'installer de driver NVIDIA dans WSL2** — c'est une erreur courante qui casse le passthrough.
3. **CUDA Toolkit dans WSL2** : `cuda-toolkit-12-X` via le repo officiel NVIDIA pour WSL (PAS le repo Linux générique qui ré-installe le driver et casse tout). Vérifier : `nvidia-smi` dans WSL2 doit voir la 3090 avec 24 Go.
4. **Docker Desktop pour Windows** + activer le backend WSL2 dans les paramètres. Plus rapide qu'installer Docker dans Ubuntu directement, et l'intégration GUI Windows est utile.
5. **NVIDIA Container Toolkit dans WSL2** : `nvidia-container-toolkit` pour que `docker run --gpus all` fonctionne depuis Docker Desktop (Settings → Resources → WSL Integration → activer pour ton distro Ubuntu).
6. **Test passthrough GPU dans conteneur** : `docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi` doit afficher la 3090.

**Points d'attention WSL2 spécifiques :**
- **Stockage des modèles** : garde tes modèles dans le filesystem WSL2 (`/home/yoann/mylab-studio/models`), PAS sur `/mnt/c/...` (le mount Windows). L'I/O disque WSL2 natif est ~5-10× plus rapide que `/mnt/c`. Charger SDXL depuis `/mnt/c` peut prendre 60s au lieu de 10s.
- **Mémoire WSL2** : par défaut WSL2 alloue 50 % de la RAM Windows. Sur ta config 32 Go, ça fait 16 Go pour WSL2 — peut être juste pour ComfyUI + Docker. Créer `~/.wslconfig` côté Windows pour allouer 24-28 Go à WSL2 (laisse 4-8 Go à Windows) :
  ```ini
  [wsl2]
  memory=24GB
  processors=12
  swap=8GB
  ```
- **Redémarrage propre** : `wsl --shutdown` depuis Windows pour relancer WSL2 si tu modifies `.wslconfig`. Sinon les changements ne s'appliquent pas.

### 3.2 Setup
1. **UPS** : branchement PC + écran, test de bascule (couper le secteur, vérifier que le PC tient et reçoit l'alerte). Activer l'arrêt propre automatique si l'autonomie tombe sous un seuil.
2. **Pilotes GPU + CUDA** : installer la version de pilote NVIDIA et le toolkit CUDA compatibles avec le framework d'inférence visé. Vérifier `nvidia-smi` (carte détectée, 24 Go visibles) et la disponibilité CUDA côté Python.
3. **Environnement Python isolé** : un venv ou conda dédié, versions épinglées (`requirements.txt` ou `environment.yml` committé). Aucune install globale.
4. **Docker + Docker Compose** *(B2)* : installer Docker Engine (Linux) ou Docker Desktop (Windows/WSL2). Tester `docker run hello-world` puis `docker run --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi` (vérifie le passthrough GPU).
5. **Git** : un dépôt `mylab-studio-worker` qui versionnera workflows ComfyUI, scripts du banc d'essai, configs et logs de résultats. Dockerfile + docker-compose.yml committés dès le début.

**Livrable** : `nvidia-smi` OK + `docker --gpus all` OK + un `requirements.txt` committé + dépôt initialisé avec Dockerfile.

---

## 4. Tâche 2 — ComfyUI + arborescence modèle "plug-and-play" (Jour 2)

But : pouvoir déposer **n'importe quel modèle** et qu'il soit immédiatement utilisable, sans réorganiser quoi que ce soit. C'est ce qui rend ton itération fluide.

### 4.1 Installation containerisée *(B2)*

Installer ComfyUI **dans un Dockerfile**, pas bare-metal. Tu lances `docker compose up` au lieu de `python main.py`. Avantages :
- Reproductibilité parfaite (devs futurs, freelance SP2 → SP7 : `git clone && docker compose up`)
- Isolation des dépendances Python (pas de conflit avec ton venv système)
- **Prêt pour SP2 sans rework** : la même image conteneur tournera sur le worker cloud failover (spec §7.1)
- Versionnement clair des modèles via volumes montés

```dockerfile
# Squelette indicatif — à compléter
FROM nvidia/cuda:12.4.0-cudnn-devel-ubuntu22.04
RUN apt-get update && apt-get install -y python3 python3-pip git wget
WORKDIR /app
RUN git clone https://github.com/comfyanonymous/ComfyUI.git
WORKDIR /app/ComfyUI
RUN pip install -r requirements.txt
COPY extra_model_paths.yaml ./
EXPOSE 8188
CMD ["python3", "main.py", "--listen", "0.0.0.0"]
```

```yaml
# docker-compose.yml indicatif
services:
  comfyui:
    build: .
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    volumes:
      - ./models:/app/ComfyUI/models     # montage par rôle (cf. §4.2)
      - ./workflows:/workflows           # workflows JSON versionnés
      - ./fixtures:/fixtures             # photos test
      - ./results:/results               # outputs banc d'essai
    ports:
      - "8188:8188"
```

### 4.2 Arborescence des modèles (par **rôle**, pas par nom) + `extra_model_paths.yaml` *(B3)*

Structure les dossiers par fonction du pipeline. ComfyUI s'attend par défaut à `models/checkpoints/`, `models/loras/`, `models/controlnet/` — donc **on configure `extra_model_paths.yaml`** pour que ton arborescence par rôle soit reconnue sans symlinks :

```
models/
  scene/            # modèle(s) de génération de scène         → mapped to "checkpoints"
  controlnet/       # contrôle de composition (depth/canny/…)  → mapped to "controlnet"
  ip_adapter/       # adhérence Brand DNA / mood board          → mapped to "ipadapter"
  relight/          # harmonisation lumière du produit          → mapped per-model
  segmentation/     # détourage produit                          → custom path
  upscale/          # finition                                   → mapped to "upscale_models"
  video/            # reels (étape séparée)                      → mapped to "checkpoints"
```

`extra_model_paths.yaml` (à committer dans le repo) :

```yaml
mylab_studio:
  base_path: /app/ComfyUI/models
  checkpoints: scene/
  controlnet: controlnet/
  ipadapter: ip_adapter/
  loras: scene/loras/        # si LoRA optionnelle utilisée
  upscale_models: upscale/
  custom_nodes: ../custom_nodes/
```

Pour les rôles non-standard (relight, segmentation), les custom nodes correspondants gèrent leurs propres chemins — à documenter au cas par cas dans le README.

> Les candidats cités dans la spec (SDXL, ControlNet Depth/Canny, IP-Adapter, IC-Light, BiRefNet/SAM/rembg, RealESRGAN, LTX/Hunyuan) sont des **points de départ optionnels**. Le banc d'essai est agnostique : tu les remplaces ou les compares librement.

### 4.3 Custom nodes
Installer uniquement les custom nodes nécessaires aux rôles ci-dessus que tu décides d'évaluer. Noter chaque node + version dans le README (reproductibilité). Les installer **dans le conteneur** via `RUN` au Dockerfile (pas en runtime) pour rester reproductible.

**Livrable** : `docker compose up` démarre ComfyUI, API répond sur `http://localhost:8188`, arborescence en place, un premier modèle de scène déposé génère une image de test.

---

## 5. Tâche 3 — Architecture **en étapes** du pipeline (Jour 3)

But : poser dès le départ la bonne architecture, qui rend le sujet VRAM (A4) largement non bloquant et rend les modèles interchangeables étape par étape.

### 5.1 Le pipeline est SÉQUENTIEL, pas simultané
Chaque étape charge ses modèles, produit sa sortie, libère la VRAM, passe la main. On ne charge **jamais** scène + controlnet + ip-adapter + relight + upscale en même temps.

```
Étape A — Scène      : [scene + controlnet + ip_adapter]  → image de fond (zone produit réservée)
Étape B — Insertion  : [aucun modèle GPU lourd]            → colle le PNG alpha (pré-calculé à l'onboarding)
Étape C — Relight    : [relight]                            → harmonise lumière/ombre du produit
Étape D — Upscale    : [upscale]                            → finition
```

Conséquence directe : le **pic VRAM réel** est le max d'une étape (typiquement l'étape A), pas la somme des étapes. C'est l'architecture par défaut saine ; le « chaînage » n'est pas un plan B, c'est le design.

### 5.2 Stratégie warm vs cold *(B6)*

Le séquentiel par étape libère la VRAM entre étapes, mais ajoute un coût I/O de chargement à chaque transition (SDXL ~7 Go = ~5-15s depuis NVMe). Pour un job isolé c'est OK ; pour une matrice de 60 images c'est gâché.

**Stratégie obligatoire pour le banc d'essai et l'usage production :**
- **Grouper les jobs par étape, pas par image** : faire 60 étapes A consécutives (modèle scène reste warm) → puis 60 étapes B (compositing CPU, instant) → puis 60 étapes C (relight reste warm) → puis 60 étapes D (upscale reste warm).
- Le temps de chargement modèle = payé 1× par étape, pas 60× par image.
- **À implémenter dès `bench.py`** (§7.2) — pas en optimisation tardive.

Cette stratégie n'est pas seulement pour la perf banc d'essai : elle correspond aussi au pattern production où plusieurs clients génèrent en parallèle sur le même template (les workers cloud failover peuvent grouper par template pour minimiser cold starts).

### 5.3 Contrat d'étape (pour l'interchangeabilité)
Définis pour chaque étape une **entrée/sortie stable** (chemins d'images + params), implémentée comme un workflow ComfyUI séparé exporté en JSON versionné :

```
workflows/
  stage_a_scene.json
  stage_c_relight.json
  stage_d_upscale.json
```

Tant qu'une étape respecte son contrat (mêmes entrées/sorties), tu changes le modèle à l'intérieur sans toucher au reste. **C'est ça qui rend ton itération modèle indolore.**

> Note : le détourage (segmentation → PNG alpha) **n'est pas dans le pipeline de génération**. Il a lieu à l'onboarding, une fois par produit, et le PNG alpha est stocké côté cloud (spec §7bis). À Sprint 0 on l'évalue séparément (§7, tâche 4).

**Livrable** : 3 workflows JSON d'étape, chacun testé isolément, avec un contrat d'E/S documenté dans le README.

---

## 6. Tâche 4 — Batterie de test (fixtures) (Jour 3-4)

But : un jeu de tests **qui stresse le pipeline là où il casse**, fixé une fois pour toutes pour que toutes tes itérations soient comparables.

### 6.1 Les 5 flacons (volontairement difficiles)
| # | Type de produit | Ce qu'il stresse |
|---|---|---|
| 1 | Flacon opaque mat, étiquette claire | Baseline "facile" — sert de référence haute |
| 2 | Verre transparent, liquide visible | Détourage (frontière ambiguë) + relight (transparence) |
| 3 | Pompe / surface chromée réfléchissante | Reflets parasites au détourage + cohérence des reflets en relight |
| 4 | Pot large / jar avec couvercle | Géométrie différente, ombre de contact |
| 5 | Produit sombre sur fond sombre voulu | Contraste de bord, halo de découpe |

### 6.2 Deux "marques fictives" (Brand DNA)
Prépare 2 mood boards / palettes distincts (ex. "bohème terracotta" vs "clinique minimal froid") pour vérifier que le Brand DNA produit des ambiances **visiblement différentes** sur le même template (anti-collision, spec §4.3).

### 6.3 Templates de test
Reprends les 4 ambiances majeures de la spec §4.2 : salle de bain bohème, vanity, packshot studio, lifestyle outdoor. Un prompt paramétrique par ambiance.

### 6.4 Matrice et budget temps *(B4)*

`5 flacons × 4 templates × 2-3 seeds` ≈ **40-60 images par passe**. C'est le **contact sheet** qui révèle où ça casse, et qui se rejoue à l'identique à chaque changement de modèle.

**Budget temps cible : <45 min par passe complète** sur le PC, sinon la boucle d'itération devient pénible.
- À ~30s/image bout-en-bout (~10s scène + ~5s relight + ~5s upscale + I/O) = ~30 min pour 60 images. OK.
- Avec stratégie warm (§5.2), gain attendu de 20-30 %.
- **Si dépassement** : réduire à `5×4×1 seed = 20 images` en itération préliminaire, et ne tourner la matrice complète 3 seeds que sur les passes convergées (1-2× par itération sérieuse).

**Livrable** : un dossier `fixtures/` (photos produit, mood boards, prompts templates) + un fichier `test_matrix.yaml` décrivant la matrice complète et la matrice réduite.

---

## 7. Tâche 5 — Banc d'essai + évaluation détourage (Jour 4-5)

But : une commande qui rejoue la matrice, capture les métriques, et assemble les sorties pour comparaison. C'est l'outil central de ta boucle d'itération.

### 7.1 Ce que le banc capture automatiquement, par étape et bout-en-bout
- **Pic VRAM** (`torch.cuda.max_memory_allocated` réinitialisé par étape, ou échantillonnage `nvidia-smi`)
- **Latence inference** (`time.perf_counter()` par étape + total)
- **Temps de chargement modèle** *(B10)* : mesurer séparément le `load_state_dict` (cold start) vs l'inference (warm), pour décider la stratégie §5.2 et planifier les cold starts cloud SP2
- **Chemins des sorties** + un **contact sheet** (grille) pour l'œil
- **Config exacte** (quels modèles à quelle étape, seeds) écrite à côté des résultats → reproductibilité
- **Filename pattern *(B7)*** : `{bottle}_{template}_{seed}_{config_hash}_{timestamp}.png` → ne jamais écraser une passe historique

### 7.2 Squelette de banc d'essai (à adapter — agnostique au modèle) *(B6 + B9)*

```python
# bench.py — rejoue la matrice de test contre le pipeline ComfyUI local.
# Aucun modèle codé en dur : tout vient de la config + des workflows JSON.
import json, time, itertools, pathlib, hashlib, asyncio, websockets, requests, yaml
import torch

COMFY_HTTP = "http://127.0.0.1:8188"
COMFY_WS = "ws://127.0.0.1:8188/ws"
RESULTS = pathlib.Path("results") / time.strftime("%Y%m%d-%H%M%S")
RESULTS.mkdir(parents=True, exist_ok=True)

async def run_workflow_ws(workflow_path, inputs):
    """B9: WebSocket events plutôt que polling /history — plus rapide, plus propre."""
    wf = json.loads(pathlib.Path(workflow_path).read_text())
    # ... injecter inputs dans les nodes ...
    torch.cuda.reset_peak_memory_stats()
    t_load_start = time.perf_counter()
    # ... handle load timing via comfyui events ...
    t_infer_start = time.perf_counter()
    async with websockets.connect(COMFY_WS) as ws:
        r = requests.post(f"{COMFY_HTTP}/prompt", json={"prompt": wf}).json()
        prompt_id = r["prompt_id"]
        async for msg in ws:
            data = json.loads(msg)
            if data.get("type") == "executing" and data["data"]["node"] is None and data["data"]["prompt_id"] == prompt_id:
                break  # workflow done
    t_total = time.perf_counter() - t_infer_start
    vram_peak = torch.cuda.max_memory_allocated() / 1e9
    out = fetch_output(prompt_id)
    return out, t_total, vram_peak, (t_infer_start - t_load_start)

def config_hash(cfg):
    """B7: hash stable pour filenames."""
    return hashlib.sha1(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:8]

async def run_matrix_grouped(cfg, matrix):
    """B6: group by stage instead of by image to minimize cold starts."""
    cfg_hash = config_hash(cfg)
    ts = time.strftime("%Y%m%d-%H%M%S")
    records = []
    # Step 1: warm scene model, generate all scenes
    scenes = {}
    for b, t, s in itertools.product(matrix["bottles"], matrix["templates"], matrix["seeds"]):
        scene_path, t_total, vram, t_load = await run_workflow_ws(cfg["stage_a"], {"bottle": b, "template": t, "seed": s})
        scenes[(b, t, s)] = scene_path
        records.append({"stage": "scene", "key": (b, t, s), "latency": t_total, "vram": vram, "load_time": t_load})
    # Step 2-4: composite + relight + upscale (grouped by stage)
    for b, t, s in itertools.product(matrix["bottles"], matrix["templates"], matrix["seeds"]):
        comp = composite(scenes[(b, t, s)], alpha_png(b))           # CPU only
        relit, t_total, vram, t_load = await run_workflow_ws(cfg["stage_c"], {"image": comp})
        final, t_total, vram, t_load = await run_workflow_ws(cfg["stage_d"], {"image": relit})
        out_path = RESULTS / f"{b}_{t}_{s}_{cfg_hash}_{ts}.png"
        save(final, out_path)
    return records

async def main():
    cfg = yaml.safe_load(open("config.yaml"))
    matrix = yaml.safe_load(open("test_matrix.yaml"))
    records = await run_matrix_grouped(cfg, matrix)
    json.dump({"config": cfg, "records": records}, open(RESULTS / "log.json", "w"), indent=2)
    build_contact_sheet(RESULTS)
    print_summary(records)  # pics VRAM + latences + load times par étape

if __name__ == "__main__":
    asyncio.run(main())
```

Boucle d'itération concrète : tu changes un modèle dans `config.yaml`, tu lances `python bench.py`, tu obtiens un nouveau dossier `results/` horodaté avec contact sheet + métriques. Tu compares les dossiers entre eux.

### 7.3 Évaluation du détourage (D1c) — protocole séparé
Sur les 5 flacons **plus** 3-4 photos « smartphone moyen » volontairement imparfaites (mauvaise lumière, fond chargé) :
1. Passe chaque candidat de segmentation que tu veux tester.
2. Inspecte le PNG alpha à **200 % de zoom** sur les zones critiques (verre, reflets, ombre au sol, bouchon).
3. Classe chaque résultat : **OK auto / récupérable par re-upload / nécessite retouche manuelle**.
4. Métrique : **% validé au 1ᵉʳ détourage auto** (cible spec : >70 % auto, <15 % manuel).

**Livrable** : `bench.py` opérationnel + un premier `results/` complet + un tableau d'éval détourage par candidat.

---

## 8. Tâche 6 — Smoke test cloud + note vidéo (Jour 6)

### 8.1 Smoke test R2 (établit la discipline §7bis dès maintenant)
Petit script `cloud_smoke.py` qui : prend un PNG de sortie → l'upload sur le bucket R2 (SDK S3-compatible) → **supprime le fichier local** → génère une **URL signée** → re-télécharge et vérifie l'intégrité (hash). Ça prouve les credentials, le SDK et le pattern « rien ne reste en local » avant de bâtir SP1/SP2.

### 8.2 Note vidéo (à cadrer, pas à résoudre ici)
La fidélité produit en **image** est résolue par le compositing du PNG. En **vidéo**, incruster un PNG figé ne transfère pas directement (relight image-par-image, mouvement). Pendant ton itération modèle vidéo, tranche tôt l'une des trois voies et note ton choix :
- **(a)** produit composité **statique**, caméra/scène animée autour → simple, fidélité conservée, mouvement limité ;
- **(b)** vidéo générative pleine → mouvement riche, **fidélité produit dégradée** (à mesurer) ;
- **(c)** approche dédiée (ex. animation de calques du composite).

Ce n'est pas un livrable de Sprint 0, mais **ajoute-le aux décisions ouvertes** (D-vidéo-fidélité, à reporter spec V2.2 §12 D12) : aujourd'hui l'argument « le flacon affiché = le flacon livré » ne tient strictement que pour l'image.

**Livrable** : `cloud_smoke.py` qui passe + une ligne tranchée (a/b/c provisoire) dans le journal de décision.

---

## 9. Tâche 7 — Boucle d'itération + porte de décision A1 (Jour 6 → ouvert)

C'est ici que **tu** itères jusqu'à atteindre le niveau visé. Le plan ne fixe pas la durée ; il fixe la **méthode** et le **critère d'arrêt**.

### 9.1 Critères d'acceptabilité écrits AVANT de regarder les images (gate A1)

Pour que la porte soit honnête, fige la grille de notation et le seuil **avant** la première passe. Proposition (ajuste les seuils, ils sont tiens) :

| Dimension | Mesure | Seuil proposé |
|---|---|---|
| Fidélité produit | Le flacon composité est reconnaissable, étiquette lisible, pas de déformation | Binaire par image — **obligatoire** |
| Intégration | Pas de halo de découpe, direction de lumière plausible, ombre de contact présente | 1-5, moyenne ≥ 3,5 |
| Adhérence Brand DNA | Palette/ambiance conformes au mood board | 1-5, moyenne ≥ 3,5 |
| « Postable » | Passerait pour le post Instagram d'une vraie marque | Binaire — **% à fixer** |
| Distinction inter-marques | Marque A ≠ marque B visuellement sur le même template | Binaire |

**Règle de décision (à fixer par toi) :** ex. « **GO** si ≥ 65 % de la grille est notée *postable* ET fidélité produit obligatoire respectée sur ≥ 90 % des images ; sinon **NO-GO → plan B**. »

### 9.2 Juges multiples — éviter le biais auteur *(B5)*

**Ne note pas seul.** Tu es l'auteur du système, tu auras un biais d'indulgence inconsciente. Recrute :
- **Toi** + **Laure** (associée MY.LAB qui connaît le métier mais pas le pipeline tech)
- **2-3 pilotes MY.LAB cosmétiques** invités à voir le contact sheet **en aveugle** (ils ne savent pas quelle passe est laquelle, ni que c'est de l'IA — juste « regardez ces visuels, vous les posteriez sur Insta ? »)
- Notation parallèle dans un Google Sheet partagé, agrégation par moyenne

**Avantage stratégique :** les pilotes recrutés ici deviennent tes premiers clients pilotes du MVP, et tu valides leur intérêt produit dès le Sprint 0. Double-usage.

### 9.3 Journal d'itération modèle (l'artefact qui opérationnalise « jusqu'à ce que ça me convienne »)

Une ligne par passe `results/` :

| Passe | scene | relight | seg. | % postable | fidélité OK | pic VRAM | latence/img | load time | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 001 | … | … | … | …% | …% | … Go | … s | … s | itérer / stop |

Tu t'arrêtes quand une passe franchit ton seuil §9.1 — **ta décision**, tracée par des chiffres.

### 9.4 Plan B si la porte A1 échoue

Le plan B **n'est pas** « rajouter une LoRA » : la LoRA approxime aussi l'étiquette, donc elle échoue pour la même raison que ce que le compositing n'a pas su faire. Le plan B réaliste est :
1. **Restreindre le répertoire de templates** à ceux où le compositing est fiable (produit central, net, packshot/flat-lay, fond propre — souvent triviaux) et **renoncer au lancement** aux compositions difficiles (flacon flou en arrière-plan, scène chargée, vu de loin — cf. spec A5).
2. Documenter quels **archétypes de template passent** la porte → c'est ça qui définit l'offre réaliste de lancement.
3. Ré-évaluer la palette créative annoncée en conséquence (ne pas survendre).
4. **À reporter dans la spec V2.2** comme mitigation officielle de R1b (cf. §0.2).

---

## 10. Hors périmètre Sprint 0 (discipline)

À **ne pas** faire maintenant, même si tentant :
- Dashboard / Next.js (c'est SP3)
- VPS API gateway + dispatcher + Redis (c'est SP2)
- Stripe / Shopify / onboarding (c'est SP6/SP7)
- Worker cloud failover (juste le **noter** comme cible SP2, et le smoke test R2 §8.1 prépare le terrain)
- Monitoring complet (un simple auto-restart du worker local suffit ici)
- Entraînement LoRA (hors chemin critique tant que le compositing n'est pas tranché)

Et : **aucun modèle imposé** — la sélection reste ta boucle.

---

## 11. Planning indicatif (~1,5 sem + itération)

| Jour | Contenu | Sortie |
|---|---|---|
| 1 | **WSL2 setup** (Ubuntu LTS, driver NVIDIA Windows, CUDA WSL2, Docker Desktop backend WSL2, NVIDIA Container Toolkit, `.wslconfig` 24 Go) + UPS + git | `nvidia-smi` dans WSL2 OK, `docker run --gpus all` OK, repo init avec Dockerfile |
| 2 | ComfyUI containerisé + arborescence par rôle + `extra_model_paths.yaml` + 1ʳᵉ scène | `docker compose up` répond, 1 image générée |
| 3 | Pipeline en étapes (workflows JSON) + fixtures (5 flacons, 2 marques, 4 templates) | 3 workflows + `test_matrix.yaml` |
| 4 | Banc d'essai (warm/cold groupé, WebSocket, load time) + éval détourage (D1c) | `bench.py`, 1ᵉʳ `results/`, tableau détourage |
| 5 | 1ʳᵉ passe complète de la matrice + mesures VRAM/latence/load (A4) + recrutement juges | log.json + contact sheet + headroom VRAM connu + 3 juges briefés |
| 6 | Smoke test cloud R2 + note vidéo + 1ʳᵉ notation collective | `cloud_smoke.py` OK, décision a/b/c, 1ère grille §9.1 notée |
| 6 → | **Boucle d'itération modèle** (durée = ta décision) | journal d'itération qui converge |
| Fin | Revue GO / NO-GO contre §9.1 (votes des 3+ juges) ; si GO, archétypes de template fiables identifiés | **décision tracée + handoff Sprint 1** |

---

## 12. Décisions à journaliser pendant ce sprint

- **B1 — OS** : WSL2 sur Windows (décidé). Noter en cours d'install : version Ubuntu retenue, version CUDA, allocation mémoire `.wslconfig`, debugs éventuels du passthrough GPU.
- **D1c — détourage** : modèle par défaut + liste des cas durs (→ alimente l'écran de validation onboarding, spec A2).
- **A4 / VRAM** — pic réel par étape ; le design en étapes (§5) suffit-il, ou faut-il de l'offload ?
- **A1 / gate** — seuils §9.1 figés (par les 3+ juges), puis verdict GO/NO-GO daté.
- **D-vidéo-fidélité** — voie a/b/c retenue (§8.2), à confirmer pendant l'itération vidéo. **Report spec V2.2 §12 D12.**
- **D5 (anticipé)** — pendant le smoke test, noter le provider cloud pressenti pour le failover SP2.
- **Pilotes recrutés** : noms + tier visé + date du briefing — base pour le recrutement officiel MVP.

---

## 13. Ce que ce sprint dé-risque pour la suite

À la fin, tu sauras — chiffres et images à l'appui — **si le pari produit central (compositing-first) tient**, avec quel headroom matériel, et sur quels archétypes de template il est fiable. Tu entres en Sprint 1 (pipeline core + API wrapper local) avec :
- Un banc d'essai qui rejoue toute régression en une commande
- Une boucle d'itération modèle déjà rodée
- Une stack containerisée prête à être déployée en cloud failover SP2 (zéro rework)
- 3+ juges dont 2-3 deviennent tes pilotes MVP
- Un journal de décisions tracé, sans avoir écrit une ligne d'infra aval

---

**Fin du plan Sprint 0 v1.1.**
