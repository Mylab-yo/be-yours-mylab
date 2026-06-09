"""Set email on contact Laure Souvay (partner 2014) = email of parent company LAURE COIFFURE."""
from _client import search_read, write

PARTNER_ID = 2014
EMAIL = "souvay.laure@orange.fr"

before = search_read("res.partner", [("id", "=", PARTNER_ID)], ["id", "name", "email"])
print("BEFORE:", before)

write("res.partner", [PARTNER_ID], {"email": EMAIL})

after = search_read("res.partner", [("id", "=", PARTNER_ID)], ["id", "name", "email"])
print("AFTER: ", after)
