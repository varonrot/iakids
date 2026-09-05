from pathlib import Path
p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
old='''        <span class="kingdom-status-label">
          רצף יומי
        </span>

        <strong class="kingdom-streak-number">
          12
          <small>ימים</small>
        </strong>

        <p>
          כל הכבוד! המשך כך
        </p>'''
new='''        <div class="kingdom-streak-headline">
          <span class="kingdom-status-label">
            רצף יומי
          </span>

          <strong class="kingdom-streak-number">
            12
            <small>ימים</small>
          </strong>
        </div>

        <p>
          כל הכבוד! המשך כך
        </p>'''
if old not in s: raise SystemExit('streak markup not found')
s=s.replace(old,new,1)
style='''\n<style id="kingdom-streak-headline-v085">\n.kingdom-status-streak .kingdom-streak-headline{display:flex!important;align-items:baseline!important;gap:10px!important;direction:rtl!important;white-space:nowrap!important;}\n.kingdom-status-streak .kingdom-streak-headline .kingdom-status-label{margin:0!important;}\n.kingdom-status-streak .kingdom-streak-headline .kingdom-streak-number{display:inline-flex!important;align-items:baseline!important;gap:4px!important;margin:0!important;line-height:1!important;}\n.kingdom-status-streak .kingdom-streak-headline .kingdom-streak-number small{font-size:9px!important;font-weight:700!important;}\n.kingdom-status-streak .kingdom-streak-main p{margin:4px 0 0!important;}\n</style>\n'''
if '</head>' not in s: raise SystemExit('head close not found')
s=s.replace('</head>',style+'</head>',1)
# current main should be 0.8.4 after prior workflow; tolerate 0.8.3 only if race landed first
if 'IAKIDS • build 0.8.4' in s: s=s.replace('IAKIDS • build 0.8.4','IAKIDS • build 0.8.5',1)
elif 'IAKIDS • build 0.8.3' in s: s=s.replace('IAKIDS • build 0.8.3','IAKIDS • build 0.8.5',1)
else: raise SystemExit('build stamp not found')
p.write_text(s,encoding='utf-8')
assert 'kingdom-streak-headline-v085' in p.read_text(encoding='utf-8')
print('v0.8.5 streak layout applied')
