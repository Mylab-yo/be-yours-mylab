# Code exécuté par l'action serveur "Répartir en cartons".
#
# Contexte d'exécution Odoo (variables disponibles) :
# - env : odoo.api.Environment
# - records : recordset de stock.picking sélectionné
# - model : env['stock.picking']
# - log(message) : logger helper
#
# Ce fichier est le contenu du champ 'code' de ir.actions.server.
# Odoo l'exécute avec safe_eval() — pas de docstrings (interdits), pas d'imports.

# === LABELS DES FAMILLES ===
FAMILY_LABELS = {
    50: "50ml sérum/huile",
    40: "200ml crème/shampoing",
    24: "200/400ml masque",
    23: "500ml crème/shampoing",
    12: "1L shampoing/masque",
}


def family_label(capacity):
    # Return human-readable label for a carton capacity
    return FAMILY_LABELS.get(capacity, f"Carton {capacity}u")


def purge_existing_packages(picking):
    # Remove previous auto-generated packages AND consolidate split move lines
    auto_package_prefix = "Carton "
    pkg_ids = set()
    for ml in picking.move_line_ids:
        if ml.result_package_id:
            pkg_ids.add(ml.result_package_id.id)
    picking.move_line_ids.write({"result_package_id": False})

    # Consolidate move lines that were split in previous runs: same move_id + product_id
    # + location + lot -> merge into one to avoid fragment accumulation
    groups = {}
    for ml in picking.move_line_ids:
        key = (
            ml.move_id.id,
            ml.product_id.id,
            ml.location_id.id,
            ml.location_dest_id.id,
            ml.lot_id.id if ml.lot_id else 0,
        )
        groups.setdefault(key, []).append(ml)
    for key, lines in groups.items():
        if len(lines) > 1:
            kept = lines[0]
            total_qty = sum(l.quantity for l in lines)
            extras = env["stock.move.line"].browse([l.id for l in lines[1:]])
            extras.unlink()
            kept.write({"quantity": total_qty})

    # Delete orphan auto-packages
    if pkg_ids:
        packages = env["stock.quant.package"].browse(list(pkg_ids))
        for pkg in packages:
            if pkg.name and pkg.name.startswith(auto_package_prefix):
                if not pkg.quant_ids:
                    pkg.unlink()


def split_move_line(ml, qty_to_split):
    # Split a move line: reduce current qty, return new move line with qty_to_split
    remaining = ml.quantity - qty_to_split
    new_ml = ml.copy({
        "quantity": qty_to_split,
        "result_package_id": False,
    })
    ml.write({"quantity": remaining})
    return new_ml


def allocate_family(picking, capacity, move_lines, carton_counter):
    # Allocate move lines of one family into cartons. Returns list of package ids created.
    if capacity == 0:
        pkg = env["stock.quant.package"].create({
            "name": f"Carton {carton_counter[0]} - Divers",
        })
        for ml in move_lines:
            ml.write({"result_package_id": pkg.id})
        carton_counter[0] += 1
        return [pkg.id]

    label = family_label(capacity)
    created_pkgs = []
    current_pkg = None
    current_pkg_units = 0
    ml_list = list(move_lines)
    i = 0
    while i < len(ml_list):
        ml = ml_list[i]
        qty = ml.quantity
        if qty <= 0:
            i += 1
            continue
        if current_pkg is None or current_pkg_units >= capacity:
            current_pkg = env["stock.quant.package"].create({
                "name": f"Carton {carton_counter[0]} - {label}",
            })
            created_pkgs.append(current_pkg.id)
            current_pkg_units = 0
            carton_counter[0] += 1
        space = capacity - current_pkg_units
        if qty <= space:
            ml.write({"result_package_id": current_pkg.id})
            current_pkg_units += qty
            i += 1
        else:
            new_ml = split_move_line(ml, space)
            new_ml.write({"result_package_id": current_pkg.id})
            current_pkg_units += space
    return created_pkgs


def rename_packages_with_total(package_ids, carton_counter):
    # Rename packages to include X/Y suffix
    total = carton_counter[0] - 1
    packages = env["stock.quant.package"].browse(package_ids)
    for pkg in packages:
        parts = pkg.name.split(" - ", 1)
        if len(parts) == 2 and parts[0].startswith("Carton "):
            idx = parts[0].replace("Carton ", "").strip()
            pkg.write({"name": f"Carton {idx}/{total} - {parts[1]}"})


# === MAIN ===
for picking in records:
    purge_existing_packages(picking)

    groups = {}
    for ml in picking.move_line_ids:
        cap = ml.product_id.x_carton_capacity or 0
        groups.setdefault(cap, []).append(ml)

    carton_counter = [1]
    all_created_pkgs = []
    sorted_caps = sorted(groups.keys(), key=lambda c: (c == 0, c))
    for cap in sorted_caps:
        pkgs = allocate_family(picking, cap, groups[cap], carton_counter)
        all_created_pkgs.extend(pkgs)

    rename_packages_with_total(all_created_pkgs, carton_counter)
