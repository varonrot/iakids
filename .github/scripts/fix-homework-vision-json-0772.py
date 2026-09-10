from pathlib import Path
import re

BACKEND = Path('backend-ai-tutor-he/main.py')
PROMPT = Path('backend-ai-tutor-he/prompts/iakids_homework_vision_prompt.txt')
INDEX = Path('he/workspace/index.html')

backend = BACKEND.read_text(encoding='utf-8')
prompt = PROMPT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

old_block = '''        try:\n\n            analysis = json.loads(\n                raw_response\n            )\n\n        except json.JSONDecodeError:\n\n            print(\n                "VISION INVALID JSON:",\n                raw_response\n            )\n\n            raise RuntimeError(\n                "Gemini Vision "\n                "returned invalid JSON"\n            )\n'''

new_block = '''        # Robust JSON parsing for homework vision. Models may occasionally\n        # wrap otherwise-valid JSON in markdown fences or add short text\n        # before/after the object. Do not fail the whole homework flow for\n        # those harmless formatting deviations.\n        cleaned_response = raw_response.strip()\n\n        if cleaned_response.startswith("```"):\n            cleaned_response = re.sub(\n                r"^```(?:json)?\\s*",\n                "",\n                cleaned_response,\n                flags=re.IGNORECASE\n            )\n            cleaned_response = re.sub(\n                r"\\s*```$",\n                "",\n                cleaned_response\n            ).strip()\n\n        analysis = None\n\n        try:\n            analysis = json.loads(cleaned_response)\n        except json.JSONDecodeError:\n            first_brace = cleaned_response.find("{")\n            last_brace = cleaned_response.rfind("}")\n\n            if first_brace >= 0 and last_brace > first_brace:\n                candidate = cleaned_response[first_brace:last_brace + 1]\n                try:\n                    analysis = json.loads(candidate)\n                except json.JSONDecodeError:\n                    analysis = None\n\n        if not isinstance(analysis, dict):\n            print(\n                "VISION INVALID JSON - SAFE FALLBACK:",\n                raw_response\n            )\n            analysis = {\n                "subject": "",\n                "topic": "",\n                "language": "",\n                "instructions": "",\n                "extracted_text": "",\n                "exercises": [],\n                "handwritten_answers": [],\n                "confidence": 0,\n                "needs_high_resolution": False\n            }\n'''

count = backend.count(old_block)
if count:
    backend = backend.replace(old_block, new_block)
elif 'VISION INVALID JSON - SAFE FALLBACK:' not in backend:
    raise SystemExit('homework vision JSON parse block not found')

if '\nimport re\n' not in backend[:1200]:
    backend = backend.replace('import math\n', 'import math\nimport re\n', 1)

# The homework analyzer already had JSON response_format. A previous patch
# accidentally inserted a second keyword argument before messages=[...].
# Remove only that duplicate compact form and keep the original formatted
# response_format block later in the call.
duplicate = '''            response_format={"type": "json_object"},\n\n            messages=[\n'''
if duplicate in backend:
    backend = backend.replace(duplicate, '            messages=[\n', 1)

extra = '''\n\nROBUST OUTPUT RULES:\n- Output one JSON object only. No markdown fences and no prose outside JSON.\n- If the image is not homework or has no identifiable exercise, still return the exact JSON structure. Use empty strings/arrays, confidence 0, and needs_high_resolution false instead of explaining or refusing.\n'''
if 'ROBUST OUTPUT RULES:' not in prompt:
    prompt = prompt.rstrip() + extra + '\n'

for old in ('0.7.69','0.7.70','0.7.71'):
    index = index.replace(f'IAKIDS • build {old}', 'IAKIDS • build 0.7.72')
    index = index.replace(f'window.IAKIDS_BUILD_VERSION = "{old}";', 'window.IAKIDS_BUILD_VERSION = "0.7.72";')

BACKEND.write_text(backend, encoding='utf-8')
PROMPT.write_text(prompt, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')

print(f'Homework vision JSON fix verified; removed duplicate response_format if present; build 0.7.72')
