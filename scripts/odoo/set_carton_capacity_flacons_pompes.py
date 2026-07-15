"""Colisage MyLab : flacons pompe 200ml -> 35/carton, bouteille verre ambre 50ml -> 69/carton.

Regle metier (Yoann, 15/07/2026) : la capacite carton est une propriete du
FLACON, pas de la gamme commerciale.

- Gamme coloristeur 200ml (masques + shampoings), dejaunisseur platine 200ml et
  gloss 200ml partagent le meme flacon "bouteille + pompe" -> 35 u/carton.
  Avant : les masques etaient a 24 (famille masque) et les shampoings a 40
  (famille shampoing), alors qu'ils ne sont ni l'un ni l'autre.
- Les 6 references en bouteille verre ambre 50ml (huiles, serums, bain
  miraculeux, repair oil) -> 69 u/carton (avant : 63).
- Bonus data : masque coloristeur tulipe noire 1000ml etait a 0 (jamais
  initialise, pas de default_code) -> 12 comme les 11 autres masques 1L.

Portee : x_carton_capacity sur product.template = colisage par defaut, tous
clients. Les colisages negocies par client vivent dans PARTNER_PRODUCT_CARTON
(cf. server_action_code.py) et restent prioritaires.

Idempotent : rejouable, n'ecrit que les ecarts. --dry-run pour simuler.
"""
import sys

from scripts.odoo._client import search_read, write

# (tmpl_id, nom attendu, capacite cible)
# Le nom attendu est un garde-fou : on refuse d'ecrire si l'id ne pointe plus
# sur le produit qu'on croit (renommage, fusion, restauration de base...).
TARGETS = [
    # --- Flacon pompe 200ml -> 35 -------------------------------------------
    (2297, "masque coloristeur blond soleil 200ml", 35),
    (2298, "masque coloristeur blond vanille 200ml", 35),
    (2299, "masque coloristeur chocolat 200ml", 35),
    (2300, "masque coloristeur cuivre 200ml", 35),
    (2301, "masque coloristeur marron noisette 200ml", 35),
    (2303, "masque dejaunisseur platine 200ml", 35),
    (2426, "masque gloss 200ml", 35),
    (2338, "shampoing coloristeur blond soleil 200ml", 35),
    (2339, "shampoing coloristeur blond vanille 200ml", 35),
    (2340, "shampoing coloristeur chocolat 200ml", 35),
    (2341, "shampoing coloristeur cuivre 200ml", 35),
    (2342, "shampoing coloristeur marron noisette 200ml", 35),
    (2344, "shampoing dejaunisseur platine 200ml", 35),
    (2424, "shampoing gloss 200ml", 35),
    # --- Bouteille verre ambre 50ml -> 69 -----------------------------------
    (2260, "bain miraculeux 50ml", 69),
    (2290, "huile a barbe 50ml", 69),
    (2446, "repair oil 50ml", 69),
    (2327, "serum barbe 50ml", 69),
    (2329, "serum finition ultime 50ml", 69),
    (2557, "serum fortifiant 50ml", 69),
    # --- Correction data ----------------------------------------------------
    (2457, "masque coloristeur tulipe noire 1000ml", 12),
]


def normalize(name: str) -> str:
    """Comparaison de noms insensible casse/accents (le catalogue melange les deux)."""
    out = name.lower().strip()
    for accented, plain in (("é", "e"), ("è", "e"), ("ê", "e"), ("à", "a"),
                            ("â", "a"), ("î", "i"), ("ï", "i"), ("ô", "o"),
                            ("û", "u"), ("ç", "c")):
        out = out.replace(accented, plain)
    return " ".join(out.split())


def main(dry_run: bool = False) -> int:
    ids = [t[0] for t in TARGETS]
    rows = search_read("product.template", [("id", "in", ids)],
                       ["id", "name", "default_code", "x_carton_capacity"])
    by_id = {r["id"]: r for r in rows}

    missing = [i for i in ids if i not in by_id]
    if missing:
        print(f"ABANDON : templates introuvables : {missing}")
        return 1

    # Garde-fou : l'id pointe-t-il toujours sur le bon produit ?
    mismatches = []
    for tmpl_id, expected_name, _cap in TARGETS:
        actual = by_id[tmpl_id]["name"]
        if normalize(actual) != normalize(expected_name):
            mismatches.append((tmpl_id, expected_name, actual))
    if mismatches:
        print("ABANDON : le nom ne correspond pas a l'id attendu (rien n'a ete ecrit) :")
        for tmpl_id, expected, actual in mismatches:
            print(f"  tmpl={tmpl_id} attendu={expected!r} trouve={actual!r}")
        return 1

    to_write: dict[int, list[int]] = {}
    unchanged = 0
    print(f"{'tmpl':>5}  {'ref':<44} {'produit':<44} {'avant':>5} -> {'apres':>5}")
    print("-" * 118)
    for tmpl_id, _expected, cap in TARGETS:
        r = by_id[tmpl_id]
        current = r.get("x_carton_capacity") or 0
        ref = r.get("default_code") or "-"
        if current == cap:
            unchanged += 1
            print(f"{tmpl_id:>5}  {ref:<44} {r['name'][:44]:<44} {current:>5}    = (deja bon)")
            continue
        to_write.setdefault(cap, []).append(tmpl_id)
        print(f"{tmpl_id:>5}  {ref:<44} {r['name'][:44]:<44} {current:>5} -> {cap:>5}")

    total = sum(len(v) for v in to_write.values())
    print("-" * 118)
    if not total:
        print(f"Rien a faire : les {unchanged} produits sont deja a la bonne capacite.")
        return 0

    if dry_run:
        print(f"DRY-RUN : {total} produits seraient modifies ({unchanged} deja bons). Rien n'a ete ecrit.")
        return 0

    for cap, tmpl_ids in sorted(to_write.items()):
        write("product.template", tmpl_ids, {"x_carton_capacity": cap})
        print(f"  ecrit capacite={cap} sur {len(tmpl_ids)} produits")
    print(f"OK : {total} produits modifies, {unchanged} deja bons.")
    return 0


if __name__ == "__main__":
    sys.exit(main(dry_run="--dry-run" in sys.argv))
