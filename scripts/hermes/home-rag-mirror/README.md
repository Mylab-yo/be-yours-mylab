# Miroir RAG maison — donner la base de connaissances au Hermes maison

But : ton **Hermes maison** (llama.cpp / llama-swap, Telegram) interroge une **AnythingLLM locale**,
tenue en **miroir** de la RAG du VPS (`rag.mylab-shop.com`). Les requêtes restent à la maison
(offline / privé), la source de vérité reste le VPS.

```
  VPS · AnythingLLM  ──(SFTP pull: mirror_from_vps.py)──▶  PC maison · AnythingLLM (127.0.0.1:3001)
  (source de vérité)                                              ▲
                                                                  │ skill mylab-rag (vector-search)
                                                          Hermes maison (llama-swap)
```

> Tout se fait **sur le PC maison**. Je n'y ai pas accès, donc ces étapes sont à lancer par toi.
> Si un chemin/port ne colle pas à ton install, dis-le-moi et j'ajuste.

---

## Pré-requis sur le PC maison
1. **AnythingLLM en local** (Desktop ou Docker), accessible sur `http://127.0.0.1:3001`.
   - Dans ses réglages, **Embedder = Native** (par défaut) → aucun coût/clé cloud pour les embeddings.
   - L'AnythingLLM locale est *indépendante* du VPS : elle ré-embedde les docs avec son propre embedder
     (le miroir copie le **texte** des docs, pas les vecteurs — c'est volontaire et auto-cohérent).
2. **Hermes maison** = le NousResearch Hermes Agent (le même logiciel que sur le VPS), branché sur
   llama-swap. Il sait charger des *skills* et lit ses creds depuis son `.env`.
3. **Python 3** + `paramiko` (`pip install paramiko`).

---

## Étape 1 — Clé API locale + config
1. Ouvre ton AnythingLLM local → **Settings → Tools → Developer API → Generate New API Key**. Copie-la.
2. Copie `.env.example` en `.env` et remplis :
   - `VPS_HOST/PORT/USER/PASS` : tes creds VPS (mêmes que `.env.vps`).
   - `LOCAL_ANYTHINGLLM_KEY` : la clé locale générée à l'instant.
   - laisse `LOCAL_ANYTHINGLLM_URL=http://127.0.0.1:3001` et `WORKSPACE=mylab-kb`.

## Étape 2 — Premier miroir (crée le workspace + importe les docs)
```bash
python mirror_from_vps.py --verbose
```
Ça crée le workspace `mylab-kb` localement s'il n'existe pas, tire les docs du VPS par SFTP,
les ré-importe et les embedde en local. Idempotent (relançable ; ne réimporte que les deltas).
Vérifie dans l'UI locale que le workspace **MyLab KB** contient bien les documents.

## Étape 3 — Câbler le skill au Hermes maison
1. **Variables d'env** — ajoute-les au `.env` de ton Hermes maison
   (pip : `~/.hermes/.env` · Docker : le `.env` monté dans `/opt/data/.env`) :
   ```
   ANYTHINGLLM_URL=http://127.0.0.1:3001
   ANYTHINGLLM_API_KEY=<ta clé locale>
   ANYTHINGLLM_WORKSPACE=mylab-kb
   ```
   ⚠️ Si ton Hermes maison tourne **dans Docker**, `127.0.0.1` désigne le conteneur, pas l'hôte →
   utilise `http://host.docker.internal:3001` (Windows/Mac) ou l'IP LAN du PC.
2. **Le skill** — copie le dossier `skills/mylab-rag/` de ce package dans le dossier *skills* du
   Hermes maison (pip : `~/.hermes/skills/` · Docker : `/opt/data/skills/`, puis
   `chown -R hermes:hermes` comme sur le VPS).
3. **Redémarre** le Hermes maison (changement de `.env`). Vérifie : `hermes skills list` doit montrer
   `mylab-rag` *enabled*.

## Étape 4 — Test
```bash
hermes -z "Dans la base de connaissances MyLab, quels sont les paliers de tarifs dégressifs par volume ? Cite la source."
```
Il doit déclencher `mylab-rag`, récupérer les passages depuis ton AnythingLLM local et répondre en
citant `20-tarifs-volumes`.

## Étape 5 — Automatiser le miroir
Pour garder le local à jour quand tu ajoutes des docs sur le VPS :
- **Windows** (Planificateur de tâches) : tâche quotidienne →
  `python C:\chemin\home-rag-mirror\mirror_from_vps.py`
- **Linux/macOS** (cron) : `0 7 * * * cd /chemin/home-rag-mirror && python3 mirror_from_vps.py`

---

## Notes
- **Sens du miroir** : VPS → maison (pull). Le VPS ne voit jamais le PC maison (NAT). La maison
  initie tout.
- **Sécurité** : `mirror_from_vps.py` utilise les creds VPS (SFTP) — garde `.env` privé (il est
  ignoré par git). Ne commite jamais `.env`.
- **Suppressions** : un doc retiré du VPS est aussi retiré du workspace local au prochain miroir.
- **Source des docs côté VPS** : `/root/anythingllm/storage/documents/custom-documents/*.json`.
  Tu alimentes la base en uploadant sur `https://rag.mylab-shop.com` (workspace MyLab KB).
