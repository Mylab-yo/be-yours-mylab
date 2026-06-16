"""Extrait le system prompt de rédaction depuis skills/mylab-email-responder/SKILL.md.

Source de vérité unique : on prend tout depuis '## Identité de l'agent' jusqu'à la fin
(identité + KB + règles + exemples), en excluant la section '## Workflow' qui décrit
des outils Gmail non pertinents pour un appel API direct.
"""

MARKER = "## Identité de l'agent"

PREAMBLE = (
    "Tu rédiges le corps HTML d'une réponse à un email professionnel reçu par MY.LAB. "
    "Réponds UNIQUEMENT avec le HTML du corps du message : pas de signature, pas de balise "
    "<html> ni <body>, pas de Markdown. Respecte scrupuleusement la base de connaissance, "
    "le ton et les règles ci-dessous.\n\n"
)


def extract_kb_prompt(skill_md_text):
    idx = skill_md_text.find(MARKER)
    if idx == -1:
        raise ValueError(f"Marqueur '{MARKER}' introuvable dans SKILL.md")
    return PREAMBLE + skill_md_text[idx:]
