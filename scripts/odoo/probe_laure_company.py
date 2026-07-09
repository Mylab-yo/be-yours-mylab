"""Check parent company LAURE COIFFURE (id 1220)."""
from _client import search_read

# Parent company
p = search_read("res.partner", [("id", "=", 1220)],
                ["id", "name", "email", "phone", "is_company", "child_ids"])
print("Company:", p)

# All contacts under it
if p:
    children = search_read("res.partner", [("parent_id", "=", 1220)],
                           ["id", "name", "email", "function", "phone"])
    print(f"\nContacts ({len(children)}):")
    for c in children:
        print(f"  [{c['id']}] {c['name']} email={c['email']!r} phone={c['phone']!r}")
