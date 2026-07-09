"""Deploy the Hermes morning brief cron : .env + config.yaml + script + cron job.

Adds Shopify/Odoo creds, Paris timezone, the morning_brief.py script, then
creates the cron job (daily 08:00 Paris). Tests it once.
"""
import os
import sys
from pathlib import Path

import paramiko
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env.vps")
load_dotenv(Path(r"D:\Configurateur Designs MyLab\mylab-configurateur\.env.local"))

# Creds from memory references (see reference_api_keys memory)
SHOPIFY_TOKEN = os.environ["SHOPIFY_ADMIN_TOKEN"]  # n8n full-scope token
SHOPIFY_STORE = "mylab-shop-3.myshopify.com"
ODOO_URL = "https://odoo.startec-paris.com"
ODOO_DB = "OdooYJ"
ODOO_UID = "8"
ODOO_API_KEY = os.environ["ODOO_API_KEY"]
YOANN_TG_ID = "7760145552"


MORNING_BRIEF_PY = r'''#!/usr/bin/env python3
"""MyLab Morning Brief — runs via Hermes cron daily 08:00 Paris.

Fetches yesterday's activity from Shopify + Odoo and outputs Markdown
for Telegram delivery. No LLM in the loop -- deterministic, free.
"""
import os
import sys
import xmlrpc.client
from datetime import datetime, timedelta, timezone

import requests

# Load .env from /opt/data/.env (volume mounted from host /root/.hermes/.env)
try:
    from dotenv import load_dotenv
    load_dotenv("/opt/data/.env")
except Exception:
    pass

SHOPIFY_TOKEN = os.environ.get("SHOPIFY_ADMIN_TOKEN", "")
SHOPIFY_STORE = os.environ.get("SHOPIFY_STORE", "")
ODOO_URL = os.environ.get("ODOO_URL", "")
ODOO_DB = os.environ.get("ODOO_DB", "")
ODOO_UID = int(os.environ.get("ODOO_UID", "0") or 0)
ODOO_API_KEY = os.environ.get("ODOO_API_KEY", "")

# Paris timezone: use UTC+1 (winter) / UTC+2 (summer). Best to use zoneinfo.
try:
    from zoneinfo import ZoneInfo
    PARIS = ZoneInfo("Europe/Paris")
except Exception:
    PARIS = timezone(timedelta(hours=1))


def fmt_eur(v):
    return f"{v:,.0f} €".replace(",", " ")


def now_paris():
    return datetime.now(tz=PARIS)


def yesterday_window():
    """Returns (start, end) ISO strings in UTC covering yesterday Paris-local."""
    today_paris = now_paris().replace(hour=0, minute=0, second=0, microsecond=0)
    start_paris = today_paris - timedelta(days=1)
    end_paris = today_paris
    return (
        start_paris.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        end_paris.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def fetch_shopify():
    """Returns dict { 'count', 'revenue_ttc', 'by_gateway': {gateway: count}, 'unpaid_pending': N }."""
    if not (SHOPIFY_TOKEN and SHOPIFY_STORE):
        return {"error": "shopify creds missing"}

    start, end = yesterday_window()
    url = f"https://{SHOPIFY_STORE}/admin/api/2024-10/orders.json"
    params = {
        "created_at_min": start,
        "created_at_max": end,
        "status": "any",
        "limit": 250,
        "fields": "id,total_price,currency,financial_status,gateway,payment_gateway_names",
    }
    headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=30)
        r.raise_for_status()
        orders = r.json().get("orders", [])
    except Exception as e:
        return {"error": f"shopify HTTP error: {e}"}

    revenue = sum(float(o.get("total_price", 0) or 0) for o in orders)
    by_gw = {}
    pending = 0
    for o in orders:
        gws = o.get("payment_gateway_names") or [o.get("gateway") or "unknown"]
        for gw in gws:
            by_gw[gw] = by_gw.get(gw, 0) + 1
        if o.get("financial_status") == "pending":
            pending += 1
    return {
        "count": len(orders),
        "revenue_ttc": revenue,
        "by_gateway": by_gw,
        "unpaid_pending": pending,
    }


def odoo_call(model, method, args, kwargs=None):
    proxy = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object", allow_none=True)
    return proxy.execute_kw(ODOO_DB, ODOO_UID, ODOO_API_KEY, model, method, args, kwargs or {})


def fetch_odoo():
    """Returns dict with new quotes/invoices counts + unpaid list summary."""
    if not (ODOO_URL and ODOO_API_KEY):
        return {"error": "odoo creds missing"}

    today = now_paris().replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = (today - timedelta(days=1)).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    today_start = today.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    seven_days_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")

    try:
        # New quotes created yesterday (sale.order in draft or sent)
        quote_ids = odoo_call("sale.order", "search", [[
            ["create_date", ">=", yesterday_start],
            ["create_date", "<", today_start],
            ["state", "in", ["draft", "sent"]],
        ]])
        # New invoices created yesterday (account.move type=out_invoice)
        invoice_ids = odoo_call("account.move", "search", [[
            ["create_date", ">=", yesterday_start],
            ["create_date", "<", today_start],
            ["move_type", "=", "out_invoice"],
            ["state", "=", "posted"],
        ]])
        # Unpaid invoices > 7 days old
        unpaid_ids = odoo_call("account.move", "search", [[
            ["move_type", "=", "out_invoice"],
            ["state", "=", "posted"],
            ["payment_state", "in", ["not_paid", "partial"]],
            ["invoice_date", "<=", seven_days_ago],
        ]])
        unpaid_total = 0.0
        unpaid_top = []
        if unpaid_ids:
            rows = odoo_call("account.move", "read", [unpaid_ids], {
                "fields": ["name", "amount_residual", "invoice_date", "partner_id"],
            })
            unpaid_total = sum(r["amount_residual"] for r in rows)
            rows.sort(key=lambda r: r["amount_residual"], reverse=True)
            for r in rows[:3]:
                partner = r["partner_id"][1] if r.get("partner_id") else "?"
                days = (now_paris().date() - datetime.strptime(r["invoice_date"], "%Y-%m-%d").date()).days
                unpaid_top.append({
                    "partner": partner[:30],
                    "amount": r["amount_residual"],
                    "days": days,
                })
        return {
            "new_quotes": len(quote_ids),
            "new_invoices": len(invoice_ids),
            "unpaid_count": len(unpaid_ids),
            "unpaid_total": unpaid_total,
            "unpaid_top": unpaid_top,
        }
    except Exception as e:
        return {"error": f"odoo error: {e}"}


def build_message(shop, odoo):
    today = now_paris().strftime("%d/%m/%Y")
    lines = [f"\U0001F4CA *MyLab — Brief du {today}*", ""]

    # Shopify
    lines.append("\U0001F6D2 *Shopify (24h)*")
    if "error" in shop:
        lines.append(f"⚠️ {shop['error']}")
    elif shop["count"] == 0:
        lines.append("Aucune commande hier")
    else:
        lines.append(f"{shop['count']} commande{'s' if shop['count'] > 1 else ''} — {fmt_eur(shop['revenue_ttc'])} TTC")
        if shop["by_gateway"]:
            gw_str = ", ".join(f"{n} {gw}" for gw, n in sorted(shop["by_gateway"].items(), key=lambda x: -x[1]))
            lines.append(f"_{gw_str}_")
        if shop["unpaid_pending"]:
            lines.append(f"⚠️ {shop['unpaid_pending']} en attente paiement")
    lines.append("")

    # Odoo
    lines.append("\U0001F4C4 *Odoo (24h)*")
    if "error" in odoo:
        lines.append(f"⚠️ {odoo['error']}")
    else:
        lines.append(f"{odoo['new_quotes']} nouveau{'x' if odoo['new_quotes'] != 1 else ''} devis")
        lines.append(f"{odoo['new_invoices']} nouvelle{'s' if odoo['new_invoices'] > 1 else ''} facture{'s' if odoo['new_invoices'] > 1 else ''}")
        if odoo["unpaid_count"]:
            lines.append(f"")
            lines.append(f"\U0001F4B8 *Impayés >7j* — {odoo['unpaid_count']} factures, {fmt_eur(odoo['unpaid_total'])}")
            for u in odoo["unpaid_top"]:
                lines.append(f"  • {u['partner']} — {fmt_eur(u['amount'])} (j+{u['days']})")
    lines.append("")
    lines.append("_Source: Shopify Admin API + Odoo XML-RPC_")
    return "\n".join(lines)


def main():
    shop = fetch_shopify()
    odoo = fetch_odoo()
    msg = build_message(shop, odoo)
    print(msg)


if __name__ == "__main__":
    main()
'''


def run(ssh, cmd, label=None):
    if label:
        print(f"\n=== {label} ===")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode(errors="replace").rstrip()
    err = stderr.read().decode(errors="replace").rstrip()
    rc = stdout.channel.recv_exit_status()
    if out:
        print(out)
    if err:
        for line in err.splitlines():
            if line.strip():
                print(f"[stderr] {line}")
    print(f"[rc={rc}]")
    return out, rc


ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(
    os.environ["VPS_HOST"],
    port=int(os.environ.get("VPS_PORT", "22")),
    username=os.environ["VPS_USER"],
    password=os.environ["VPS_PASS"],
    timeout=15,
)
sftp = ssh.open_sftp()

# --- 1. Append cron-related creds to .env (idempotent: strip existing then append)
print("[1/5] Update /root/.hermes/.env with creds + TELEGRAM_HOME_CHANNEL")
with sftp.open("/root/.hermes/.env", "r") as f:
    existing = f.read().decode("utf-8")

# Remove any lines that we will (re)set so the file stays clean across reruns
keys_to_reset = (
    "TELEGRAM_HOME_CHANNEL", "SHOPIFY_ADMIN_TOKEN", "SHOPIFY_STORE",
    "ODOO_URL", "ODOO_DB", "ODOO_UID", "ODOO_API_KEY",
)
kept = [l for l in existing.splitlines() if not any(l.startswith(k + "=") for k in keys_to_reset)]
new_env = "\n".join(kept).rstrip() + f"""

# === morning_brief cron creds ===
TELEGRAM_HOME_CHANNEL={YOANN_TG_ID}
SHOPIFY_ADMIN_TOKEN={SHOPIFY_TOKEN}
SHOPIFY_STORE={SHOPIFY_STORE}
ODOO_URL={ODOO_URL}
ODOO_DB={ODOO_DB}
ODOO_UID={ODOO_UID}
ODOO_API_KEY={ODOO_API_KEY}
"""
with sftp.open("/root/.hermes/.env", "w") as f:
    f.write(new_env)
sftp.chmod("/root/.hermes/.env", 0o600)
print("  .env updated")

# --- 2. Add timezone Europe/Paris to config.yaml (only if not already set)
print("\n[2/5] Set timezone Europe/Paris in config.yaml")
with sftp.open("/root/.hermes/config.yaml", "r") as f:
    cfg = f.read().decode("utf-8")
if "timezone:" not in cfg:
    cfg = "timezone: Europe/Paris\n\n" + cfg
    with sftp.open("/root/.hermes/config.yaml", "w") as f:
        f.write(cfg)
    print("  timezone: Europe/Paris added")
else:
    print("  timezone: already configured, skipping")

# --- 3. Drop morning_brief.py into /root/.hermes/scripts/
print("\n[3/5] Write /root/.hermes/scripts/morning_brief.py")
ssh.exec_command("mkdir -p /root/.hermes/scripts")[1].read()
with sftp.open("/root/.hermes/scripts/morning_brief.py", "w") as f:
    f.write(MORNING_BRIEF_PY)
sftp.chmod("/root/.hermes/scripts/morning_brief.py", 0o755)
print("  morning_brief.py written")

sftp.close()

# --- 4. Restart container so new env vars are loaded
print("\n[4/5] Restart container")
run(ssh, "cd /root/hermes && docker compose restart && sleep 5", label="docker compose restart")
run(ssh, "docker ps --filter name=hermes-gateway --format '{{.Status}}'", label="container status")

# --- 5. Test the script in isolation (inside container) before creating the cron
print("\n[5/5] Test the script (no LLM) inside the container")
run(ssh, "docker exec hermes-gateway python /opt/data/scripts/morning_brief.py", label="dry-run morning_brief.py")

ssh.close()
