from pathlib import Path
import re

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

# Add one small helper that awards exactly 10 coins and refreshes the top counter.
marker = '/* =====================================================\n   LESSON RENDERER V1\n===================================================== */'
if marker not in s:
    raise SystemExit('lesson renderer marker not found')
helper = '''async function awardPartCoins(amount = 10){\n  const kidId = CURRENT_KID?.id || localStorage.getItem("active_kid_id");\n  if(!kidId) return;\n\n  const { data: profile, error: readError } = await sb\n    .from("kids_profiles")\n    .select("coins")\n    .eq("id", kidId)\n    .single();\n\n  if(readError || !profile){\n    console.error("COIN REWARD READ ERROR:", readError);\n    return;\n  }\n\n  const nextCoins = Number(profile.coins || 0) + Number(amount || 0);\n  const { error: updateError } = await sb\n    .from("kids_profiles")\n    .update({ coins: nextCoins })\n    .eq("id", kidId);\n\n  if(updateError){\n    console.error("COIN REWARD UPDATE ERROR:", updateError);\n    return;\n  }\n\n  if(CURRENT_KID) CURRENT_KID.coins = nextCoins;\n  const coinsEl = document.getElementById("kidCoinsValue");\n  if(coinsEl) coinsEl.textContent = nextCoins.toLocaleString("he-IL");\n  console.log("🪙 PART REWARD:", { amount, coins: nextCoins });\n}\n\n'''
if 'async function awardPartCoins(' not in s:
    s = s.replace(marker, helper + marker, 1)

# Find the universal coach-finished transition block by its isLastPart calculation.
# Insert the reward once per completion event, immediately before branching to next part / lesson end.
patterns = [
    r'(const\s+isLastPart\s*=\s*[\s\S]{0,500}?;)([\s\S]{0,700}?)(\n\s*if\s*\(\s*!?isLastPart\s*\))',
    r'(let\s+isLastPart\s*=\s*[\s\S]{0,500}?;)([\s\S]{0,700}?)(\n\s*if\s*\(\s*!?isLastPart\s*\))',
]
match = None
for pat in patterns:
    for m in re.finditer(pat, s):
        ctx = m.group(0)
        if 'part' in ctx.lower() and ('coach' in s[max(0,m.start()-2500):m.start()].lower() or 'CURRENT_LESSON' in ctx):
            match = m
            break
    if match:
        break

if not match:
    # Fallback: locate isLastPart and show useful context in Actions log, but do not modify wrong code.
    positions = [m.start() for m in re.finditer(r'isLastPart', s)]
    for pos in positions[:10]:
        print('--- isLastPart context ---')
        print(s[max(0,pos-1200):pos+1800])
    raise SystemExit('could not safely locate unique part-completion branch')

block = match.group(0)
if 'awardPartCoins(10)' not in block:
    insert_at = match.start(3)
    s = s[:insert_at] + '\n\n  await awardPartCoins(10);\n' + s[insert_at:]

if 'IAKIDS • build 0.7.8' not in s:
    raise SystemExit('build 0.7.8 stamp not found')
s = s.replace('IAKIDS • build 0.7.8', 'IAKIDS • build 0.7.9', 1)

p.write_text(s, encoding='utf-8')
out = p.read_text(encoding='utf-8')
for token in ['async function awardPartCoins(', 'await awardPartCoins(10);', 'IAKIDS • build 0.7.9']:
    if token not in out:
        raise SystemExit(f'missing validation token: {token}')
print('v0.7.9: +10 coins after each completed lesson part')
