import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sync_volume_tiers import parse_tier_string, build_metafield_payloads


def test_parse_tier_string_basic():
    assert parse_tier_string("6:850,12:805,24:765") == [[6, 850], [12, 805], [24, 765]]


def test_parse_tier_string_sorts_and_trims():
    assert parse_tier_string(" 12:805 , 6:850 ") == [[6, 850], [12, 805]]


def test_build_metafield_payloads():
    product_map = {
        "bain-miraculeux": {
            "sizes": {"50": "bain-miraculeux"},
            "tiers": {"50": "6:850,12:805"},
        },
        "shampoing-nourrissant": {
            "sizes": {"200": "shampoing-nourrissant", "500": "shampoing-nourrissant-500ml"},
            "tiers": {"200": "6:700,12:665", "500": "6:1490,12:1340"},
        },
    }
    out = build_metafield_payloads(product_map)
    by_handle = {p["handle"]: p for p in out}
    assert by_handle["bain-miraculeux"]["tiers"] == [[6, 850], [12, 805]]
    assert by_handle["bain-miraculeux"]["base_price"] == 850
    assert by_handle["shampoing-nourrissant-500ml"]["base_price"] == 1490
    assert len(out) == 3


def test_build_metafield_payloads_skips_meta_entries():
    # Le vrai ml-product-map.json contient une clé "_doc" (chaîne) et "_pumps"
    # (dict sans sizes/tiers). Ni l'une ni l'autre ne doit faire planter ni produire de payload.
    product_map = {
        "_doc": "Source de vérité unique — contenances liées + paliers.",
        "_pumps": {"200": "pompe-200", "500": "pompe-500"},
        "bain-miraculeux": {
            "sizes": {"50": "bain-miraculeux"},
            "tiers": {"50": "6:850,12:805"},
        },
    }
    out = build_metafield_payloads(product_map)
    assert len(out) == 1
    assert out[0]["handle"] == "bain-miraculeux"
