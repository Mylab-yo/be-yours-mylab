# -*- coding: utf-8 -*-
import _client as C

# CENDREE (compte société, id=1970)
before = C.execute("res.partner","read",[[1970]],
    {"fields":["name","invoice_edi_format","invoice_edi_format_store"]})[0]
print("AVANT :", before)

# Poser explicitement Factur-X sur le champ stocké
C.write("res.partner", [1970], {"invoice_edi_format_store": "facturx"})

after = C.execute("res.partner","read",[[1970]],
    {"fields":["name","invoice_edi_format","invoice_edi_format_store"]})[0]
print("APRES :", after)
print("OK -> computed =", after["invoice_edi_format"], "(doit valoir facturx)")
