from pathlib import Path

p = Path('he2/index.html')
s = p.read_text(encoding='utf-8')
marker = '/* ===== PARENTS BG FULLBLEED V10 ===== */'
css = r'''
/* ===== PARENTS BG FULLBLEED V10 ===== */
.parents-showcase-v2{
  position:relative!important;
  width:100%!important;
  max-width:none!important;
  margin:0!important;
  background:none!important;
  overflow:hidden!important;
  isolation:isolate!important;
}
.parents-showcase-v2::before{
  content:""!important;
  position:absolute!important;
  top:0!important;
  bottom:0!important;
  left:50%!important;
  width:100vw!important;
  transform:translateX(-50%)!important;
  background-image:url('/assets/he2/sections/parents-section-bg.webp?v=10')!important;
  background-repeat:no-repeat!important;
  background-position:center center!important;
  background-size:100% 100%!important;
  z-index:-2!important;
  pointer-events:none!important;
}
.parents-showcase-v2::after{
  content:""!important;
  position:absolute!important;
  top:0!important;
  bottom:0!important;
  left:50%!important;
  width:100vw!important;
  transform:translateX(-50%)!important;
  background:linear-gradient(90deg,rgba(4,17,32,.98) 0%,rgba(4,17,32,.92) 24%,rgba(4,17,32,.72) 40%,rgba(4,17,32,.30) 58%,rgba(4,17,32,.08) 76%,rgba(4,17,32,0) 100%)!important;
  z-index:-1!important;
  pointer-events:none!important;
}
.parents-v2-inner{
  position:relative!important;
  z-index:1!important;
}
@media(max-width:760px){
  .parents-showcase-v2::before{
    background-size:cover!important;
    background-position:center center!important;
  }
  .parents-showcase-v2::after{
    background:linear-gradient(180deg,rgba(4,17,32,.94) 0%,rgba(4,17,32,.76) 44%,rgba(4,17,32,.26) 72%,rgba(4,17,32,.06) 100%)!important;
  }
}
'''
if marker not in s:
    s = s.replace('</style>', css + '\n</style>', 1)
else:
    s = s.replace("parents-section-bg.webp?v=9", "parents-section-bg.webp?v=10")
p.write_text(s, encoding='utf-8')
print('Applied HE2 parents full-bleed background v10')
