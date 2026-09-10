#!/usr/bin/env python3
"""Turn the tutor's request-path routes into `async def` without rewriting them by hand.

    backend/.venv/bin/python backend-ai-tutor-he/tools/async_routes.py           # dry run
    backend/.venv/bin/python backend-ai-tutor-he/tools/async_routes.py --apply

Why: every route in main.py is a plain `def`, so FastAPI runs it in the worker
threadpool and each request keeps a thread for the whole model call — seconds. The
pool is the service's ceiling. A route that *awaits* the model gives the thread back
while the model thinks, and the ceiling becomes the model provider's rate limit.

What it does, inside each function named in CONVERT and only there (nested defs and
lambdas are left alone — a nested `operation()` handed to supabase_with_retry must
stay synchronous):

    def f(...)                                      -> async def f(...)
    client.chat.completions.create(...)             -> await aclient.chat.completions.create(...)
    client.beta.chat.completions.parse(...)         -> await aclient.beta.chat.completions.parse(...)
    gemini_client.models.generate_content(...)      -> await gemini_client.aio.models.generate_content(...)
    sb....execute()  /  sb.storage....upload(...)   -> (await run_in_threadpool(lambda: sb....execute()))
    supabase_with_retry(...)                        -> (await run_in_threadpool(lambda: supabase_with_retry(...)))
    gemini_client.<anything else>(...)              -> (await run_in_threadpool(lambda: ...))
    <a function in HEAVY>(...)                      -> (await run_in_threadpool(lambda: ...))
    <a function in CONVERT>(...)                    -> await <call>
    time.sleep(x)                                   -> await asyncio.sleep(x)

Only the outermost call of a chain is wrapped, so `sb.table().select().execute()`
becomes one threadpool hop, not three. The database calls stay synchronous code
run off the loop — the win is that the *model* wait no longer holds a thread; the
DB calls hold one for tens of milliseconds, which is what a threadpool is for.

The background pipeline (audio, visuals, hero images, intro videos) is deliberately
not converted: it already runs off the request through BackgroundTasks and its own
ThreadPoolExecutors, and executor.submit() cannot run a coroutine.

libcst preserves every comment and every line of formatting outside the edits.
"""
import re, sys, os
import libcst as cst
import libcst.matchers as m

APPLY = '--apply' in sys.argv
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(HERE, 'main.py')

# Routes and helpers that wait on a model *during a request*.
CONVERT = {
    'tutor_chat', 'tutor_tts', 'homework_turn', 'homework_simple_test', 'homework_analyze',
    'curriculum_builder_chat', 'run_learning_coach', 'structured_lesson',
    'get_or_generate_unit_lesson', 'regenerate_unit_lesson_transition',
    'regenerate_lesson_transition_only', 'get_or_generate_unit_lesson_hero_image',
}
# The generation pipeline: stays synchronous, is called through the threadpool.
HEAVY = {
    'generate_all_lesson_visuals_background', 'generate_and_store_lesson_audio',
    'generate_and_store_lesson_hero_image', 'generate_and_store_lesson_visual_image',
    'generate_first_lesson_visual_background', 'generate_kid_lesson_intro_videos_background',
    'generate_lesson_hero_image_bytes', 'generate_lesson_visual_image_bytes',
    'generate_single_kid_lesson_intro_video', 'generate_tts_wav_bytes',
    'generate_unit_lesson_audio', 'generate_unit_lesson_audio_background',
}
THREAD_ROOTS = {'sb', 'supabase_with_retry'} | HEAVY


def root_name(node):
    """The leftmost Name of a call chain: sb.table(..).select(..).execute() -> 'sb'."""
    while True:
        if isinstance(node, cst.Call): node = node.func
        elif isinstance(node, cst.Attribute): node = node.value
        elif isinstance(node, cst.Subscript): node = node.value
        elif isinstance(node, cst.Name): return node.value
        else: return None


def dotted(node):
    """'client.beta.chat.completions.parse' for the func of a Call, or None."""
    parts = []
    while isinstance(node, cst.Attribute):
        parts.append(node.attr.value); node = node.value
    if isinstance(node, cst.Name):
        parts.append(node.value); return '.'.join(reversed(parts))
    return None


class Convert(cst.CSTTransformer):
    def __init__(self):
        self.stack = []          # function names, outermost first
        self.wrap_depth = 0      # >0 while inside a call we are already wrapping
        self.lambda_depth = 0
        self.outer = set()       # id() of the calls that start a threadpool hop
        self.changes = {}

    def _active(self):
        # only the body of a CONVERT function itself: not nested defs, not lambdas
        return len(self.stack) == 1 and self.stack[0] in CONVERT and self.lambda_depth == 0

    def visit_FunctionDef(self, node):
        self.stack.append(node.name.value)
    def leave_FunctionDef(self, original, updated):
        name = self.stack.pop()
        if not self.stack and name in CONVERT and updated.asynchronous is None:
            self.changes[name] = self.changes.get(name, 0)
            return updated.with_changes(asynchronous=cst.Asynchronous())
        return updated

    def visit_Lambda(self, node): self.lambda_depth += 1
    def leave_Lambda(self, o, u): self.lambda_depth -= 1; return u

    def _kind(self, call):
        f = dotted(call.func) or ''
        if f in ('client.chat.completions.create', 'client.beta.chat.completions.parse',
                 'client.responses.create', 'client.images.generate'):
            return 'openai'
        if f == 'gemini_client.models.generate_content':
            return 'gemini'
        if f == 'time.sleep':
            return 'sleep'
        r = root_name(call)
        if r in THREAD_ROOTS or (r == 'gemini_client'):
            return 'thread'
        if isinstance(call.func, cst.Name) and call.func.value in CONVERT:
            return 'await'
        return None

    def visit_Call(self, node):
        if self._active() and self._kind(node) == 'thread':
            self.wrap_depth += 1
            if self.wrap_depth == 1:
                self.outer.add(id(node))
        return True

    def leave_Call(self, original, updated):
        if not self._active():
            return updated
        kind = self._kind(original)
        if kind is None:
            return updated
        fn = self.stack[0]
        if kind == 'thread':
            outer = id(original) in self.outer
            self.wrap_depth -= 1
            if not outer:
                return updated            # inner sb call: stays inside the outer lambda
            self.changes[fn] = self.changes.get(fn, 0) + 1
            wrapped = cst.Call(func=cst.Name('run_in_threadpool'),
                               args=[cst.Arg(cst.Lambda(params=cst.Parameters(), body=updated))])
            return cst.Await(expression=wrapped, lpar=[cst.LeftParen()], rpar=[cst.RightParen()])
        if self.wrap_depth:                # a model call inside an sb chain? never, but be safe
            return updated
        self.changes[fn] = self.changes.get(fn, 0) + 1
        if kind == 'openai':
            new_func = cst.parse_expression('a' + dotted(original.func))
            return cst.Await(expression=updated.with_changes(func=new_func),
                             lpar=[cst.LeftParen()], rpar=[cst.RightParen()])
        if kind == 'gemini':
            new_func = cst.parse_expression('gemini_client.aio.models.generate_content')
            return cst.Await(expression=updated.with_changes(func=new_func),
                             lpar=[cst.LeftParen()], rpar=[cst.RightParen()])
        if kind == 'sleep':
            return cst.Await(expression=updated.with_changes(func=cst.parse_expression('asyncio.sleep')))
        if kind == 'await':
            return cst.Await(expression=updated, lpar=[cst.LeftParen()], rpar=[cst.RightParen()])
        return updated


HEADER_IMPORTS = """import asyncio
from starlette.concurrency import run_in_threadpool
from openai import AsyncOpenAI
"""
ACLIENT = """
# The async twin of `client`, for the routes that await the model instead of
# holding a worker thread through the call (tools/async_routes.py).
aclient = AsyncOpenAI(
    api_key=OPENAI_API_KEY
)
"""


def main():
    src = open(MAIN, encoding='utf-8').read()
    if 'aclient = AsyncOpenAI' in src:
        print('main.py already converted'); return 0
    mod = cst.parse_module(src)
    t = Convert()
    out = mod.visit(t).code

    # imports: after `from openai import OpenAI`
    out = out.replace('from openai import OpenAI\n', 'from openai import OpenAI\n' + HEADER_IMPORTS, 1)
    # the async client: after the sync one
    anchor = re.search(r'client = OpenAI\(\n\s*api_key=OPENAI_API_KEY\n\)\n', out)
    assert anchor, 'could not find the OpenAI client construction'
    out = out[:anchor.end()] + ACLIENT + out[anchor.end():]

    missing = sorted(CONVERT - set(t.changes))
    print(f'{len(t.changes)} functions converted:')
    for k, v in sorted(t.changes.items()):
        print(f'  {k:42} {v:3} awaits')
    if missing:
        print('  NOT FOUND:', missing)
    if APPLY:
        open(MAIN, 'w', encoding='utf-8').write(out)
        print('written')
    else:
        open('/tmp/main.async.py', 'w', encoding='utf-8').write(out)
        print('dry run -> /tmp/main.async.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
