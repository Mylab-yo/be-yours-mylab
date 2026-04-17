"""
Code exécuté par l'action serveur "Répartir en cartons".

Contexte d'exécution Odoo (variables disponibles) :
- env : odoo.api.Environment
- records : recordset de stock.picking sélectionné
- model : env['stock.picking']
- log(message) : logger helper

Ce fichier est le contenu du champ 'code' de ir.actions.server.
Odoo l'exécute avec exec() dans un scope limité.
"""

# === LABELS DES FAMILLES ===
FAMILY_LABELS = {
    50: "50ml sérum/huile",
    40: "200ml crème/shampoing",
    24: "200/400ml masque",
    23: "500ml crème/shampoing",
    12: "1L shampoing/masque",
}


def family_label(capacity):
    return FAMILY_LABELS.get(capacity, f"Carton {capacity}u")


def purge_existing_packages(picking):
    """Remove previous auto-generated packages for this picking."""
    auto_package_prefix = "Carton "
    # Find packages referenced by this picking's move lines
    pkg_ids = set()
    for ml in picking.move_line_ids:
        if ml.result_package_id:
            pkg_ids.add(ml.result_package_id.id)
    # Unlink move line -> package
    picking.move_line_ids.write({"result_package_id": False})
    # Delete packages that have our auto-prefix AND are now orphan
    if pkg_ids:
        packages = env["stock.quant.package"].browse(list(pkg_ids))
        for pkg in packages:
            if pkg.name and pkg.name.startswith(auto_package_prefix):
                if not pkg.quant_ids:  # orphan = no quants
                    pkg.unlink()


def split_move_line(ml, qty_to_split):
    """Split a move line: reduce current qty, return a new move line with qty_to_split."""
    remaining = ml.qty_done - qty_to_split
    new_ml = ml.copy({
        "qty_done": qty_to_split,
        "result_package_id": False,
    })
    ml.qty_done = remaining
    return new_ml


def allocate_family(picking, capacity, move_lines, carton_counter):
    """Allocate move lines of one family into cartons. Returns list of package ids created."""
    if capacity == 0:
        # Family "Divers" : one single package for everything
        pkg = env["stock.quant.package"].create({
            "name": f"Carton {carton_counter[0]} - Divers",
        })
        for ml in move_lines:
            ml.result_package_id = pkg.id
        carton_counter[0] += 1
        return [pkg.id]

    label = family_label(capacity)
    total_units = sum(ml.qty_done for ml in move_lines)
    nb_full = int(total_units // capacity)
    remainder = int(total_units % capacity)
    nb_cartons = nb_full + (1 if remainder else 0)

    created_pkgs = []
    # Sequential fill
    current_pkg = None
    current_pkg_units = 0
    # Work on a list we can mutate (splits append new items)
    ml_list = list(move_lines)
    i = 0
    while i < len(ml_list):
        ml = ml_list[i]
        qty = ml.qty_done
        if qty <= 0:
            i += 1
            continue
        if current_pkg is None or current_pkg_units >= capacity:
            # Open new package
            current_pkg = env["stock.quant.package"].create({
                "name": f"Carton {carton_counter[0]} - {label}",
            })
            created_pkgs.append(current_pkg.id)
            current_pkg_units = 0
            carton_counter[0] += 1
        space = capacity - current_pkg_units
        if qty <= space:
            ml.result_package_id = current_pkg.id
            current_pkg_units += qty
            i += 1
        else:
            # Need to split: fill current carton, queue remainder
            new_ml = split_move_line(ml, space)
            new_ml.result_package_id = current_pkg.id
            current_pkg_units += space
            # ml still has (qty - space), continue in next iteration with same i
    return created_pkgs


def rename_packages_with_total(package_ids, carton_counter):
    """Rename packages to include X/Y suffix."""
    total = carton_counter[0] - 1
    packages = env["stock.quant.package"].browse(package_ids)
    for pkg in packages:
        # Name format: "Carton N - <label>" -> "Carton N/total - <label>"
        parts = pkg.name.split(" - ", 1)
        if len(parts) == 2 and parts[0].startswith("Carton "):
            idx = parts[0].replace("Carton ", "").strip()
            pkg.name = f"Carton {idx}/{total} - {parts[1]}"


# === MAIN ===
for picking in records:
    # 1. Purge
    purge_existing_packages(picking)

    # 2. Group move lines by capacity
    groups = {}
    for ml in picking.move_line_ids:
        cap = ml.product_id.x_carton_capacity or 0
        groups.setdefault(cap, []).append(ml)

    # 3. Allocate per family (sorted: real families first, Divers last)
    carton_counter = [1]  # list for mutability across helper calls
    all_created_pkgs = []
    sorted_caps = sorted(groups.keys(), key=lambda c: (c == 0, c))
    for cap in sorted_caps:
        pkgs = allocate_family(picking, cap, groups[cap], carton_counter)
        all_created_pkgs.extend(pkgs)

    # 4. Rename with total count
    rename_packages_with_total(all_created_pkgs, carton_counter)
