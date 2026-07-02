# -*- coding: utf-8 -*-
import _client as C

ids = C.search("res.partner",[("customer_rank",">",0),("invoice_edi_format_store","in",[False])])
print(f"Clients a corriger : {len(ids)}")

# Ecriture par lots
CHUNK=50
for i in range(0,len(ids),CHUNK):
    C.write("res.partner", ids[i:i+CHUNK], {"invoice_edi_format_store":"facturx"})

# Verif : combien reste-t-il en ubl_21_fr calcule cote clients ?
rows = C.execute("res.partner","read",[ids],{"fields":["name","invoice_edi_format","invoice_edi_format_store"]})
bad = [r for r in rows if r["invoice_edi_format"]!="facturx"]
print(f"Apres correction -> encore != facturx : {len(bad)}")
for r in bad[:20]: print("   ", r["name"], r["invoice_edi_format"], r["invoice_edi_format_store"])

# Sanity : plus aucun client (rank>0) ne calcule ubl_21_fr par defaut ?
still_empty = C.search("res.partner",[("customer_rank",">",0),("invoice_edi_format_store","in",[False])])
print(f"Clients encore en store VIDE : {len(still_empty)}")
print("OK, les", len(ids), "clients sont maintenant en Factur-X (envoi email sans PDP).")
