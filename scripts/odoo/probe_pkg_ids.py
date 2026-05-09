"""Check package ids vs names on the new picking."""
from scripts.odoo._client import search_read

# Find the new picking (most recent OUT for SO S00418)
pickings = search_read("stock.picking",
    [("origin", "=", "S00418"), ("picking_type_id", "=", 10)],
    ["id", "name", "state", "create_date"])
pickings.sort(key=lambda p: p['create_date'] or '', reverse=True)
pid = pickings[0]['id']
print(f"Latest picking: {pickings[0]['name']} (id={pid}, state={pickings[0]['state']})")

# All packages on this picking
mls = search_read("stock.move.line", [("picking_id", "=", pid)],
    ["id", "result_package_id"])
pkg_ids = sorted({m['result_package_id'][0] for m in mls if m['result_package_id']})
print(f"\nPackages on picking ({len(pkg_ids)}):")
pkgs = search_read("stock.quant.package", [("id", "in", pkg_ids)],
    ["id", "name", "create_date"])
# Sort by id ASC (= what the template now does)
pkgs_by_id = sorted(pkgs, key=lambda p: p['id'])
for p in pkgs_by_id:
    print(f"  id={p['id']:4d}  name={p['name']}")

print("\n---")
print("If the template now sorts by id ASC, the print order above is what should appear in PDF.")
print("If PDF shows reverse, either (a) template push didn't apply, or (b) sort by id is wrong direction.")

# Verify deployed template
view = search_read("ir.ui.view", [("id", "=", 3359)], ["arch_db", "name"])[0]
print(f"\nDeployed template name: {view['name']}")
print(f"Looking for sorted() in arch:")
arch = view['arch_db'] or ''
for line in arch.split('\n'):
    if 'packages' in line.lower() or 'sorted' in line.lower() or 'mapped' in line.lower():
        print(f"  > {line.strip()}")
