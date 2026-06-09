"""Debug : check the actual report binding for the 'Print Quote' button
and simulate the filename evaluation."""
from scripts.odoo._client import search_read, execute

# 1. Check all bindings of type 'report' on sale.order
print("=== All ir.actions.report with binding to sale.order ===")
reports = search_read(
    "ir.actions.report",
    [("model", "=", "sale.order")],
    ["id", "name", "report_name", "print_report_name",
     "binding_model_id", "binding_type", "binding_view_types"],
)
for r in reports:
    print(f"\n  ID {r['id']} {r['name']}")
    print(f"    binding_type   = {r['binding_type']}")
    print(f"    binding_views  = {r['binding_view_types']}")
    print(f"    print_report_name = {r['print_report_name']}")

# 2. Try to simulate the filename eval on the recent order S00566
print("\n\n=== Simulate filename for S00566 ===")
so = search_read("sale.order", [("name", "=", "S00566")],
                 ["id", "name", "state", "partner_id"])
if so:
    so = so[0]
    print(f"Order S00566 found: id={so['id']}, state={so['state']}, partner={so['partner_id'][1]}")
    # Call ir.actions.report._get_report_filename on each report binding
    for r in reports:
        try:
            # Build eval context like Odoo does
            from xmlrpc.client import ServerProxy
            # Call get_report_filename method via XML-RPC (may not be exposed)
            result = execute(
                "ir.actions.report",
                "_get_report_filename",
                [[r["id"]], [so["id"]]],
            )
            print(f"  Report {r['id']} {r['name']} -> filename: {result!r}")
        except Exception as e:
            print(f"  Report {r['id']} {r['name']} -> ERROR: {e}")

# 3. Force a registry refresh by writing a dummy field
print("\n=== Force cache invalidation by re-writing print_report_name ===")
from scripts.odoo._client import write
for r in reports:
    current_expr = r["print_report_name"]
    if current_expr:
        # Re-write the same value (forces invalidate)
        write("ir.actions.report", [r["id"]], {"print_report_name": current_expr})
        print(f"  Touched ID {r['id']}")
