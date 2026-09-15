from pathlib import Path
import re

root = Path('.')
js_path = root / 'he/workspace/openai-clean-chat.js'
index_path = root / 'he/workspace/index.html'

js = js_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')

old = """    view.querySelector('input[type=file]')?.addEventListener('change',async e=>{\n      const file=e.target.files?.[0]; if(!file) return;\n      imageDataUrl=await readFile(file);\n      const card=view.querySelector('.occ-image-card');\n      card.innerHTML=`<img alt=\"דף העבודה\">`;\n      card.querySelector('img').src=imageDataUrl;\n      setStatus('התמונה מוכנה לשליחה ל-OpenAI');\n    });\n"""
new = """    view.querySelector('input[type=file]')?.addEventListener('change',async e=>{\n      const file=e.target.files?.[0]; if(!file) return;\n      imageDataUrl=await readFile(file);\n      const card=view.querySelector('.occ-image-card');\n      card.innerHTML=`<img alt=\"דף העבודה\">`;\n      card.querySelector('img').src=imageDataUrl;\n      const input=view.querySelector('textarea');\n      if(input && !String(input.value||'').trim()){\n        input.value='תסתכל על דף העבודה ותלמד אותי איך לפתור אותו שלב אחרי שלב. אל תיתן לי את התשובה מיד.';\n      }\n      setStatus('שולח את התמונה ל-OpenAI...');\n      await sendMessage();\n    });\n"""

if old not in js:
    raise SystemExit('upload handler not found')
js = js.replace(old, new, 1)

index = re.sub(r'openai-clean-chat\.js\?v=\d+', 'openai-clean-chat.js?v=07101', index)
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.101', index)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.101";', index, count=1)

js_path.write_text(js, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')
print('OpenAI clean chat auto-sends uploaded image; build 0.7.101')
