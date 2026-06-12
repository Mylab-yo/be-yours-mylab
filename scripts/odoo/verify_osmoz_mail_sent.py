"""Verify the corrected invoice email was logged + sent on invoice 456 chatter."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from _client import search_read, execute

msgs = search_read(
    "mail.message",
    [("model", "=", "account.move"), ("res_id", "=", 456),
     ("message_type", "in", ["email", "email_outgoing", "comment"])],
    ["id", "date", "subject", "email_from", "message_type", "subtype_id",
     "attachment_ids"],
    limit=5,
)
for m in sorted(msgs, key=lambda x: x["date"], reverse=True)[:3]:
    print(m)

# mail tracking / notification status for the latest
latest = max(msgs, key=lambda x: x["date"]) if msgs else None
if latest:
    notifs = search_read(
        "mail.notification",
        [("mail_message_id", "=", latest["id"])],
        ["res_partner_id", "notification_type", "notification_status",
         "failure_reason"],
    )
    print("\nnotifications:", notifs)
    atts = latest.get("attachment_ids") or []
    if atts:
        names = execute("ir.attachment", "read", [atts], {"fields": ["name"]})
        print("attachments:", [n["name"] for n in names])
