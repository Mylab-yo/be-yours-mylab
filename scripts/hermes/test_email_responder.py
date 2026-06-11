"""Tests helpers purs du worker — run: python scripts/hermes/test_email_responder.py"""
import email_responder as er

def test_build_search_queries():
    qs = er.build_search_queries()
    assert qs == [
        'label:URGENT is:unread -label:Hermes-Drafted',
        'label:"Commandes & Devis" is:unread -label:Hermes-Drafted',
    ]

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

if __name__ == "__main__":
    test_build_search_queries()
    test_append_signature()
    test_summary_empty()
    test_summary_drafted_and_error()
    test_summary_capped()
    print("OK email_responder helpers")
