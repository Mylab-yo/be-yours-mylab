#!/usr/bin/env python3
"""One-time : refresh token Google Workspace ELARGI (Gmail + Calendar + Drive)
pour yoann@mylab-shop.com, destiné au MCP workspace-mcp dans Hermes.

Réutilise le client OAuth Desktop existant "MyLab Hermes Email Responder"
(projet mylab-design-studio) — mêmes GMAIL_CLIENT_ID/SECRET que l'email-responder,
mais avec 3 scopes au lieu d'un seul.

PREREQUIS côté Google Cloud (projet mylab-design-studio), À FAIRE AVANT de lancer :
  1. Activer "Google Calendar API" et "Google Drive API" (APIs & Services > Library)
  2. OAuth consent screen > ajouter les 3 scopes : gmail.modify, calendar, drive
  3. yoann@mylab-shop.com doit être test user (déjà le cas pour l'email-responder)

Usage (PowerShell, depuis le repo) :
  python scripts/hermes/google_workspace_oauth_setup.py
  # ouvre le navigateur, tu consens avec yoann@mylab-shop.com, le token est
  # écrit dans .env.vps (GOOGLE_WS_*) — JAMAIS affiché dans le terminal.

Le GMAIL_REFRESH_TOKEN existant (email-responder) n'est PAS touché.
"""
import http.server
import json
import os
import re
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
ENV_VPS = ROOT / ".env.vps"
load_dotenv(ENV_VPS)

CLIENT_ID = os.environ["GMAIL_CLIENT_ID"]
CLIENT_SECRET = os.environ["GMAIL_CLIENT_SECRET"]
SCOPES = " ".join([
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
])
PORT = int(os.environ.get("PORT", "8766"))
REDIRECT = f"http://localhost:{PORT}/callback"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
STATE = secrets.token_urlsafe(16)
RESULT = {}


def upsert_env(path: Path, updates: dict):
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = content.splitlines()
    seen = set()
    for i, line in enumerate(lines):
        for k, v in updates.items():
            if re.match(rf"^{re.escape(k)}=", line):
                lines[i] = f"{k}={v}"
                seen.add(k)
    for k, v in updates.items():
        if k not in seen:
            lines.append(f"{k}={v}")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


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
            RESULT.update(json.loads(resp.read().decode()))
        self._html(200, "<h1>OK</h1><p>Token recupere, retourne au terminal.</p>")
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
        "scope": SCOPES, "access_type": "offline", "prompt": "consent", "state": STATE,
        "login_hint": "yoann@mylab-shop.com",
    })
    url = f"{AUTH_URL}?{params}"
    print("Ouvre cette URL et connecte-toi avec yoann@mylab-shop.com :\n")
    print(f"    {url}\n")
    print("(Google affichera 'app non verifiee' -> Parametres avances -> Continuer)")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    http.server.HTTPServer(("localhost", PORT), Handler).serve_forever()

    rt = RESULT.get("refresh_token")
    if not rt:
        print(f"\nECHEC — pas de refresh_token. Reponse : {RESULT}", file=sys.stderr)
        sys.exit(1)
    upsert_env(ENV_VPS, {
        "GOOGLE_WS_CLIENT_ID": CLIENT_ID,
        "GOOGLE_WS_CLIENT_SECRET": CLIENT_SECRET,
        "GOOGLE_WS_REFRESH_TOKEN": rt,
    })
    print("\n" + "=" * 60)
    print(f"SUCCESS — GOOGLE_WS_* ecrits dans {ENV_VPS.name}")
    print("Scopes accordes :", RESULT.get("scope", "(non renvoye)"))
    print("Le refresh token n'est PAS affiche (anti-leak transcript).")
    print("=" * 60)


if __name__ == "__main__":
    main()
