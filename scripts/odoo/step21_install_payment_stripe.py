"""Install the payment_stripe module on Odoo 18.

Idempotent: skips if already installed. Triggers a synchronous install via
button_immediate_install (same as clicking "Install" in Apps UI).

Run: python step02_install_payment_stripe.py
"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import execute, search_read

MODULE = "payment_stripe"

mod = search_read("ir.module.module", [("name", "=", MODULE)],
                  ["id", "state", "shortdesc"])
if not mod:
    print(f"ERROR: module {MODULE} not found")
    sys.exit(1)

m = mod[0]
print(f"Module: {m['shortdesc']} (id={m['id']})")
print(f"Current state: {m['state']}")

if m["state"] == "installed":
    print("Already installed — nothing to do.")
    sys.exit(0)

if m["state"] not in ("uninstalled", "to install"):
    print(f"ERROR: unexpected state '{m['state']}', aborting.")
    sys.exit(1)

print(f"\nInstalling {MODULE}... (10-30s)")
t0 = time.time()
execute("ir.module.module", "button_immediate_install", [[m["id"]]])
elapsed = time.time() - t0
print(f"Install command returned in {elapsed:.1f}s")

# Verify
mod2 = search_read("ir.module.module", [("id", "=", m["id"])],
                   ["state"])[0]
print(f"New state: {mod2['state']}")

if mod2["state"] == "installed":
    print("\n✓ payment_stripe installed successfully")
    # Check that a provider record was created
    providers = search_read("payment.provider", [("code", "=", "stripe")],
                            ["id", "name", "state"])
    if providers:
        print(f"✓ Stripe provider record created: id={providers[0]['id']}, "
              f"state={providers[0]['state']}")
    else:
        print("⚠ No Stripe provider record found — may need refresh")
else:
    print(f"\n✗ Install did not complete cleanly (state={mod2['state']})")
    sys.exit(1)
