"""Quality checks for the gifted familiarisation bank (backend-ai-tutor-he/data/checks/gifted.json).

Used by tools/prompt_gate.py (gifted_quality_checks). Each check answers one question a test publisher
asks before an item ships (research 2026-09-25, Haladyna et al. item-writing guidelines, Raven/CogAT
item design):

  key_spread      the correct answer is not concentrated on one letter in a section (<= 40 %)
  context_blind   the correct answer of a figural item cannot be found WITHOUT the question: it must not
                  be the one option that shares the most features with the others (a distractor built as
                  "the key with one feature changed" gives the key away)
  series / matrix every simple rule that fits the shapes shown must predict the same next shape, and that
                  shape must be the key (a second rule that fits = two defensible answers)
  shapenum        every simple formula that fits all the complete examples must give the key; a different
                  fitting formula whose result is one of the options = two defensible answers

Pure functions, no I/O; `check(bank)` returns a list of failure messages.
"""
from collections import Counter
from itertools import product

ATTRS = ("sides", "fill", "rotation", "dots")
FILL_ORDER = ["empty", "half", "full"]


# ------------------------------------------------------------------ helpers
def _num(v):
    if v == "circle":
        return 0          # a circle has no sides; rules on sides never mix circles and polygons in this bank
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _same(a, b, attr):
    if attr == "rotation":
        return _num(a) is not None and _num(b) is not None and (_num(a) - _num(b)) % 360 == 0
    return str(a) == str(b)


def _seq_predictions(vals, attr):
    """Every simple rule that fits the whole sequence -> its prediction for the next term."""
    preds = set()
    n = len(vals)
    # repeating cycle of period p (1 = constant)
    for p in (1, 2, 3):
        if n > p and all(_same(vals[i], vals[i - p], attr) for i in range(p, n)):
            preds.add(str(vals[n - p]) if attr != "rotation" else str(int(_num(vals[n - p]) % 360)))
    nums = [_num(v) for v in vals]
    if all(x is not None for x in nums) and attr != "fill" and "circle" not in map(str, vals):
        d = [nums[i + 1] - nums[i] for i in range(n - 1)]
        if d and all(x == d[0] for x in d) and d[0] != 0:                       # constant step
            nxt = nums[-1] + d[0]
            preds.add(str(int(nxt % 360)) if attr == "rotation" else str(int(nxt)))
        if n >= 3 and len(d) >= 2 and all(d[i + 1] - d[i] == d[1] - d[0] for i in range(len(d) - 1)) and d[1] != d[0]:
            nxt = nums[-1] + d[-1] + (d[1] - d[0])                                # growing step (+1, +2, +3)
            preds.add(str(int(nxt % 360)) if attr == "rotation" else str(int(nxt)))
    if attr == "fill" and all(v in FILL_ORDER for v in vals):
        idx = [FILL_ORDER.index(v) for v in vals]
        d = [idx[i + 1] - idx[i] for i in range(n - 1)]
        if d and all(x == d[0] for x in d) and d[0] != 0 and 0 <= idx[-1] + d[0] < 3:
            preds.add(FILL_ORDER[idx[-1] + d[0]])
    return preds


def _norm(v, attr):
    if attr == "rotation":
        return str(int(_num(v) % 360)) if _num(v) is not None else str(v)
    if attr in ("sides", "dots") and _num(v) is not None and str(v) != "circle":
        return str(int(_num(v)))
    return str(v)


# ------------------------------------------------------------------ checks
def key_spread(section):
    items = section.get("items") or []
    if len(items) < 4:
        return []
    c = Counter(it.get("answer") for it in items)
    letter, n = c.most_common(1)[0]
    if n / len(items) > 0.40:
        return [f"{section['id']}: the correct answer is option {'ABCD'[letter]} in {n} of {len(items)} items: a child who always "
                f"picks it scores without understanding (max 40 %)"]
    return []


def _tile(t):
    return "|".join(_norm((t or {}).get(a), a) for a in ATTRS) if t else "-"


def context_blind(it):
    opts = it.get("options") or []
    if not opts or not all(isinstance(o, dict) for o in opts):
        return []
    if all("patch" in o for o in opts):
        # a carpet patch: each of its cells is a feature (the tile drawn there)
        opts = [{f"cell{i}": _tile(t) for i, t in enumerate(sum(o["patch"], []))} for o in opts]
        return _blind(it, opts, list(opts[0].keys()))
    return _blind(it, opts, ATTRS)


def _blind(it, opts, attrs):
    typ = []
    for o in opts:
        t = 0
        for a in attrs:
            vals = [_norm(x.get(a), a) for x in opts]
            top = Counter(vals).most_common()
            mode, cnt = top[0]
            # only a feature with ONE most common value says "typical"; a 2-2 split (the 2x2 design) says nothing
            if cnt > 1 and (len(top) == 1 or top[1][1] < cnt) and _norm(o.get(a), a) == mode:
                t += 1
        typ.append(t)
    k = it.get("answer")
    if typ[k] == max(typ) and typ.count(max(typ)) == 1:
        return [f"{it['id']}: the correct shape is the only option that shares the most features with the others: it can be "
                f"picked without looking at the question (build the options as 2x2 on two features)"]
    return []


def series_rule(it):
    f = it.get("figure") or {}
    seq = f.get("series") or []
    if f.get("kind") != "series" or len(seq) < 3:
        return []
    key = it["options"][it["answer"]]
    bad = []
    for a in ATTRS:
        preds = _seq_predictions([s.get(a) for s in seq], a)
        if len(preds) > 1:
            bad.append(f"{it['id']}: the {a} of the shapes fits two rules that predict different next shapes {sorted(preds)}: two answers are defensible")
        elif preds and _norm(key.get(a), a) not in preds:
            bad.append(f"{it['id']}: by the {a} rule the next shape has {a}={preds.pop()}, but the key has {key.get(a)}")
    return bad


def matrix_rule(it):
    f = it.get("figure") or {}
    grid = f.get("grid") or []
    if f.get("kind") != "matrix" or len(grid) != 9 or grid[8] is not None:
        return []
    key = it["options"][it["answer"]]
    rows = [grid[0:3], grid[3:6], grid[6:9]]
    cols = [[grid[i], grid[i + 3], grid[i + 6]] for i in range(3)]
    bad = []
    for a in ATTRS:
        preds = set()
        # rule within each row (the same rule restarts in every row), checked on the two complete rows
        for p in _row_rules(rows, a):
            preds.add(p)
        for p in _row_rules(cols, a):
            preds.add(p)
        if len(preds) > 1:
            bad.append(f"{it['id']}: the {a} in the grid fits rules that give different missing shapes {sorted(preds)}: two answers are defensible")
        elif preds and _norm(key.get(a), a) not in preds:
            bad.append(f"{it['id']}: by the {a} rule the missing shape has {a}={preds.pop()}, but the key has {key.get(a)}")
    return bad


def carpet_rule(it):
    """A carpet repeats: a tile equals the tile one shift (dr, dc) away. Every shift that the complete tiles
    obey (on at least 3 pairs) predicts the hole; all predictions must agree and give the key's patch."""
    f = it.get("figure") or {}
    if f.get("kind") != "carpet":
        return []
    tiles, h = f.get("tiles") or [], f.get("hole") or {}
    R, C = len(tiles), len(tiles[0]) if tiles else 0
    known = {(r, c): _tile(tiles[r][c]) for r in range(R) for c in range(C) if tiles[r][c]}
    hole = [(h["r"] + i, h["c"] + j) for i in range(h.get("h", 2)) for j in range(h.get("w", 2))]
    shifts = []
    for dr in range(-3, 4):
        for dc in range(-3, 4):
            if (dr, dc) == (0, 0):
                continue
            pairs = [(k, (k[0] + dr, k[1] + dc)) for k in known if (k[0] + dr, k[1] + dc) in known]
            if len(pairs) >= 3 and all(known[a] == known[b] for a, b in pairs):
                shifts.append((dr, dc))
    bad, pred = [], {}
    for cell in hole:
        vals = set()
        for dr, dc in shifts:
            for sgn in (1, -1):
                src = (cell[0] + sgn * dr, cell[1] + sgn * dc)
                if src in known:
                    vals.add(known[src])
        if len(vals) > 1:
            bad.append(f"{it['id']}: the carpet repeats in ways that fill cell {cell} differently: two answers are defensible")
        elif not vals:
            bad.append(f"{it['id']}: nothing in the carpet decides cell {cell}: the child cannot find the missing piece")
        else:
            pred[cell] = vals.pop()
    if not bad:
        key = sum(it["options"][it["answer"]]["patch"], [])
        want = [pred[c] for c in hole]
        if [_tile(t) for t in key] != want:
            bad.append(f"{it['id']}: the carpet's pattern gives a different patch than the key")
        others = [i for i, o in enumerate(it["options"]) if i != it["answer"] and [_tile(t) for t in sum(o["patch"], [])] == want]
        if others:
            bad.append(f"{it['id']}: option {others[0]} is also the missing patch: two correct answers")
    return bad


def _row_rules(lines, a):
    """Predictions for the last cell of the third line from rules that fit the two complete lines."""
    full = [[_norm(s.get(a), a) for s in line] for line in lines[:2]]
    last = [_norm(s.get(a), a) for s in lines[2][:2]]
    out = set()
    # constant along the line
    if all(len(set(l)) == 1 for l in full):
        out.add(last[0])
    # the same set of values in every line (each value once per line)
    if all(sorted(l) == sorted(full[0]) for l in full) and len(set(full[0])) == 3:
        rest = [v for v in full[0] if v not in last]
        if len(rest) == 1:
            out.add(rest[0])
    # constant step along the line, the same step in every line
    nums = [[_num(x) for x in l] for l in full]
    if a != "fill" and all(None not in l for l in nums) and _num(last[0]) is not None and _num(last[1]) is not None:
        steps = {l[1] - l[0] for l in nums} | {l[2] - l[1] for l in nums}
        if len(steps) == 1 and 0 not in steps:
            nxt = _num(last[1]) + steps.pop()
            out.add(str(int(nxt % 360)) if a == "rotation" else str(int(nxt)))
    return out


# formulas per number-shape layout: name -> function(inputs) ; inputs per example follow the layout's cells
_F2 = {"a+b": lambda a, b: a + b, "a*b": lambda a, b: a * b, "|a-b|": lambda a, b: abs(a - b),
       "a*b-1": lambda a, b: a * b - 1, "a*b+1": lambda a, b: a * b + 1, "a+b+1": lambda a, b: a + b + 1,
       "2a+b": lambda a, b: 2 * a + b, "a+2b": lambda a, b: a + 2 * b, "a*b-a": lambda a, b: a * b - a}


def _machine_fits(pairs):
    """x -> m*x + k fitted on two examples (the only simple rules a grade 2-3 child is asked to find)."""
    fits = set()
    for m in (1, 2, 3, 4, 5):
        ks = {y - m * x for x, y in pairs}
        if len(ks) == 1:
            fits.add((m, ks.pop()))
    return fits


def shapenum_rule(it):
    f = it.get("figure") or {}
    lay, cells, opts = f.get("layout"), f.get("cells") or [], it.get("options") or []
    key = opts[it["answer"]] if opts else None
    preds = set()
    if lay in ("circle3", "tree"):
        # circle3: [top, bottom_right, bottom_left]; tree: [root, right_leaf, left_leaf]; top = F(two others)
        full = [c for c in cells if None not in c]
        miss = [c for c in cells if None in c]
        if not miss:
            return []
        m = miss[0]
        for name, fn in _F2.items():
            if all(fn(c[1], c[2]) == c[0] or fn(c[2], c[1]) == c[0] for c in full):
                if m[0] is None:
                    preds.add(fn(m[1], m[2])) if fn(full[0][1], full[0][2]) == full[0][0] else preds.add(fn(m[2], m[1]))
                else:  # a leaf is missing: solve F(x, known) = top by trying small values
                    known = m[1] if m[2] is None else m[2]
                    for x in range(0, 200):
                        if fn(known, x) == m[0] or fn(x, known) == m[0]:
                            preds.add(x); break
        # the missing top may come from one of the others alone (top = m*leaf + k)
        if m[0] is None:
            for leaf in (1, 2):
                for mul, add in _machine_fits([(c[leaf], c[0]) for c in full]):
                    preds.add(mul * m[leaf] + add)
        # tree: each leaf may also come from the root (leaf = m*root + k, fitted on the complete trees)
        if lay == "tree":
            for leaf in (1, 2):
                if m[leaf] is None and m[0] is not None:
                    for mul, add in _machine_fits([(c[0], c[leaf]) for c in full]):
                        preds.add(mul * m[0] + add)
                    other = 2 if leaf == 1 else 1        # or from the root and the other leaf
                    for name, fn in _F2.items():
                        if all(fn(c[0], c[other]) == c[leaf] for c in full) and m[other] is not None:
                            preds.add(fn(m[0], m[other]))
    elif lay == "pyramid":
        # every brick = F(the two below it); rows from the bottom
        for name, fn in _F2.items():
            ok, holes = True, []
            for k in range(1, len(cells)):
                for j, v in enumerate(cells[k]):
                    a, b = cells[k - 1][j], cells[k - 1][j + 1]
                    if None in (a, b, v):
                        continue
                    if fn(a, b) != v:
                        ok = False
            if not ok:
                continue
            # solve the hole
            for k, row in enumerate(cells):
                for j, v in enumerate(row):
                    if v is not None:
                        continue
                    if k > 0 and None not in (cells[k - 1][j], cells[k - 1][j + 1]):
                        preds.add(fn(cells[k - 1][j], cells[k - 1][j + 1]))
                    else:  # a lower brick is missing: find x with F(neighbours) = brick above
                        for x in range(0, 300):
                            trial = [r[:] for r in cells]
                            trial[k][j] = x
                            good = True
                            for kk in range(1, len(trial)):
                                for jj, vv in enumerate(trial[kk]):
                                    a, b = trial[kk - 1][jj], trial[kk - 1][jj + 1]
                                    if None in (a, b, vv):
                                        continue
                                    if fn(a, b) != vv:
                                        good = False
                            if good:
                                preds.add(x); break
    elif lay == "machine":
        full = [c for c in cells if None not in c]
        miss = [c for c in cells if None in c]
        if not miss:
            return []
        for m_, k_ in _machine_fits(full):
            x, y = miss[0]
            if y is None:
                preds.add(m_ * x + k_)
            elif (y - k_) % m_ == 0:
                preds.add((y - k_) // m_)
    elif lay == "arrows":
        arrows = f.get("arrows") or []
        # each arrow adds the same w: box[i+1] = box[i] + arrows[i]*w ; w fitted on complete steps
        ws = set()
        for i in range(len(cells) - 1):
            a, b = cells[i], cells[i + 1]
            if None not in (a, b) and arrows[i]:
                if (b - a) % arrows[i] == 0:
                    ws.add((b - a) // arrows[i])
                else:
                    ws.add(None)
        if len(ws) == 1 and None not in ws:
            w = ws.pop()
            for i, v in enumerate(cells):
                if v is None:
                    preds.add(cells[i - 1] + arrows[i - 1] * w if i > 0 else cells[i + 1] - arrows[i] * w)
    else:
        return []
    bad = []
    in_opts = {p for p in preds if p in opts}
    if key not in preds:
        bad.append(f"{it['id']}: no simple rule that fits the complete shapes gives the key {key} (found {sorted(preds)[:4]}): the item may be wrong")
    if len(in_opts) > 1:
        bad.append(f"{it['id']}: two rules fit the complete shapes and give different options {sorted(in_opts)}: two answers are defensible")
    return bad


def check(bank: dict) -> list:
    bad = []
    for sec in bank.get("sections") or []:
        bad += key_spread(sec)
        for it in sec.get("items") or []:
            bad += context_blind(it)
            if sec["id"] == "nextshape":
                bad += series_rule(it) + matrix_rule(it) + carpet_rule(it)
            if sec["id"] == "shapenum":
                bad += shapenum_rule(it)
    return bad
