# -*- coding: utf-8 -*-
"""Classificateur pur bulk/retail pour le split de stock MyLab.

Une ligne est 'bulk' si qty x contenance_ml >= seuil (defaut 50 L), OU si la
commande porte le tag 'bulk-labo'. Les testeurs sont toujours 'retail'.
Contenance introuvable (hors testeur) -> 'ambiguous' (a signaler, jamais deviner).
"""
import os
import re

BULK_THRESHOLD_ML = int(os.environ.get("BULK_THRESHOLD_ML", "50000"))
BULK_TAG = "bulk-labo"

_CONT_RE = re.compile(r"(\d+)\s*ml\b")


def parse_contenance_ml(text):
    """Extrait la contenance en ml depuis un nom/SKU, sinon None."""
    if not text:
        return None
    norm = text.lower().replace("-", " ")
    m = _CONT_RE.search(norm)
    return int(m.group(1)) if m else None


def classify_line(name, sku, qty, order_tags, threshold_ml=BULK_THRESHOLD_ML):
    """Renvoie (kind, contenance_ml, reason). kind in bulk|retail|ambiguous."""
    tags = [t.lower() for t in (order_tags or [])]
    blob = f"{name or ''} {sku or ''}".lower()

    if BULK_TAG in tags:
        return ("bulk", parse_contenance_ml(blob), "tag")
    if "testeur" in blob:
        return ("retail", None, "testeur")

    cont = parse_contenance_ml(name) or parse_contenance_ml(sku)
    if cont is None:
        return ("ambiguous", None, "no-contenance")

    volume = (qty or 0) * cont
    if volume >= threshold_ml:
        return ("bulk", cont, f"volume={volume}ml>=seuil")
    return ("retail", cont, f"volume={volume}ml<seuil")
