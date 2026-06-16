"""Morning brief v2 : ajoute n8n failed workflows + santé containers Docker.

- Mount Docker socket dans Hermes container (-> docker ps)
- Mount n8n_data RO (-> query SQLite directe via Python)
- Update morning_brief.py
- Recreate container (docker compose up -d, pas restart, pour appliquer les volumes)
- Test
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


COMPOSE_V2 = """services:
  hermes:
    image: nousresearch/hermes-agent:latest
    container_name: hermes-gateway
    restart: unless-stopped
    command: gateway run
    volumes:
      - /root/.hermes:/opt/data
      # v2: docker socket pour `docker ps` (santé containers)
      - /var/run/docker.sock:/var/run/docker.sock
      # v2: n8n SQLite read-only pour query failed workflows
      - /var/lib/docker/volumes/n8n_data/_data:/n8n_data:ro
    deploy:
      resources:
        limits:
          memory: 2G
"""


MORNING_BRIEF_V2_PY = r'''#!/usr/bin/env python3
"""MyLab Morning Brief v2 - runs via Hermes cron daily 08:00 Paris.

v1: Shopify orders + Odoo quotes/invoices/unpaid
v2: + n8n failed workflows last 24h, + Docker containers health
"""
import os
import re
import subprocess
import sys
import sqlite3
import xmlrpc.client
from datetime import datetime, timedelta, timezone

import requests

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

# v2 paths inside container
N8N_DB_PATH = "/n8n_data/database.sqlite"
DOCKER_BIN = "/usr/bin/docker"

try:
    from zoneinfo import ZoneInfo
    PARIS = ZoneInfo("Europe/Paris")
except Exception:
    PARIS = timezone(timedelta(hours=1))


def fmt_eur(v):
    return f"{v:,.0f} €".replace(",", " ")


def now_paris():
    return datetime.now(tz=PARIS)


def yesterday_window():
    today_paris = now_paris().replace(hour=0, minute=0, second=0, microsecond=0)
    start_paris = today_paris - timedelta(days=1)
    end_paris = today_paris
    return (
        start_paris.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        end_paris.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def fetch_shopify():
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
    if not (ODOO_URL and ODOO_API_KEY):
        return {"error": "odoo creds missing"}
    today = now_paris().replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = (today - timedelta(days=1)).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    today_start = today.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    seven_days_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    try:
        quote_ids = odoo_call("sale.order", "search", [[
            ["create_date", ">=", yesterday_start],
            ["create_date", "<", today_start],
            ["state", "in", ["draft", "sent"]],
        ]])
        invoice_ids = odoo_call("account.move", "search", [[
            ["create_date", ">=", yesterday_start],
            ["create_date", "<", today_start],
            ["move_type", "=", "out_invoice"],
            ["state", "=", "posted"],
        ]])
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


def fetch_n8n_failures():
    """Query n8n SQLite for executions that failed in the last 24h."""
    if not os.path.exists(N8N_DB_PATH):
        return {"error": "n8n DB not mounted"}
    # Read-only URI mode; n8n is writing concurrently so handle it gracefully
    uri = f"file:{N8N_DB_PATH}?mode=ro&immutable=0"
    cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=10)
        cur = conn.cursor()
        # n8n status enum: success, error, failed, crashed, canceled, running, waiting
        cur.execute(
            """
            SELECT e.id, e.startedAt, e.status, COALESCE(w.name, e.workflowId) AS wf_name
            FROM execution_entity e
            LEFT JOIN workflow_entity w ON e.workflowId = w.id
            WHERE e.status IN ('error', 'failed', 'crashed')
              AND e.startedAt > ?
            ORDER BY e.startedAt DESC
            LIMIT 50
            """,
            (cutoff,),
        )
        rows = cur.fetchall()
        conn.close()
        # Group by workflow name + status
        by_wf = {}
        for _id, _ts, status, wf in rows:
            key = (wf or "?", status)
            by_wf[key] = by_wf.get(key, 0) + 1
        # Top 5 by count
        ranked = sorted(by_wf.items(), key=lambda x: -x[1])[:5]
        return {
            "total": len(rows),
            "top": [{"workflow": wf, "status": status, "count": n} for (wf, status), n in ranked],
        }
    except Exception as e:
        return {"error": f"n8n DB error: {e}"}


def fetch_docker_health():
    """Liste containers Docker du host, repere les non-running ou unhealthy."""
    try:
        proc = subprocess.run(
            [DOCKER_BIN, "ps", "-a", "--format", "{{.Names}}|{{.Status}}|{{.State}}"],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode != 0:
            return {"error": f"docker ps failed: {proc.stderr.strip()}"}
        lines = [l for l in proc.stdout.strip().split("\n") if l]
        running = []
        problems = []
        for line in lines:
            parts = line.split("|", 2)
            if len(parts) < 3:
                continue
            name, status, state = parts[0], parts[1], parts[2]
            # Skip ourselves
            if name == "hermes-gateway":
                continue
            if state == "running":
                if "(unhealthy)" in status:
                    problems.append({"name": name, "issue": "unhealthy"})
                else:
                    running.append(name)
            else:
                problems.append({"name": name, "issue": f"{state}: {status[:40]}"})
        return {"running_count": len(running), "running_names": running, "problems": problems}
    except Exception as e:
        return {"error": f"docker exec error: {e}"}


def build_message(shop, odoo, n8n, docker):
    today = now_paris().strftime("%d/%m/%Y")
    lines = [f"\U0001F4CA *MyLab - Brief du {today}*", ""]

    # Shopify
    lines.append("\U0001F6D2 *Shopify (24h)*")
    if "error" in shop:
        lines.append(f"⚠️ {shop['error']}")
    elif shop["count"] == 0:
        lines.append("Aucune commande hier")
    else:
        lines.append(f"{shop['count']} commande{'s' if shop['count'] > 1 else ''} - {fmt_eur(shop['revenue_ttc'])} TTC")
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
            lines.append("")
            lines.append(f"\U0001F4B8 *Impayes >7j* - {odoo['unpaid_count']} factures, {fmt_eur(odoo['unpaid_total'])}")
            for u in odoo["unpaid_top"]:
                lines.append(f"  - {u['partner']} - {fmt_eur(u['amount'])} (j+{u['days']})")
    lines.append("")

    # n8n
    lines.append("⚡ *n8n (24h)*")
    if "error" in n8n:
        lines.append(f"⚠️ {n8n['error']}")
    elif n8n["total"] == 0:
        lines.append("Aucune execution echouee")
    else:
        lines.append(f"{n8n['total']} executions echouees")
        for t in n8n["top"]:
            wf_display = t["workflow"][:35] if t["workflow"] else "?"
            lines.append(f"  - {wf_display} ({t['status']}) x{t['count']}")
    lines.append("")

    # Docker host
    lines.append("\U0001F433 *Containers Docker*")
    if "error" in docker:
        lines.append(f"⚠️ {docker['error']}")
    else:
        lines.append(f"{docker['running_count']} containers running : {', '.join(docker['running_names'])}")
        if docker["problems"]:
            lines.append("⚠️ *Problemes :*")
            for p in docker["problems"]:
                lines.append(f"  - {p['name']} : {p['issue']}")
        else:
            lines.append("✅ Tous nominaux")
    lines.append("")
    lines.append("_Source: Shopify API + Odoo XML-RPC + n8n SQLite + docker ps_")
    return "\n".join(lines)


def main():
    shop = fetch_shopify()
    odoo = fetch_odoo()
    n8n = fetch_n8n_failures()
    docker = fetch_docker_health()
    msg = build_message(shop, odoo, n8n, docker)
    print(msg)


if __name__ == "__main__":
    main()
'''


def run(ssh, cmd, label=None, timeout=60):
    if label:
        print(f"\n=== {label} ===")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
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

# 1. Backup + write new docker-compose.yml with v2 volumes
print("[1/4] Write new docker-compose.yml (with /var/run/docker.sock + n8n_data RO)")
with sftp.open("/root/hermes/docker-compose.yml.bak-v1", "w") as f:
    f.write(sftp.open("/root/hermes/docker-compose.yml", "r").read())
with sftp.open("/root/hermes/docker-compose.yml", "w") as f:
    f.write(COMPOSE_V2)
print("  done (backup: docker-compose.yml.bak-v1)")

# 2. Write new morning_brief.py
print("\n[2/4] Write new /root/.hermes/scripts/morning_brief.py")
with sftp.open("/root/.hermes/scripts/morning_brief.py.bak-v1", "w") as f:
    f.write(sftp.open("/root/.hermes/scripts/morning_brief.py", "r").read())
with sftp.open("/root/.hermes/scripts/morning_brief.py", "w") as f:
    f.write(MORNING_BRIEF_V2_PY)
sftp.chmod("/root/.hermes/scripts/morning_brief.py", 0o755)
print("  done (backup: morning_brief.py.bak-v1)")

sftp.close()

# 3. Recreate container (compose up -d applies new volumes; restart wouldn't)
run(ssh, "cd /root/hermes && docker compose up -d 2>&1 | tail -10", label="docker compose up -d (recreate)", timeout=120)
run(ssh, "sleep 5 && docker ps --filter name=hermes-gateway --format '{{.Status}}\\t{{.Mounts}}' | head -2", label="container status + mounts")

# 4. Test script in container
print("\n[4/4] Test the v2 script in container (no LLM)")
run(ssh, "docker exec hermes-gateway python /opt/data/scripts/morning_brief.py", label="dry-run morning_brief.py v2", timeout=60)

ssh.close()
