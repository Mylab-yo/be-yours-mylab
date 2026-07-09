"""Check real Shopify financial_status + payment gateway for the cron-target
invoices that originate from Shopify orders. Rule (per Yoann): Shopify orders
are ALL paid EXCEPT those paid by bank transfer (virement)."""
import sys, io, os
import urllib.request, json
from pathlib import Path
from dotenv import load_dotenv
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv(Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local"))
TOKEN = os.environ["SHOPIFY_ADMIN_TOKEN"]  # from .env.local (read_orders)
STORE = "mylab-shop-3.myshopify.com"
API = "2024-10"

# order_id : (FAC, partner, Shopify#)
ORDERS = {
    "8564475330894": ("FAC/2026/00096", "C DIGNITY", "#3489"),
    "8565124825422": ("FAC/2026/00097", "Smaily Charles", "#3490"),
    "8569315492174": ("FAC/2026/00098", "Dordet Tiberio/E.Leclerc", "#3491"),
    "8569829327182": ("FAC/2026/00099", "ERINA NYX", "#3492"),
    "8572546220366": ("FAC/2026/00101", "Cannelle Coiffure", "#3493"),
    "8573261381966": ("FAC/2026/00102", "Nuances Bresil", "#3494"),
    "8576621871438": ("FAC/2026/00104", "Mahine Hairstylist", "#3495"),
    "8580694901070": ("FAC/2026/00107", "Heliconia", "#3497"),
}

def get(oid):
    url = (f"https://{STORE}/admin/api/{API}/orders/{oid}.json"
           "?fields=id,name,financial_status,gateway,payment_gateway_names,"
           "total_price,total_outstanding,tags,note")
    req = urllib.request.Request(url, headers={"X-Shopify-Access-Token": TOKEN})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["order"]

print(f"{'FAC':<16} {'Shop#':<7} {'financial_status':<18} {'gateways':<28} {'outstanding':<11} verdict")
print("-" * 110)
for oid, (fac, partner, shop) in ORDERS.items():
    try:
        o = get(oid)
        gw = ",".join(o.get("payment_gateway_names") or []) or (o.get("gateway") or "")
        fs = o.get("financial_status") or ""
        out = o.get("total_outstanding") or ""
        # heuristic verdict
        is_transfer = any(k in gw.lower() for k in
                          ["virement", "bank", "transfer", "manual", "wire"])
        if fs == "paid":
            verdict = "PAYÉ (carte) -> NE PAS relancer, réconcilier Odoo"
        elif is_transfer:
            verdict = "VIREMENT en attente -> relance légitime"
        else:
            verdict = f"À VÉRIFIER (fs={fs}, gw={gw})"
        print(f"{fac:<16} {shop:<7} {fs:<18} {gw:<28} {str(out):<11} {verdict}")
    except Exception as e:
        print(f"{fac:<16} {shop:<7} ERROR: {e}")
