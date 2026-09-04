from pathlib import Path
p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
css=r'''
/* =====================================================
   HOME DAILY STREAK CARD — balanced 4-card row
   build 0.7.7
===================================================== */
.kingdom-status-row{
  grid-template-columns: 1fr 1fr 1.18fr 1fr !important;
}
.kingdom-status-row .kingdom-status-card:nth-child(2){
  min-width:0 !important;
  overflow:hidden !important;
}
.kingdom-status-row .kingdom-status-card:nth-child(2) .kingdom-status-card-inner,
.kingdom-status-row .kingdom-status-card:nth-child(2) .kingdom-streak-inner{
  width:100% !important;
  min-width:0 !important;
  box-sizing:border-box !important;
}
.kingdom-status-row .kingdom-status-card:nth-child(2) .kingdom-streak-days{
  width:100% !important;
  min-width:0 !important;
  justify-content:space-between !important;
  gap:4px !important;
}
.kingdom-status-row .kingdom-status-card:nth-child(2) .kingdom-streak-day{
  flex:0 1 auto !important;
  min-width:0 !important;
}
'''
marker='HOME DAILY STREAK CARD — balanced 4-card row'
if marker not in s:
    i=s.find('</style>')
    if i<0: raise SystemExit('style closing tag not found')
    s=s[:i]+'\n'+css+'\n'+s[i:]
s=s.replace('IAKIDS • build 0.7.6','IAKIDS • build 0.7.7')
p.write_text(s,encoding='utf-8')
