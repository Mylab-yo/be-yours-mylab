"""Investigate the two email failures shown in user's Odoo notification panel:
- FAC/2026/00027 (account.move) - 15 mai
- S00479 (sale.order) - 15 mai
"""
from _client import search_read, execute


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# 1. Find FAC/2026/00027
section("INVOICE FAC/2026/00027")
inv = search_read(
    "account.move",
    [("name", "=", "FAC/2026/00027")],
    ["id", "name", "state", "partner_id", "invoice_user_id", "amount_total", "invoice_date"],
)
print(inv)

if inv:
    inv_id = inv[0]["id"]
    # Find mail messages linked
    msgs = search_read(
        "mail.message",
        [("model", "=", "account.move"), ("res_id", "=", inv_id)],
        ["id", "date", "subject", "message_type", "subtype_id", "email_from", "author_id"],
        limit=10,
    )
    print(f"\nMessages linked ({len(msgs)}):")
    for m in msgs:
        print(f"  [{m['id']}] {m['date']} type={m['message_type']} from={m['email_from']} subj={m['subject']!r}")

    # Find mail.mail (queue) records
    mails = search_read(
        "mail.mail",
        [("model", "=", "account.move"), ("res_id", "=", inv_id)],
        ["id", "state", "failure_reason", "failure_type", "email_to", "subject", "create_date"],
        limit=10,
    )
    print(f"\nMail.mail records ({len(mails)}):")
    for m in mails:
        print(f"  [{m['id']}] state={m['state']} fail={m['failure_type']} to={m['email_to']}")
        print(f"       subj={m['subject']!r}")
        if m.get("failure_reason"):
            print(f"       REASON: {m['failure_reason'][:300]}")

    # Find notifications (mail.notification) - this is what shows in the inbox bubbles
    notifs = search_read(
        "mail.notification",
        [("res_partner_id.user_ids", "!=", False), ("mail_message_id.model", "=", "account.move"),
         ("mail_message_id.res_id", "=", inv_id)],
        ["id", "notification_type", "notification_status", "failure_type", "failure_reason", "res_partner_id"],
        limit=10,
    )
    print(f"\nMail.notification records ({len(notifs)}):")
    for n in notifs:
        print(f"  [{n['id']}] status={n['notification_status']} fail={n['failure_type']} partner={n['res_partner_id']}")
        if n.get("failure_reason"):
            print(f"       REASON: {n['failure_reason'][:300]}")


# 2. Find S00479
section("SALE ORDER S00479")
so = search_read(
    "sale.order",
    [("name", "=", "S00479")],
    ["id", "name", "state", "partner_id", "user_id", "amount_total", "date_order"],
)
print(so)

if so:
    so_id = so[0]["id"]
    msgs = search_read(
        "mail.message",
        [("model", "=", "sale.order"), ("res_id", "=", so_id)],
        ["id", "date", "subject", "message_type", "email_from"],
        limit=10,
    )
    print(f"\nMessages linked ({len(msgs)}):")
    for m in msgs:
        print(f"  [{m['id']}] {m['date']} type={m['message_type']} from={m['email_from']} subj={m['subject']!r}")

    mails = search_read(
        "mail.mail",
        [("model", "=", "sale.order"), ("res_id", "=", so_id)],
        ["id", "state", "failure_reason", "failure_type", "email_to", "subject", "create_date"],
        limit=10,
    )
    print(f"\nMail.mail records ({len(mails)}):")
    for m in mails:
        print(f"  [{m['id']}] state={m['state']} fail={m['failure_type']} to={m['email_to']}")
        print(f"       subj={m['subject']!r}")
        if m.get("failure_reason"):
            print(f"       REASON: {m['failure_reason'][:300]}")

    notifs = search_read(
        "mail.notification",
        [("mail_message_id.model", "=", "sale.order"),
         ("mail_message_id.res_id", "=", so_id),
         ("notification_status", "in", ["exception", "bounce"])],
        ["id", "notification_type", "notification_status", "failure_type", "failure_reason", "res_partner_id"],
        limit=10,
    )
    print(f"\nFailed mail.notification records ({len(notifs)}):")
    for n in notifs:
        print(f"  [{n['id']}] status={n['notification_status']} fail={n['failure_type']} partner={n['res_partner_id']}")
        if n.get("failure_reason"):
            print(f"       REASON: {n['failure_reason'][:300]}")
