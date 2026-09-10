from pathlib import Path

p = Path('he2/index.html')
s = p.read_text(encoding='utf-8')

marker = '/* ===== PARENTS BG STRETCH V9 ===== */'
override = r'''
/* ===== PARENTS BG STRETCH V9 ===== */
.parents-showcase-v2{
  width:100vw!important;
  max-width:none!important;
  margin-left:calc(50% - 50vw)!important;
  margin-right:calc(50% - 50vw)!important;
  background-image:url('/assets/he2/sections/parents-section-bg.webp?v=9')!important;
  background-repeat:no-repeat!important;
  background-position:center center!important;
  background-size:100% 100%!important;
}
@media(max-width:760px){
  .parents-showcase-v2{
    width:100vw!important;
    margin-left:calc(50% - 50vw)!important;
    margin-right:calc(50% - 50vw)!important;
    background-size:cover!important;
    background-position:center center!important;
  }
}
'''

if marker not in s:
    if '</style>' not in s:
        raise SystemExit('Could not find </style> in he2/index.html')
    s = s.replace('</style>', override + '\n</style>', 1)
else:
    s = s.replace("parents-section-bg.webp?v=8", "parents-section-bg.webp?v=9")

p.write_text(s, encoding='utf-8')
print('Applied parents background stretch override')
