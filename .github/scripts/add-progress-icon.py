import base64, pathlib
DATA = pathlib.Path('/tmp/icon.b64')
# payload is stored in this script's adjacent file to keep execution simple
b64 = pathlib.Path('.github/scripts/progress-icon.b64').read_text().strip()
out = pathlib.Path('he/assets/lesson/my-progress.webp')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(base64.b64decode(b64))
assert out.stat().st_size < 70000
print(out, out.stat().st_size)
