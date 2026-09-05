from pathlib import Path
p=Path('he/parent-panel/index.html')
s=p.read_text(encoding='utf-8')
old='''      .select(`
        id,
        learning_lesson_id,
        grade,
        subject,
        parent_lesson,
        unit_order,
        unit_name,
        lesson_order,
        lesson_name
      `)'''
new='''      .select(`
        id,
        learning_lesson_id,
        unit_order,
        unit_name,
        lesson_order,
        lesson_name
      `)'''
if old not in s:
    raise SystemExit('lesson_units_content select block not found')
s=s.replace(old,new,1)
if '<!-- IAKIDS parent panel build 0.7.1 -->' in s:
    s=s.replace('<!-- IAKIDS parent panel build 0.7.1 -->','<!-- IAKIDS parent panel build 0.7.2 -->',1)
elif '<!-- IAKIDS parent panel build 0.7.2 -->' not in s:
    raise SystemExit('parent panel build stamp not found')
p.write_text(s,encoding='utf-8')
out=p.read_text(encoding='utf-8')
assert 'lesson_name' in out
assert 'grade,\n        subject,\n        parent_lesson' not in out
assert 'parent panel build 0.7.2' in out
print('parent panel v0.7.2 lesson name query fixed')
