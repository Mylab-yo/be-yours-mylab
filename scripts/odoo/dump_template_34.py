"""Dump template id=34 body to a file (avoid encoding issues in stdout)."""
from pathlib import Path
from scripts.odoo._client import search_read

t = search_read("mail.template", [("id", "=", 34)],
    ["name", "subject", "body_html"])[0]
out = Path("scripts/odoo/_template_34_dump.html")
out.write_text(
    f"<!-- name: {t['name']} -->\n"
    f"<!-- subject: {t['subject']} -->\n\n"
    f"{t['body_html']}",
    encoding="utf-8")
print(f"Wrote {out}")
