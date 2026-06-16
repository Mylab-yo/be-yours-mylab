"""Restart the Odoo container on the VPS to clear ormcache and pick up new
print_report_name values.

Per memory project_vps_odoo_infra.md :
- Compose path: /root/odoo
- Service: 'web' (container 'odoo')
- restart unless-stopped
"""
import paramiko
from pathlib import Path
from dotenv import dotenv_values

env = dotenv_values(Path(r"d:\be-yours-mylab\.env.vps"))
host = env["VPS_HOST"]
port = int(env.get("VPS_PORT", 22))
user = env["VPS_USER"]
password = env["VPS_PASS"]

print(f"Connecting to {user}@{host}:{port}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port=port, username=user, password=password, timeout=30)

def run(cmd):
    print(f"\n$ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    if out: print(out)
    if err: print(f"STDERR: {err}")
    print(f"exit={code}")
    return code, out, err

# Find the Odoo container
run("docker ps --filter 'name=odoo' --format 'table {{.Names}}\\t{{.Status}}\\t{{.Image}}'")

# Restart the web service via docker compose
run("cd /root/odoo && docker compose restart web")

# Verify it's back up
run("sleep 5 && docker ps --filter 'name=odoo' --format 'table {{.Names}}\\t{{.Status}}'")

ssh.close()
print("\nDONE - try printing the quote again now")
