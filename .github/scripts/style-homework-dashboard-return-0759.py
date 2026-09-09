from pathlib import Path
import re

js=Path('he/workspace/lesson-completion.js')
idx=Path('he/workspace/index.html')
s=js.read_text(encoding='utf-8')
old='''.iakids-homework-dashboard-return{display:none;position:fixed;top:104px;left:24px;z-index:10050;height:42px;padding:0 15px;border-radius:12px;border:1px solid rgba(86,157,238,.35);background:linear-gradient(180deg,#12345f,#0b2548);color:#eef7ff;align-items:center;gap:8px;font:900 12px "Heebo",Arial,sans-serif;cursor:pointer;box-shadow:0 10px 28px rgba(0,0,0,.28)}
      .iakids-homework-dashboard-return:hover{border-color:rgba(92,205,255,.7);transform:translateY(-1px)}
      body.homework-lesson-mode .iakids-homework-dashboard-return{display:flex!important}
      @media(max-width:900px){.iakids-homework-dashboard-return{top:78px;left:12px;height:38px;padding:0 11px;font-size:11px}}'''
new='''.iakids-homework-dashboard-return{
        display:none;
        position:fixed;
        top:116px;
        left:28px;
        z-index:10050;
        height:34px;
        padding:0 11px;
        border-radius:10px;
        border:1px solid rgba(83,155,235,.28);
        background:linear-gradient(180deg,rgba(18,52,95,.94),rgba(9,32,63,.96));
        color:#dcecff;
        align-items:center;
        gap:6px;
        font:850 11px "Heebo",Arial,sans-serif;
        cursor:pointer;
        box-shadow:0 7px 20px rgba(0,0,0,.24);
        white-space:nowrap;
        opacity:.96;
      }
      .iakids-homework-dashboard-return i{font-size:11px;color:#86d8ff}
      .iakids-homework-dashboard-return:hover{
        border-color:rgba(92,205,255,.58);
        background:linear-gradient(180deg,rgba(23,68,119,.98),rgba(11,40,77,.98));
        transform:translateY(-1px)
      }
      body.homework-lesson-mode .iakids-homework-dashboard-return{display:flex!important}
      @media(max-width:900px){
        .iakids-homework-dashboard-return{top:82px;left:10px;height:32px;padding:0 9px;font-size:10px;border-radius:9px}
      }'''
if old not in s:
    raise SystemExit('return button CSS block not found')
s=s.replace(old,new,1)
s=re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "[0-9.]+";','window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.59";',s,count=1)
js.write_text(s,encoding='utf-8')

h=idx.read_text(encoding='utf-8')
h=re.sub(r'/he/workspace/lesson-completion\.js\?v=\d+','/he/workspace/lesson-completion.js?v=0759',h,count=1)
h=re.sub(r'IAKIDS • build [0-9.]+','IAKIDS • build 0.7.59',h,count=1)
h=re.sub(r'window\.IAKIDS_BUILD_VERSION = "[0-9.]+";','window.IAKIDS_BUILD_VERSION = "0.7.59";',h,count=1)
idx.write_text(h,encoding='utf-8')
print('styled homework dashboard return; build 0.7.59')
