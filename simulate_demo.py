"""Fill data.json with made-up results to preview the page mid-tournament -> demo_data.json"""
import copy, json, os, random, re

here = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(here, "data.json"), encoding="utf-8"))
rnd = random.Random(15)


def set_score(winner_first=True, deciding=False):
    target = 15 if deciding else 25
    lose = rnd.choice([target - 2 - rnd.randint(0, 9), target - 2]) if rnd.random() < .85 else None
    if lose is None:  # extra points
        w = target + rnd.randint(1, 4); return [w, w - 2]
    return [target, max(lose, 5)]


def play(n_sets, best_of):
    """returns sets from team A's perspective"""
    sets = []
    if best_of == 2:  # pool play: always 2 sets, can split
        for _ in range(2):
            s = set_score(); sets.append(s if rnd.random() < .5 else s[::-1])
        return sets[:n_sets]
    need = best_of // 2 + 1
    a = b = 0
    while a < need and b < need and len(sets) < n_sets:
        s = set_score(deciding=(len(sets) == best_of - 1))
        if rnd.random() < .55: sets.append(s); a += 1
        else: sets.append(s[::-1]); b += 1
    return sets


def finish_pool_match(m, best_of, n_sets=None):
    m["sets"] = play(n_sets or 9, best_of)
    if n_sets and n_sets < 2:
        m["status"] = "live"; m.pop("winner", None); return
    aw = sum(1 for x, y in m["sets"] if x > y); bw = len(m["sets"]) - aw
    m["status"] = "final"
    m["winner"] = m["a"] if aw > bw else m["b"] if bw > aw else None


def tally(p):
    for t in p["teams"]:
        t["w"] = t["l"] = t["diff"] = 0
    by = {t["team"]: t for t in p["teams"]}
    for m in p["matches"]:
        for x, y in m["sets"]:
            if m["a"] in by: by[m["a"]]["w" if x > y else "l"] += 1; by[m["a"]]["diff"] += x - y
            if m["b"] in by: by[m["b"]]["w" if y > x else "l"] += 1; by[m["b"]]["diff"] += y - x


def pool_done(p):
    tally(p)
    order = sorted(p["teams"], key=lambda t: (-t["w"], -t["diff"]))
    for s, t in zip(p["standings"], order):
        s["team"] = t["team"]


def run_pools(sheet, n_final, live_next=False, names=None):
    for p in sheet["pools"]:
        if p["name"].startswith("Iron") or (names and p["name"] not in names):
            continue
        for i, m in enumerate(p["matches"]):
            if i < n_final: finish_pool_match(m, p["bestOf"])
            elif i == n_final and live_next: finish_pool_match(m, p["bestOf"], 1)
        tally(p)
        if n_final >= len(p["matches"]):
            pool_done(p)


def norm(seed):
    return re.sub(r"\.0$", "", str(seed))


def all_slots(sheet):
    for b in sheet["brackets"]:
        for cl in b["clusters"]:
            for m in cl["matches"]:
                yield b, cl, m


def place(sheets, adv, team):
    """'Gold Ball Class 7A-2' / 'Division I-Class 8A #3' / 'Copper-8' / 'Iron Pool B-2' -> put team in that slot"""
    for sh in sheets:
        m = re.match(r"Iron Pool ([A-Z])-(\d)", adv)
        if m:
            for p in sh["pools"]:
                if p["name"] == f"Iron Pool {m[1]}":
                    for t in p["teams"]:
                        if t["seed"] == int(m[2]):
                            ph = f"Team {t['seed']}"; t["team"] = team
                            for mm in p["matches"]:
                                if mm["a"] == ph: mm["a"] = team
                                if mm["b"] == ph: mm["b"] = team
            continue
        m = re.match(r"(?:Gold Ball Class |Division [IV]+-Class )(\d+A)[ -]#?(\d+)", adv)
        tab, seed = ("Gold Ball", f"{m[1]} #{m[2]}") if m else (None, None)
        m2 = re.match(r"(Copper|Bronze|Silver)-(\d+)", adv)
        if m2: tab, seed = m2[1], m2[2]
        if not tab: continue
        for b, cl, mm in all_slots(sh):
            if tab in b["tab"]:
                for k in ("top", "bottom"):
                    if norm(mm[k]["seed"]) == seed and not mm[k]["team"]:
                        mm[k]["team"] = team; return


def play_bracket(m, n_sets=None):
    sets = play(n_sets or 9, m["bestOf"])
    aw = sum(1 for x, y in sets if x > y); bw = len(sets) - aw
    need = m["bestOf"] // 2 + 1
    if max(aw, bw) < need:
        m["status"] = "live"; m["sets"] = sets; return None
    top_won = aw > bw
    w, l = (m["top"], m["bottom"]) if top_won else (m["bottom"], m["top"])
    ws = sets if top_won else [s[::-1] for s in sets]  # winner's points first, like the sheets
    w["score"] = ", ".join(f"{x}-{y}" for x, y in ws)
    m["sets"], m["winner"], m["loser"], m["status"] = ws, w["team"], l["team"], "final"
    return w["team"], l["team"]


def feeders_fill(cl):
    """winners of round-1 pairs (by row) move into the next column's slots"""
    cols = sorted({m["col"] for m in cl["matches"]})
    for c0, c1 in zip(cols, cols[1:]):
        prev = sorted([m for m in cl["matches"] if m["col"] == c0], key=lambda m: m["row"])
        nxt = sorted([m for m in cl["matches"] if m["col"] == c1], key=lambda m: m["row"])
        for i, m in enumerate(nxt):
            for k, src in zip(("top", "bottom"), prev[2 * i:2 * i + 2]):
                if src.get("winner") and not m[k]["team"]:
                    m[k]["team"] = src["winner"]


S = {s["label"].strip(): s for s in D["sheets"]}

# --- G14u Division 1: pools done, Gold Ball quarters done, semis in progress ---
g14 = S["G14u Division 1"]
run_pools(g14, 99)
for p in g14["pools"]:
    for s in p["standings"]:
        if s["team"]: place([g14], s["adv"], s["team"])
for b, cl, m in list(all_slots(g14)):
    if b["tab"].endswith("Gold Ball Brackets") and m["round"] == 0 and m["top"]["team"] and m["bottom"]["team"]:
        w, l = play_bracket(m)
        if m.get("loserTo"): place([g14], m["loserTo"], l)
for b in g14["brackets"]:
    if b["tab"].endswith("Gold Ball Brackets"):
        for cl in b["clusters"]:
            feeders_fill(cl)
            semis = sorted([m for m in cl["matches"] if m["round"] == 1], key=lambda m: m["row"])
            if semis: play_bracket(semis[0])
            if len(semis) > 1: play_bracket(semis[1], 1)
            feeders_fill(cl)
    if b["tab"].endswith("Copper"):
        q = [m for cl in b["clusters"] for m in cl["matches"] if m["top"]["team"] and m["bottom"]["team"]]
        for m in q[:2]: play_bracket(m)
for p in g14["pools"]:
    if p["name"].startswith("Iron"):
        for m in p["matches"][:2]:
            if not m["a"].startswith("Team"): finish_pool_match(m, p["bestOf"])
        for m in p["matches"][2:3]:
            if not m["a"].startswith("Team"): finish_pool_match(m, p["bestOf"], 1)
        tally(p)

# --- G16u pools: halfway, one match live per pool ---
run_pools(S["G16u Division 1 & 2: POOLS"], 3, live_next=True)
# --- G18u D1/D2 pools: just getting going ---
run_pools(S["G18u Division 1 & 2: POOLS"], 1, live_next=True)
# --- GJV: pools A-D finished ---
run_pools(S["GJV"], 99, names={"Pool A", "Pool B", "Pool C", "Pool D"})
for p in S["GJV"]["pools"]:
    for s in p["standings"]:
        if s["team"]: place([S["GJV"]], s["adv"], s["team"])

D["demo"] = True
json.dump(D, open(os.path.join(here, "demo_data.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("wrote demo_data.json")
