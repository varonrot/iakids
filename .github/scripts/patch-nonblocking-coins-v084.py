from pathlib import Path
p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
old='  await awardPartCoins(10, currentPartNumber);'
new='  awardPartCoins(10, currentPartNumber).catch((error) => {\n    console.error("NON-BLOCKING COIN REWARD ERROR:", error);\n  });'
if old not in s: raise SystemExit('award await not found')
s=s.replace(old,new,1)
# bump whichever deployed frontend stamp is current in main
if 'IAKIDS • build 0.8.3' in s:
    s=s.replace('IAKIDS • build 0.8.3','IAKIDS • build 0.8.4',1)
elif 'IAKIDS • build 0.8.2' in s:
    s=s.replace('IAKIDS • build 0.8.2','IAKIDS • build 0.8.4',1)
else:
    raise SystemExit('expected build stamp not found')
p.write_text(s,encoding='utf-8')
out=p.read_text(encoding='utf-8')
assert 'awardPartCoins(10, currentPartNumber).catch' in out
assert 'IAKIDS • build 0.8.4' in out
print('v0.8.4 applied')
