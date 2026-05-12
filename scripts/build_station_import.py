"""Build a Station.NET-compatible address import file from a DPD shipment export.

Reads the DPD STARTEC_U4.csv export, dedupes recipients, parses street addresses
into number/street parts, maps country codes, and writes a 26-column TSV in the
same shape as C:\\ProgramData\\Station.NET\\Adresses.txt.

Usage:
    python build_station_import.py <input.csv> <output.txt>
"""

import csv
import re
import sys
from pathlib import Path

COUNTRY_MAP = {
    "FRANCE": "F",
    "PORTUGAL": "P",
    "POLOGNE": "PL",
    "BELGIQUE": "B",
    "ESPAGNE": "E",
    "ITALIE": "I",
    "ALLEMAGNE": "D",
    "LUXEMBOURG": "L",
    "SUISSE": "CH",
    "GRECE": "GR",
    "AUTRICHE": "A",
    "PAYS-BAS": "NL",
    "ROYAUME-UNI": "GB",
}

NUM_RE = re.compile(r"^(\d+\s*[A-Za-z]?)[,\s]+(.+)$")


def parse_address(raw):
    """Split '78 RUE X' -> ('78', 'RUE X'). Strips leading commas."""
    raw = (raw or "").strip()
    if not raw:
        return "", ""
    m = NUM_RE.match(raw)
    if m:
        return m.group(1).strip().rstrip(","), m.group(2).strip()
    return "", raw


def normalize_phone(raw):
    """Strip spaces, convert +33X to 0X."""
    if not raw:
        return ""
    p = re.sub(r"\s+", "", raw.strip())
    if p.startswith("+33") and len(p) >= 11:
        p = "0" + p[3:]
    return p


def load_existing(out_path: Path) -> set:
    """Return set of (NOM, CP, VILLE, ADRESSE) keys already in the output file."""
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


def main(in_path: Path, out_path: Path) -> int:
    existing_keys = load_existing(out_path)
    print(f"Existing clients in {out_path.name}: {len(existing_keys)}")
    seen = {}
    with in_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("Nom du destinataire") or "").strip()
            cp = (row.get("Code postal") or "").strip()
            ville = (row.get("Ville") or "").strip()
            adresse = (row.get("Adresse de livraison") or "").strip()
            pays_raw = (row.get("Pays de destination") or "").strip().upper()
            tel = normalize_phone(row.get("TÃ©lÃ©phone") or row.get("Téléphone") or "")

            if not name or not cp:
                continue

            key = (name.upper(), cp, ville.upper(), adresse.upper())
            if key in existing_keys:
                continue  # already in the output file
            existing = seen.get(key)
            if existing and existing["tel"]:
                continue  # keep first with phone
            if existing and not tel:
                continue

            num, voie = parse_address(adresse)
            pays = COUNTRY_MAP.get(pays_raw, pays_raw[:2] if pays_raw else "F")

            seen[key] = {
                "raison": name.upper(),
                "commercial": name.title(),
                "pays": pays,
                "cp": cp,
                "ville": ville.upper(),
                "voie": voie,
                "num": num,
                "tel": tel,
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
    print(f"{verb} {len(seen)} new unique clients to {out_path}")
    print(f"Total clients in file: {len(existing_keys) + len(seen)}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
