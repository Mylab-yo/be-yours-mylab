"""Decode base64 from gdrive download and extract ZIP."""
import base64, zipfile, io, sys, os

# Read base64 from stdin
b64 = sys.stdin.read().strip()
zip_bytes = base64.b64decode(b64)

out_dir = os.path.dirname(os.path.abspath(__file__))
with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
    z.extractall(out_dir)
    print(f"Extracted {len(z.namelist())} files:")
    for name in z.namelist():
        path = os.path.join(out_dir, name)
        size = os.path.getsize(path)
        print(f"  {name} ({size} bytes)")
