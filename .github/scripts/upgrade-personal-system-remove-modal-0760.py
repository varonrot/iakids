from pathlib import Path
import re

INDEX = Path('he/workspace/index.html')
LOADER = Path('he/workspace/lesson-completion.js')

index = INDEX.read_text(encoding='utf-8')
loader = LOADER.read_text(encoding='utf-8')

MARKER = 'IAKIDS_PERSONAL_SYSTEM_REMOVE_MODAL_0760'

if MARKER not in index:
    style_anchor = '''  .iakids-personal-systems-empty{\n    padding:10px 12px;color:#788eaf;font-size:12px;font-weight:700;text-align:right;\n  }\n'''
    if style_anchor not in index:
        raise RuntimeError('personal systems style anchor not found')

    modal_css = r'''

  /* IAKIDS_PERSONAL_SYSTEM_REMOVE_MODAL_0760 */
  .iakids-ps-modal-backdrop{
    position:fixed;inset:0;z-index:100000;
    display:flex;align-items:center;justify-content:center;
    padding:22px;
    background:rgba(1,8,22,.76);
    backdrop-filter:blur(10px);
    animation:iakidsPsModalFade .16s ease-out;
  }
  .iakids-ps-modal{
    width:min(460px,94vw);
    border:1px solid rgba(82,157,255,.42);
    border-radius:24px;
    background:
      radial-gradient(circle at 78% 4%,rgba(115,70,255,.22),transparent 33%),
      linear-gradient(180deg,#0b1d3b 0%,#07152d 100%);
    box-shadow:0 28px 75px rgba(0,0,0,.48),inset 0 0 0 1px rgba(112,80,255,.06);
    padding:25px 25px 22px;
    color:#f4f8ff;
    direction:rtl;
    transform-origin:center;
    animation:iakidsPsModalPop .18s ease-out;
  }
  .iakids-ps-modal-icon{
    width:54px;height:54px;border-radius:17px;
    display:grid;place-items:center;
    margin-bottom:16px;
    border:1px solid rgba(255,110,128,.30);
    background:linear-gradient(145deg,rgba(117,31,52,.42),rgba(71,24,52,.35));
    color:#ff9aaa;font-size:21px;
    box-shadow:0 0 22px rgba(255,79,110,.10);
  }
  .iakids-ps-modal h3{
    margin:0 0 8px;font-size:23px;line-height:1.2;font-weight:950;color:#fff;
  }
  .iakids-ps-modal p{
    margin:0;color:#b8c9e4;font-size:14px;line-height:1.7;font-weight:650;
  }
  .iakids-ps-modal p strong{color:#eef6ff;font-weight:900;}
  .iakids-ps-modal-note{
    display:flex;align-items:center;gap:8px;
    margin-top:13px;padding:10px 12px;border-radius:13px;
    border:1px solid rgba(83,156,255,.18);
    background:rgba(27,64,114,.23);
    color:#8fb7ea;font-size:12px;font-weight:750;
  }
  .iakids-ps-modal-actions{
    display:flex;gap:10px;justify-content:flex-start;margin-top:22px;
  }
  .iakids-ps-modal-btn{
    min-width:112px;height:44px;border-radius:13px;
    font:900 14px "Heebo",Arial,sans-serif;cursor:pointer;
    transition:.16s ease;
  }
  .iakids-ps-modal-btn.cancel{
    border:1px solid rgba(92,146,217,.28);
    background:rgba(22,48,86,.68);color:#d5e3f7;
  }
  .iakids-ps-modal-btn.remove{
    border:1px solid rgba(255,108,128,.46);
    background:linear-gradient(135deg,#8d2943,#b83b52);color:#fff;
    box-shadow:0 8px 18px rgba(155,42,67,.22);
  }
  .iakids-ps-modal-btn:hover{transform:translateY(-1px);filter:brightness(1.08);}
  @keyframes iakidsPsModalFade{from{opacity:0}to{opacity:1}}
  @keyframes iakidsPsModalPop{from{opacity:0;transform:scale(.96) translateY(5px)}to{opacity:1;transform:scale(1) translateY(0)}}
'''
    index = index.replace(style_anchor, style_anchor + modal_css, 1)

    fn_anchor = '''  async function archivePersonalSystem(subject){\n'''
    if fn_anchor not in index:
        raise RuntimeError('archivePersonalSystem anchor not found')

    modal_fn = r'''  function showRemovePersonalSystemModal(subject){
    return new Promise(resolve => {
      document.querySelectorAll('.iakids-ps-modal-backdrop').forEach(el => el.remove());

      const safeName = String(subject?.subject_name || 'המקצוע');
      const backdrop = document.createElement('div');
      backdrop.className = 'iakids-ps-modal-backdrop';
      backdrop.setAttribute('role','presentation');
      backdrop.innerHTML = `
        <div class="iakids-ps-modal" role="dialog" aria-modal="true" aria-labelledby="iakidsPsModalTitle">
          <div class="iakids-ps-modal-icon"><i class="fa-solid fa-trash-can"></i></div>
          <h3 id="iakidsPsModalTitle">הסרת מקצוע</h3>
          <p>להסיר את <strong>${escapeHtml(safeName)}</strong> מהמערכת האישית שלך?</p>
          <div class="iakids-ps-modal-note"><i class="fa-solid fa-circle-info"></i><span>אפשר יהיה להוסיף את המקצוע מחדש בעתיד.</span></div>
          <div class="iakids-ps-modal-actions">
            <button type="button" class="iakids-ps-modal-btn remove">הסר מקצוע</button>
            <button type="button" class="iakids-ps-modal-btn cancel">ביטול</button>
          </div>
        </div>`;

      const finish = value => {
        document.removeEventListener('keydown', onKeyDown);
        backdrop.remove();
        resolve(value);
      };
      const onKeyDown = event => {
        if(event.key === 'Escape') finish(false);
      };

      backdrop.addEventListener('click', event => {
        if(event.target === backdrop) finish(false);
      });
      backdrop.querySelector('.iakids-ps-modal-btn.cancel')?.addEventListener('click', ()=>finish(false));
      backdrop.querySelector('.iakids-ps-modal-btn.remove')?.addEventListener('click', ()=>finish(true));
      document.addEventListener('keydown', onKeyDown);
      document.body.appendChild(backdrop);
      requestAnimationFrame(()=>backdrop.querySelector('.iakids-ps-modal-btn.cancel')?.focus());
    });
  }

'''
    index = index.replace(fn_anchor, modal_fn + fn_anchor, 1)

    old_confirm = '''    const ok = window.confirm(`להסיר את "${subject.subject_name}" מהמערכת האישית?\\nאפשר יהיה להוסיף מקצוע חדש בעתיד.`);\n    if(!ok) return;\n'''
    if old_confirm not in index:
        raise RuntimeError('native confirm block not found')
    index = index.replace(old_confirm, '''    const ok = await showRemovePersonalSystemModal(subject);\n    if(!ok) return;\n''', 1)

# visible build bump
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.60', index, count=1)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.60";', index, count=1)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0760', index, count=1)
loader = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.60";', loader, count=1)
loader = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0760', loader, count=1)

INDEX.write_text(index, encoding='utf-8')
LOADER.write_text(loader, encoding='utf-8')
print('Personal system remove modal upgraded; build 0.7.60')
