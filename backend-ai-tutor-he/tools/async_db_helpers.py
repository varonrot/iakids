#!/usr/bin/env python3
"""Second pass after tools/async_routes.py: move the synchronous DB helpers off the event loop.

    backend/.venv/bin/python backend-ai-tutor-he/tools/async_db_helpers.py           # dry run
    backend/.venv/bin/python backend-ai-tutor-he/tools/async_db_helpers.py --apply

Why: the first pass made the routes `async def` and awaited the model, but every one
of them still calls authenticate_user(), get_child_by_id(), get_unit_lesson(), ...
directly. Each of those is a synchronous HTTPS round trip to Supabase (100-300 ms),
executed *on the event loop*, so while it runs no other request in the process
moves — not even one that is only waiting for OpenAI. Measured on 2026-09-14: a
cached lesson open spends ~1.5 s in such calls. That caps the whole web process at
a handful of requests per second regardless of CPU or thread count.

What it does, inside each function in CONVERT (the already-async routes), at the
function's own level only (nested defs and lambdas are left alone):

    <helper in DB_HELPERS>(...)   ->   (await run_in_threadpool(lambda: <helper>(...)))

unless the call is already under an `await` or inside a lambda. Only the outermost
call of a nested chain is wrapped. libcst keeps every comment and line.
"""
import os
import re
import sys
import libcst as cst

APPLY = '--apply' in sys.argv
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(HERE, 'main.py')

CONVERT = {
    'tutor_chat', 'tutor_tts', 'homework_turn', 'homework_simple_test', 'homework_analyze',
    'curriculum_builder_chat', 'run_learning_coach', 'structured_lesson',
    'get_or_generate_unit_lesson', 'regenerate_unit_lesson_transition',
    'regenerate_lesson_transition_only', 'get_or_generate_unit_lesson_hero_image',
    'homework_coach',
}


def db_helpers(src: str) -> set:
    """Module-level sync `def`s whose body touches Supabase (sb. / supabase_with_retry)."""
    lines = src.split('\n')
    out = set()
    for i, l in enumerate(lines):
        m = re.match(r'def (\w+)\(', l)
        if not m:
            continue
        j = i + 1
        while j < len(lines) and not re.match(r'(async )?def |@app\.', lines[j]):
            j += 1
        if re.search(r'\bsb\.|supabase_with_retry\(', '\n'.join(lines[i:j])):
            out.add(m.group(1))
    return out


class Pass2(cst.CSTTransformer):
    def __init__(self, helpers):
        self.helpers = helpers
        self.stack = []
        self.lambda_depth = 0
        self.await_depth = 0
        self.wrap_depth = 0
        self.outer = set()
        self.changes = {}

    def _active(self):
        return len(self.stack) == 1 and self.stack[0] in CONVERT and self.lambda_depth == 0 and self.await_depth == 0

    def visit_FunctionDef(self, node): self.stack.append(node.name.value)
    def leave_FunctionDef(self, o, u): self.stack.pop(); return u
    def visit_Lambda(self, node): self.lambda_depth += 1
    def leave_Lambda(self, o, u): self.lambda_depth -= 1; return u
    def visit_Await(self, node): self.await_depth += 1
    def leave_Await(self, o, u): self.await_depth -= 1; return u

    def _is_helper(self, call):
        return isinstance(call.func, cst.Name) and call.func.value in self.helpers

    def visit_Call(self, node):
        if self._active() and self._is_helper(node):
            self.wrap_depth += 1
            if self.wrap_depth == 1:
                self.outer.add(id(node))
        return True

    def leave_Call(self, original, updated):
        if not (self._active() and self._is_helper(original)):
            return updated
        outer = id(original) in self.outer
        self.wrap_depth -= 1
        if not outer:
            return updated
        fn = self.stack[0]
        self.changes[fn] = self.changes.get(fn, 0) + 1
        wrapped = cst.Call(func=cst.Name('run_in_threadpool'),
                           args=[cst.Arg(cst.Lambda(params=cst.Parameters(), body=updated))])
        return cst.Await(expression=wrapped, lpar=[cst.LeftParen()], rpar=[cst.RightParen()])


def main():
    src = open(MAIN, encoding='utf-8').read()
    helpers = db_helpers(src) - {'supabase_with_retry'}   # bare sb chains were handled by pass 1
    t = Pass2(helpers)
    out = cst.parse_module(src).visit(t).code
    print(f'{len(helpers)} DB helpers known; wrapped calls per route:')
    for k, v in sorted(t.changes.items()):
        print(f'  {k:42} {v:3}')
    print('  total', sum(t.changes.values()))
    if APPLY:
        open(MAIN, 'w', encoding='utf-8').write(out); print('written')
    else:
        open('/tmp/main.pass2.py', 'w', encoding='utf-8').write(out); print('dry run -> /tmp/main.pass2.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
