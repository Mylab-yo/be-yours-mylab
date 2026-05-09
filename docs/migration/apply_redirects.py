"""
Bulk redirect creator for WP→Shopify migration.

USAGE:
  # 1. Dry-run (default) — shows what would happen, no API write:
  python apply_redirects.py

  # 2. Execute for real:
  python apply_redirects.py --apply

  # 3. Filter by priority tier:
  python apply_redirects.py --apply --priority P1_HOT
  python apply_redirects.py --apply --priority P1_HOT,P2_RANKED

  # 4. Skip TODO_MANUAL (entries needing human mapping):
  python apply_redirects.py --apply --skip-manual

INPUT: docs/migration/redirect_plan.csv
OUTPUT: docs/migration/redirect_apply.log

Idempotent: re-runnable safely. Existing redirects with matching target are skipped (NOOP).
Existing redirects with different target are DELETED then recreated (REPLACE).
"""
import argparse, csv, json, os, sys, time, urllib.error, urllib.parse, urllib.request

SHOP = "mylab-shop-3.myshopify.com"
TOKEN = os.environ.get("SHOPIFY_CONTENT_TOKEN")
if not TOKEN:
    sys.exit("ERROR: set SHOPIFY_CONTENT_TOKEN env var (Shopify Admin API token with write_themes/write_content scope)")
PLAN_FILE = os.path.join(os.path.dirname(__file__), 'redirect_plan.csv')
LOG_FILE = os.path.join(os.path.dirname(__file__), 'redirect_apply.log')


def api(method, path, body=None):
    url = f"https://{SHOP}/admin/api/2024-10/{path}"
    data = json.dumps(body).encode('utf-8') if body else None
    req = urllib.request.Request(url, data=data, method=method,
        headers={'X-Shopify-Access-Token': TOKEN, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read()) if r.status != 204 else None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace')


def find_redirect_id(path):
    """Look up redirect ID by path."""
    code, data = api('GET', f'redirects.json?path={urllib.parse.quote(path, safe="")}&limit=1')
    if code == 200 and data.get('redirects'):
        return data['redirects'][0]['id']
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='Actually write to Shopify (default is dry-run)')
    ap.add_argument('--priority', default='P1_HOT,P2_RANKED,P3_INDEXED,P4_LONGTAIL',
                    help='Comma-separated priority tiers to process')
    ap.add_argument('--skip-manual', action='store_true', help='Skip TODO_MANUAL entries')
    args = ap.parse_args()

    priorities = set(args.priority.split(','))
    rows = list(csv.DictReader(open(PLAN_FILE, encoding='utf-8')))
    rows = [r for r in rows if r['priority'] in priorities]
    if args.skip_manual:
        rows = [r for r in rows if r['action'] != 'TODO_MANUAL']

    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f"=== {mode} mode | priorities={sorted(priorities)} | {len(rows)} entries ===\n")

    log = open(LOG_FILE, 'a', encoding='utf-8')
    log.write(f"\n=== Run {time.strftime('%Y-%m-%d %H:%M:%S')} {mode} ===\n")

    counts = {'NOOP': 0, 'CREATE': 0, 'REPLACE': 0, 'KEEP_EXISTING': 0, 'TODO_MANUAL': 0, 'ERROR': 0}

    for i, r in enumerate(rows, 1):
        action = r['action']
        path = r['wp_path']
        target = r['suggested_target']
        existing = r['existing_redirect']
        prefix = f"[{i}/{len(rows)}] {r['priority']:<11} {action:<14}"

        if action == 'NOOP':
            print(f"{prefix} {path} (already → {target})")
            counts['NOOP'] += 1

        elif action == 'KEEP_EXISTING':
            print(f"{prefix} {path} (keeping existing → {existing})")
            counts['KEEP_EXISTING'] += 1

        elif action == 'TODO_MANUAL':
            print(f"{prefix} {path} (need manual mapping — {r['note']})")
            counts['TODO_MANUAL'] += 1

        elif action == 'CREATE':
            print(f"{prefix} {path} → {target}", end='')
            if args.apply:
                code, data = api('POST', 'redirects.json',
                    {'redirect': {'path': path, 'target': target}})
                if code == 201:
                    print(' ✓')
                    counts['CREATE'] += 1
                    log.write(f"CREATE {path} → {target}\n")
                else:
                    print(f' ✗ HTTP {code} {str(data)[:120]}')
                    counts['ERROR'] += 1
                    log.write(f"ERROR CREATE {path}: {code} {data}\n")
            else:
                print(' (dry-run)')
                counts['CREATE'] += 1

        elif action == 'REPLACE':
            print(f"{prefix} {path}: {existing} → {target}", end='')
            if args.apply:
                rid = find_redirect_id(path)
                if rid:
                    code, data = api('PUT', f'redirects/{rid}.json',
                        {'redirect': {'id': rid, 'path': path, 'target': target}})
                    if code == 200:
                        print(' ✓')
                        counts['REPLACE'] += 1
                        log.write(f"REPLACE {path}: {existing} → {target}\n")
                    else:
                        print(f' ✗ HTTP {code} {str(data)[:120]}')
                        counts['ERROR'] += 1
                        log.write(f"ERROR REPLACE {path}: {code} {data}\n")
                else:
                    print(f' ✗ Could not find existing redirect ID')
                    counts['ERROR'] += 1
            else:
                print(' (dry-run)')
                counts['REPLACE'] += 1

        # Rate-limit safe (Shopify allows ~2 req/s on standard plan)
        if args.apply:
            time.sleep(0.55)

    print(f"\n=== {mode} SUMMARY ===")
    for k, v in counts.items():
        print(f"  {k:<15} {v}")
    log.write(f"SUMMARY: {counts}\n")
    log.close()


if __name__ == '__main__':
    main()
