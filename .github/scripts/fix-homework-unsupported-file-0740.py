from pathlib import Path
import re

ROOT = Path('.')
js_path = ROOT / 'he/workspace/lesson-completion.js'
index_path = ROOT / 'he/workspace/index.html'

js = js_path.read_text(encoding='utf-8')

# Bump loader/version regardless of the currently deployed patch level.
js = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION\s*=\s*"0\.7\.\d+";',
            'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.40";', js, count=1)
js = re.sub(r'lesson-completion-core\.js\?v=\d+',
            'lesson-completion-core.js?v=0740', js, count=1)

anchor = '  async function handleHomeworkPdfUpload(file){\n'
if anchor not in js:
    raise SystemExit('PDF handler anchor not found')

helper = r'''  function renderUnsupportedHomeworkFile(file){
    showHomeworkLessonWorkspace({keepPreview:false});

    const stage = document.querySelector(".lesson-visual-stage");
    if(!stage) return;

    const safeName = String(file?.name || "הקובץ").replace(/[<>]/g, "");

    stage.innerHTML = `
      <div class="homework-stage-shell">
        <section class="homework-upload-card" style="min-height:330px">
          <div class="homework-upload-icon" style="color:#ffb7c7;border-color:rgba(255,103,139,.48);background:linear-gradient(145deg,rgba(112,31,58,.82),rgba(63,31,104,.82))">
            <i class="fa-solid fa-file-circle-xmark"></i>
          </div>
          <h2>סוג הקובץ הזה אינו נתמך</h2>
          <p><strong style="color:#d8e7ff">${safeName}</strong><br>אפשר להעלות תמונה מסוג JPG, PNG או WEBP, או קובץ PDF.</p>
          <div class="homework-upload-actions">
            <button type="button" class="homework-upload-action primary" data-homework-camera-retry>
              <i class="fa-solid fa-camera"></i>
              <span>צלם שיעורי בית</span>
            </button>
            <button type="button" class="homework-upload-action" data-homework-file-retry>
              <i class="fa-solid fa-file-arrow-up"></i>
              <span>נסה קובץ אחר</span>
            </button>
          </div>
          <div class="homework-stage-note"><i class="fa-solid fa-circle-info"></i><span>לא התחלתי לנתח את הקובץ, לכן אפשר לנסות שוב מיד.</span></div>
        </section>
      </div>`;

    stage.querySelector("[data-homework-camera-retry]")?.addEventListener("click", () => {
      const input = document.getElementById("homeworkCameraInput");
      if(input){ input.value = ""; input.click(); }
    });

    stage.querySelector("[data-homework-file-retry]")?.addEventListener("click", () => {
      const input = document.getElementById("homeworkFileInput");
      if(input){ input.value = ""; input.click(); }
    });

    const steps = document.querySelectorAll(".homework-sidebar-step");
    steps.forEach(step => step.classList.remove("active"));
    steps[0]?.classList.add("active");
  }

  function isSupportedHomeworkImage(file){
    const type = String(file?.type || "").toLowerCase();
    const name = String(file?.name || "").toLowerCase();
    const supportedMime = new Set(["image/jpeg", "image/png", "image/webp"]);
    if(supportedMime.has(type)) return true;
    return /\.(jpe?g|png|webp)$/i.test(name);
  }

'''

if 'function renderUnsupportedHomeworkFile(file)' not in js:
    js = js.replace(anchor, helper + anchor, 1)

old = '''      if(isPdf){
        // Stop the legacy image-only handler from trying to compress a PDF.
        event.preventDefault();
        event.stopImmediatePropagation();
        handleHomeworkPdfUpload(file);
        return;
      }

      showHomeworkLessonWorkspace({keepPreview:true});
      showHomeworkPreview(file);
'''

new = '''      if(isPdf){
        // Stop the legacy image-only handler from trying to compress a PDF.
        event.preventDefault();
        event.stopImmediatePropagation();
        handleHomeworkPdfUpload(file);
        return;
      }

      if(!isSupportedHomeworkImage(file)){
        // Reject unsupported files before preview, compression or AI analysis.
        event.preventDefault();
        event.stopImmediatePropagation();
        event.target.value = "";
        renderUnsupportedHomeworkFile(file);
        return;
      }

      showHomeworkLessonWorkspace({keepPreview:true});
      showHomeworkPreview(file);
'''

if old not in js:
    raise SystemExit('Upload branch anchor not found')
js = js.replace(old, new, 1)

js_path.write_text(js, encoding='utf-8')

index = index_path.read_text(encoding='utf-8')
# Bump visible build stamp wherever the existing homework patch left it.
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.40', index)
index = re.sub(r'build\s*0\.7\.\d+', 'build 0.7.40', index)
# Ensure browser requests the newest loader.
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0740', index)
index_path.write_text(index, encoding='utf-8')

print('Applied unsupported homework file handling and bumped build to 0.7.40')
