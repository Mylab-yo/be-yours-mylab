"""Build a Station.NET-compatible address import file from a WordPress/WooCommerce user export.

Reads a WP users CSV (columns billing_first_name, billing_last_name, billing_company,
billing_phone, billing_address_1/2, billing_postcode, billing_city, billing_country,
fallbacks to shipping_*), maps country codes, parses street number, and writes a
26-column TSV in the same shape as C:\\ProgramData\\Station.NET\\Adresses.txt.

Append mode if output exists — dedupes against existing rows on (NOM, CP, VILLE, ADRESSE).

Usage:
    python build_station_from_wp.py <input_wp.csv> <output_station.txt>
"""

import csv
import re
import sys
from pathlib import Path

# WP billing_country (ISO 3166-1 alpha-2) → Station.NET code
COUNTRY_MAP = {
    "FR": "F", "BE": "B", "CH": "CH", "DE": "D", "ES": "E", "IT": "I",
    "LU": "L", "NL": "NL", "PT": "P", "PL": "PL", "GB": "GB", "UK": "GB",
    "GR": "GR", "AT": "A", "IE": "IRL", "DK": "DK", "SE": "S", "FI": "FIN",
    "NO": "N", "CZ": "CZ", "HU": "H", "RO": "RO", "BG": "BG", "HR": "HR",
    "SK": "SK", "SI": "SLO", "LT": "LT", "LV": "LV", "EE": "EE",
}

NUM_RE = re.compile(r"^(\d+\s*[A-Za-z]?)[,\s]+(.+)$")


def parse_address(raw):
    raw = (raw or "").strip()
    if not raw:
        return "", ""
    m = NUM_RE.match(raw)
    if m:
        return m.group(1).strip().rstrip(","), m.group(2).strip()
    return "", raw


def normalize_phone(raw):
    if not raw:
        return ""
    p = re.sub(r"[\s\.\-\(\)]+", "", raw.strip())
    if p.startswith("+33") and len(p) >= 11:
        p = "0" + p[3:]
    elif p.startswith("0033") and len(p) >= 12:
        p = "0" + p[4:]
    return p


def load_existing(out_path: Path) -> set:
    if not out_path.exists():
        return set()
    keys = set()
    with out_path.open("r", encoding="utf-8") as f:
        for line in f:
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 14 or not cols[0]:
                continue
            nom = cols[0].upper()
            cp = cols[9]
            ville = cols[10].upper()
            num = cols[13].strip()
            voie = cols[12].strip()
            addr = (f"{num} {voie}".strip() if num else voie).upper()
            keys.add((nom, cp, ville, addr))
    return keys


def pick(row, *names):
    for n in names:
        v = (row.get(n) or "").strip()
        if v:
            return v
    return ""


def main(in_path: Path, out_path: Path) -> int:
    existing_keys = load_existing(out_path)
    print(f"Existing clients in {out_path.name}: {len(existing_keys)}")

    seen = {}
    skipped_empty = 0
    skipped_country = 0
    with in_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            first = pick(row, "billing_first_name", "shipping_first_name", "first_name")
            last = pick(row, "billing_last_name", "shipping_last_name", "last_name")
            company = pick(row, "billing_company", "shipping_company")
            phone = normalize_phone(pick(row, "billing_phone", "shipping_phone"))
            addr1 = pick(row, "billing_address_1", "shipping_address_1")
            addr2 = pick(row, "billing_address_2", "shipping_address_2")
            cp = pick(row, "billing_postcode", "shipping_postcode")
            ville = pick(row, "billing_city", "shipping_city")
            country_iso = pick(row, "billing_country", "shipping_country").upper()

            full_addr = f"{addr1} {addr2}".strip() if addr2 else addr1
            person = f"{first} {last}".strip()

            # Need at least a name + a postal code + an address
            if not (person or company) or not cp or not full_addr:
                skipped_empty += 1
                continue

            pays = COUNTRY_MAP.get(country_iso)
            if not pays:
                if country_iso:
                    pays = country_iso[:3]
                else:
                    pays = "F"

            # Raison sociale: company if present, else person
            raison_src = company if company else person
            raison = raison_src.upper()
            commercial = (company if company else person).title()

            key = (raison, cp, ville.upper(), full_addr.upper())
            if key in existing_keys:
                continue
            existing = seen.get(key)
            if existing and existing["tel"]:
                continue
            if existing and not phone:
                continue

            num, voie = parse_address(full_addr)

            seen[key] = {
                "raison": raison[:35],
                "commercial": commercial[:35],
                "pays": pays,
                "cp": cp[:10],
                "ville": ville.upper()[:35],
                "voie": voie[:35],
                "num": num[:10],
                "tel": phone[:15],
            }

    mode = "a" if existing_keys else "w"
    with out_path.open(mode, encoding="utf-8", newline="") as f:
        for rec in seen.values():
            cols = [""] * 26
            cols[0] = rec["raison"]
            cols[2] = rec["commercial"]
            cols[8] = rec["pays"]
            cols[9] = rec["cp"]
            cols[10] = rec["ville"]
            cols[12] = rec["voie"]
            cols[13] = rec["num"]
            cols[15] = rec["tel"]
            f.write("\t".join(cols) + "\n")

    verb = "Appended" if existing_keys else "Wrote"
    print(f"Skipped (incomplete): {skipped_empty}")
    print(f"{verb} {len(seen)} new unique clients to {out_path}")
    print(f"Total clients in file: {len(existing_keys) + len(seen)}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
