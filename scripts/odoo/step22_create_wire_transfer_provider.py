"""Create a Wire Transfer (Virement bancaire) payment provider.

Required because payment_custom in Odoo 18 doesn't auto-create the provider
record on install — has to be done explicitly.

Idempotent: skips if a wire transfer provider already exists.
Initial state: 'disabled' (you enable it manually in UI after reviewing IBAN).

Run: python step03_create_wire_transfer_provider.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read, create, execute

# Check if already exists
existing = search_read(
    "payment.provider",
    [("code", "=", "custom"), ("custom_mode", "=", "wire_transfer")],
    ["id", "name", "state"],
)
if existing:
    p = existing[0]
    print(f"✓ Wire transfer provider already exists: [{p['id']}] {p['name']} (state={p['state']})")
    sys.exit(0)

# Read company bank account for pending msg
companies = search_read("res.company", [], ["id", "name", "partner_id"])
company_id = companies[0]["id"]
partner_id = companies[0]["partner_id"][0]

bank_accounts = search_read(
    "res.partner.bank",
    [("partner_id", "=", partner_id)],
    ["acc_number", "bank_id"],
)
iban_text = ""
if bank_accounts:
    iban = bank_accounts[0]["acc_number"]
    bank = bank_accounts[0]["bank_id"][1] if bank_accounts[0]["bank_id"] else ""
    iban_text = f"\n\nIBAN: {iban}\nBanque: {bank}"
    print(f"Found bank account: {iban} ({bank})")

pending_msg = (
    "<p>Merci pour votre commande. Votre devis va rester en attente jusqu'à "
    "réception du virement. Veuillez utiliser la <strong>référence "
    "{order_reference}</strong> en libellé."
    + iban_text +
    "</p>"
)

values = {
    "name": "Virement bancaire",
    "code": "custom",
    "custom_mode": "wire_transfer",
    "state": "disabled",  # User enables manually after review
    "company_id": company_id,
    "pending_msg": pending_msg,
}

new_id = create("payment.provider", values)
print(f"✓ Created wire transfer provider: id={new_id}, state=disabled")
print(f"  → Pour activer : ouvre {new_id} dans l'UI Payment Providers, passe State=Enabled")
