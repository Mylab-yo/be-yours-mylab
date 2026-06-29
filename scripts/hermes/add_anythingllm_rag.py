"""Branche Hermes sur la base de connaissances RAG AnythingLLM (VPS).

Idempotent. Côté AnythingLLM (https://rag.mylab-shop.com, conteneur `anythingllm`) :
  - crée une clé API nommée `hermes-rag` si absente (insérée dans api_keys, jamais affichée)
  - crée le workspace `mylab-kb` si absent
Côté Hermes (`/opt/data/.env` = host `/root/.hermes/.env`) :
  - injecte ANYTHINGLLM_URL / ANYTHINGLLM_API_KEY / ANYTHINGLLM_WORKSPACE
  - re-chown hermes:hermes + chmod 600

Le SKILL.md `mylab-rag` lui-même se déploie via `deploy_skills_to_hermes.py`
(il est déjà dans la liste SKILLS). Après ce script : `docker compose restart` du
gateway (fait par le déployeur de skills) pour recharger l'env.

Run: python scripts/hermes/add_anythingllm_rag.py
"""
import os
import sys
from pathlib import Path

import paramiko
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env.vps")

# Bootstrap exécuté SUR le VPS (clé jamais rapatriée côté Windows / stdout)
REMOTE = r'''
import sqlite3, secrets, json, urllib.request, urllib.error, time, os, subprocess
DB="/root/anythingllm/storage/anythingllm.db"; BASE="http://127.0.0.1:3001"
def api(m,p,key=None,body=None,timeout=120):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(BASE+p,data=data,method=m); req.add_header("Content-Type","application/json")
    if key: req.add_header("Authorization","Bearer "+key)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r: return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e: return e.code,{"_err":e.read().decode()[:300]}
    except Exception as e: return -1,{"_err":str(e)[:200]}

con=sqlite3.connect(DB)
row=con.execute("SELECT secret FROM api_keys WHERE name='hermes-rag'").fetchone()
if row: key=row[0]; print("KEY exists")
else:
    key=secrets.token_hex(24)
    con.execute("INSERT INTO api_keys (secret,name,createdAt,lastUpdatedAt) VALUES (?,?,datetime('now'),datetime('now'))",(key,'hermes-rag'))
    con.commit(); print("KEY created")
con.close()

st,_=api("GET","/api/v1/auth",key)
if st!=200:
    subprocess.run(["docker","restart","anythingllm"],capture_output=True)
    for _ in range(25):
        time.sleep(3); s,_=api("GET","/api/v1/auth",key)
        if s==200: st=200; break
if st!=200: raise SystemExit("AUTH FAIL")
print("AUTH",st)

st,ws=api("GET","/api/v1/workspaces",key); slug=None
for w in (ws.get("workspaces") or []):
    if w.get("slug")=="mylab-kb" or w.get("name")=="MyLab KB": slug=w["slug"]
if not slug:
    st,r=api("POST","/api/v1/workspace/new",key,{"name":"MyLab KB"})
    slug=((r.get("workspace") or {}) if isinstance(r,dict) else {}).get("slug") or "mylab-kb"
    print("WS created",slug)
else: print("WS exists",slug)

ENVF="/root/.hermes/.env"
lines=open(ENVF).read().splitlines() if os.path.exists(ENVF) else []
add={"ANYTHINGLLM_URL":"https://rag.mylab-shop.com","ANYTHINGLLM_API_KEY":key,"ANYTHINGLLM_WORKSPACE":slug}
seen=set(); out=[]
for l in lines:
    k=l.split('=',1)[0] if '=' in l else None
    if k in add: out.append("%s=%s"%(k,add[k])); seen.add(k)
    else: out.append(l)
for k,v in add.items():
    if k not in seen: out.append("%s=%s"%(k,v))
open(ENVF,"w").write("\n".join(out)+"\n")
print("ENV updated, SLUG",slug)
'''


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(os.environ["VPS_HOST"], port=int(os.environ.get("VPS_PORT", "22")),
                username=os.environ["VPS_USER"], password=os.environ["VPS_PASS"], timeout=15)
    sftp = ssh.open_sftp()
    with sftp.open("/root/anythingllm/_add_rag.py", "w") as f:
        f.write(REMOTE)
    sftp.close()
    _i, o, _e = ssh.exec_command("cd /root/anythingllm && python3 _add_rag.py 2>&1; echo EXIT=$?", timeout=300)
    print(o.read().decode(errors="replace").strip())
    # re-sécurise l'env Hermes (réécrit par root) + nettoie
    ssh.exec_command("docker exec hermes-gateway chown hermes:hermes /opt/data/.env; "
                     "chmod 600 /root/.hermes/.env; rm -f /root/anythingllm/_add_rag.py")[1].read()
    print("\n→ Lance maintenant: python scripts/hermes/deploy_skills_to_hermes.py (déploie le SKILL.md + restart)")
    ssh.close()


if __name__ == "__main__":
    main()
