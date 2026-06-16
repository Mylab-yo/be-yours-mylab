import json, sys, re
from datetime import datetime
from pathlib import Path

VAULT_PATH = Path(r"C:\Users\startec\Documents\MyLab")
EXPORT_DIR = VAULT_PATH / "Claude Code"
CLAUDE_DIR = Path.home() / ".claude"
QUIET = "--quiet" in sys.argv

def log(msg):
    if not QUIET:
        print(msg)

def sanitize(name):
    name = re.sub(r'[<>:"/\\|?*]', '-', name)
    return re.sub(r'-+', '-', name).strip('-')[:100]

def extract_text(conv_file):
    messages = []
    for line in open(conv_file, 'r', encoding='utf-8'):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        etype = entry.get('type', '')
        if etype not in ('user', 'assistant'):
            continue
        msg = entry.get('message', {})
        role = msg.get('role', '')
        content = msg.get('content', '')
        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get('type') == 'text':
                    parts.append(block.get('text', ''))
            text = '\n'.join(parts).strip()
        else:
            continue
        if not text:
            continue
        if text.startswith('{') and text.endswith('}'):
            continue
        if text.startswith('[') and text.endswith(']'):
            continue
        label = 'Yoann' if role == 'user' else 'Claude'
        messages.append(f'### {label}\n\n{text}\n')
    return messages

def find_conversations():
    convs = []
    for d in [CLAUDE_DIR / 'projects', CLAUDE_DIR / 'sessions']:
        if d.exists():
            convs.extend(d.rglob('*.jsonl'))
    convs.extend(CLAUDE_DIR.glob('*.jsonl'))
    return convs

def export_conv(conv_file):
    messages = extract_text(conv_file)
    if len(messages) < 2:
        return False
    stat = conv_file.stat()
    date = datetime.fromtimestamp(stat.st_mtime)
    date_str = date.strftime('%Y-%m-%d')
    first_msg = ''
    for msg in messages:
        if 'Yoann' in msg:
            first_msg = msg.split('\n\n', 1)[-1].split('\n')[0][:80]
            break
    if not first_msg:
        first_msg = conv_file.stem
    filename = sanitize(f'{date_str} - {first_msg}')
    filepath = EXPORT_DIR / f'{filename}.md'
    if filepath.exists() and stat.st_mtime <= filepath.stat().st_mtime:
        return False
    header = f'---\ndate: {date_str}\nsource: Claude Code\n---\n\n# {first_msg}\n\n'
    content = header + '\n---\n\n'.join(messages)
    filepath.write_text(content, encoding='utf-8')
    log(f'  Exported: {filepath.name}')
    return True

def main():
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    log('Scanning Claude Code conversations...')
    convs = find_conversations()
    log(f'Found {len(convs)} conversation files')
    count = sum(1 for c in convs if export_conv(c))
    log(f'Exported {count} conversations to {EXPORT_DIR}')

if __name__ == '__main__':
    main()