#!/usr/bin/env python3
"""One-time : obtenir un refresh token Gmail (scope gmail.modify) pour yoann@mylab-shop.com.

Prérequis (Task 0) : client OAuth 'Desktop app' dans le projet mylab-design-studio,
Gmail API activée, yoann@mylab-shop.com en test user.

Usage (PowerShell) :
  $env:GMAIL_CLIENT_ID="..."; $env:GMAIL_CLIENT_SECRET="..."; python scripts/hermes/gmail_oauth_setup.py

Le script ouvre la page de consentement, reçoit le code sur localhost, et imprime
le refresh token à coller dans .env.vps (poste) puis dans /root/.hermes/.env (Task 7).
"""
import http.server
import os
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser

CLIENT_ID = os.environ["GMAIL_CLIENT_ID"]
CLIENT_SECRET = os.environ["GMAIL_CLIENT_SECRET"]
SCOPE = "https://www.googleapis.com/auth/gmail.modify"
PORT = int(os.environ.get("PORT", "8765"))
REDIRECT = f"http://localhost:{PORT}/callback"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
STATE = secrets.token_urlsafe(16)
RESULT = {}


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if qs.get("state", [None])[0] != STATE or "code" not in qs:
            self._html(400, "<h1>Erreur</h1>")
            return
        body = urllib.parse.urlencode({
            "code": qs["code"][0], "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT, "grant_type": "authorization_code",
        }).encode()
        req = urllib.request.Request(TOKEN_URL, data=body, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            import json
            data = json.loads(resp.read().decode())
        RESULT.update(data)
        self._html(200, "<h1>OK</h1><p>Refresh token récupéré, retourne au terminal.</p>")
        import threading
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def _html(self, code, html):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())


def main():
    params = urllib.parse.urlencode({
        "client_id": CLIENT_ID, "redirect_uri": REDIRECT, "response_type": "code",
        "scope": SCOPE, "access_type": "offline", "prompt": "consent", "state": STATE,
        "login_hint": "yoann@mylab-shop.com",
    })
    url = f"{AUTH_URL}?{params}"
    print("Ouvre cette URL et connecte-toi avec yoann@mylab-shop.com :\n")
    print(f"    {url}\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    http.server.HTTPServer(("localhost", PORT), Handler).serve_forever()
    rt = RESULT.get("refresh_token")
    if rt:
        print("\n" + "=" * 60)
        print("SUCCESS — ajoute ces lignes à .env.vps :")
        print(f"GMAIL_CLIENT_ID={CLIENT_ID}")
        print(f"GMAIL_CLIENT_SECRET={CLIENT_SECRET}")
        print(f"GMAIL_REFRESH_TOKEN={rt}")
        print("=" * 60)
    else:
        print(f"\nÉCHEC — pas de refresh_token. Réponse : {RESULT}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
