"""Patch the live n8n workflow to insert a 'Register Payment' Code node between
'Create Invoice' and 'Activity on Picking'.

Idempotent: re-running detects the node already exists and just updates its jsCode.

Reads the JS body from 02_odoo_client.js + 09_register_payment.js (concatenated),
then PUTs the modified workflow to the n8n API.
"""
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

HERE = Path(__file__).parent
N8N_URL = 'https://n8n.startec-paris.com'
WORKFLOW_ID = 'Xj8T5a7aO8drZk5v'
NEW_NODE_NAME = 'Register Payment'
ANCHOR_BEFORE = 'Create Invoice'       # insert AFTER this node
ANCHOR_AFTER = 'Activity on Picking'   # insert BEFORE this node

N8N_KEY = (
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.'
    'eyJzdWIiOiI3OWY4MjJjYy01NGQzLTQ2ZjUtODlkYi03OTU3ZTNmZjFkNDkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZWFmYjUzMmUtNDlkYS00NThlLTkyYTgtYjhlMTk3YTJlNGNiIiwiaWF0IjoxNzc2MTQ4MTMxfQ.'
    'AHitW3y2ZHSRC6JVR3nqXeMSwzj6wNMz1W5ElGPjMAc'
)


def build_js() -> str:
    odoo_client = (HERE / '02_odoo_client.js').read_text(encoding='utf-8')
    payment = (HERE / '09_register_payment.js').read_text(encoding='utf-8')
    return odoo_client + '\n\n' + payment


def api_get(path: str) -> dict:
    req = urllib.request.Request(
        f'{N8N_URL}{path}',
        headers={'X-N8N-API-KEY': N8N_KEY, 'Accept': 'application/json'},
    )
    return json.loads(urllib.request.urlopen(req).read())


def api_put(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f'{N8N_URL}{path}',
        data=json.dumps(body).encode('utf-8'),
        headers={
            'X-N8N-API-KEY': N8N_KEY,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        },
        method='PUT',
    )
    return json.loads(urllib.request.urlopen(req).read())


def main():
    print(f'Fetching workflow {WORKFLOW_ID}...')
    wf = api_get(f'/api/v1/workflows/{WORKFLOW_ID}')
    print(f'  name="{wf["name"]}" active={wf.get("active")} nodes={len(wf.get("nodes", []))}')

    nodes = wf['nodes']
    connections = wf.get('connections', {})

    by_name = {n['name']: n for n in nodes}
    if ANCHOR_BEFORE not in by_name:
        sys.exit(f'ERROR: anchor "{ANCHOR_BEFORE}" not found in workflow')
    if ANCHOR_AFTER not in by_name:
        sys.exit(f'ERROR: anchor "{ANCHOR_AFTER}" not found in workflow')

    before = by_name[ANCHOR_BEFORE]
    after = by_name[ANCHOR_AFTER]
    js_code = build_js()

    existing = by_name.get(NEW_NODE_NAME)
    if existing:
        existing['parameters'] = existing.get('parameters', {})
        existing['parameters']['jsCode'] = js_code
        existing['parameters']['mode'] = 'runOnceForAllItems'
        existing['parameters']['language'] = 'javaScript'
        print(f'  Node "{NEW_NODE_NAME}" already exists -> updating jsCode only')
    else:
        bx, by_ = before['position']
        ax, ay = after['position']
        new_pos = [(bx + ax) // 2, (by_ + ay) // 2]
        if new_pos == before['position'] or new_pos == after['position']:
            new_pos = [bx + 220, by_]
        new_node = {
            'parameters': {
                'mode': 'runOnceForAllItems',
                'language': 'javaScript',
                'jsCode': js_code,
            },
            'name': NEW_NODE_NAME,
            'type': 'n8n-nodes-base.code',
            'typeVersion': 2,
            'position': new_pos,
        }
        nodes.append(new_node)

        if ANCHOR_BEFORE in connections:
            old_main = connections[ANCHOR_BEFORE].get('main', [[]])
            new_main = []
            redirected = False
            for branch in old_main:
                kept = []
                for link in branch:
                    if link.get('node') == ANCHOR_AFTER:
                        kept.append({'node': NEW_NODE_NAME, 'type': 'main', 'index': 0})
                        redirected = True
                    else:
                        kept.append(link)
                new_main.append(kept)
            if not redirected:
                if new_main and new_main[0] is not None:
                    new_main[0].append({'node': NEW_NODE_NAME, 'type': 'main', 'index': 0})
                else:
                    new_main = [[{'node': NEW_NODE_NAME, 'type': 'main', 'index': 0}]]
            connections[ANCHOR_BEFORE]['main'] = new_main
        else:
            connections[ANCHOR_BEFORE] = {
                'main': [[{'node': NEW_NODE_NAME, 'type': 'main', 'index': 0}]]
            }

        connections[NEW_NODE_NAME] = {
            'main': [[{'node': ANCHOR_AFTER, 'type': 'main', 'index': 0}]]
        }
        print(f'  Inserted new node "{NEW_NODE_NAME}" at position {new_pos}')

    allowed_settings_keys = {
        'executionOrder',
        'saveDataErrorExecution',
        'saveDataSuccessExecution',
        'saveExecutionProgress',
        'saveManualExecutions',
        'timezone',
        'errorWorkflow',
        'callerPolicy',
        'executionTimeout',
    }
    raw_settings = wf.get('settings') or {}
    settings = {k: v for k, v in raw_settings.items() if k in allowed_settings_keys}

    put_body = {
        'name': wf['name'],
        'nodes': nodes,
        'connections': connections,
        'settings': settings,
    }
    if wf.get('staticData'):
        put_body['staticData'] = wf['staticData']

    print('PUTting updated workflow...')
    try:
        resp = api_put(f'/api/v1/workflows/{WORKFLOW_ID}', put_body)
    except urllib.error.HTTPError as e:
        print(f'HTTP {e.code}: {e.read().decode()[:500]}')
        raise

    wf2 = api_get(f'/api/v1/workflows/{WORKFLOW_ID}')
    names = [n['name'] for n in wf2['nodes']]
    print(f'Verified -- nodes: {names}')
    assert NEW_NODE_NAME in names, 'New node missing after PUT'
    print(f'DONE -- workflow has {len(names)} nodes, "{NEW_NODE_NAME}" present')


if __name__ == '__main__':
    main()
