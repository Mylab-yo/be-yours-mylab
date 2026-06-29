"""Odoo XML-RPC client helper for MyLab scripts.

Portable Windows (poste Yoann) / VPS :
- Si .env.local (poste) existe, on le charge (comportement historique inchange).
- Sinon, si $ODOO_ENV_FILE pointe vers un fichier, on le charge (VPS).
- Sinon, on s'appuie sur les variables d'env deja presentes dans l'environnement
  (ex: exportees par le wrapper run.sh du cron VPS).
"""
import os
import xmlrpc.client
from pathlib import Path
from dotenv import load_dotenv

# Source of truth historique : .env.local du repo configurateur (poste Windows)
ENV_PATH = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local")
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
elif os.environ.get("ODOO_ENV_FILE") and Path(os.environ["ODOO_ENV_FILE"]).exists():
    load_dotenv(os.environ["ODOO_ENV_FILE"])
elif not os.environ.get("ODOO_URL"):
    # Ni fichier local, ni $ODOO_ENV_FILE, ni vars deja en environnement : on ne peut rien faire.
    raise FileNotFoundError(
        f"Aucune source de config Odoo : {ENV_PATH} introuvable, "
        "$ODOO_ENV_FILE non defini, et $ODOO_URL absent de l'environnement."
    )

URL = os.environ["ODOO_URL"].strip()
DB = os.environ["ODOO_DB"].strip()
# ODOO_LOGIN = email used for Odoo web login (ODOO_USER in .env.local is a comment, not a login)
LOGIN = os.environ.get("ODOO_LOGIN", "").strip() or os.environ["ODOO_USER"].strip()
API_KEY = os.environ["ODOO_API_KEY"].strip()

_common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common", allow_none=True)
UID = _common.authenticate(DB, LOGIN, API_KEY, {})
if not UID:
    raise RuntimeError(f"Odoo authentication failed (login={LOGIN!r}, db={DB!r})")

_models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object", allow_none=True)


def execute(model: str, method: str, args: list, kwargs: dict | None = None):
    """Call any Odoo model method.

    Workaround Odoo 18 : OdooMarshaller(allow_none=False) cote serveur crash
    quand la methode appelee retourne None (ex: mail.mail.send, mail.activity.unlink,
    mail.activity.action_feedback, etc.). Le travail est bien fait cote Odoo,
    seul le marshalling de la reponse foire. On catche ce Fault specifique et on
    retourne None, ce qui correspond a la valeur reelle de retour.
    """
    try:
        return _models.execute_kw(DB, UID, API_KEY, model, method, args, kwargs or {})
    except xmlrpc.client.Fault as exc:
        if "cannot marshal None" in str(exc):
            return None
        raise


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
