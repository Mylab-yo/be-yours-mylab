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

**JAMAIS** editer le jsCode des nodes via l'UI n8n. Les fichiers .js de ce dossier sont la source de verite. Workflow :

1. Editer `01_*.js` ou `02_*.js`
2. `python patch_workflow.py --dry-run` pour valider la lecture
3. `python patch_workflow.py` pour deployer
4. Tester via le formulaire ou via curl avec les test payloads
5. Commiter les .js + l'export `docs/n8n-devis-manuel.json` re-genere

## Source de la cle API N8N

Le script lit la cle dans `d:\Configurateur Designs MyLab\mylab-configurateur\.env.local` ligne 39 (0-indexed), meme source que `create_order_cancelled_workflow.py`. Pas de `.env.local` au root du repo `be-yours-mylab`.

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
