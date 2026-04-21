"""V2 : mentions légales, notre-histoire, rejoignez-nous, articles blog."""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_contents import (
    MENTIONS_LEGALES,
    NOTRE_HISTOIRE,
    REJOIGNEZ_NOUS,
    BLOG_HANDLE,
    ARTICLES,
)

TOKEN = os.environ.get("TOKEN") or os.environ.get("SHOPIFY_ADMIN_TOKEN")
SHOP = os.environ.get("SHOP", "mylab-shop-3.myshopify.com")
BASE = f"https://{SHOP}/admin/api/2024-10"

if not TOKEN:
    sys.exit("ERROR: set TOKEN")


def req(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("X-Shopify-Access-Token", TOKEN)
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read()
            return (json.loads(raw) if raw else None), resp.status
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode(errors="ignore")}, e.code


def find_page(handle):
    data, _ = req("GET", f"/pages.json?handle={handle}&fields=id,handle,title,body_html")
    return (data.get("pages") or [None])[0]


def update_page(handle, title, body):
    p = find_page(handle)
    if not p:
        print(f"  SKIP (not found): {handle}")
        return
    payload = {"page": {"id": p["id"], "title": title, "body_html": body}}
    data, status = req("PUT", f"/pages/{p['id']}.json", payload)
    print(f"  UPDATE page {handle} -> {'OK' if status == 200 else f'FAIL {status} {data}'}")


print("=== 1. Pages institutionnelles (v2) ===")
update_page("mentions-legales", "Mentions légales", MENTIONS_LEGALES)
update_page("notre-histoire-mylab", "Notre histoire", NOTRE_HISTOIRE)
update_page("rejoignez-nous", "Rejoignez-nous", REJOIGNEZ_NOUS)
print()

print("=== 2. Articles de blog (Actualités) ===")
# Find blog
data, _ = req("GET", f"/blogs.json?handle={BLOG_HANDLE}")
blogs = data.get("blogs", [])
if not blogs:
    print(f"  ERROR: blog {BLOG_HANDLE} not found")
    sys.exit(1)
blog_id = blogs[0]["id"]
print(f"  blog id={blog_id} handle={BLOG_HANDLE}")

# List existing articles to avoid duplicates
data, _ = req("GET", f"/blogs/{blog_id}/articles.json?limit=250&fields=id,handle,title")
existing = {a["handle"]: a["id"] for a in data.get("articles", [])}

for art in ARTICLES:
    # Use Shopify's handle generation (slug from title) — let them handle it
    title = art["title"]
    payload = {
        "article": {
            "title": title,
            "body_html": art["body_html"],
            "summary_html": art["summary_html"],
            "tags": art["tags"],
            "author": "MY.LAB",
            "published": True,
        }
    }
    # Try to match existing by title start (unique)
    slug_guess = None
    for h, aid in existing.items():
        if h.startswith(title.lower().split(":")[0].strip().replace(" ", "-")[:40]):
            slug_guess = (h, aid)
            break
    if slug_guess:
        h, aid = slug_guess
        payload["article"]["id"] = aid
        data, status = req("PUT", f"/blogs/{blog_id}/articles/{aid}.json", payload)
        print(f"  UPDATE article {h!r} -> {'OK' if status == 200 else f'FAIL {status}'}")
    else:
        data, status = req("POST", f"/blogs/{blog_id}/articles.json", payload)
        if status in (200, 201):
            h = data.get("article", {}).get("handle", "?")
            print(f"  CREATE article -> {title[:60]!r} (handle={h})")
        else:
            print(f"  FAIL create {title[:50]!r} status={status} {data}")

print()
print("Done.")
