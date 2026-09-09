from pathlib import Path
import re

p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
MARK='IAKIDS_PROGRESS_ROUTE_TO_PRO_0762'
if MARK in s:
    print('already applied')
    raise SystemExit(0)

old="""document.addEventListener('click',function(event){const item=event.target?.closest?.('.kid-actions .side-item');if(!item)return;const text=String(item.textContent||'').replace(/\\s+/g,' ').trim();if(!text.includes('התקדמות'))return;event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();document.querySelectorAll('.kid-actions .side-item').forEach(x=>x.classList.remove('active'));item.classList.add('active');if(typeof window.closeWorkspaceAchievements==='function')window.closeWorkspaceAchievements();open()},true);"""
new="""/* IAKIDS_PROGRESS_ROUTE_TO_PRO_0762 */
document.addEventListener('click',function(event){const item=event.target?.closest?.('.kid-actions .side-item');if(!item)return;const text=String(item.textContent||'').replace(/\\s+/g,' ').trim();if(!text.includes('התקדמות'))return;event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();document.querySelectorAll('.kid-actions .side-item').forEach(x=>x.classList.remove('active'));item.classList.add('active');if(typeof window.closeWorkspaceAchievements==='function')window.closeWorkspaceAchievements();if(typeof window.openProgressDashboard==='function'){window.openProgressDashboard()}else{open()}},true);"""

if old not in s:
    raise SystemExit('old progress route not found')
s=s.replace(old,new,1)
s=re.sub(r'IAKIDS • build [0-9.]+','IAKIDS • build 0.7.62',s,count=1)
s=re.sub(r'window\.IAKIDS_BUILD_VERSION = "[0-9.]+";','window.IAKIDS_BUILD_VERSION = "0.7.62";',s,count=1)
p.write_text(s,encoding='utf-8')
print('progress route now opens pro dashboard; build 0.7.62')
