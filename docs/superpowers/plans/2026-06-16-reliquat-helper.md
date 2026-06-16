# Reliquat assisté (helper « Préparer le dispo ») — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettre au préparateur d'expédier le stock disponible d'un BL Odoo en un clic (pré-remplissage), de laisser Odoo créer le reliquat natif, et de notifier le client de la bonne partie.

**Architecture:** Déploiement 100 % XML-RPC (pas de module addon, pas de redémarrage Odoo). Une action serveur `ir.actions.server` (state=code) + un bouton d'en-tête sur le BL (vue héritée) ; le reliquat utilise le wizard natif `stock.backorder.confirmation` ; le mail d'expédition (template id=27) et le matcher tracking reçoivent de petits ajustements.

**Tech Stack:** Python 3.12 + xmlrpc.client via `scripts/odoo/_client.py` ; Odoo 18 Community ; QWeb (mail body). Spec : `docs/superpowers/specs/2026-06-16-reliquat-helper-design.md`.

**Note vérification :** ce repo n'a ni pytest ni runner. Chaque tâche se « teste » par un script de probe/lecture ou un dry-run, avec une **sortie attendue** explicite. Tout ce qui mute du stock réel est soit réversible (`do_unreserve`), soit explicitement marqué « gated » (accord de Yoann requis).

---

### Task 1 : Probe des mécaniques stock Odoo 18 (dé-risquer avant de coder)

But : confirmer les champs réels avant d'écrire l'action serveur (les internes stock varient entre versions Odoo).

**Files:**
- Create: `scripts/odoo/probe_stock_prefill_mechanics.py`

- [ ] **Step 1 : Écrire le probe (réversible : assign puis unreserve)**

```python
"""Confirme les champs Odoo 18 utilises par l'action 'Preparer le dispo'.
Reversible : action_assign puis do_unreserve -> remet le picking dans son etat initial."""
from scripts.odoo._client import search_read, execute

# Un BL confirme avec dispo partiel (cf simulation) : MYVO/OUT/00025 ou un autre 'confirmed'
pk = search_read("stock.picking",
    [("picking_type_code", "=", "outgoing"), ("state", "=", "confirmed")],
    ["id", "name", "state"], limit=1)[0]
pid = pk["id"]
print(f"Picking test: {pk['name']} (id={pid}) state={pk['state']}")

# Champs move + product
print("\nChamps stock.move (quantity/picked/product_uom_qty/state) :")
fg = execute("stock.move", "fields_get", [["quantity", "picked", "product_uom_qty", "state"]],
             {"attributes": ["string", "type", "readonly"]})
for f, m in fg.items():
    print(f"  {f}: {m}")
print("product.product a-t-il 'is_storable' ?",
      "is_storable" in execute("product.product", "fields_get", [], {"attributes": ["type"]}))

# Avant
moves = search_read("stock.move", [("picking_id", "=", pid)],
    ["product_id", "product_uom_qty", "quantity", "picked", "state"])
print("\nAVANT action_assign :")
for m in moves:
    print(f"  {m['product_id'][1][:30]:<30} demande={m['product_uom_qty']} quantity={m.get('quantity')} picked={m.get('picked')} state={m['state']}")

# action_assign (reserve le dispo)
execute("stock.picking", "action_assign", [[pid]])
moves = search_read("stock.move", [("picking_id", "=", pid)],
    ["product_id", "product_uom_qty", "quantity", "picked", "state"])
print("\nAPRES action_assign (quantity doit = reserve) :")
for m in moves:
    print(f"  {m['product_id'][1][:30]:<30} demande={m['product_uom_qty']} quantity={m.get('quantity')} picked={m.get('picked')} state={m['state']}")

# Restaure
execute("stock.picking", "do_unreserve", [[pid]])
print("\ndo_unreserve OK -> picking restaure")
```

- [ ] **Step 2 : Lancer le probe**

Run : `python -m scripts.odoo.probe_stock_prefill_mechanics`
Attendu : la sortie confirme que (a) `stock.move.quantity` existe et est éditable, (b) `picked` existe, (c) `product.product.is_storable` == True, (d) après `action_assign`, `quantity` des lignes en stock passe au montant réservé (peut rester 0 si rupture). Si un champ diffère (ex. pas de `picked`, ou `quantity` non peuplé), **noter la correction** à reporter dans Task 2 Step 1.

- [ ] **Step 3 : Commit**

```bash
git add scripts/odoo/probe_stock_prefill_mechanics.py
git commit -m "chore(reliquat): probe mecaniques stock Odoo 18 (prefill/backorder)"
```

---

### Task 2 : Action serveur « Préparer le dispo » + bouton (C1)

**Files:**
- Create: `scripts/odoo/ship_available_code.py` (corps de l'action serveur)
- Create: `scripts/odoo/step_create_ship_available_action.py` (déploie l'action + le bouton)

- [ ] **Step 1 : Écrire le code de l'action serveur**

`scripts/odoo/ship_available_code.py` (⚠️ safe_eval : pas d'imports, pas de docstrings ; `env`/`records`/`UserError` fournis. Ajuster les noms de champs selon le probe Task 1 si besoin) :

```python
# Code de l'action serveur "Preparer le dispo" (ir.actions.server, state='code').
# Contexte: env, records (stock.picking), model, log, UserError disponibles.

for picking in records:
    if picking.state not in ('confirmed', 'assigned', 'waiting'):
        continue
    # 1. Reserve tout le stock disponible
    picking.action_assign()
    # 2. Pre-remplit "Fait" = reserve (storable) / demande (service/non stocke)
    total = 0.0
    for move in picking.move_ids:
        if move.state in ('done', 'cancel'):
            continue
        if move.product_id.is_storable:
            qty = move.quantity            # reserve par action_assign
        else:
            qty = move.product_uom_qty     # service/conso : tout part
        move.quantity = qty
        move.picked = True
        total += qty
    # 3. Garde-fou : rien dispo
    if total <= 0:
        raise UserError("Aucun stock disponible pour ce bon de livraison - rien a expedier. Reapprovisionnez ou ajustez les quantites manuellement avant de valider.")
```

- [ ] **Step 2 : Écrire le déployeur (action + bouton), idempotent**

`scripts/odoo/step_create_ship_available_action.py` (modelé sur `step03_create_server_action.py` + `step05_add_picking_button.py`) :

```python
"""Cree/maj l'action serveur 'Preparer le dispo' sur stock.picking + le bouton d'en-tete."""
from pathlib import Path
from scripts.odoo._client import search, create, write, search_read

ACTION_NAME = "Préparer le dispo"
MODEL_NAME = "stock.picking"
CODE_FILE = Path("scripts/odoo/ship_available_code.py")
VIEW_KEY = "mylab.picking_form_ship_available_button"


def upsert_action(model_id):
    code = CODE_FILE.read_text(encoding="utf-8")
    values = {"name": ACTION_NAME, "model_id": model_id, "state": "code",
              "code": code, "binding_model_id": model_id, "binding_type": "action"}
    existing = search("ir.actions.server",
                      [("name", "=", ACTION_NAME), ("model_id", "=", model_id)])
    if existing:
        write("ir.actions.server", existing, values)
        print(f"Updated server action id={existing[0]}")
        return existing[0]
    new_id = create("ir.actions.server", values)
    print(f"Created server action id={new_id}")
    return new_id


def upsert_button(sa_id):
    ref = search_read("ir.model.data",
        [("module", "=", "stock"), ("name", "=", "view_picking_form")],
        ["res_id"], limit=1)
    if not ref:
        raise RuntimeError("Vue parente stock.view_picking_form introuvable")
    parent_id = ref[0]["res_id"]
    arch = f"""<data>
    <xpath expr="//header" position="inside">
        <button name="{sa_id}" type="action"
                string="Préparer le dispo"
                class="btn-primary"
                invisible="state not in ('confirmed','assigned','waiting')"/>
    </xpath>
</data>"""
    values = {"name": VIEW_KEY, "type": "form", "model": "stock.picking",
              "inherit_id": parent_id, "arch_base": arch, "key": VIEW_KEY}
    existing = search("ir.ui.view", [("key", "=", VIEW_KEY)])
    if existing:
        write("ir.ui.view", existing, {"arch_base": arch})
        print(f"Updated button view id={existing[0]}")
    else:
        print(f"Created button view id={create('ir.ui.view', values)}")


def main():
    model_id = search("ir.model", [("model", "=", MODEL_NAME)])[0]
    sa_id = upsert_action(model_id)
    upsert_button(sa_id)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3 : Déployer**

Run : `python -m scripts.odoo.step_create_ship_available_action`
Attendu : « Created/Updated server action id=… » puis « Created/Updated button view id=… », sans exception.

- [ ] **Step 4 : Vérifier que l'action et le bouton existent**

Run :
```bash
python -c "from scripts.odoo._client import search_read as s; print(s('ir.actions.server',[('name','=','Préparer le dispo')],['id','state','binding_type'])); print(s('ir.ui.view',[('key','=','mylab.picking_form_ship_available_button')],['id','inherit_id']))"
```
Attendu : l'action (state='code', binding_type='action') + la vue héritée existent (listes non vides).

- [ ] **Step 5 : Commit**

```bash
git add scripts/odoo/ship_available_code.py scripts/odoo/step_create_ship_available_action.py
git commit -m "feat(reliquat): action serveur 'Preparer le dispo' + bouton BL"
```

---

### Task 3 : Test du bouton (pré-remplissage + garde-fou), réversible

**Files:**
- Create: `scripts/odoo/test_ship_available.py`

- [ ] **Step 1 : Écrire le test (réversible)**

`scripts/odoo/test_ship_available.py` — exécute l'action serveur sur un BL réel, vérifie le pré-remplissage, puis **annule la réservation** (ne valide PAS, donc pas de mouvement de stock) :

```python
"""Teste l'action 'Preparer le dispo' sur un BL, SANS valider (reversible).
Usage: python -m scripts.odoo.test_ship_available MYVO/OUT/00025"""
import sys
from scripts.odoo._client import search, search_read, execute

name = sys.argv[1] if len(sys.argv) > 1 else None
domain = [("name", "=", name)] if name else \
    [("picking_type_code", "=", "outgoing"), ("state", "=", "confirmed")]
pk = search_read("stock.picking", domain, ["id", "name", "state"], limit=1)[0]
pid = pk["id"]
sa_id = search("ir.actions.server", [("name", "=", "Préparer le dispo")])[0]
print(f"BL {pk['name']} (id={pid}) — exécution de l'action {sa_id}")

# Execute l'action serveur avec le picking en contexte actif
try:
    execute("ir.actions.server", "run", [[sa_id]],
            {"context": {"active_model": "stock.picking", "active_ids": [pid], "active_id": pid}})
    print("Action exécutée. Pré-remplissage :")
    moves = search_read("stock.move", [("picking_id", "=", pid)],
        ["product_id", "product_uom_qty", "quantity", "picked"])
    for m in moves:
        print(f"  {m['product_id'][1][:32]:<32} demande={m['product_uom_qty']} fait={m.get('quantity')} picked={m.get('picked')}")
finally:
    execute("stock.picking", "do_unreserve", [[pid]])
    # remet picked=False pour ne pas laisser le BL en etat "pret a valider"
    mv = search("stock.move", [("picking_id", "=", pid)])
    if mv:
        execute("stock.move", "write", [mv, {"picked": False}])
    print("Réservation annulée + picked remis à False -> BL restauré.")
```

- [ ] **Step 2 : Lancer le test sur un BL partiel**

Run : `python -m scripts.odoo.test_ship_available MYVO/OUT/00025`
Attendu : pour chaque ligne, `fait` = quantité disponible (≤ demande), `picked=True` ; puis « BL restauré ». (Comparer au résultat de `simulate_reliquat.py MYVO/OUT/00025`.)

- [ ] **Step 3 : Vérifier le garde-fou « rien dispo »**

Run : `python -m scripts.odoo.test_ship_available MYVO/OUT/00007`
Attendu : l'action lève `UserError` « Aucun stock disponible… » (le test affiche l'erreur). Le `finally` restaure quand même le BL.

- [ ] **Step 4 : Test e2e LIVE (gated — accord Yoann requis)**

⚠️ Crée de vrais mouvements de stock + un vrai reliquat. À faire UNIQUEMENT avec Yoann, sur une commande qu'il s'apprête réellement à expédier :
1. Dans Odoo : ouvrir le BL → bouton **Préparer le dispo** → vérifier le pré-remplissage → ajuster → **Valider** → popup « Créer un reliquat » → Oui.
2. Vérifier : 2 BL (un `done`, un reliquat `confirmed`) ; le reliquat a bien le transporteur DPD hérité.
Run de contrôle : `python -m scripts.odoo.probe_s00533_reliquat` (adapter au n° de commande testé) — attendu : `delivery_count=2`, un picking done + un backorder.

- [ ] **Step 5 : Commit**

```bash
git add scripts/odoo/test_ship_available.py
git commit -m "test(reliquat): test reversible du bouton 'Preparer le dispo' + garde-fou"
```

---

### Task 4 : Notification adaptée au partiel/complément (C3)

**Files:**
- Create: `scripts/odoo/update_shipping_partial_wording.py`

- [ ] **Step 1 : Écrire le patch du body template id=27 (idempotent)**

`scripts/odoo/update_shipping_partial_wording.py` (pattern `update_devis_template_greeting.py`) :

```python
"""Adapte le corps du template d'expedition id=27 : complet / partiel / complement.
Idempotent : ne re-patche pas si deja fait."""
from scripts.odoo._client import search_read, write

TEMPLATE_ID = 27
OLD = "Bonne nouvelle ! Votre commande a été expédiée."
NEW = ("Bonne nouvelle ! "
       "<t t-if=\"object.backorder_id\">Le complément de votre commande a bien été expédié.</t>"
       "<t t-elif=\"object.backorder_ids\">Une partie de votre commande a été expédiée ; "
       "le reste vous sera envoyé dès réception du stock.</t>"
       "<t t-else=\"\">Votre commande a bien été expédiée.</t>")


def main():
    body = search_read("mail.template", [("id", "=", TEMPLATE_ID)], ["body_html"])[0]["body_html"]
    if "object.backorder_id" in body:
        print("Déjà patché -> no-op.")
        return
    assert OLD in body, "Ancre introuvable dans le body du template 27"
    write("mail.template", [TEMPLATE_ID], {"body_html": body.replace(OLD, NEW, 1)})
    after = search_read("mail.template", [("id", "=", TEMPLATE_ID)], ["body_html"])[0]["body_html"]
    assert "object.backorder_ids" in after and OLD not in after, "Patch non appliqué"
    print("OK -> body template 27 patché (complet/partiel/complément).")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2 : Vérifier l'ancre avant patch**

Run : `python -c "from scripts.odoo._client import search_read as s; b=s('mail.template',[('id','=',27)],['body_html'])[0]['body_html']; print('ANCRE OK' if 'Bonne nouvelle ! Votre commande a été expédiée.' in b else 'ANCRE KO')"`
Attendu : `ANCRE OK`. Si `KO`, lire le body (`dump_template_27.py`) et ajuster `OLD`.

- [ ] **Step 3 : Déployer**

Run : `python -m scripts.odoo.update_shipping_partial_wording`
Attendu : « OK -> body template 27 patché ».

- [ ] **Step 4 : Vérifier le rendu sur un cas partiel (BL ayant un reliquat)**

Run : `python -m scripts.odoo.station_preview_send --picking <BL_partiel_done> --tracking 10843001000000 --to yoann@mylab-shop.com`
Attendu : mail reçu par Yoann affichant « Une partie de votre commande a été expédiée… ». (Si pas encore de BL partiel réel, refaire après le test e2e Task 3 Step 4.)

- [ ] **Step 5 : Commit**

```bash
git add scripts/odoo/update_shipping_partial_wording.py
git commit -m "feat(reliquat): mail expedition adapte complet/partiel/complement (tpl 27)"
```

---

### Task 5 : Raffinement du matcher tracking (C4)

**Files:**
- Modify: `scripts/odoo/station_notify_tracking.py` (fonction `build_plan`, le tri des candidats)

- [ ] **Step 1 : Modifier le tri des BL candidats**

Dans `build_plan`, remplacer le bloc de tri actuel :

```python
        if len(bls) > 1 and sdate:
            bls.sort(key=lambda b: abs(((to_date(b.get("scheduled_date")) or sdate) - sdate).days))
        chosen = bls[0]
```

par (priorité d'abord à l'état réellement parti, puis proximité de date) :

```python
        if len(bls) > 1:
            state_rank = {"done": 0, "assigned": 1, "confirmed": 2, "waiting": 3}
            bls.sort(key=lambda b: (
                state_rank.get(b.get("state"), 9),
                abs(((to_date(b.get("scheduled_date")) or sdate) - sdate).days) if sdate else 0))
        chosen = bls[0]
```

- [ ] **Step 2 : Vérifier que le dry-run tourne toujours**

Run : `python -m scripts.odoo.station_notify_tracking`
Attendu : même sortie qu'avant (11 à notifier sur `20260615_Expeditions.txt`), aucune régression. Le tri ne change le choix que pour les clients ayant ≥2 BL ouverts.

- [ ] **Step 3 : Commit**

```bash
git add scripts/odoo/station_notify_tracking.py
git commit -m "fix(reliquat): matcher tracking prefere le BL parti au reliquat en attente"
```

---

## Self-Review

**Spec coverage :**
- C1 (bouton « Préparer le dispo ») → Task 2 (+ probe Task 1, test Task 3). ✓
- C2 (reliquat natif) → pas de dev ; couvert par le test e2e Task 3 Step 4 (popup native). ✓
- C3 (mail complet/partiel/complément) → Task 4. ✓
- C4 (matcher préfère le BL parti) → Task 5. ✓
- Garde-fou « rien dispo » → Task 2 code Step 1 + Task 3 Step 3. ✓
- Lignes service/conso → Task 2 code (branche `is_storable`). ✓

**Placeholder scan :** aucun TBD/TODO ; tout le code est complet. Seule dépendance : Task 1 confirme les champs (`quantity`/`picked`/`is_storable`) ; si un nom diffère, Task 2 Step 1 est ajusté en conséquence (explicitement noté).

**Type consistency :** `Préparer le dispo` (nom action), `mylab.picking_form_ship_available_button` (clé vue), `object.backorder_id`/`backorder_ids` (champs Odoo standard), `state_rank` — cohérents entre tâches.

## Notes de déploiement / risques

- Tout est idempotent et XML-RPC ; aucun module, aucun redémarrage Odoo.
- Le seul mouvement de stock réel = Task 3 Step 4 (gated, avec Yoann).
- Hors périmètre (rappel spec) : wizard sur-mesure, mode « forcer », activation `--send` + tâche 20h30.
