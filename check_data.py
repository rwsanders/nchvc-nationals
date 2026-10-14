"""Refuse to deploy a scrape that looks broken compared with the data already live.

python check_data.py data.json prev_data.json
Exit code 1 keeps the last good site up (the workflow stops before deploying).
"""
import json, os, sys

new = json.load(open(sys.argv[1], encoding="utf-8"))
prev = json.load(open(sys.argv[2], encoding="utf-8")) if len(sys.argv) > 2 and os.path.exists(sys.argv[2]) else None


def counts(d):
    out = {}
    for s in d["sheets"]:
        pools = [p for p in s["pools"] if not p["name"].startswith("Iron")]
        out[s["label"]] = {
            "pool teams": sum(1 for p in pools for t in p["teams"] if t["team"]),
            "pool match times": sum(1 for p in s["pools"] for m in p["matches"] if m["time"]),
            "bracket matches": sum(len(c["matches"]) for b in s["brackets"] for c in b["clusters"]),
            "bracket times": sum(1 for b in s["brackets"] for c in b["clusters"] for m in c["matches"] if m["time"] and m["court"]),
        }
    return out


problems = []
c = counts(new)
teams = {(s["age"], t["team"]) for s in new["sheets"] for p in s["pools"] if not p["name"].startswith("Iron")
         for t in p["teams"] if t["team"]}
if len(new["sheets"]) < 10:
    problems.append(f"only {len(new['sheets'])} division sheets")
if len(teams) < 150:
    problems.append(f"only {len(teams)} teams")
if prev:
    p = counts(prev)
    for label, old in p.items():
        if label not in c:
            problems.append(f"sheet disappeared: {label}")
            continue
        for k, v in old.items():
            if v >= 5 and c[label][k] < 0.9 * v:
                problems.append(f"{label}: {k} dropped {v} -> {c[label][k]}")
print(f"{len(new['sheets'])} sheets, {len(teams)} teams" + (f", compared with live data from {prev['generated']}" if prev else ", no live data to compare"))
if problems:
    print("Not deploying, this scrape looks broken:\n  " + "\n  ".join(problems))
    sys.exit(1)
print("ok")
