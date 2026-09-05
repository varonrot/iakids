from pathlib import Path
p=Path('he/workspace/index.html'); s=p.read_text(encoding='utf-8')
a='''requestBody = {\n  message: text,\n\n  kid_id:\n    CURRENT_KID.id,\n'''
z='''requestBody = {\n  message: text,\n\n  part_number:\n    Number(window.CURRENT_LESSON_VISUAL_PART || 1),\n\n  kid_id:\n    CURRENT_KID.id,\n'''
if a not in s: raise SystemExit('frontend anchor missing')
s=s.replace(a,z).replace('IAKIDS • build 0.8.9','IAKIDS • build 0.9.0'); p.write_text(s,encoding='utf-8')
p=Path('backend-ai-tutor-he/main.py'); s=p.read_text(encoding='utf-8')
a='    message: str | None = None\n'; z=a+'\n    part_number: int | None = None\n'
if a not in s: raise SystemExit('request model anchor missing')
s=s.replace(a,z,1)
a='''coach_part_number = int(\n                    flow_state.get(\n                        "part_number"\n                    )\n                    or 1\n                )'''
z='''coach_part_number = int(\n                    body.part_number\n                    or flow_state.get(\n                        "part_number"\n                    )\n                    or 1\n                )'''
n=s.count(a)
if n < 2: raise SystemExit(f'coach anchors missing: {n}')
s=s.replace(a,z); p.write_text(s,encoding='utf-8'); print('patched',n,'coach branches')
