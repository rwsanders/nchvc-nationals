"""Rewind a completed tournament (data_2025.json) to moments on Thu/Fri/Sat -> test-site/snap-*.html

Used to test the viewer as parents would see it mid-tournament, with real scores.
Approximation: pool matches after the first are "rolling", so their start is estimated at 50 minutes apiece.
"""
import copy, json, os, re

here = os.path.dirname(os.path.abspath(__file__))
SRC = json.load(open(os.path.join(here, "data_2025.json"), encoding="utf-8"))
TPL = open(os.path.join(here, "page_template.html"), encoding="utf-8").read()
OUT = os.path.join(here, "test-site")
DAY = {"Thursday": 0, "Friday": 1, "Saturday": 2, "THU": 0, "FRI": 1, "SAT": 2}
SNAPS = [  # id, label, day, minutes after midnight
    ("thu-1000", "Thursday 10:00 AM", 0, 10 * 60),
    ("thu-1530", "Thursday 3:30 PM", 0, 15 * 60 + 30),
    ("fri-1800", "Friday 6:00 PM", 1, 18 * 60),
    ("sat-1400", "Saturday 2:00 PM", 2, 14 * 60),
    ("final", "Saturday night (all finished)", 3, 0),
]


def clock(t):
    m = re.search(r"(\d{1,2}):(\d{2})\s*(AM|PM)?", t or "", re.I)
    if not m:
        return None
    return int(m[1]) % 12 * 60 + int(m[2]) + (720 if (m[3] or "").upper() == "PM" else 0)


def tally(p):
    by = {t["team"]: t for t in p["teams"]}
    for t in p["teams"]:
        t["w"] = t["l"] = t["diff"] = 0
    for m in p["matches"]:
        for x, y in m["sets"]:
            if m["a"] in by: by[m["a"]]["w" if x > y else "l"] += 1; by[m["a"]]["diff"] += x - y
            if m["b"] in by: by[m["b"]]["w" if y > x else "l"] += 1; by[m["b"]]["diff"] += y - x


def rewind(data, cut_day, cut_min):
    cut = cut_day * 1440 + cut_min
    d = copy.deepcopy(data)
    events = []  # (start, end, age, kind, obj, pool)
    for s in d["sheets"]:
        for p in s["pools"]:
            start = None
            for i, m in enumerate(p["matches"]):
                dm = re.match(r"(THU|FRI|SAT)\s+", m["time"] or "", re.I)
                day = DAY[dm[1].upper()] if dm else (1 if p["name"].startswith("Iron") else 0)
                c = clock(m["time"])
                if c is not None:
                    start = day * 1440 + c
                elif start is not None:
                    start += 50
                st = start if start is not None else day * 1440 + 8 * 60 + 50 * i
                events.append((st, st + 50, s["age"], "pool", m, p))
        for b in s["brackets"]:
            for cl in b["clusters"]:
                for m in cl["matches"]:
                    c = clock(m["time"])
                    st = DAY.get(m["day"], 1) * 1440 + (c if c is not None else 12 * 60)
                    events.append((st, st + (90 if m["bestOf"] == 5 else 60), s["age"], "bracket", m, b))
    for st, en, age, kind, m, _ in events:
        if en <= cut:
            continue
        live = st <= cut
        if kind == "pool":
            m["sets"] = m["sets"][:1] if live else []
            m["status"] = "live" if live and m["sets"] else "upcoming"
            m.pop("winner", None)
        else:
            m["sets"] = m["sets"][:1] if live else []
            m["status"] = "live" if live and m["sets"] else "upcoming"
            m["winner"] = None
            m["loser"] = ""
            m["top"]["score"] = m["bottom"]["score"] = ""
    # a bracket spot is only known once every earlier match in that age group is final
    for st, en, age, kind, m, _ in events:
        if kind == "bracket" and m["status"] == "upcoming":
            earlier = [e for e in events if e[2] == age and e[0] < st]
            if any(e[4]["status"] != "final" for e in earlier):
                m["top"]["team"] = m["bottom"]["team"] = ""
    for s in d["sheets"]:
        for p in s["pools"]:
            tally(p)
            if any(m["status"] != "final" for m in p["matches"]):
                for row in p["standings"]:
                    row["team"] = ""
        for b in s["brackets"]:
            done = all(m["status"] == "final" for cl in b["clusters"] for m in cl["matches"])
            for r in b["results"]:
                for row in r["rows"]:
                    if not done:
                        row["team"] = ""
    return d


def page(data, label):
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", r"<\/")
    banner = ('<div style="background:var(--live);color:var(--surface);text-align:center;padding:8px 16px;font-weight:700">'
              f'TEST SNAPSHOT: last year’s real results, shown as they stood {label}</div>')
    body = TPL.replace("__DATA__", blob).replace("<!--BANNER-->", banner)
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '<style>[hidden]{display:none!important} body{margin:0}</style>\n</head>\n<body>\n' + body + '\n</body>\n</html>\n')


os.makedirs(OUT, exist_ok=True)
links = []
for sid, label, day, mins in SNAPS:
    d = rewind(SRC, day, mins) if day < 3 else copy.deepcopy(SRC)
    n = sum(1 for s in d["sheets"] for p in s["pools"] for m in p["matches"] if m["status"] == "final") + \
        sum(1 for s in d["sheets"] for b in s["brackets"] for c in b["clusters"] for m in c["matches"] if m["status"] == "final")
    live = sum(1 for s in d["sheets"] for p in s["pools"] for m in p["matches"] if m["status"] == "live") + \
        sum(1 for s in d["sheets"] for b in s["brackets"] for c in b["clusters"] for m in c["matches"] if m["status"] == "live")
    open(os.path.join(OUT, f"snap-{sid}.html"), "w", encoding="utf-8").write(page(d, label))
    links.append(f'<li><a href="snap-{sid}.html">{label}</a> ({n} final, {live} in progress)</li>')
    print(f"snap-{sid}.html  {label:<32} final={n:4} live={live:3}")
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(
    "<!doctype html><meta charset=utf-8><title>Test snapshots</title><h1>Test snapshots (2025 data)</h1><ul>"
    + "".join(links) + "</ul>")
