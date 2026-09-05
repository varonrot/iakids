from pathlib import Path

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

old_stats = '''    <div class="topbar-stats">\n\n      <div class="stat-pill">\n        <span class="stat-icon">⭐</span>\n        <span class="stat-value">890</span>\n      </div>\n\n      <div class="stat-pill">\n        <span class="stat-icon">💎</span>\n        <span class="stat-value">45</span>'''
new_stats = '''    <div class="topbar-stats">\n\n      <div class="stat-pill">\n        <span class="stat-icon">🪙</span>\n        <span class="stat-value" id="kidCoinsValue">0</span>\n      </div>\n\n      <div class="stat-pill">\n        <span class="stat-icon">💎</span>\n        <span class="stat-value" id="kidDiamondsValue">0</span>'''
if old_stats not in s:
    raise SystemExit('topbar stats block not found')
s = s.replace(old_stats, new_stats, 1)

old_select = '''    id,\n    child_name,\n    age,\n    avatar_key,'''
new_select = '''    id,\n    child_name,\n    age,\n    avatar_key,\n    coins,\n    diamonds,'''
if old_select not in s:
    raise SystemExit('kid profile select block not found')
s = s.replace(old_select, new_select, 1)

old_current = '''CURRENT_KID = kid;\n\n/* הערך שנשמר בפרופיל הוא כבר הכיתה: 1-6 */'''
new_current = '''CURRENT_KID = kid;\n\nconst coinsEl = document.getElementById("kidCoinsValue");\nconst diamondsEl = document.getElementById("kidDiamondsValue");\nif (coinsEl) coinsEl.textContent = Number(kid.coins ?? 0).toLocaleString("he-IL");\nif (diamondsEl) diamondsEl.textContent = Number(kid.diamonds ?? 0).toLocaleString("he-IL");\n\n/* הערך שנשמר בפרופיל הוא כבר הכיתה: 1-6 */'''
if old_current not in s:
    raise SystemExit('CURRENT_KID assignment block not found')
s = s.replace(old_current, new_current, 1)

if 'IAKIDS • build 0.7.7' not in s:
    raise SystemExit('build 0.7.7 stamp not found')
s = s.replace('IAKIDS • build 0.7.7', 'IAKIDS • build 0.7.8', 1)

p.write_text(s, encoding='utf-8')

# validations
out = p.read_text(encoding='utf-8')
for required in ['id="kidCoinsValue"', 'id="kidDiamondsValue"', 'coins,', 'diamonds,', 'IAKIDS • build 0.7.8']:
    if required not in out:
        raise SystemExit(f'missing validation token: {required}')
print('v0.7.8 currency counters patch applied')
