"""Dump the jsCode of Register Payment (broken) and Create Invoice (works) to
locate the `input` reference at line 184 and compare the input-access preamble."""
import sys, io, json, urllib.request
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

lines = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local").read_text(
    encoding="utf-8", errors="replace").splitlines()
API_KEY = lines[39].strip()
BASE = "https://n8n.startec-paris.com/api/v1"
WF = "Xj8T5a7aO8drZk5v"

req = urllib.request.Request(f"{BASE}/workflows/{WF}",
                             headers={"X-N8N-API-KEY": API_KEY, "Accept": "application/json"})
with urllib.request.urlopen(req, timeout=60) as r:
    wf = json.load(r)

for n in wf["nodes"]:
    if n["name"] not in ("Register Payment", "Create Invoice"):
        continue
    code = n.get("parameters", {}).get("jsCode", "")
    code_lines = code.splitlines()
    print(f"\n{'='*70}\n=== {n['name']} — {len(code_lines)} lines ===")
    # show first 20 lines (preamble: how `input` is defined)
    print("--- PREAMBLE (1-20) ---")
    for i, l in enumerate(code_lines[:20], 1):
        print(f"{i:4}: {l}")
    # show around line 184 for Register Payment
    if n["name"] == "Register Payment":
        print("--- AROUND LINE 184 (178-190) ---")
        for i in range(177, min(191, len(code_lines))):
            print(f"{i+1:4}: {code_lines[i]}")
    # grep bare `input` (not $input)
    print("--- bare `input` references ---")
    import re
    for i, l in enumerate(code_lines, 1):
        if re.search(r'(?<![\w$])input\b', l):
            print(f"{i:4}: {l.strip()}")
