"""Create (or update) the 'Répartir en cartons' server action on stock.picking."""
from pathlib import Path
from scripts.odoo._client import execute, search, create, write

ACTION_NAME = "Répartir en cartons"
MODEL_NAME = "stock.picking"
CODE_FILE = Path("scripts/odoo/server_action_code.py")


def main():
    # Find model id
    model_ids = search("ir.model", [("model", "=", MODEL_NAME)])
    if not model_ids:
        raise RuntimeError(f"Model {MODEL_NAME} not found")
    model_id = model_ids[0]

    # Read code
    if not CODE_FILE.exists():
        raise FileNotFoundError(CODE_FILE)
    code = CODE_FILE.read_text(encoding="utf-8")

    values = {
        "name": ACTION_NAME,
        "model_id": model_id,
        "state": "code",
        "code": code,
        "binding_model_id": model_id,
        "binding_type": "action",
    }

    # Idempotent: find by name+model
    existing = search("ir.actions.server",
                      [("name", "=", ACTION_NAME), ("model_id", "=", model_id)])
    if existing:
        write("ir.actions.server", existing, values)
        print(f"Updated server action id={existing[0]}")
    else:
        new_id = create("ir.actions.server", values)
        print(f"Created server action id={new_id}")


if __name__ == "__main__":
    main()
