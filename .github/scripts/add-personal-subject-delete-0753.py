from pathlib import Path
import re
p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
MARK='IAKIDS_PERSONAL_SUBJECT_DELETE_0753'
if MARK in s:
    print('already applied'); raise SystemExit(0)

# Add styles before the personal card width block.
style='''\n<style id="IAKIDS_PERSONAL_SUBJECT_DELETE_0753">\n  .iakids-personal-safe-row{position:relative!important;padding-left:46px!important;}\n  .iakids-personal-safe-delete{\n    position:absolute;left:9px;top:50%;transform:translateY(-50%);\n    width:31px;height:31px;border-radius:9px;border:1px solid rgba(255,91,91,.28);\n    background:rgba(184,45,55,.12);color:#ff7b82;display:grid;place-items:center;\n    cursor:pointer;opacity:.78;transition:.18s ease;z-index:4;padding:0;\n  }\n  .iakids-personal-safe-delete:hover{opacity:1;background:rgba(210,49,60,.22);border-color:rgba(255,105,105,.55);transform:translateY(-50%) scale(1.04);}\n  .iakids-personal-safe-delete:disabled{opacity:.4;cursor:wait;}\n</style>\n'''
anchor='<style id="IAKIDS_PERSONAL_SYSTEM_CARD_WIDTHS_0737">'
if anchor not in s: raise SystemExit('personal styles anchor not found')
s=s.replace(anchor,style+'\n'+anchor,1)

old='''    items.forEach(subject=>{\n      const row=document.createElement('button');\n      row.type='button';\n      row.className='iakids-personal-safe-row';\n      row.innerHTML=`<span class="psri"><i class="fa-solid fa-star"></i></span><span>${esc(subject.subject_name)}</span>`;\n      row.addEventListener('click',()=>openSubject(subject));\n      list.appendChild(row);\n    });'''
new='''    items.forEach(subject=>{\n      const row=document.createElement('div');\n      row.className='iakids-personal-safe-row';\n      row.setAttribute('role','button');\n      row.tabIndex=0;\n      row.innerHTML=`<span class="psri"><i class="fa-solid fa-star"></i></span><span>${esc(subject.subject_name)}</span><button type="button" class="iakids-personal-safe-delete" title="הסרת מקצוע" aria-label="הסרת ${esc(subject.subject_name)}"><i class="fa-solid fa-trash-can"></i></button>`;\n      row.addEventListener('click',event=>{\n        if(event.target?.closest?.('.iakids-personal-safe-delete')) return;\n        openSubject(subject);\n      });\n      row.addEventListener('keydown',event=>{\n        if(event.key==='Enter'||event.key===' '){event.preventDefault();openSubject(subject);}\n      });\n      const del=row.querySelector('.iakids-personal-safe-delete');\n      del?.addEventListener('click',async event=>{\n        event.preventDefault();event.stopPropagation();\n        const ok=window.confirm(`להסיר את ${subject.subject_name} מהמערכת האישית שלך?\\n\\nאפשר יהיה להוסיף את המקצוע שוב בעתיד.`);\n        if(!ok) return;\n        del.disabled=true;\n        try{\n          const client=getClient(); const kid=getKid();\n          if(!client||!kid?.id) throw new Error('missing client or kid');\n          const {error}=await client.from('kid_custom_subjects').update({status:'archived',updated_at:new Date().toISOString()}).eq('id',subject.id).eq('kid_id',kid.id);\n          if(error) throw error;\n          await load();\n          try{ window.refreshCustomSubjectProgress?.(); }catch(_e){}\n        }catch(e){\n          console.error('PERSONAL SUBJECT REMOVE',e);\n          del.disabled=false;\n          alert('לא הצלחנו להסיר את המקצוע כרגע. נסו שוב.');\n        }\n      });\n      list.appendChild(row);\n    });'''
if old not in s: raise SystemExit('personal render block not found')
s=s.replace(old,new,1)

s=re.sub(r'IAKIDS • build [0-9.]+','IAKIDS • build 0.7.53',s,count=1)
s=re.sub(r'window\.IAKIDS_BUILD_VERSION = "[0-9.]+";','window.IAKIDS_BUILD_VERSION = "0.7.53";',s,count=1)
p.write_text(s,encoding='utf-8')
print('personal subject delete added; build 0.7.53')
