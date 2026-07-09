"""Cat the sale_pdf_quote_builder ir_actions_report.py + sale_order.py."""
import paramiko
from pathlib import Path
from dotenv import dotenv_values

env = dotenv_values(Path(r"d:\be-yours-mylab\.env.vps"))
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(env["VPS_HOST"], port=int(env.get("VPS_PORT", 22)),
            username=env["VPS_USER"], password=env["VPS_PASS"], timeout=30)

def run(cmd):
    print(f"\n========== $ {cmd}")
    _, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    print(out)
    err = stderr.read().decode()
    if err: print(f"STDERR: {err}")

run("docker exec odoo cat /usr/lib/python3/dist-packages/odoo/addons/sale_pdf_quote_builder/models/ir_actions_report.py")
print("\n\n#### sale_order.py:")
run("docker exec odoo cat /usr/lib/python3/dist-packages/odoo/addons/sale_pdf_quote_builder/models/sale_order.py")

ssh.close()
