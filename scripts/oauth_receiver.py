#!/usr/bin/env python3
"""
MY.LAB — One-shot OAuth receiver for Shopify Theme Sync app.

Listens on port 3000, waits for Shopify's OAuth callback after user installs
the app, exchanges the code for a permanent Admin API token (shpat_...), and
prints it.

Usage:
  python scripts/oauth_receiver.py
"""
import http.server
import json
import os
import secrets
import sys
import urllib.parse
import urllib.request

CLIENT_ID = os.environ.get("SHOPIFY_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("SHOPIFY_CLIENT_SECRET", "")
SCOPES = os.environ.get("SHOPIFY_SCOPES", "write_themes,read_themes,write_files,read_files")
SHOP = os.environ.get("SHOPIFY_SHOP", "mylab-shop-3.myshopify.com")
PORT = int(os.environ.get("PORT", "3000"))

STATE = secrets.token_urlsafe(16)
RESULT = {"token": None, "shop": None}


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        sys.stderr.write(f"  [oauth] {format % args}\n")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path not in ("/auth/callback", "/"):
            self.send_response(404)
            self.end_headers()
            return

        qs = urllib.parse.parse_qs(parsed.query)
        code = qs.get("code", [None])[0]
        shop = qs.get("shop", [None])[0]
        state = qs.get("state", [None])[0]

        if not code:
            self._respond(200, "<h1>Ready</h1><p>Waiting for Shopify callback on this URL.</p>")
            return

        if state != STATE:
            self._respond(400, f"<h1>State mismatch</h1><p>Expected {STATE} got {state}</p>")
            return

        # Exchange code for access token
        token_url = f"https://{shop}/admin/oauth/access_token"
        body = urllib.parse.urlencode({
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
        }).encode("utf-8")

        req = urllib.request.Request(token_url, data=body, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            token = data.get("access_token")
            RESULT["token"] = token
            RESULT["shop"] = shop
            self._respond(200, f"""
                <h1>Installation reussie</h1>
                <p>Token recupere — tu peux fermer cet onglet et retourner au terminal.</p>
                <p>Shop: <code>{shop}</code></p>
            """)
            print("\n" + "=" * 60)
            print("SUCCESS")
            print(f"Shop: {shop}")
            print(f"Token: {token}")
            print("=" * 60 + "\n")
            # Shutdown server after a short delay
            import threading
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        except Exception as e:
            self._respond(500, f"<h1>Échange échoué</h1><pre>{e}</pre>")
            print(f"ERROR: {e}", file=sys.stderr)

    def _respond(self, code, html):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))


def main():
    ngrok_url = os.environ.get("NGROK_URL", "").rstrip("/")
    if not ngrok_url:
        print("ERROR: set NGROK_URL env var first (e.g. https://xxx.ngrok-free.app)", file=sys.stderr)
        sys.exit(1)

    redirect_uri = f"{ngrok_url}/auth/callback"
    install_url = (
        f"https://{SHOP}/admin/oauth/authorize?"
        f"client_id={CLIENT_ID}&"
        f"scope={SCOPES}&"
        f"redirect_uri={urllib.parse.quote(redirect_uri, safe='')}&"
        f"state={STATE}"
    )

    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    print("=" * 70)
    print(f"[oauth] Server listening on http://0.0.0.0:{PORT}")
    print(f"[oauth] Redirect URI  : {redirect_uri}")
    print(f"[oauth] State         : {STATE}")
    print("=" * 70)
    print()
    print(">>> OPEN THIS URL IN YOUR BROWSER TO INSTALL:")
    print()
    print(f"    {install_url}")
    print()
    print("Waiting for Shopify callback...")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

    if RESULT["token"]:
        print(f"\nFinal token: {RESULT['token']}")
        print(f"Copy this into /opt/mylab-theme/.env.sync on the VPS.")


if __name__ == "__main__":
    main()
