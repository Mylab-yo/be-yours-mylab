"""Tests helpers purs du worker — run: python scripts/hermes/test_email_responder.py"""
import email_responder as er

def test_build_search_queries():
    qs = er.build_search_queries()
    assert qs == [
        'label:URGENT is:unread -from:mailer-daemon newer_than:14d',
        'label:"Commandes et Devis mylab" is:unread -from:mailer-daemon newer_than:14d',
        'label:"Yoann MYLAB" is:unread -from:mailer-daemon newer_than:14d',
    ]

def test_thread_has_draft():
    no_draft = {"messages": [{"labelIds": ["UNREAD", "INBOX"]},
                             {"labelIds": ["SENT"]}]}
    with_draft = {"messages": [{"labelIds": ["UNREAD", "INBOX"]},
                              {"labelIds": ["DRAFT", "Label_7"]}]}
    assert not er.thread_has_draft(no_draft)
    assert er.thread_has_draft(with_draft)
    assert not er.thread_has_draft({"messages": []})

def test_should_skip_thread():
    # dernier message de nous → skip
    assert er.should_skip_thread({"from_email": "yoann@mylab-shop.com", "subject": "Devis"})
    assert er.should_skip_thread({"from_email": "Contact@MyLab-Shop.com", "subject": "x"})
    # expéditeurs automatiques → skip (par adresse)
    assert er.should_skip_thread({"from_email": "mailer-daemon@googlemail.com", "subject": "x"})
    assert er.should_skip_thread({"from_email": "root@dpd013.dpd.fr", "subject": "Suivi colis"})
    assert er.should_skip_thread({"from_email": "no-reply@shopify.com", "subject": "x"})
    # plateformes (marketing/transactionnel) → skip par domaine
    assert er.should_skip_thread({"from_email": "hello@shopify.com", "from_name": "Shopify", "subject": "Welcome"})
    assert er.should_skip_thread({"from_email": "envoi@boxtal.com", "from_name": "Boxtal", "subject": "Confirmation envoi"})
    # nom affiché "Ne pas répondre" → skip même si l'adresse ne matche pas
    assert er.should_skip_thread({"from_email": "tracking@xyz.fr", "from_name": "Boxtal - Ne pas répondre", "subject": "x"})
    # bounce par sujet → skip
    assert er.should_skip_thread({"from_email": "x@y.fr", "subject": "Delivery Status Notification (Failure)"})
    assert er.should_skip_thread({"from_email": "x@y.fr", "subject": "Undeliverable: Votre catalogue"})
    # vrai client → on répond
    assert not er.should_skip_thread({"from_email": "marie@salon.fr", "subject": "Demande de devis"})

def test_append_signature():
    assert er.append_signature("<p>Bonjour</p>", "<table>SIG</table>") == \
        "<p>Bonjour</p><br><br><table>SIG</table>"

def test_summary_empty():
    out = er.format_telegram_summary([], 0)
    assert "aucun nouveau mail" in out

def test_summary_drafted_and_error():
    results = [
        {"status": "drafted", "from_name": "Marie", "from_email": "m@x.fr",
         "subject": "Devis shampoing", "summary": "Tarifs envoyés"},
        {"status": "error", "from_email": "bad@x.fr", "error": "thread illisible"},
    ]
    out = er.format_telegram_summary(results, 0)
    assert "1 brouillon(s)" in out
    assert "Marie" in out and "Devis shampoing" in out
    assert "1 échec(s)" in out and "bad@x.fr" in out
    assert "rien n'a été envoyé" in out

def test_summary_capped():
    results = [{"status": "drafted", "from_name": "A", "from_email": "a@x.fr",
                "subject": "S", "summary": "x"}]
    out = er.format_telegram_summary(results, 3)
    assert "3 mail(s) restant" in out

def _b64url(s):
    import base64
    return base64.urlsafe_b64encode(s.encode("utf-8")).decode("ascii")

def test_parse_thread_extracts_last_sender_and_body():
    thread = {"id": "T1", "messages": [
        {"payload": {"headers": [{"name": "From", "value": "Marie <m@x.fr>"},
                                 {"name": "Subject", "value": "Devis"},
                                 {"name": "Message-ID", "value": "<a@mail>"}],
                     "mimeType": "text/plain",
                     "body": {"data": _b64url("Bonjour, vos prix ?")}}},
    ]}
    p = er.parse_thread(thread)
    assert p["from_email"] == "m@x.fr"
    assert p["from_name"] == "Marie"
    assert p["subject"] == "Devis"
    assert p["message_id"] == "<a@mail>"
    assert "vos prix" in p["conversation"]

def test_parse_thread_multipart_prefers_plain():
    thread = {"id": "T2", "messages": [
        {"payload": {"headers": [{"name": "From", "value": "p@x.fr"}],
                     "mimeType": "multipart/alternative",
                     "parts": [
                         {"mimeType": "text/plain", "body": {"data": _b64url("texte brut")}},
                         {"mimeType": "text/html", "body": {"data": _b64url("<p>html</p>")}},
                     ]}},
    ]}
    p = er.parse_thread(thread)
    assert "texte brut" in p["conversation"]

def test_build_reply_subject():
    assert er.build_reply_subject("Devis") == "Re: Devis"
    assert er.build_reply_subject("Re: Devis") == "Re: Devis"
    assert er.build_reply_subject("RE: Devis") == "RE: Devis"

def test_build_reply_mime_is_html_in_thread():
    raw = er.build_reply_mime("m@x.fr", "Devis", "<p>Bonjour</p>", "<a@mail>", "")
    import base64
    decoded = base64.urlsafe_b64decode(raw + "===").decode("utf-8", "replace")
    assert "To: m@x.fr" in decoded
    assert "Subject: Re: Devis" in decoded
    assert "In-Reply-To: <a@mail>" in decoded
    assert "References: <a@mail>" in decoded
    assert "text/html" in decoded
    assert "<p>Bonjour</p>" in decoded

def test_parse_thread_captures_references():
    thread = {"id": "T4", "messages": [
        {"payload": {"headers": [{"name": "From", "value": "a@x.fr"},
                                 {"name": "References", "value": "<r1@mail>"},
                                 {"name": "Message-ID", "value": "<m1@mail>"}],
                     "mimeType": "text/plain", "body": {"data": _b64url("x")}}},
    ]}
    p = er.parse_thread(thread)
    assert p["references"] == "<r1@mail>"

def test_parse_thread_decodes_encoded_from_name():
    from email.header import Header
    enc = Header("Marie Hélène", "utf-8").encode()
    thread = {"id": "T3", "messages": [
        {"payload": {"headers": [{"name": "From", "value": f"{enc} <mh@x.fr>"}],
                     "mimeType": "text/plain", "body": {"data": _b64url("hi")}}},
    ]}
    p = er.parse_thread(thread)
    assert p["from_name"] == "Marie Hélène"
    assert p["from_email"] == "mh@x.fr"

def test_build_reply_mime_dedups_references():
    import base64
    raw = er.build_reply_mime("m@x.fr", "Devis", "<p>x</p>", "<a@mail>", "<prev@mail> <a@mail>")
    decoded = base64.urlsafe_b64decode(raw + "===").decode("utf-8", "replace")
    refs_line = [l for l in decoded.splitlines() if l.startswith("References:")][0]
    assert refs_line.count("<a@mail>") == 1

if __name__ == "__main__":
    test_build_search_queries()
    test_should_skip_thread()
    test_thread_has_draft()
    test_append_signature()
    test_summary_empty()
    test_summary_drafted_and_error()
    test_summary_capped()
    test_parse_thread_extracts_last_sender_and_body()
    test_parse_thread_multipart_prefers_plain()
    test_build_reply_subject()
    test_build_reply_mime_is_html_in_thread()
    test_parse_thread_captures_references()
    test_parse_thread_decodes_encoded_from_name()
    test_build_reply_mime_dedups_references()
    print("OK email_responder helpers")
