"""Odoo XML-RPC client helper for MyLab scripts."""
import os
import xmlrpc.client
from pathlib import Path
from dotenv import load_dotenv

# Load .env.local from configurateur repo (source of truth per memory)
ENV_PATH = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local")
if not ENV_PATH.exists():
    raise FileNotFoundError(f"Missing env file: {ENV_PATH}")
load_dotenv(ENV_PATH)

URL = os.environ["ODOO_URL"].strip()
DB = os.environ["ODOO_DB"].strip()
# ODOO_LOGIN = email used for Odoo web login (ODOO_USER in .env.local is a comment, not a login)
LOGIN = os.environ.get("ODOO_LOGIN", "").strip() or os.environ["ODOO_USER"].strip()
API_KEY = os.environ["ODOO_API_KEY"].strip()

_common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
UID = _common.authenticate(DB, LOGIN, API_KEY, {})
if not UID:
    raise RuntimeError(f"Odoo authentication failed (login={LOGIN!r}, db={DB!r})")

_models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")


def execute(model: str, method: str, args: list, kwargs: dict | None = None):
    """Call any Odoo model method."""
    return _models.execute_kw(DB, UID, API_KEY, model, method, args, kwargs or {})


def search_read(model: str, domain: list, fields: list, limit: int = 0):
    return execute(model, "search_read", [domain], {"fields": fields, "limit": limit})


def create(model: str, values: dict) -> int:
    return execute(model, "create", [values])


def write(model: str, ids: list, values: dict) -> bool:
    return execute(model, "write", [ids, values])


def search(model: str, domain: list, limit: int = 0) -> list:
    return execute(model, "search", [domain], {"limit": limit})


def unlink(model: str, ids: list) -> bool:
    return execute(model, "unlink", [ids])


if __name__ == "__main__":
    # Sanity check: list first 3 products
    prods = search_read("product.template", [("sale_ok", "=", True)],
                        ["id", "name"], limit=3)
    print(f"Connected as UID={UID}")
    for p in prods:
        print(f"  {p['id']}: {p['name']}")
