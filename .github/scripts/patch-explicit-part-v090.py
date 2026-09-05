from pathlib import Path

front = Path('he/workspace/index.html')
text = front.read_text(encoding='utf-8')
old = '''requestBody = {
  message: text,

  kid_id:
    CURRENT_KID.id,
'''
new = '''requestBody = {
  message: text,

  part_number:
    Number(window.CURRENT_LESSON_VISUAL_PART || 1),

  kid_id:
    CURRENT_KID.id,
'''
count = text.count(old)
if count < 1:
    raise SystemExit('frontend lesson requestBody anchor not found')
text = text.replace(old, new)
text = text.replace('IAKIDS • build 0.8.9', 'IAKIDS • build 0.9.0')
front.write_text(text, encoding='utf-8')

back = Path('backend-ai-tutor-he/main.py')
b = back.read_text(encoding='utf-8')
# Add optional request field to lesson body model next to message where the lesson request model is defined.
model_anchor = '    message: Optional[str] = None\n'
if model_anchor not in b:
    raise SystemExit('backend message field anchor not found')
b = b.replace(model_anchor, model_anchor + '    part_number: Optional[int] = None\n', 1)

old_logic = '''coach_part_number = int(
        flow_state.get("part_number") or 1
    )'''
new_logic = '''coach_part_number = int(
        body.part_number
        or flow_state.get("part_number")
        or 1
    )'''
if old_logic not in b:
    raise SystemExit('coach_part_number logic anchor not found')
b = b.replace(old_logic, new_logic, 1)
back.write_text(b, encoding='utf-8')

print(f'patched frontend request bodies: {count}; backend explicit part precedence enabled')
