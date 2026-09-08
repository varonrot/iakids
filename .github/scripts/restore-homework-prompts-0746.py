from pathlib import Path
import subprocess, re

OLD='de6b3c147a4547fb96a58d09d160f755dfb03e87'
backend_path=Path('backend-ai-tutor-he/main.py')
core_path=Path('he/workspace/lesson-completion-core.js')
index_path=Path('he/workspace/index.html')


def git_show(path):
    return subprocess.check_output(['git','show',f'{OLD}:{path}'], text=True, encoding='utf-8')

old_backend=git_show(str(backend_path))
cur_backend=backend_path.read_text(encoding='utf-8')

# Restore HomeworkTurnRequest model exactly from the last known good prompt build.
def extract_class(src, name):
    m=re.search(rf'^class {re.escape(name)}\(BaseModel\):\n(?:(?:    .*|\s*)\n)+?(?=^class |^@app\.|^def )', src, re.M)
    if not m:
        raise SystemExit(f'cannot extract class {name}')
    return m.group(0)

def replace_class(cur, old, name):
    new=extract_class(old,name)
    m=re.search(rf'^class {re.escape(name)}\(BaseModel\):\n(?:(?:    .*|\s*)\n)+?(?=^class |^@app\.|^def )', cur, re.M)
    if not m:
        raise SystemExit(f'cannot find current class {name}')
    return cur[:m.start()]+new+cur[m.end():]

cur_backend=replace_class(cur_backend, old_backend, 'HomeworkTurnRequest')

# Restore the complete pedagogy/routing bundle: global prompt, 4 teaching styles,
# strategies, 5 help modes and all resolver functions.
start='HOMEWORK_GLOBAL_PEDAGOGY_PROMPT ='
end='@app.post("/api/tutor/homework-turn")'

def slice_between(src,a,b):
    i=src.find(a); j=src.find(b,i)
    if i<0 or j<0: raise SystemExit(f'cannot slice {a} -> {b}')
    return src[i:j]

old_bundle=slice_between(old_backend,start,end)
i=cur_backend.find(start); j=cur_backend.find(end,i)
if i<0 or j<0:
    raise SystemExit('current homework pedagogy bundle anchors not found')
cur_backend=cur_backend[:i]+old_bundle+cur_backend[j:]

# Restore the homework-turn endpoint itself so help_mode/style instructions are actually used.
def extract_endpoint(src, decorator):
    i=src.find(decorator)
    if i<0: raise SystemExit(f'missing endpoint {decorator}')
    m=re.search(r'^@app\.(?:get|post|put|delete)\(', src[i+len(decorator):], re.M)
    if not m:
        return src[i:]
    return src[i:i+len(decorator)+m.start()]

old_ep=extract_endpoint(old_backend,end)
i=cur_backend.find(end)
if i<0: raise SystemExit('current homework-turn endpoint missing')
m=re.search(r'^@app\.(?:get|post|put|delete)\(', cur_backend[i+len(end):], re.M)
j=len(cur_backend) if not m else i+len(end)+m.start()
cur_backend=cur_backend[:i]+old_ep+cur_backend[j:]
backend_path.write_text(cur_backend,encoding='utf-8')

# Restore the last known-good homework core that contains the same 5 mode prompts,
# mode selection payloads and pedagogical step-progress logic.
old_core=git_show(str(core_path))
core_path.write_text(old_core,encoding='utf-8')

# Bump visible build + force cache refresh for the homework loader/core without restoring
# the old MutationObserver audio implementation in lesson-completion.js.
s=index_path.read_text(encoding='utf-8')
s=re.sub(r'IAKIDS • build [0-9.]+','IAKIDS • build 0.7.46',s,count=1)
s=re.sub(r'window\.IAKIDS_BUILD_VERSION = "[0-9.]+";','window.IAKIDS_BUILD_VERSION = "0.7.46";',s,count=1)
s=re.sub(r'/he/workspace/lesson-completion\.js\?v=\d+','/he/workspace/lesson-completion.js?v=0746',s,count=1)
index_path.write_text(s,encoding='utf-8')

# Sanity checks
out=backend_path.read_text(encoding='utf-8')
for token in ['HOMEWORK_TEACHING_STYLE_PROMPTS','quantitative_math','text_comprehension','conceptual_science','language_writing','HOMEWORK_HELP_MODE_PROMPTS','understand_question','explain_topic','hint','solve_together','check_answer','ACTIVE HELP MODE']:
    if token not in out:
        raise SystemExit(f'missing restored token: {token}')
core=core_path.read_text(encoding='utf-8')
for token in ['HOMEWORK_HELP_MODE_PROMPTS','understand_question','explain_topic','hint','solve_together','check_answer']:
    if token not in core:
        raise SystemExit(f'missing core token: {token}')
print('Restored 4 teaching-style prompts + 5 homework help-mode prompts and routing; build 0.7.46')
