from pathlib import Path
import re

root = Path('.')
backend_path = root / 'backend-ai-tutor-he/main.py'
core_path = root / 'he/workspace/lesson-completion-core.js'
loader_path = root / 'he/workspace/lesson-completion.js'
index_path = root / 'he/workspace/index.html'

backend = backend_path.read_text(encoding='utf-8')
core = core_path.read_text(encoding='utf-8')
loader = loader_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')

# 1) Extend HomeworkCoachRequest with optional image_url for V2 multimodal input.
if 'image_url: Optional[str] = None' not in backend:
    m = re.search(r'class HomeworkCoachRequest\(BaseModel\):\n', backend)
    if not m:
        raise SystemExit('HomeworkCoachRequest class not found')
    insert_at = m.end()
    backend = backend[:insert_at] + '    image_url: Optional[str] = None\n' + backend[insert_at:]

# 2) Replace V2 message construction so the model sees the real worksheet image.
old = '''    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]
'''
new = '''    worksheet_content = [{"type": "text", "text": context}]
    image_url = str(req.image_url or "").strip()
    if image_url:
        worksheet_content.append({
            "type": "image_url",
            "image_url": {"url": image_url, "detail": "high"}
        })

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": worksheet_content},
    ]
'''
if old not in backend:
    raise SystemExit('V2 messages block not found')
backend = backend.replace(old, new, 1)

# 3) Frontend helper: use original image URL; convert blob URLs to data URLs.
if 'async function getHomeworkV2WorksheetImageUrl' not in core:
    marker = '  async function runHomeworkV2Coach(messageText=""){\n'
    if marker not in core:
        raise SystemExit('runHomeworkV2Coach marker not found')
    helper = '''  async function getHomeworkV2WorksheetImageUrl(analysis){
    let candidate = String(
      analysis?.file_url ||
      analysis?.source_file_url ||
      analysis?.image_url ||
      analysis?.preview_url ||
      ""
    ).trim();

    if(!candidate){
      const img = document.querySelector(
        '.homework-document-preview img, .homework-source-preview img, .homework-preview img, .lesson-homework-image, img[data-homework-source]'
      );
      candidate = String(img?.currentSrc || img?.src || '').trim();
    }

    if(!candidate) return '';
    if(candidate.startsWith('data:image/')) return candidate;
    if(/^https?:\/\//i.test(candidate)) return candidate;

    if(candidate.startsWith('blob:')){
      try{
        const response = await fetch(candidate);
        const blob = await response.blob();
        return await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result || ''));
          reader.onerror = reject;
          reader.readAsDataURL(blob);
        });
      }catch(error){
        console.warn('HOMEWORK V2 IMAGE CONVERT WARNING', error);
      }
    }
    return '';
  }

'''
    core = core.replace(marker, helper + marker, 1)

old_body = '''      body:JSON.stringify({
        kid_id:kidId,
        source_text:String(analysis?.extracted_text || ""),
        current_question:String(current?.text || ""),
        history:window.HOMEWORK_V2_HISTORY,
        message:String(messageText || "")
      })
'''
new_body = '''      body:JSON.stringify({
        kid_id:kidId,
        source_text:String(analysis?.extracted_text || ""),
        current_question:String(current?.text || ""),
        image_url:await getHomeworkV2WorksheetImageUrl(analysis),
        history:window.HOMEWORK_V2_HISTORY,
        message:String(messageText || "")
      })
'''
if old_body not in core:
    raise SystemExit('V2 request body not found')
core = core.replace(old_body, new_body, 1)

# 4) Version/cache bump.
loader = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.97";', loader, count=1)
loader = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0797', loader, count=1)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0797', index)
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.97', index)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.97";', index, count=1)

backend_path.write_text(backend, encoding='utf-8')
core_path.write_text(core, encoding='utf-8')
loader_path.write_text(loader, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')

print('Homework V2 now sends the real worksheet image to GPT-5.6 Sol; build 0.7.97')
