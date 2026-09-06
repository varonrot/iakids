from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

# Add a resolver that can see both global lexical bindings and window fallbacks.
anchor = '''  function getHomeworkGrade(){\n'''
helper = r'''  function getHomeworkKidObject(){
    try{
      if(typeof CURRENT_KID !== "undefined" && CURRENT_KID) return CURRENT_KID;
    }catch(_error){}

    try{
      if(typeof SELECTED_KID !== "undefined" && SELECTED_KID) return SELECTED_KID;
    }catch(_error){}

    return (
      window.CURRENT_KID
      || window.SELECTED_KID
      || window.currentKid
      || window.selectedKid
      || {}
    );
  }

  function getHomeworkKidId(){
    const kid = getHomeworkKidObject();
    return String(kid?.id || kid?.kid_id || "").trim();
  }

'''
if 'function getHomeworkKidObject' not in core:
    if anchor not in core:
        raise SystemExit('getHomeworkGrade anchor not found')
    core = core.replace(anchor, helper + anchor, 1)

# Make grade use the real resolved kid object.
old = '''  function getHomeworkGrade(){
    const raw =
      window.CURRENT_KID?.grade
      ?? window.CURRENT_KID?.age
      ?? 4;
'''
new = '''  function getHomeworkGrade(){
    const kid = getHomeworkKidObject();
    const raw =
      kid?.grade
      ?? kid?.age
      ?? 4;
'''
if old not in core:
    raise SystemExit('getHomeworkGrade block not found')
core = core.replace(old, new, 1)

# Make name/gender helpers use the same resolved kid.
old = '''    const kid =
      window.CURRENT_KID
      || window.SELECTED_KID
      || window.currentKid
      || window.selectedKid
      || {};
'''
if old in core:
    core = core.replace(old, '    const kid = getHomeworkKidObject();\n', 2)

# The critical fix: do not send undefined kid_id to /homework-turn.
old = '''            kid_id: window.CURRENT_KID?.id || window.SELECTED_KID?.id,
'''
new = '''            kid_id: getHomeworkKidId(),
'''
count = core.count(old)
if count < 1:
    raise SystemExit('structured homework kid_id payload not found')
core = core.replace(old, new)

# Fail locally with a precise message if kid context is ever missing again.
needle = '''    const token = await getHomeworkAccessToken();
    if(!token){
      addMessage("assistant", "צריך להתחבר מחדש כדי להמשיך.");
      return;
    }

    addMessage("user", answer);
'''
replacement = '''    const token = await getHomeworkAccessToken();
    if(!token){
      addMessage("assistant", "צריך להתחבר מחדש כדי להמשיך.");
      return;
    }

    const kidId = getHomeworkKidId();
    if(!kidId){
      console.error("HOMEWORK TURN: kid id missing", {
        resolvedKid: getHomeworkKidObject()
      });
      addMessage("assistant", "לא הצלחתי לזהות את פרופיל הילדה. רענני את המסך ונסי שוב.");
      return;
    }

    addMessage("user", answer);
'''
if needle not in core:
    raise SystemExit('homework token/answer anchor not found')
core = core.replace(needle, replacement, 1)

# Use local kidId in payload, avoiding a second lookup during the request.
core = core.replace('            kid_id: getHomeworkKidId(),\n', '            kid_id: kidId,\n')

# Better console diagnostics for the exact backend response.
core = core.replace(
    '        throw new Error("homework turn failed");',
    '        throw new Error(`homework turn failed: ${response.status} ${errorText}`);',
    1
)

# Expose resolver for testing in browser console.
export_anchor = '''  window.getCurrentHomeworkQuestion = getCurrentHomeworkQuestion;\n'''
exports = '''  window.getHomeworkKidObject = getHomeworkKidObject;\n  window.getHomeworkKidId = getHomeworkKidId;\n'''
if exports not in core:
    if export_anchor not in core:
        raise SystemExit('structured homework export anchor not found')
    core = core.replace(export_anchor, exports + export_anchor, 1)

# Bump visible build/cache.
index = index.replace('IAKIDS • build 0.7.27', 'IAKIDS • build 0.7.28')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.27";', 'window.IAKIDS_BUILD_VERSION = "0.7.28";')
index = index.replace('/he/workspace/lesson-completion.js?v=0727', '/he/workspace/lesson-completion.js?v=0728')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.27";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.28";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0727', '/he/workspace/lesson-completion-core.js?v=0728')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')

print(f'Fixed structured homework kid context in {count} payload(s); build 0.7.28')

# trigger workflow
