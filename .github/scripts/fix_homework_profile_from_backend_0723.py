from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')
BACKEND = Path('backend-ai-tutor-he/main.py')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')
backend = BACKEND.read_text(encoding='utf-8')

# -----------------------------------------------------
# 1) Frontend: make analyzer-returned child profile authoritative.
# -----------------------------------------------------
old = '''  function getHomeworkKidName(){
    const kid =
      window.CURRENT_KID
      || window.SELECTED_KID
      || window.currentKid
      || window.selectedKid
      || {};

    const candidates = [
      kid?.child_name,
'''
new = '''  function getHomeworkKidName(analysis=null){
    const sourceAnalysis =
      analysis
      || activeHomeworkAnalysis
      || window.CURRENT_HOMEWORK_ANALYSIS
      || {};

    const kid =
      window.CURRENT_KID
      || window.SELECTED_KID
      || window.currentKid
      || window.selectedKid
      || {};

    const candidates = [
      sourceAnalysis?.child_name,
      sourceAnalysis?.kid_name,
      sourceAnalysis?.profile?.child_name,
      kid?.child_name,
'''
if old not in core:
    raise SystemExit('getHomeworkKidName anchor not found')
core = core.replace(old, new, 1)

old = '''  function getHomeworkKidGender(){
    const kid =
      window.CURRENT_KID
      || window.SELECTED_KID
      || window.currentKid
      || window.selectedKid
      || {};

    const raw = String(
      kid?.gender
      || kid?.sex
      || window.CURRENT_KID_GENDER
      || ""
    ).trim().toLowerCase();
'''
new = '''  function getHomeworkKidGender(analysis=null){
    const sourceAnalysis =
      analysis
      || activeHomeworkAnalysis
      || window.CURRENT_HOMEWORK_ANALYSIS
      || {};

    const kid =
      window.CURRENT_KID
      || window.SELECTED_KID
      || window.currentKid
      || window.selectedKid
      || {};

    const raw = String(
      sourceAnalysis?.gender
      || sourceAnalysis?.child_gender
      || sourceAnalysis?.profile?.gender
      || kid?.gender
      || kid?.sex
      || window.CURRENT_KID_GENDER
      || ""
    ).trim().toLowerCase();
'''
if old not in core:
    raise SystemExit('getHomeworkKidGender anchor not found')
core = core.replace(old, new, 1)

old = '''  function getHomeworkGenderLanguage(){
    const female = getHomeworkKidGender() === "female";
    return {
      gender: female ? "נקבה" : (getHomeworkKidGender() === "male" ? "זכר" : "לא ידוע"),
'''
new = '''  function getHomeworkGenderLanguage(analysis=null){
    const resolvedGender = getHomeworkKidGender(analysis);
    const female = resolvedGender === "female";
    return {
      gender: female ? "נקבה" : (resolvedGender === "male" ? "זכר" : "לא ידוע"),
'''
if old not in core:
    raise SystemExit('getHomeworkGenderLanguage anchor not found')
core = core.replace(old, new, 1)

core = core.replace('    const kidName = getHomeworkKidName();\n    const language = getHomeworkGenderLanguage();',
                    '    const kidName = getHomeworkKidName(analysis);\n    const language = getHomeworkGenderLanguage(analysis);', 1)
core = core.replace('    const kidName = getHomeworkKidName() || "לא ידוע";\n    const language = getHomeworkGenderLanguage();',
                    '    const kidName = getHomeworkKidName(analysis) || "לא ידוע";\n    const language = getHomeworkGenderLanguage(analysis);', 1)
core = core.replace('    const kidName = getHomeworkKidName() || "לא ידוע";\n    const language = getHomeworkGenderLanguage();',
                    '    const kidName = getHomeworkKidName(analysis) || "לא ידוע";\n    const language = getHomeworkGenderLanguage(analysis);', 1)

# Persist authoritative values returned by analyzer for the entire homework flow.
old = '''  async function smartHomeworkAnalysisIntro(analysis){
    activeHomeworkAnalysis = analysis || null;
    window.CURRENT_HOMEWORK_ANALYSIS = analysis || null;

    setHomeworkSidebarStep(2);
'''
new = '''  async function smartHomeworkAnalysisIntro(analysis){
    activeHomeworkAnalysis = analysis || null;
    window.CURRENT_HOMEWORK_ANALYSIS = analysis || null;

    if(analysis?.child_name){
      window.CURRENT_HOMEWORK_CHILD_NAME = String(analysis.child_name).trim();
    }
    if(analysis?.gender || analysis?.child_gender){
      window.CURRENT_HOMEWORK_CHILD_GENDER = String(
        analysis.gender || analysis.child_gender
      ).trim().toLowerCase();
    }

    setHomeworkSidebarStep(2);
'''
if old not in core:
    raise SystemExit('smartHomeworkAnalysisIntro anchor not found')
core = core.replace(old, new, 1)

# Include persisted values as final fallback.
core = core.replace('      window.CURRENT_KID_NAME,\n', '      window.CURRENT_HOMEWORK_CHILD_NAME,\n      window.CURRENT_KID_NAME,\n', 1)
core = core.replace('      || window.CURRENT_KID_GENDER\n', '      || window.CURRENT_HOMEWORK_CHILD_GENDER\n      || window.CURRENT_KID_GENDER\n', 1)

# -----------------------------------------------------
# 2) Backend: return child_name + gender from the DB profile in homework-analyze.
#    The endpoint already loads child through get_child_by_id; add fields to response.
# -----------------------------------------------------
anchor = '''            "vision_status":
                vision_status,

            "needs_high_resolution":
'''
replacement = '''            "vision_status":
                vision_status,

            # Authoritative profile data for personalized homework UI/TTS.
            # Never infer these from the child's name in the frontend.
            "child_name":
                str(child.get("child_name") or "").strip(),

            "gender":
                str(child.get("gender") or "unknown").strip().lower(),

            "needs_high_resolution":
'''
count = backend.count(anchor)
if count < 1:
    raise SystemExit('homework analyze response anchor not found')
backend = backend.replace(anchor, replacement)

# -----------------------------------------------------
# 3) Bump visible frontend/cache version.
# -----------------------------------------------------
index = index.replace('IAKIDS • build 0.7.22', 'IAKIDS • build 0.7.23')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.22";', 'window.IAKIDS_BUILD_VERSION = "0.7.23";')
index = index.replace('/he/workspace/lesson-completion.js?v=0722', '/he/workspace/lesson-completion.js?v=0723')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.22";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.23";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0722', '/he/workspace/lesson-completion-core.js?v=0723')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
BACKEND.write_text(backend, encoding='utf-8')

print(f'Homework analyzer now returns authoritative child profile; patched {count} response block(s); build 0.7.23')
