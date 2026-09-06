from pathlib import Path

# Trigger: apply homework sidebar build 0.7.10.
path = Path('he/workspace/index.html')
text = path.read_text(encoding='utf-8')
original = text

old_colors = ".side-item:nth-of-type(1) i{background:linear-gradient(135deg,#7b5cff,#5d3ee7)}.side-item:nth-of-type(2) i{background:linear-gradient(135deg,#4fa9ff,#4089ee)}.side-item:nth-of-type(3) i{background:linear-gradient(135deg,#ff9e5d,#ff7a48)}.side-item:nth-of-type(4) i{background:linear-gradient(135deg,#ff7abb,#ee5aa0)}.side-item:nth-of-type(5) i{background:linear-gradient(135deg,#57c8ff,#3f9de8)}.side-item:nth-of-type(6) i{background:linear-gradient(135deg,#49cb88,#34ad70)}.side-item:nth-of-type(7) i{background:linear-gradient(135deg,#ffd153,#f0ae25)}.side-item:nth-of-type(8) i{background:linear-gradient(135deg,#9d70ff,#704be7)}.side-item:nth-of-type(9) i{background:linear-gradient(135deg,#4acbe9,#2daec9)}"
new_colors = ".side-item:nth-of-type(1) i{background:linear-gradient(135deg,#7b5cff,#5d3ee7)}.side-item:nth-of-type(2) i{background:linear-gradient(135deg,#4fa9ff,#4089ee)}.side-item:nth-of-type(3) i{background:linear-gradient(135deg,#36c7ff,#287fdd)}.side-item:nth-of-type(4) i{background:linear-gradient(135deg,#ff9e5d,#ff7a48)}.side-item:nth-of-type(5) i{background:linear-gradient(135deg,#ff7abb,#ee5aa0)}.side-item:nth-of-type(6) i{background:linear-gradient(135deg,#57c8ff,#3f9de8)}.side-item:nth-of-type(7) i{background:linear-gradient(135deg,#49cb88,#34ad70)}.side-item:nth-of-type(8) i{background:linear-gradient(135deg,#ffd153,#f0ae25)}.side-item:nth-of-type(9) i{background:linear-gradient(135deg,#9d70ff,#704be7)}.side-item:nth-of-type(10) i{background:linear-gradient(135deg,#4acbe9,#2daec9)}"

if old_colors not in text:
    raise SystemExit('Sidebar color rule not found')
text = text.replace(old_colors, new_colors, 1)

anchor = '''    <!-- הכנה למבחן -->
    <button
      class="side-item"
      onclick="window.location.href='https://iakids.app/he/exam-prep/'"
    >'''

homework = '''    <!-- עזרה בשיעורי בית -->
    <button
      class="side-item homework-side-item"
      id="homeworkSidebarBtn"
      onclick="startHomeworkCamera()"
    >
      <i class="fa-solid fa-camera"></i>

      <div class="side-text">
        <span class="side-title">
          עזרה בשיעורי בית
        </span>
      </div>
    </button>


'''

if 'id="homeworkSidebarBtn"' not in text:
    if anchor not in text:
        raise SystemExit('Exam prep anchor not found')
    text = text.replace(anchor, homework + anchor, 1)

if 'startHomeworkCamera()' not in text:
    raise SystemExit('Existing homework logic not found')

text = text.replace('IAKIDS • build 0.7.9', 'IAKIDS • build 0.7.10')
text = text.replace('build 0.7.9', 'build 0.7.10')

if text == original:
    raise SystemExit('No changes required')

path.write_text(text, encoding='utf-8')
print('Added homework sidebar button wired to startHomeworkCamera; build 0.7.10')
