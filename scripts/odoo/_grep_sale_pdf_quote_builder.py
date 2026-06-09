"""Grep Odoo source on VPS to find where 'Devis - %s' filename comes from."""
import paramiko
from pathlib import Path
from dotenv import dotenv_values

env = dotenv_values(Path(r"d:\be-yours-mylab\.env.vps"))
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(env["VPS_HOST"], port=int(env.get("VPS_PORT", 22)),
            username=env["VPS_USER"], password=env["VPS_PASS"], timeout=30)

def run(cmd):
    print(f"\n$ {cmd}")
    _, stdout, stderr = ssh.exec_command(cmd)
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err: print(f"STDERR: {err}")

# Find Odoo source inside the running container
run("docker exec odoo find /usr/lib/python3/dist-packages/odoo/addons/sale_pdf_quote_builder -type f -name '*.py' | head -20")

# Look for filename generation
run("docker exec odoo grep -rn 'Devis' /usr/lib/python3/dist-packages/odoo/addons/sale_pdf_quote_builder/ 2>/dev/null | head -30")
run("docker exec odoo grep -rn 'Quotation' /usr/lib/python3/dist-packages/odoo/addons/sale_pdf_quote_builder/models/ 2>/dev/null | head -30")
run("docker exec odoo grep -rn 'attachment.*name\\|filename\\|file_name' /usr/lib/python3/dist-packages/odoo/addons/sale_pdf_quote_builder/models/ 2>/dev/null | head -30")

ssh.close()
