# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

def strip(name):
    # meme expression que le t-out QWeb
    return name.split('] ', 1)[-1] if name and name.startswith('[') and '] ' in name else name

cases = [
    "[creme-ha-repulpe-200-ml] creme ha repulpe 200ml",
    "[shampoing-dejaunisseur-platine-1000-ml] shampoing dejaunisseur platine 1000ml",
    "[creation-du-dossier-cosmetologique] Création du dossier cosmétologique",
    "Formule Shampoing Volume 200ml",                     # deja sans ref
    "Remplissage MY.LAB",                                  # sans ref
    "DOSSIER COSMETOLOGIQUE + ETIQUETTES",                 # section
    "Acompte (réf : FAC/2026/00183 le 22/07/2026)",        # note acompte, contient ] ? non
    "Packaging MY.LAB Standard\nFlacon MY.LAB Standard (inclus dans la production)",  # multiligne sans ref
    "Frais de livraison DPD\nFrais de livraison — DPD CLASSIC",  # multiligne sans ref
    "[115x50mm X 1 référence] Etiquettes sur mesure 50ml - 115x50mm X 1 référence",  # ref avec espace interne
]
for c in cases:
    print(f"IN : {c!r}\nOUT: {strip(c)!r}\n")
