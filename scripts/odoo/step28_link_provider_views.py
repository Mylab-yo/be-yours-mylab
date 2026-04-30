"""Link the technical view templates each provider needs to render its
payment form on the portal.

Required after creating a payment.provider via XML-RPC — the data XML
that ships with each provider module wouldn't normally apply to a
manually-created record, so the view fields stay empty and the JS
crashes with 'Cannot read properties of null (reading setAttribute)'
in _processRedirectFlow.

Idempotent: looks up by xml_id, sets only if missing.

Run: python step28_link_provider_views.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import execute, search_read, write

def get_view_id(xml_id: str) -> int | None:
    """Resolve a view xml_id to its id, or None if not found."""
    module, name = xml_id.split(".", 1)
    rec = search_read("ir.model.data",
                     [("module", "=", module), ("name", "=", name),
                      ("model", "=", "ir.ui.view")],
                     ["res_id"])
    return rec[0]["res_id"] if rec else None

# Map: (provider_code, view_field, xml_id_to_link)
LINKS = [
    ("custom",  "redirect_form_view_id",         "payment_custom.redirect_form"),
    ("stripe",  "inline_form_view_id",           "payment_stripe.inline_form"),
    ("stripe",  "express_checkout_form_view_id", "payment_stripe.express_checkout_form"),
    # PayPal in Odoo 18 doesn't use a redirect/inline view — uses the JS SDK button
    # via payment_paypal.payment_submit_button_inherit (qweb inherit, applied automatically)
]

for code, field, xml_id in LINKS:
    providers = search_read("payment.provider",
                            [("code", "=", code)],
                            ["id", "name", field])
    if not providers:
        print(f"⚠ No provider with code='{code}' — skipping")
        continue
    p = providers[0]
    print(f"\nProvider [{p['id']}] {p['name']} — field {field}")
    current = p[field]
    if current:
        print(f"  Already set: {current}")
        continue

    view_id = get_view_id(xml_id)
    if not view_id:
        print(f"  ⚠ Could not resolve {xml_id}")
        continue
    print(f"  Linking {xml_id} (id={view_id})")
    write("payment.provider", [p["id"]], {field: view_id})
    print(f"  ✓ Done")

print("\n=== Final state ===")
for code in ("custom", "stripe", "paypal"):
    p = search_read("payment.provider",
                    [("code", "=", code)],
                    ["id", "name", "state", "redirect_form_view_id",
                     "inline_form_view_id", "express_checkout_form_view_id"])
    if not p:
        continue
    p = p[0]
    print(f"  [{p['id']}] {p['name']} state={p['state']}")
    print(f"    redirect_form_view_id:         {p['redirect_form_view_id']}")
    print(f"    inline_form_view_id:           {p['inline_form_view_id']}")
    print(f"    express_checkout_form_view_id: {p['express_checkout_form_view_id']}")
