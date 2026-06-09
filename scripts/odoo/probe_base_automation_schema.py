"""Inspect base.automation + ir.actions.server schema in Odoo 18."""
from scripts.odoo._client import execute, search_read

print("=== base.automation fields ===")
fields = execute("base.automation", "fields_get", [], {"attributes": ["string", "type", "selection"]})
relevant = ["trigger", "model_id", "model_name", "action_server_id", "filter_domain",
            "filter_pre_domain", "trigger_field_ids", "active", "name", "state",
            "binding_model_id", "code", "on_change_field_ids"]
for k in relevant:
    if k in fields:
        info = fields[k]
        sel = info.get("selection")
        print(f"  {k}: {info['type']}", end="")
        if sel:
            print(f" - choices={[s[0] for s in sel]}", end="")
        print(f" - {info['string']}")

# Existing automations (sale.order context)
print("\n=== Existing base.automation on sale.order ===")
auts = search_read("base.automation",
                   [("model_id.model", "=", "sale.order")],
                   ["id", "name", "trigger", "active"])
for a in auts:
    name = a["name"].encode("ascii", "replace").decode("ascii")
    print(f"  id={a['id']} active={a['active']} trigger={a['trigger']!r} | {name}")

# Sample an existing one to understand structure
print("\n=== Sample full record ===")
if auts:
    sample = search_read("base.automation", [("id", "=", auts[0]["id"])],
                         ["id", "name", "model_id", "trigger", "filter_domain",
                          "filter_pre_domain", "active"])
    for k, v in sample[0].items():
        vs = str(v)
        if len(vs) > 100:
            vs = vs[:100] + "..."
        print(f"  {k}: {vs!r}")
