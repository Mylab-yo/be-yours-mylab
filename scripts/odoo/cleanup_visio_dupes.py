# -*- coding: utf-8 -*-
"""Delete ALL [MY.LAB] n8n duplicate calendar.events WITHOUT notifying attendees.

The legitimate record is Cal.eu's native "Rendez-vous de 15 min" event (kept).
These "[MY.LAB] RDV Extension Gamme" events were created by the now-disabled
n8n workflow (3x per booking, wrong location). Idempotent."""
from _client import execute, search_read

DOMAIN = [("name", "ilike", "[MY.LAB] RDV Extension Gamme")]

evs = search_read("calendar.event", DOMAIN, ["id", "name", "start", "google_id"])
print(f"Found {len(evs)} Visio dup events")
synced = sum(1 for e in evs if e.get("google_id"))
print(f"  with google_id (synced to GCal): {synced}")

ids = [e["id"] for e in evs]

# Suppress ALL notifications on unlink (no cancellation mail to prospects / demo attendee)
ctx = {
    "no_mail_to_attendees": True,
    "dont_notify": True,
    "mail_notify_author": False,
    "mail_create_nolog": True,
    "tracking_disable": True,
}

if ids:
    # delete in chunks to stay safe
    CHUNK = 50
    deleted = 0
    for i in range(0, len(ids), CHUNK):
        batch = ids[i:i+CHUNK]
        execute("calendar.event", "unlink", [batch], {"context": ctx})
        deleted += len(batch)
        print(f"  unlinked {deleted}/{len(ids)}")

# verify
left = execute("calendar.event", "search_count", [DOMAIN])
print(f"Remaining Visio dup events in Odoo: {left}")
