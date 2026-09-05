from pathlib import Path

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

# Add lightweight animation CSS near the topbar styles.
css_marker = '.top-actions{display:flex;align-items:center;gap:10px}.top-pill'
if css_marker not in s:
    raise SystemExit('topbar css marker not found')

css = '''.stat-pill{position:relative;overflow:visible}\n.coin-reward-pop{\n  position:absolute;\n  left:50%;\n  top:100%;\n  transform:translate(-50%,6px) scale(.92);\n  min-width:72px;\n  padding:6px 10px;\n  border-radius:999px;\n  background:linear-gradient(135deg,#fff4ad,#ffd54f);\n  color:#7a5200;\n  font-size:14px;\n  font-weight:900;\n  text-align:center;\n  box-shadow:0 8px 24px rgba(172,125,0,.22);\n  opacity:0;\n  pointer-events:none;\n  z-index:9999;\n  animation:coinRewardPop 1.15s ease forwards;\n  white-space:nowrap;\n}\n@keyframes coinRewardPop{\n  0%{opacity:0;transform:translate(-50%,10px) scale(.86)}\n  18%{opacity:1;transform:translate(-50%,0) scale(1.06)}\n  72%{opacity:1;transform:translate(-50%,-7px) scale(1)}\n  100%{opacity:0;transform:translate(-50%,-18px) scale(.96)}\n}\n'''
if '@keyframes coinRewardPop' not in s:
    s = s.replace(css_marker, css + css_marker, 1)

old = '''  if(CURRENT_KID) CURRENT_KID.coins = nextCoins;\n  const coinsEl = document.getElementById("kidCoinsValue");\n  if(coinsEl) coinsEl.textContent = nextCoins.toLocaleString("he-IL");\n  console.log("🪙 PART REWARD:", { amount, coins: nextCoins });'''
new = '''  if(CURRENT_KID) CURRENT_KID.coins = nextCoins;\n  const coinsEl = document.getElementById("kidCoinsValue");\n  if(coinsEl){\n    coinsEl.textContent = nextCoins.toLocaleString("he-IL");\n    const pill = coinsEl.closest(".stat-pill");\n    if(pill){\n      pill.querySelectorAll(".coin-reward-pop").forEach(el => el.remove());\n      const pop = document.createElement("span");\n      pop.className = "coin-reward-pop";\n      pop.textContent = `+${Number(amount || 0)} 🪙`;\n      pill.appendChild(pop);\n      window.setTimeout(() => pop.remove(), 1300);\n    }\n  }\n  console.log("🪙 PART REWARD:", { amount, coins: nextCoins });'''
if old not in s:
    raise SystemExit('awardPartCoins update block not found')
s = s.replace(old, new, 1)

if 'IAKIDS • build 0.7.9' not in s:
    raise SystemExit('build 0.7.9 stamp not found')
s = s.replace('IAKIDS • build 0.7.9', 'IAKIDS • build 0.8.0', 1)

p.write_text(s, encoding='utf-8')

out = p.read_text(encoding='utf-8')
for token in ['coin-reward-pop', '@keyframes coinRewardPop', 'pop.textContent = `+${Number(amount || 0)} 🪙`;', 'IAKIDS • build 0.8.0']:
    if token not in out:
        raise SystemExit(f'missing validation token: {token}')
print('v0.8.0 coin reward animation applied')
