from pathlib import Path

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

start = s.find('async function awardPartCoins(amount = 10){')
end_marker = '\n\n/* =====================================================\n   LESSON RENDERER V1'
end = s.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit('awardPartCoins function not found')

old = s[start:end]
new = '''async function awardPartCoins(amount = 10){
  const kidId = CURRENT_KID?.id || localStorage.getItem("active_kid_id");
  const unitLessonId = Number(window.CURRENT_UNIT_LESSON_ID || window.CURRENT_LESSON_ID || CURRENT_LESSON?.id || 0);
  const partNumber = Number(window.CURRENT_LESSON_VISUAL_PART || window.CURRENT_LESSON_PART_NUMBER || 1);
  if(!kidId || !unitLessonId || !partNumber) return;

  const { data, error } = await sb.rpc("claim_part_coin_reward", {
    p_kid_id: kidId,
    p_unit_lesson_id: unitLessonId,
    p_part_number: partNumber,
    p_amount: Number(amount || 10)
  });

  if(error){
    console.error("COIN REWARD CLAIM ERROR:", error);
    return;
  }

  const result = Array.isArray(data) ? data[0] : data;
  const nextCoins = Number(result?.coins ?? CURRENT_KID?.coins ?? 0);
  const awarded = result?.awarded === true;

  if(CURRENT_KID) CURRENT_KID.coins = nextCoins;
  const coinsEl = document.getElementById("kidCoinsValue");
  if(coinsEl){
    coinsEl.textContent = nextCoins.toLocaleString("he-IL");
    if(awarded){
      const pill = coinsEl.closest(".stat-pill");
      if(pill){
        pill.querySelectorAll(".coin-reward-pop").forEach(el => el.remove());
        const pop = document.createElement("span");
        pop.className = "coin-reward-pop";
        pop.textContent = `+${Number(amount || 0)} 🪙`;
        pill.appendChild(pop);
        window.setTimeout(() => pop.remove(), 1300);
      }
    }
  }
  console.log("🪙 PART REWARD CLAIM:", { awarded, unitLessonId, partNumber, coins: nextCoins });
}'''

s = s[:start] + new + s[end:]
if 'IAKIDS • build 0.8.0' not in s:
    raise SystemExit('build 0.8.0 stamp not found')
s = s.replace('IAKIDS • build 0.8.0', 'IAKIDS • build 0.8.1', 1)
p.write_text(s, encoding='utf-8')
out = p.read_text(encoding='utf-8')
for token in ['claim_part_coin_reward', 'if(awarded){', 'IAKIDS • build 0.8.1']:
    if token not in out:
        raise SystemExit('validation failed: ' + token)
print('v0.8.1 idempotent part coin rewards applied')
