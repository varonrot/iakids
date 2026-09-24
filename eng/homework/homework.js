'use strict';
const $=id=>document.getElementById(id);
const questions=[
 {a:1,b:3,c:1,d:6,op:'+'},{a:2,b:5,c:1,d:5,op:'+'},{a:1,b:4,c:1,d:2,op:'+'},
 {a:3,b:4,c:1,d:8,op:'−'},{a:5,b:6,c:1,d:3,op:'−'},{a:7,b:8,c:1,d:8,op:'−'},
 {a:1,b:2,c:1,d:3,op:'+'},{a:2,b:3,c:1,d:6,op:'−'}
];
let selected=2,mode='solve',step=0,custom=false,zoom=100,objectUrl=null;
const frac=(n,d)=>'<span class="frac"><span>'+n+'</span><span>'+d+'</span></span>';
const gcd=(a,b)=>b?gcd(b,a%b):a;
function common(q){return q.b*q.d/gcd(q.b,q.d);}
function result(q){let d=common(q),n=q.a*d/q.b+(q.op==='+'?1:-1)*q.c*d/q.d;let g=gcd(Math.abs(n),d);return [n/g,d/g];}
const sheet=$('worksheet');
const grid=$('exerciseGrid');
questions.forEach((q,i)=>{
 const btn=document.createElement('button');btn.type='button';btn.className='exercise';
 btn.innerHTML='<b>'+(i+1)+'.</b>'+frac(q.a,q.b)+' '+q.op+' '+frac(q.c,q.d)+' = ___';
 btn.setAttribute('aria-label','Question '+(i+1)+': '+q.a+'/'+q.b+' '+(q.op==='+'?'plus':'minus')+' '+q.c+'/'+q.d);
 btn.onclick=()=>choose(i);grid.append(btn);
});
function options(items){$('answerOptions').replaceChildren();for(const [label,fn] of items){const b=document.createElement('button');b.type='button';b.textContent=label;b.onclick=fn;$('answerOptions').append(b);}}
function render(){
 $('feedback').textContent='';$('answerForm').hidden=true;$('fractionVisual').replaceChildren();options([]);
 document.querySelectorAll('[data-mode]').forEach(b=>{const on=b.dataset.mode===mode;b.setAttribute('aria-pressed',String(on));b.querySelector('b').textContent=on?'✓':'›';});
 if(custom){$('coachMessage').textContent='Your homework is ready to view. AI reading and help for personal homework are not connected yet. You can explore the guided example while this feature is being built.';$('askForm').hidden=true;return;}
 $('askForm').hidden=false;
 const q=questions[selected],den=common(q);
 $('questionCount').textContent='Question '+(selected+1)+' of '+questions.length;
 [...grid.children].forEach((b,i)=>{b.classList.toggle('selected',i===selected);b.setAttribute('aria-pressed',String(i===selected));});
 $('previousQuestion').disabled=selected===0;$('nextQuestion').disabled=selected===questions.length-1;
 const bars=(n,d)=>'<div class="fraction-group">'+frac(n,d)+'<div class="fraction-bar" aria-hidden="true">'+Array.from({length:d},(_,i)=>'<i class="'+(i<n?'filled':'')+'"></i>').join('')+'</div></div>';
 $('fractionVisual').innerHTML=bars(q.a,q.b)+bars(q.c,q.d);
 if(mode==='understand')$('coachMessage').textContent='Question '+(selected+1)+' asks you to '+(q.op==='+'?'add the two fractions. Find how much they make together.':'subtract the second fraction from the first. Find how much is left.')+' The bottom number tells you how many equal parts make one whole.';
 if(mode==='explain')$('coachMessage').textContent='The denominator is the bottom number. The numerator counts the parts you have. To '+(q.op==='+'?'add':'subtract')+' fractions, the parts must be the same size. Here, both fractions can use '+den+' as their denominator.';
 if(mode==='solve'){
  $('coachMessage').textContent=step===0?'Let’s work on question '+(selected+1)+'.\n'+(q.b===q.d?'The denominators already match. What should we do next?':'First, we need equal-sized parts. What should we do first?'):'Use '+den+' as the common denominator.\n'+q.a+'/'+q.b+' = '+q.a*den/q.b+'/'+den+' and '+q.c+'/'+q.d+' = '+q.c*den/q.d+'/'+den+'.\nNow '+(q.op==='+'?'add':'subtract')+' the numerators and keep the denominator. What do you get?';
  if(step===0)options([[q.b===q.d?(q.op==='+'?'Add the numerators':'Subtract the numerators'):'Find a common denominator',()=>{step=1;render();}],['Add the denominators',()=>{$('feedback').textContent='Keep the parts the same size. We do not add the denominators.';}],['I’m not sure',()=>{$('feedback').textContent='Think about equal slices of a whole. '+den+' equal parts will work for both fractions.';}]]);
  else $('answerForm').hidden=false;
 }
 if(mode==='check'){$('coachMessage').textContent='What answer did you get for question '+(selected+1)+'? Enter a fraction, such as 3/4. Equivalent fractions are welcome.';$('answerForm').hidden=false;}
}
function choose(i){selected=i;step=0;render();}
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{mode=b.dataset.mode;render();});
$('previousQuestion').onclick=()=>choose(Math.max(0,selected-1));
$('nextQuestion').onclick=()=>choose(Math.min(questions.length-1,selected+1));
$('answerForm').onsubmit=e=>{
 e.preventDefault();const v=$('answerInput').value.trim();const m=v.match(/^([+-]?\d+)\s*\/\s*(\d+)$/);let n,d;
 if(m){n=Number(m[1]);d=Number(m[2]);}else if(/^\d+(\.\d+)?$/.test(v)){n=Number(v);d=1;}else{$('feedback').textContent='Enter a fraction like 3/4, or a decimal like 0.75.';return;}
 if(!d){$('feedback').textContent='The denominator cannot be zero.';return;}
 const [rn,rd]=result(questions[selected]);
 $('feedback').textContent=Math.abs(n/d-rn/rd)<1e-8?'That’s right! '+rn+'/'+rd+' is the answer. Great work.':'Not quite yet. Check the common denominator, then '+(questions[selected].op==='+'?'add':'subtract')+' only the numerators. Try again.';
};
$('askForm').onsubmit=e=>{e.preventDefault();const s=$('askInput').value.trim().toLowerCase();if(!s)return;
 if(/denominator|bottom/.test(s)){mode='explain';render();}else if(/numerator|top/.test(s)){$('feedback').textContent='The numerator is the top number. It counts how many equal parts you have.';}else if(/help|stuck|understand/.test(s)){mode='understand';render();}else{$('feedback').textContent='This is a guided example, not a live AI chat yet. Try asking about the denominator or numerator, or choose a help mode above.';}
 $('askInput').value='';
};
function zoomDocument(delta){zoom=Math.min(180,Math.max(60,zoom+delta));$('zoomValue').textContent=zoom+'%';const el=$('documentStage').firstElementChild;if(el)el.style.width=zoom+'%';}
$('zoomIn').onclick=()=>zoomDocument(10);$('zoomOut').onclick=()=>zoomDocument(-10);
function clearUrl(){if(objectUrl){URL.revokeObjectURL(objectUrl);objectUrl=null;}}
function showCustom(el,name,status){
 custom=true;zoom=100;$('zoomValue').textContent='100%';$('documentStage').replaceChildren(el);
 $('documentLabel').textContent=name;$('demoTag').hidden=true;$('coachDemo').hidden=true;$('questionCount').textContent='Your homework';
 $('coachTitle').textContent='Your homework';$('coachTopic').textContent='Preview';$('coachIntro').textContent='Choose how you would like to work on your question.';
 $('fileStatus').textContent=status;$('previousQuestion').disabled=true;$('nextQuestion').disabled=true;render();
}
async function openFile(file){
 if(!file)return;
 if(file.size>20*1024*1024){$('fileStatus').textContent='Please choose a file smaller than 20 MB.';return;}
 const image=file.type.startsWith('image/'),pdf=file.type==='application/pdf'||/\.pdf$/i.test(file.name),txt=file.type==='text/plain'||/\.txt$/i.test(file.name);
 if(!image&&!pdf&&!txt){$('fileStatus').textContent='Please choose an image, PDF or plain text file.';return;}
 clearUrl();let el;
 try{
 if(txt){el=document.createElement('article');el.className='worksheet typed-preview';el.textContent=await file.text();}
 else{objectUrl=URL.createObjectURL(file);el=document.createElement(image?'img':'iframe');el.className='upload-preview';el.src=objectUrl;if(image)el.alt='Your uploaded homework';else el.title='Your homework PDF';}
 showCustom(el,file.name,'Local preview only — this file has not been sent to AI or saved to a server.');
 }catch(err){$('fileStatus').textContent='Could not open this file. Please try another file.';}
}
$('photoBtn').onclick=()=>$('photoInput').click();$('fileBtn').onclick=()=>$('fileInput').click();
for(const id of ['photoInput','fileInput'])$(id).onchange=e=>{openFile(e.target.files[0]);e.target.value='';};
$('typeBtn').onclick=()=>$('questionDialog').showModal();$('closeDialog').onclick=()=>$('questionDialog').close();
$('questionForm').onsubmit=e=>{e.preventDefault();const text=$('typedQuestion').value.trim();if(!text)return;clearUrl();const el=document.createElement('article');el.className='worksheet typed-preview';el.textContent=text;showCustom(el,'Typed question','Your question is shown locally. AI help is not connected yet.');$('questionDialog').close();};
$('resetDemo').onclick=()=>{clearUrl();custom=false;zoom=100;sheet.style.width='100%';$('documentStage').replaceChildren(sheet);$('zoomValue').textContent='100%';$('documentLabel').textContent='Fractions practice';$('demoTag').hidden=false;$('coachDemo').hidden=false;$('coachTitle').textContent='Let’s work it out!';$('coachTopic').textContent='Math · Fractions';$('coachIntro').textContent='Learn how to add fractions with different denominators.';$('fileStatus').textContent='Choose a question on the example worksheet to try the guided practice.';mode='solve';choose(2);};
window.addEventListener('beforeunload',clearUrl);
render();
