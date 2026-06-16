"""Test eval print_report_name on Odoo server via odoo shell.
Uses a Python file written to /tmp on the container to avoid quoting issues.
"""
import paramiko
from pathlib import Path
from dotenv import dotenv_values

env = dotenv_values(Path(r"d:\be-yours-mylab\.env.vps"))
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(env["VPS_HOST"], port=int(env.get("VPS_PORT", 22)),
            username=env["VPS_USER"], password=env["VPS_PASS"], timeout=30)

# Write the Python test script to /tmp on the container
test_py = '''
report = env["ir.actions.report"].browse(412)
print("=== report 412 ===")
print("print_report_name field:", repr(report.print_report_name))

order = env["sale.order"].browse(533)  # S00566
print("=== order 533 / S00566 ===")
print("name:", order.name, "state:", order.state, "partner:", order.partner_id.name)

from odoo.tools.safe_eval import safe_eval
result = safe_eval(report.print_report_name, {"object": order})
print("=== EVAL RESULT ===")
print(repr(result))

# Test if _get_report_from_name returns cached/stale
report2 = env["ir.actions.report"]._get_report_from_name("sale.report_saleorder")
print("=== via _get_report_from_name ===")
print("id:", report2.id, "print_report_name:", repr(report2.print_report_name))

# Test the FULL filename method
filename = report._get_report_filenames("sale.report_saleorder", [order.id])
print("=== _get_report_filenames ===")
print(repr(filename))
'''

# Send to container
sftp = ssh.open_sftp()
# Direct write to host then docker cp
with sftp.file('/tmp/test_report.py', 'w') as f:
    f.write(test_py)
sftp.close()

# Copy into container
def run(cmd):
    print(f"\n$ {cmd}")
    _, stdout, stderr = ssh.exec_command(cmd, timeout=120)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out: print(out)
    if err: print("STDERR:", err[-2000:] if len(err) > 2000 else err)

run("docker cp /tmp/test_report.py odoo:/tmp/test_report.py")
run("docker exec odoo bash -c 'cat /tmp/test_report.py | odoo shell -d OdooYJ --no-http 2>&1' | tail -40")

ssh.close()
