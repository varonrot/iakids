"""Checks the gate runs on every commit that touches main.py (tools/prompt_gate.py, performance_checks).
No server, no network: they read main.py, performance/routes.py and the last results file.

  route_coverage        every @app route in main.py has a performance test in routes.py
  blocking_async_routes no `async def` route calls the database, a model client or sleep
                        directly on the event loop (one process serves every child: a blocked
                        loop freezes all of them - 2026-09-25, openai-clean-chat, homework-coach-v2
                        and the lesson open did this on every request)
  catalog_shape         every catalog entry has a known kind and a latency budget
  results_checks        every catalog route has a result in results/latest-fake.json, it did
                        not fail with a 5xx, and its steady-state database calls are within
                        its db_max budget (pins the database-layer savings)
"""
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MAIN = ROOT / "backend-ai-tutor-he" / "main.py"
RESULTS = HERE / "results" / "latest-fake.json"

KINDS = {"health", "read", "write", "model", "media", "admin"}
# a call on the event loop that waits on the network or sleeps
BLOCKING_PREFIXES = ("sb.", "client.", "gemini_client.models", "gemini_client.files", "time.sleep", "requests.",
                     "httpx.get", "httpx.post", "urllib.", "supabase_with_retry", "storage_with_retry")
OFFLOAD = ("run_in_threadpool", "to_thread", "run_sync")


def _catalog():
    sys.path.insert(0, str(HERE))
    import importlib
    import routes
    importlib.reload(routes)
    return routes.ROUTES


def _dotted(n):
    parts = []
    while isinstance(n, (ast.Attribute, ast.Call, ast.Subscript)):
        if isinstance(n, ast.Call):
            n = n.func; continue
        if isinstance(n, ast.Subscript):
            n = n.value; continue
        parts.append(n.attr); n = n.value
    if isinstance(n, ast.Name):
        parts.append(n.id)
    return ".".join(reversed(parts))


def app_routes(main_src: str) -> list:
    """(method, path, function name, is_async) for every @app.get/post/... in main.py."""
    out = []
    for n in ast.parse(main_src).body:
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for d in n.decorator_list:
            if (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and getattr(d.func.value, "id", "") == "app"
                    and d.func.attr in ("get", "post", "put", "patch", "delete") and d.args
                    and isinstance(d.args[0], ast.Constant)):
                out.append((d.func.attr.upper(), d.args[0].value, n.name, isinstance(n, ast.AsyncFunctionDef)))
    return out


def _template_re(path: str):
    return re.compile("^" + re.sub(r"\\\{[^}]+\\\}", "[^/]+", re.escape(path)) + "$")


def route_coverage(main_src: str, catalog: dict | None = None) -> list:
    catalog = catalog if catalog is not None else _catalog()
    tested = [(spec["method"], spec["path"].split("?")[0].replace("{kid}", "X").replace("{ul}", "1").replace("{ll}", "1"))
              for spec in catalog.values()]
    fails = []
    for method, path, fn, _ in app_routes(main_src):
        rx = _template_re(path)
        if not any(m == method and rx.match(p) for m, p in tested):
            fails.append(f"performance: route {method} {path} ({fn}) has no performance test in performance/routes.py: "
                         f"nobody knows how many children it holds before it slows every other request (2026-09-25)")
    return fails


def blocking_async_routes(main_src: str) -> list:
    tree = ast.parse(main_src)
    funcs = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

    def calls_in(fn):
        return [_dotted(c.func) for c in ast.walk(fn) if isinstance(c, ast.Call)]

    # sync helpers that (transitively) wait on the network
    io = {name for name, f in funcs.items() if isinstance(f, ast.FunctionDef)
          and any(c.startswith(BLOCKING_PREFIXES) for c in calls_in(f))}
    changed = True
    while changed:
        changed = False
        for name, f in funcs.items():
            if isinstance(f, ast.FunctionDef) and name not in io and any(c in io for c in calls_in(f)):
                io.add(name); changed = True

    fails = []
    for method, path, fn_name, is_async in app_routes(main_src):
        if not is_async:
            continue                      # plain def routes run in the threadpool: blocking is fine there
        hits = []

        class V(ast.NodeVisitor):
            def visit_Lambda(self, n): pass
            def visit_FunctionDef(self, n): pass
            def visit_AsyncFunctionDef(self, n): pass

            def visit_Call(self, n):
                d = _dotted(n.func)
                if d.split(".")[-1] in OFFLOAD:
                    return
                if d.startswith(BLOCKING_PREFIXES) or d in io:
                    hits.append(f"line {n.lineno} {d}()")
                    return
                self.generic_visit(n)

        for st in funcs[fn_name].body:
            V().visit(st)
        if hits:
            fails.append(f"performance: async route {method} {path} ({fn_name}) waits on the network ON the event loop "
                         f"({', '.join(hits[:4])}): with one process, every other child's request freezes until it returns. "
                         f"Wrap it: await run_in_threadpool(lambda: ...) (2026-09-25)")
    return fails


def catalog_shape(catalog: dict | None = None) -> list:
    catalog = catalog if catalog is not None else _catalog()
    fails = []
    for name, spec in catalog.items():
        if spec.get("kind") not in KINDS:
            fails.append(f"performance: routes.py entry {name} has kind {spec.get('kind')!r}, not one of {sorted(KINDS)}")
        if not isinstance(spec.get("p95_ms"), (int, float)) or spec["p95_ms"] <= 0:
            fails.append(f"performance: routes.py entry {name} has no latency budget (p95_ms)")
        if spec.get("method") not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            fails.append(f"performance: routes.py entry {name} has no method")
    return fails


def main_sha() -> str:
    return hashlib.sha256(MAIN.read_bytes()).hexdigest()[:16]


def results_checks(catalog: dict | None = None, results_path: Path = RESULTS) -> list:
    catalog = catalog if catalog is not None else _catalog()
    if not results_path.exists():
        return [f"performance: no results yet ({results_path.relative_to(ROOT)}): run backend/.venv/bin/python performance/run.py --profile-only"]
    res = json.loads(results_path.read_text()).get("routes", {})
    fails = []
    for name, spec in catalog.items():
        r = res.get(name)
        if r is None:
            fails.append(f"performance: route {name} was never measured: run performance/run.py --profile-only --only {name}")
            continue
        if r.get("status", 0) >= 500 or r.get("status", 0) == 0:
            fails.append(f"performance: route {name} answered {r.get('status')} in the last performance run: it fails under test")
        cap = spec.get("db_max")
        if cap is not None and r.get("db_calls", 0) > cap:
            fails.append(f"performance: route {name} makes {r['db_calls']} database calls per request, budget {cap}: "
                         f"every extra call is multiplied by every child polling it (2026-09-25)")
    return fails


def stale_results_note(results_path: Path = RESULTS) -> str | None:
    if not results_path.exists():
        return None
    sha = json.loads(results_path.read_text()).get("main_sha")
    if sha and sha != main_sha():
        return "performance: main.py changed since the last performance run (results are from an older main.py); re-run performance/run.py before trusting the numbers"
    return None


def all_checks(main_src: str | None = None) -> list:
    if main_src is None:   # main.py + the route modules that register on main.app (tools/prompt_gate.py ROUTE_MODULES)
        extra = [ROOT / "backend-ai-tutor-he" / "english_tutor.py", ROOT / "backend-ai-tutor-he" / "qbank_admin.py",
                 ROOT / "backend-ai-tutor-he" / "admin_guard.py"]
        main_src = "\n\n".join(p.read_text(encoding="utf-8") for p in [MAIN] + extra if p.exists())
    try:
        ast.parse(main_src)
    except SyntaxError as e:
        return [f"performance: main.py does not parse (line {e.lineno}): the service would not start"]
    cat = _catalog()
    return route_coverage(main_src, cat) + blocking_async_routes(main_src) + catalog_shape(cat) + results_checks(cat)


if __name__ == "__main__":
    f = all_checks()
    note = stale_results_note()
    print("\n".join(f) if f else "performance checks OK")
    if note:
        print("note:", note)
    sys.exit(1 if f else 0)
