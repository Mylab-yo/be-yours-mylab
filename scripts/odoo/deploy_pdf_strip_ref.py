# -*- coding: utf-8 -*-
"""Retire la reference produit [code] en tete de line.name sur les PDF
devis (sale) ET facture (account), de facon ROBUSTE et upgrade-safe.

Pourquoi pas editer la vue standard en place :
    sale.report_saleorder_document (1286) et account.report_invoice_document
    (1143) sont des vues STANDARD Odoo (noupdate=False, arch_fs = fichier du
    module). Toute edition en place de leur arch est ECRASEE a la prochaine
    mise a jour des modules `sale` / `account`.

Approche robuste (meme pattern que mylab.report_invoice_document_ch_note) :
    - on RESTAURE la vue standard (revert d'un eventuel patch en place) ;
    - on cree une vue HERITEE MyLab (DB-only, sans xmlid -> aucun module ne la
      reset) qui remplace via xpath le seul <span> de la ligne PRODUIT.

Le prefixe strippe est "[default_code] " en tout debut de line.name
("[creme-ha-repulpe-200-ml] creme ha repulpe 200ml" -> "creme ha repulpe 200ml").
Sections, notes, acomptes et lignes sans crochet ne sont pas touchees.
line.name reste INTACT en base : on ne modifie que le rendu.

Usage :
    python -m scripts.odoo.deploy_pdf_strip_ref            # dry-run
    python -m scripts.odoo.deploy_pdf_strip_ref --apply    # applique
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from scripts.odoo._client import search_read, execute, write, create

DRY_RUN = "--apply" not in sys.argv

# Expression QWeb (safe_eval : pas de module re -> string ops uniquement)
EXPR = (
    "line.name.split('] ', 1)[-1] "
    "if line.name and line.name.startswith('[') and '] ' in line.name "
    "else line.name"
)

SALE_STRIP = '<span t-out="%s">Produit</span>' % EXPR
SALE_ORIG = '<span t-field="line.name">Produit</span>'
INV_STRIP = ('<span t-if="line.name" t-out="%s" t-options="{\'widget\': \'text\'}"'
             ' dir="auto">Bacon Burger</span>') % EXPR
INV_ORIG = ('<span t-if="line.name" t-field="line.name" t-options="{\'widget\': \'text\'}"'
            ' dir="auto">Bacon Burger</span>')

CONFIGS = [
    {
        "base_view": 1286,
        "key": "mylab.report_saleorder_strip_ref",
        "name": "MyLab — Retire ref produit [code] (devis / bon de commande)",
        "strip_in_base": SALE_STRIP,
        "orig_in_base": SALE_ORIG,
        "xpath": "//td[@name='td_name']/span",
        "replacement": SALE_STRIP,
    },
    {
        "base_view": 1143,
        "key": "mylab.report_invoice_strip_ref",
        "name": "MyLab — Retire ref produit [code] (facture / avoir)",
        "strip_in_base": INV_STRIP,
        "orig_in_base": INV_ORIG,
        "xpath": "//td[@name='account_invoice_line_name']/span",
        "replacement": INV_STRIP,
    },
]

PRIORITY = 99  # s'applique apres les autres vues heritees (l10n_fr, etc.)


def revert_base(cfg):
    """Restaure la vue standard si un patch strip a ete pose en place."""
    v = search_read("ir.ui.view", [("id", "=", cfg["base_view"])], ["key", "arch_db"])[0]
    arch = v["arch_db"] or ""
    if cfg["strip_in_base"] not in arch:
        print(f"  base {cfg['base_view']} ({v['key']}) : deja standard (rien a revert)")
        return
    new_arch = arch.replace(cfg["strip_in_base"], cfg["orig_in_base"])
    print(f"  base {cfg['base_view']} ({v['key']}) : revert edition en place -> standard")
    if not DRY_RUN:
        write("ir.ui.view", [cfg["base_view"]], {"arch_base": new_arch})
        check = search_read("ir.ui.view", [("id", "=", cfg["base_view"])], ["arch_db"])[0]["arch_db"]
        assert cfg["strip_in_base"] not in check, "revert base echoue"


def deploy_inherited(cfg):
    """Cree ou met a jour la vue heritee MyLab (DB-only) qui strippe le prefixe."""
    inh_arch = '<xpath expr="%s" position="replace">%s</xpath>' % (cfg["xpath"], cfg["replacement"])
    existing = search_read("ir.ui.view", [("key", "=", cfg["key"])],
                           ["id", "arch_db", "active", "priority", "inherit_id"])
    if existing:
        vid = existing[0]["id"]
        print(f"  vue heritee {cfg['key']} existe (id={vid}) -> update")
        if not DRY_RUN:
            write("ir.ui.view", [vid], {
                "arch_base": inh_arch, "active": True,
                "priority": PRIORITY, "inherit_id": cfg["base_view"], "mode": "extension",
            })
    else:
        print(f"  vue heritee {cfg['key']} absente -> create")
        if not DRY_RUN:
            vid = create("ir.ui.view", {
                "name": cfg["name"],
                "key": cfg["key"],
                "type": "qweb",
                "inherit_id": cfg["base_view"],
                "mode": "extension",
                "priority": PRIORITY,
                "active": True,
                "arch_base": inh_arch,
            })
            print(f"    -> cree id={vid}")


def verify(cfg):
    combined = execute("ir.ui.view", "get_combined_arch", [[cfg["base_view"]]])
    if isinstance(combined, (list, tuple)):
        combined = combined[0]
    base = search_read("ir.ui.view", [("id", "=", cfg["base_view"])], ["arch_db"])[0]["arch_db"] or ""
    strip_in_combined = 'line.name.split' in combined
    strip_in_base = cfg["strip_in_base"] in base
    mark = "OK" if (strip_in_combined and not strip_in_base) else "KO"
    print(f"  [{mark}] view {cfg['base_view']} : strip present dans le rendu={strip_in_combined}"
          f" | base standard (sans strip en place)={not strip_in_base}")


def main():
    print("=== Deploy strip reference produit (devis + facture) — vues heritees ===")
    print(f"DRY_RUN = {DRY_RUN}  (passer --apply pour ecrire)\n")

    print("1) Revert d'eventuelles editions en place sur les vues standard :")
    for cfg in CONFIGS:
        revert_base(cfg)

    print("\n2) Deploiement des vues heritees MyLab :")
    for cfg in CONFIGS:
        deploy_inherited(cfg)

    if not DRY_RUN:
        print("\n3) Verification (arch combinee) :")
        for cfg in CONFIGS:
            verify(cfg)
        print("\nTermine. Verifier un PDF devis ET un PDF facture recents.")
    else:
        print("\nDry-run : rien ecrit. Relancer avec --apply.")


if __name__ == "__main__":
    main()
