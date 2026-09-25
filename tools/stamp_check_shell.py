#!/usr/bin/env python3
"""Stamp every בדיקות ומעקב page's check-shell.js / check-shell.css reference with the build number AND a
hash of the file's content: ?v=07N.<hash8>. nginx caches JS/CSS for 4 hours, so a shell change under the
same build left browsers on the old shell and buttons threw (2026-09-24: "עכשיו אני מנסה" did nothing).
Run after changing the shell or bumping the build; tools/prompt_gate.py fails on a stale stamp."""
import hashlib, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIAG = ROOT / "he" / "diagnostics"


def expected() -> dict:
    ws = (ROOT / "he" / "workspace" / "index.html").read_text(encoding="utf-8")
    n = re.search(r'IAKIDS_BUILD_VERSION = "0\.7\.(\d+)"', ws).group(1)
    return {name: f"07{n}.{hashlib.sha1((DIAG / name).read_bytes()).hexdigest()[:8]}"
            for name in ("check-shell.js", "check-shell.css")}


def pages():
    # the English tutor (2026-09-25) is built on the same shell look, so it is stamped with the same address
    return [DIAG / "index.html"] + sorted(DIAG.glob("*/index.html")) + [ROOT / "he" / "english-tutor" / "index.html"]


def main():
    want = expected()
    for f in pages():
        t = f.read_text(encoding="utf-8")
        new = t
        for name, v in want.items():
            new = re.sub(r"/he/diagnostics/" + re.escape(name) + r'(\?v=[\w.]+)?"', f'/he/diagnostics/{name}?v={v}"', new)
        if new != t:
            f.write_text(new, encoding="utf-8")
            print("stamped", f.relative_to(ROOT))
    print("check shell stamps:", want)


if __name__ == "__main__":
    sys.exit(main())
