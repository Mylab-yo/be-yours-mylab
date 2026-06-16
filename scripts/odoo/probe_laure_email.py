"""Check the partner LAURE COIFFURE (id 2014) email and all related notifications."""
from _client import search_read

print("=== Partner 2014 ===")
p = search_read("res.partner", [("id", "=", 2014)],
                ["id", "name", "email", "email_formatted", "is_company", "parent_id", "child_ids"])
print(p)

# Check children too (Laure Souvay might be a contact under LAURE COIFFURE)
print("\n=== Children of partner 2014 ===")
children = search_read("res.partner", [("parent_id", "=", 2014)],
                       ["id", "name", "email", "function"])
for c in children:
    print(c)

# All failed notifications recently for this partner
print("\n=== All failed mail.notification for partner 2014 ===")
notifs = search_read(
    "mail.notification",
    [("res_partner_id", "=", 2014), ("notification_status", "in", ["exception", "bounce"])],
    ["id", "mail_message_id", "notification_status", "failure_type", "failure_reason"],
    limit=20,
)
for n in notifs:
    print(f"  [{n['id']}] status={n['notification_status']} fail={n['failure_type']}")
    print(f"       msg_id={n['mail_message_id']}")
    if n.get("failure_reason"):
        print(f"       REASON: {n['failure_reason'][:400]}")

# Also check invoice 368 notifications more broadly (no status filter)
print("\n=== ALL notifications on invoice 368 ===")
inv_notifs = search_read(
    "mail.notification",
    [("mail_message_id.model", "=", "account.move"),
     ("mail_message_id.res_id", "=", 368)],
    ["id", "notification_status", "failure_type", "failure_reason", "res_partner_id"],
    limit=20,
)
for n in inv_notifs:
    print(f"  [{n['id']}] status={n['notification_status']} fail={n['failure_type']} partner={n['res_partner_id']}")
    if n.get("failure_reason"):
        print(f"       REASON: {n['failure_reason'][:400]}")
