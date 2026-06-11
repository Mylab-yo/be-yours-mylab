"""Tests for build_email_prompt — run: python scripts/hermes/test_build_email_prompt.py"""
from build_email_prompt import extract_kb_prompt

SAMPLE = """---
name: x
---
# Title

## Workflow
Étape 1 : utilise gmail_search_messages ...

## Identité de l'agent
Tu es Yoann.

## Base de connaissance MY.LAB
Prix shampoing 200ml : 7.00€
"""

def test_drops_workflow_keeps_identity_and_kb():
    out = extract_kb_prompt(SAMPLE)
    assert "gmail_search_messages" not in out          # workflow API-tool removed
    assert "Tu es Yoann." in out                        # identity kept
    assert "Prix shampoing 200ml : 7.00€" in out        # KB kept

def test_has_html_only_preamble():
    out = extract_kb_prompt(SAMPLE)
    assert "UNIQUEMENT" in out and "HTML" in out        # output instruction present

def test_raises_without_marker():
    try:
        extract_kb_prompt("no marker here")
        assert False, "should have raised"
    except ValueError:
        pass

if __name__ == "__main__":
    test_drops_workflow_keeps_identity_and_kb()
    test_has_html_only_preamble()
    test_raises_without_marker()
    print("OK build_email_prompt")
