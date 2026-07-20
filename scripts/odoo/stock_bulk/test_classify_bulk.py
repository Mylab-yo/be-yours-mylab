# -*- coding: utf-8 -*-
"""Test standalone (sans pytest) : `python test_classify_bulk.py` -> 'OK' ou AssertionError."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from classify_bulk import parse_contenance_ml, classify_line

# --- parse_contenance_ml ---
assert parse_contenance_ml("shampoing nourrissant 200ml") == 200
assert parse_contenance_ml("shampoing-nourrissant-1000-ml") == 1000
assert parse_contenance_ml("shampoing-hydratant-200ml") == 200
assert parse_contenance_ml("shampoing nourrissant 5000ml") == 5000
assert parse_contenance_ml("shampoing-nourrissant-125ml") == 125
assert parse_contenance_ml("shampoing-nourrissant-testeur") is None
assert parse_contenance_ml("coffret sans contenance") is None

# --- classify_line ---
assert classify_line("shampoing nourrissant 200ml", "shampoing-nourrissant-200-ml", 250, [])[0] == "bulk"
assert classify_line("shampoing nourrissant 200ml", "shampoing-nourrissant-200-ml", 200, [])[0] == "retail"
assert classify_line("shampoing nourrissant 500ml", "shampoing-nourrissant-500-ml", 100, [])[0] == "bulk"
assert classify_line("shampoing nourrissant testeur", "shampoing-nourrissant-testeur", 5, [])[0] == "retail"
assert classify_line("shampoing nourrissant 200ml", "shampoing-nourrissant-200-ml", 6, ["bulk-labo"])[0] == "bulk"
assert classify_line("produit mystere", "produit-mystere", 300, [])[0] == "ambiguous"

print("OK")
