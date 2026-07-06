# -*- coding: utf-8 -*-
"""Ajoute les tranches de poids manquantes (>30kg) aux zones Europe des profils de livraison.

Contexte (diagnostic 2026-07-06) : toutes les zones EUROPE (1 a 4) du profil de
livraison utilise par les produits s'arretent a 30 kg. Au-dela, le checkout ne
propose AUCUNE option de livraison -> commande impossible (constate pour
l'Allemagne, vaut aussi pour CH/AT/BE/SE/etc.). La France a des tranches bien
au-dela et n'est pas touchee.

Le script prolonge lineairement le motif existant (prix de la tranche 0-10kg
par colis de 10 kg supplementaire, ex. zone 1 : 22,50 -> 90,00 / 112,50 / ...)
jusqu'a MAX_KG.

Prerequis : un token admin avec scopes read_shipping + write_shipping dans
.env.local du configurateur (SHOPIFY_ADMIN_TOKEN=...). Aucun token actuel ne
les a — ajouter le scope a la custom app dans l'admin Shopify d'abord.

Usage :
    python fix_europe_weight_brackets.py            # dry-run (affiche le plan)
    python fix_europe_weight_brackets.py --apply    # applique
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

STORE = "mylab-shop-3.myshopify.com"
ENV = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local")
GQL = f"https://{STORE}/admin/api/2024-07/graphql.json"
APPLY = "--apply" in sys.argv
MAX_KG = 100.0
STEP_KG = 10.0
# Zones a completer : toute zone (hors France) contenant au moins un de ces pays
TARGET_COUNTRIES = {"DE", "BE", "LU", "NL", "CH", "GB", "AT", "CZ", "IT", "PL", "PT", "ES",
                    "HR", "DK", "EE", "HU", "IE", "LV", "LT", "SK", "SI", "SE",
                    "BG", "FI", "GR", "RO"}


def candidate_tokens():
    return [m.group(1) for line in ENV.read_text(encoding="utf-8", errors="ignore").splitlines()
            for m in re.finditer(r"(shpat_[A-Za-z0-9]+)", line)]


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    r = urllib.request.Request(GQL, data=body, method="POST",
        headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"})
    with urllib.request.urlopen(r) as resp:
        return json.loads(resp.read())


PROFILES_QUERY = """
{
  deliveryProfiles(first: 10) {
    nodes {
      id name default
      profileLocationGroups {
        locationGroup { id }
        locationGroupZones(first: 30) {
          nodes {
            zone { id name countries { code { countryCode restOfWorld } } }
            methodDefinitions(first: 50) {
              nodes {
                id name active
                rateProvider { __typename ... on DeliveryRateDefinition { price { amount currencyCode } } }
                methodConditions {
                  field operator
                  conditionCriteria { __typename ... on Weight { unit value } }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

UPDATE_MUTATION = """
mutation($id: ID!, $profile: DeliveryProfileInput!) {
  deliveryProfileUpdate(id: $id, profile: $profile) {
    profile { id }
    userErrors { field message }
  }
}
"""


def pick_token():
    denied = []
    for t in candidate_tokens():
        try:
            out = gql(t, "{ deliveryProfiles(first: 1) { nodes { id } } }")
        except Exception:
            continue
        if not out.get("errors"):
            return t
        denied.append(t[:12])
    print("ERREUR : aucun token avec le scope read_shipping/write_shipping.")
    print("-> Admin Shopify > Applications > custom app > Configurer les scopes Admin API")
    print("   ajouter read_shipping + write_shipping, puis relancer.")
    sys.exit(1)


def weight_bounds(md):
    """(min_kg, max_kg) d'une methodDefinition, ou None si pas basee poids."""
    lo = hi = None
    for c in md.get("methodConditions", []):
        crit = c.get("conditionCriteria") or {}
        if crit.get("__typename") != "Weight" or c.get("field") != "TOTAL_WEIGHT":
            continue
        v = float(crit["value"])
        if crit.get("unit") == "GRAMS":
            v /= 1000.0
        if c["operator"] == "GREATER_THAN_OR_EQUAL_TO":
            lo = v
        elif c["operator"] == "LESS_THAN_OR_EQUAL_TO":
            hi = v
    return (lo, hi) if lo is not None or hi is not None else None


def main():
    token = pick_token()
    data = gql(token, PROFILES_QUERY)
    if data.get("errors"):
        print("ERREUR lecture profils:", json.dumps(data["errors"], indent=1))
        sys.exit(1)

    plans = []  # (profile_id, location_group_id, zone_id, zone_name, service_name, currency, [(lo, hi, prix)])
    for prof in data["data"]["deliveryProfiles"]["nodes"]:
        for lg in prof.get("profileLocationGroups", []):
            lg_id = lg["locationGroup"]["id"]
            for z in lg.get("locationGroupZones", {}).get("nodes", []):
                zone = z["zone"]
                codes = {c["code"].get("countryCode") for c in zone.get("countries", [])}
                if not (codes & TARGET_COUNTRIES) or codes == {"FR"}:
                    continue
                mds = [md for md in z.get("methodDefinitions", {}).get("nodes", []) if md.get("active")]
                weighted = [(md, weight_bounds(md)) for md in mds]
                weighted = [(md, wb) for md, wb in weighted if wb]
                if not weighted:
                    continue
                cur_max = max(wb[1] or 0 for _, wb in weighted)
                if cur_max >= MAX_KG:
                    print(f"[OK] {prof['name']} / {zone['name']} : deja couvert jusqu'a {cur_max}kg")
                    continue
                # tranche de base = celle qui demarre a 0
                base = next(((md, wb) for md, wb in weighted if (wb[0] or 0) == 0), None)
                if not base:
                    print(f"[SKIP] {prof['name']} / {zone['name']} : pas de tranche 0-Xkg lisible")
                    continue
                base_md, base_wb = base
                rp = base_md.get("rateProvider") or {}
                if rp.get("__typename") != "DeliveryRateDefinition":
                    print(f"[SKIP] {prof['name']} / {zone['name']} : tarif calcule par transporteur")
                    continue
                step_price = float(rp["price"]["amount"])
                currency = rp["price"]["currencyCode"]
                name = base_md["name"]
                new_brackets = []
                lo = cur_max
                n = round(cur_max / STEP_KG)
                while lo < MAX_KG:
                    hi = lo + STEP_KG
                    n += 1
                    new_brackets.append((lo, hi, round(step_price * n, 2)))
                    lo = hi
                plans.append((prof["id"], lg_id, zone["id"], f"{prof['name']} / {zone['name']}",
                              name, currency, new_brackets))

    if not plans:
        print("Rien a faire.")
        return

    print(f"\n=== PLAN ({'APPLY' if APPLY else 'DRY-RUN'}) ===")
    for _, _, _, zone_label, name, currency, brackets in plans:
        print(f"\n{zone_label} — service '{name}' ({currency})")
        for lo, hi, price in brackets:
            print(f"  + {lo:.0f}-{hi:.0f}kg = {price:.2f}")

    if not APPLY:
        print("\nDry-run. Relancer avec --apply pour ecrire.")
        return

    for prof_id, lg_id, zone_id, zone_label, name, currency, brackets in plans:
        method_defs = [{
            "name": name,
            "active": True,
            "rateDefinition": {"price": {"amount": price, "currencyCode": currency}},
            "weightConditionsToCreate": [
                {"criteria": {"value": lo, "unit": "KILOGRAMS"}, "operator": "GREATER_THAN_OR_EQUAL_TO"},
                {"criteria": {"value": hi, "unit": "KILOGRAMS"}, "operator": "LESS_THAN_OR_EQUAL_TO"},
            ],
        } for lo, hi, price in brackets]
        profile_input = {
            "locationGroupsToUpdate": [{
                "id": lg_id,
                "zonesToUpdate": [{"id": zone_id, "methodDefinitionsToCreate": method_defs}],
            }]
        }
        out = gql(pick_token(), UPDATE_MUTATION, {"id": prof_id, "profile": profile_input})
        errs = (out.get("data", {}).get("deliveryProfileUpdate") or {}).get("userErrors") or out.get("errors")
        print(f"{'ERREUR ' + json.dumps(errs) if errs else 'OK'} — {zone_label}")


if __name__ == "__main__":
    main()
