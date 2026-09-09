from pathlib import Path
import re

workspace=Path('he/workspace/index.html')
addpage=Path('he/add-subject/index.html')
ws=workspace.read_text(encoding='utf-8')
ap=addpage.read_text(encoding='utf-8')
MARK='IAKIDS_CUSTOM_SUBJECT_EDIT_0757'
if MARK in ws and MARK in ap:
    print('already applied'); raise SystemExit(0)

# ---------- workspace: edit button next to trash ----------
if MARK not in ws:
    style='''\n<style id="IAKIDS_CUSTOM_SUBJECT_EDIT_0757">\n  .iakids-personal-safe-row{padding-left:84px!important;}\n  .iakids-personal-safe-edit{\n    position:absolute;left:45px;top:50%;transform:translateY(-50%);\n    width:31px;height:31px;border-radius:9px;border:1px solid rgba(74,163,255,.28);\n    background:rgba(45,104,184,.12);color:#79bdff;display:grid;place-items:center;\n    cursor:pointer;opacity:.88;transition:.18s ease;z-index:4;padding:0;\n  }\n  .iakids-personal-safe-edit:hover{opacity:1;background:rgba(45,116,210,.24);border-color:rgba(105,190,255,.58);transform:translateY(-50%) scale(1.04);}\n</style>\n'''
    anchor='<style id="IAKIDS_PERSONAL_SYSTEM_CARD_WIDTHS_0737">'
    if anchor not in ws: raise SystemExit('workspace style anchor missing')
    ws=ws.replace(anchor,style+'\n'+anchor,1)

    old='''row.innerHTML=`<span class="psri"><i class="fa-solid fa-star"></i></span><span>${esc(subject.subject_name)}</span><button type="button" class="iakids-personal-safe-delete" title="הסרת מקצוע" aria-label="הסרת ${esc(subject.subject_name)}"><i class="fa-solid fa-trash-can"></i></button>`;'''
    new='''row.innerHTML=`<span class="psri"><i class="fa-solid fa-star"></i></span><span>${esc(subject.subject_name)}</span><button type="button" class="iakids-personal-safe-edit" title="עריכת תוכנית" aria-label="עריכת ${esc(subject.subject_name)}"><i class="fa-solid fa-pen"></i></button><button type="button" class="iakids-personal-safe-delete" title="הסרת מקצוע" aria-label="הסרת ${esc(subject.subject_name)}"><i class="fa-solid fa-trash-can"></i></button>`;'''
    if old not in ws: raise SystemExit('workspace row html not found')
    ws=ws.replace(old,new,1)

    old2="""if(event.target?.closest?.('.iakids-personal-safe-delete')) return;"""
    new2="""if(event.target?.closest?.('.iakids-personal-safe-delete,.iakids-personal-safe-edit')) return;"""
    if old2 not in ws: raise SystemExit('workspace row click guard not found')
    ws=ws.replace(old2,new2,1)

    needle="""const del=row.querySelector('.iakids-personal-safe-delete');"""
    insert="""const edit=row.querySelector('.iakids-personal-safe-edit');\n      edit?.addEventListener('click',event=>{\n        event.preventDefault();event.stopPropagation();\n        location.href=`/he/add-subject/?edit=${encodeURIComponent(subject.id)}`;\n      });\n      const del=row.querySelector('.iakids-personal-safe-delete');"""
    if needle not in ws: raise SystemExit('workspace delete selector not found')
    ws=ws.replace(needle,insert,1)

    ws=re.sub(r'IAKIDS • build [0-9.]+','IAKIDS • build 0.7.57',ws,count=1)
    ws=re.sub(r'window\.IAKIDS_BUILD_VERSION = "[0-9.]+";','window.IAKIDS_BUILD_VERSION = "0.7.57";',ws,count=1)
    workspace.write_text(ws,encoding='utf-8')

# ---------- add-subject: edit existing curriculum ----------
if MARK not in ap:
    # add edit mode styles before </head>
    style2='''\n<style id="IAKIDS_CUSTOM_SUBJECT_EDIT_0757">\n  body.edit-existing .head .spark{color:#48b7ff}\n  body.edit-existing .approve.ready{background:linear-gradient(135deg,#176dd9,#4a50ff)}\n  body.edit-existing .suggestions button{white-space:nowrap}\n  .edit-mode-chip{display:inline-flex;align-items:center;gap:6px;margin-top:7px;padding:5px 10px;border-radius:999px;border:1px solid rgba(72,166,255,.28);background:rgba(46,109,191,.12);color:#8cc8ff;font-size:10px;font-weight:800}\n</style>\n'''
    ap=ap.replace('</head>',style2+'\n</head>',1)

    # declare edit id after state vars
    state_anchor='''let CURRENT_VERSION = null;\nlet CONVERSATION_HISTORY = [];'''
    state_new='''let CURRENT_VERSION = null;\nlet CONVERSATION_HISTORY = [];\nconst EDIT_SUBJECT_ID = new URLSearchParams(location.search).get("edit");'''
    if state_anchor not in ap: raise SystemExit('addpage state anchor missing')
    ap=ap.replace(state_anchor,state_new,1)

    # inject edit loader before render()
    render_anchor='''function render(plan, options = {}) {'''
    loader=r'''
async function loadExistingCurriculumForEdit(){
  if(!EDIT_SUBJECT_ID || !CURRENT_KID?.id) return;
  try{
    const [{data:subject,error:subjectError},{data:curricula,error:currError}] = await Promise.all([
      sb.from('kid_custom_subjects').select('id,subject_name,status').eq('id',EDIT_SUBJECT_ID).eq('kid_id',CURRENT_KID.id).single(),
      sb.from('kid_custom_curriculums').select('id,curriculum_json,version,status,updated_at').eq('custom_subject_id',EDIT_SUBJECT_ID).eq('kid_id',CURRENT_KID.id).order('updated_at',{ascending:false}).limit(1)
    ]);
    if(subjectError) throw subjectError;
    if(currError) throw currError;
    const curriculum=(curricula||[])[0];
    if(!subject || !curriculum?.curriculum_json) throw new Error('existing curriculum not found');

    CURRENT_CUSTOM_SUBJECT_ID=subject.id;
    CURRENT_CURRICULUM_ID=curriculum.id;
    CURRENT_VERSION=Number(curriculum.version||1);
    CURRENT_PLAN=curriculum.curriculum_json;
    document.body.classList.add('edit-existing');

    const head=document.querySelector('.head h1');
    if(head) head.textContent=`עריכת ${subject.subject_name}`;
    const subtitle=document.getElementById('subtitle');
    if(subtitle) subtitle.innerHTML=`עדכנו את תוכנית הלימודים של ${esc(subject.subject_name)} <span class="edit-mode-chip"><i class="fa-solid fa-pen"></i> מצב עריכה · גרסה ${CURRENT_VERSION}</span>`;
    const welcome=document.getElementById('welcome');
    if(welcome) welcome.innerHTML=`שלום 👋<br>אני כאן כדי לעזור לך לעדכן את תוכנית הלימודים של <strong>${esc(subject.subject_name)}</strong>.<br><br>מה תרצה לשנות, להוסיף או להסיר?`;

    const suggestions=document.querySelector('.suggestions');
    if(suggestions){
      suggestions.innerHTML=`
        <button data-topic="הוסף נושא חדש לתוכנית">הוסף נושא</button>
        <button data-topic="הוסף שיעורים חדשים">הוסף שיעורים</button>
        <button data-topic="אני רוצה להסיר נושא מהתוכנית">הסר נושא</button>
        <button data-topic="שנה את סדר הנושאים והיחידות">שנה סדר</button>
        <button data-topic="העמק את אחת היחידות עם תוכן נוסף">העמק יחידה</button>`;
      suggestions.querySelectorAll('[data-topic]').forEach(b=>b.onclick=()=>submitText(b.dataset.topic));
    }

    render(CURRENT_PLAN);
    const approve=document.getElementById('approveBtn');
    if(approve){approve.textContent='✦ שמור שינויים';approve.disabled=false;approve.classList.add('ready');}
    const input=document.getElementById('chatInput');
    if(input){input.placeholder='מה תרצה לשנות בתוכנית?';setTimeout(()=>input.focus(),120)}
  }catch(e){
    console.error('EDIT CURRICULUM LOAD',e);
    msg('ai','לא הצלחתי לטעון את התוכנית הקיימת לעריכה. נסו לחזור ולפתוח שוב את העריכה.');
  }
}

'''
    if render_anchor not in ap: raise SystemExit('addpage render anchor missing')
    ap=ap.replace(render_anchor,loader+render_anchor,1)

    # make approve UI text appropriate for edit mode
    ap=ap.replace('''btn.textContent =\n    "✦ מאשר את תוכנית הלימודים...";''','''btn.textContent =\n    EDIT_SUBJECT_ID ? "✦ שומר את השינויים..." : "✦ מאשר את תוכנית הלימודים...";''',1)
    ap=ap.replace('''btn.textContent =\n      "✓ תוכנית הלימודים אושרה";''','''btn.textContent =\n      EDIT_SUBJECT_ID ? "✓ השינויים נשמרו" : "✓ תוכנית הלימודים אושרה";''',1)

    # init then edit loader
    oldcall="""document.getElementById('openParentModal').onclick=()=>location.href='/he/workspace/';document.getElementById('openSettings').onclick=()=>location.href='/he/workspace/';document.getElementById('manageSubscriptionSide').onclick=()=>location.href='/he/workspace/';init();"""
    newcall="""document.getElementById('openParentModal').onclick=()=>location.href='/he/workspace/';document.getElementById('openSettings').onclick=()=>location.href='/he/workspace/';document.getElementById('manageSubscriptionSide').onclick=()=>location.href='/he/workspace/';init().then(loadExistingCurriculumForEdit);"""
    if oldcall not in ap: raise SystemExit('addpage init call missing')
    ap=ap.replace(oldcall,newcall,1)
    addpage.write_text(ap,encoding='utf-8')

print('custom subject edit mode added; build 0.7.57')
