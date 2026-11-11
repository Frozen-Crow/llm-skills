#!/usr/bin/env python3
"""Agent scoreboard: route work by evidence, not by which vendor the coordinator
comes from.

  suggest  pick a builder and a reviewer for every piece in a wave
  record   log one settled builder or reviewer result
  summary  show which agents do best at which task types

Results live one JSON object per line in ~/.frozencrow/agent-scoreboard.jsonl.
Set FROZENCROW_SCOREBOARD to a shared path to pool results across a team.
The roster comes from "agents" in ~/.frozencrow/orchestration.json, or from the
agent CLIs installed on this machine. Agents at 90%+ of an Orca rate limit are
skipped.

Usage:
  scoreboard.py suggest --pieces api=api,client=ui --self claude [--agents a,b] [--no-explore] [--no-review] [--json]
  scoreboard.py record --task-type api --agent codex --outcome succeeded [--role builder|reviewer]
                       [--model ID] [--retries N] [--blocking N] [--minor N] [--accepted N]
                       [--minutes N] [--piece NAME] [--run ID] [--dispatch ID] [--explore]
  scoreboard.py summary [--task-type api] [--json]
"""
import argparse
import collections
import datetime
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from workspace_map import resolve_orca  # noqa: E402

TASK_TYPES = ["api", "ui", "mobile", "shared", "wordpress", "bugfix", "tests", "refactor", "infra", "docs", "design"]
CLI_TO_AGENT = {"claude": "claude", "codex": "codex", "gemini": "gemini", "grok": "grok",
                "cursor-agent": "cursor", "antigravity": "antigravity", "opencode": "opencode", "kimi": "kimi"}
MIN_RUNS = 3          # fewer runs than this on a task type = not enough evidence yet
SELF_MARGIN = 0.05    # the coordinator's own agent must win by at least this much
MIX_MAX_GAP = 0.25    # keep a wave mixed only by swapping in an agent within this score gap
RATE_LIMIT_CEILING = 90


def board_path():
    return os.environ.get("FROZENCROW_SCOREBOARD") or os.path.expanduser("~/.frozencrow/agent-scoreboard.jsonl")


def load_prefs():
    try:
        with open(os.path.expanduser("~/.frozencrow/orchestration.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def load_rows():
    rows = []
    try:
        with open(board_path()) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        pass
    except OSError:
        pass
    return rows


def roster(explicit):
    if explicit:
        return [a.strip() for a in explicit.split(",") if a.strip()], "given"
    saved = (load_prefs().get("default") or {}).get("agents") or load_prefs().get("agents")
    if saved:
        return list(saved), "saved"
    return [agent for cli, agent in CLI_TO_AGENT.items() if shutil.which(cli)], "detected"


def rate_limited(agents):
    orca = resolve_orca()
    if not orca:
        return {}
    try:
        r = subprocess.run(orca + ["account", "list", "--json"], capture_output=True, text=True, timeout=30)
        limits = (json.loads(r.stdout).get("result") or {}).get("rateLimits") or {}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {}
    out = {}
    for agent in agents:
        windows = limits.get(agent)
        if not isinstance(windows, dict):
            continue
        for name in ("session", "weekly"):
            w = windows.get(name)
            if isinstance(w, dict) and (w.get("usedPercent") or 0) >= RATE_LIMIT_CEILING:
                out[agent] = f"{name} limit {w['usedPercent']}% used"
    return out


def quality(row):
    if row.get("role", "builder") == "reviewer":
        return min(1.0, (row.get("accepted") or 0) / 2)   # two accepted findings = a full point
    if row.get("outcome") != "succeeded":
        return 0.0
    if (row.get("blocking") or 0) or (row.get("retries") or 0):
        return 0.5
    return 1.0


def stats(rows, task_type, role):
    s = collections.defaultdict(lambda: {"runs": 0, "q": 0.0, "minutes": []})
    for r in rows:
        if r.get("taskType") != task_type or r.get("role", "builder") != role:
            continue
        e = s[r.get("agent")]
        e["runs"] += 1
        e["q"] += quality(r)
        if r.get("minutes"):
            e["minutes"].append(r["minutes"])
    return s


def score(e):
    return round((e["q"] + 1) / (e["runs"] + 2), 3)   # unknown agents start at 0.5


def pick(candidates, st, me, used, explore_ok):
    def runs(a):
        return st[a]["runs"] if a in st else 0

    def info(a, why, explore=False):
        e = st[a] if a in st else {"runs": 0, "q": 0.0, "minutes": []}
        return {"agent": a, "why": why, "score": score(e), "runs": e["runs"], "explore": explore}

    if not candidates:
        return None
    thin = [a for a in candidates if runs(a) < MIN_RUNS]
    if explore_ok and thin:
        thin.sort(key=lambda a: (runs(a), a == me, a in used, a))
        return info(thin[0], "trial: little evidence on this task type yet", True)

    def avg_minutes(a):
        m = st[a]["minutes"] if a in st else []
        return sum(m) / len(m) if m else 1e9

    ranked = sorted(candidates, key=lambda a: (-score(st[a]) if a in st else -0.5, a == me, a in used, avg_minutes(a), a))
    best = ranked[0]
    others = [a for a in ranked if a != me]
    if best == me and others:
        top_other = score(st[others[0]]) if others[0] in st else 0.5
        mine = score(st[me]) if me in st else 0.5
        if mine - top_other < SELF_MARGIN:
            return info(others[0], f"near-tie with the coordinator's own agent ({me}); ties go elsewhere")
    if runs(best) < MIN_RUNS:
        return info(best, "no clear leader yet; spreading work across agents")
    return info(best, "best score")


def cmd_suggest(args):
    rows = load_rows()
    agents, source = roster(args.agents)
    skipped = rate_limited(agents)
    available = [a for a in agents if a not in skipped]
    pieces = []
    for item in args.pieces.split(","):
        name, _, task_type = item.partition("=")
        task_type = task_type or name
        if task_type not in TASK_TYPES:
            sys.exit(f"Unknown task type '{task_type}'. Use one of: {', '.join(TASK_TYPES)}")
        pieces.append((name.strip(), task_type.strip()))

    used, explore_free, out = [], not args.no_explore, []
    for name, task_type in pieces:
        b = pick(available, stats(rows, task_type, "builder"), args.self, used, explore_free)
        if b and b["explore"]:
            explore_free = False                     # one trial slot per wave
        if b:
            used.append(b["agent"])
        out.append({"piece": name, "taskType": task_type, "builder": b})

    # Keep a wave of two or more pieces mixed, but never by swapping in an agent
    # the evidence says is clearly worse.
    notes = []
    if len(out) >= 2 and len({o["builder"]["agent"] for o in out if o["builder"]}) == 1 and len(available) >= 2:
        swap_best, swap_gap = None, None
        for o in out:
            st = stats(rows, o["taskType"], "builder")
            alt = pick([a for a in available if a != o["builder"]["agent"]], st, args.self, used, False)
            gap = o["builder"]["score"] - alt["score"]
            if swap_gap is None or gap < swap_gap:
                swap_best, swap_gap = (o, alt), gap
        o, alt = swap_best
        if swap_gap <= MIX_MAX_GAP or alt["runs"] < MIN_RUNS:
            alt["why"] = "keeps the wave mixed: " + alt["why"]
            o["builder"] = alt
        else:
            notes.append(f"{o['builder']['agent']} leads clearly on every piece, so this wave stays single-agent.")

    if not args.no_review:
        for o in out:
            if not o["builder"]:
                continue
            reviewers = [a for a in available if a != o["builder"]["agent"]]
            o["reviewer"] = pick(reviewers, stats(rows, o["taskType"], "reviewer"), args.self, [], True)

    result = {"roster": agents, "rosterSource": source, "skipped": skipped, "self": args.self,
              "scoreboard": board_path(), "assignments": out, "notes": notes}
    if args.json:
        print(json.dumps(result, indent=2))
        return
    print(f"Roster ({source}): {', '.join(agents) or 'none'}")
    for agent, why in skipped.items():
        print(f"  skipped {agent}: {why}")
    for note in notes:
        print(f"Note: {note}")
    for o in out:
        def fmt(p):
            if not p:
                return "none available"
            return f"{p['agent']}  [{p['why']}; score {p['score']}, {p['runs']} runs]"
        print(f"{o['piece']} ({o['taskType']})\n  builder:  {fmt(o['builder'])}")
        if "reviewer" in o:
            print(f"  reviewer: {fmt(o['reviewer'])}")


def cmd_record(args):
    if args.task_type not in TASK_TYPES:
        sys.exit(f"Unknown task type '{args.task_type}'. Use one of: {', '.join(TASK_TYPES)}")
    row = {
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "taskType": args.task_type, "role": args.role, "agent": args.agent, "model": args.model or "default",
        "outcome": args.outcome, "retries": args.retries, "blocking": args.blocking, "minor": args.minor,
        "accepted": args.accepted, "minutes": args.minutes, "piece": args.piece, "run": args.run,
        "dispatch": args.dispatch, "explore": args.explore,
    }
    path = board_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps({k: v for k, v in row.items() if v is not None}) + "\n")
    print(f"Recorded {args.role} {args.agent} on {args.task_type}: {args.outcome} -> {path}")


def cmd_summary(args):
    rows = load_rows()
    types = [args.task_type] if args.task_type else sorted({r.get("taskType") for r in rows if r.get("taskType")})
    report = {}
    for t in types:
        report[t] = {}
        for role in ("builder", "reviewer"):
            st = stats(rows, t, role)
            models = collections.defaultdict(set)
            for r in rows:
                if r.get("taskType") == t and r.get("role", "builder") == role:
                    models[r.get("agent")].add(r.get("model", "default"))
            report[t][role] = sorted(
                ({"agent": a, "score": score(e), "runs": e["runs"],
                  "avgMinutes": round(sum(e["minutes"]) / len(e["minutes"])) if e["minutes"] else None,
                  "models": sorted(models[a])} for a, e in st.items()),
                key=lambda x: -x["score"])
    if args.json:
        print(json.dumps({"scoreboard": board_path(), "taskTypes": report}, indent=2))
        return
    if not rows:
        print(f"No results yet in {board_path()}.")
        return
    for t, roles in report.items():
        print(f"\n{t}")
        for role, entries in roles.items():
            if not entries:
                continue
            thin = "" if entries[0]["runs"] >= MIN_RUNS else "  (thin evidence)"
            print(f"  {role}s:{thin}")
            for e in entries:
                mins = f", ~{e['avgMinutes']} min" if e["avgMinutes"] else ""
                print(f"    {e['agent']:<12} score {e['score']:.2f}  {e['runs']} runs{mins}  models: {', '.join(e['models'])}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("suggest")
    s.add_argument("--pieces", required=True, help="piece=taskType,... (task type defaults to the piece name)")
    s.add_argument("--self", required=True, help="the agent id the coordinator runs as")
    s.add_argument("--agents", help="comma-separated roster; default: saved or installed agents")
    s.add_argument("--no-explore", action="store_true")
    s.add_argument("--no-review", action="store_true")
    s.add_argument("--json", action="store_true")

    r = sub.add_parser("record")
    r.add_argument("--task-type", required=True)
    r.add_argument("--agent", required=True)
    r.add_argument("--outcome", required=True, choices=["succeeded", "failed"])
    r.add_argument("--role", default="builder", choices=["builder", "reviewer"])
    r.add_argument("--model")
    r.add_argument("--retries", type=int, default=0)
    r.add_argument("--blocking", type=int, default=0, help="blocking review findings against this builder")
    r.add_argument("--minor", type=int, default=0, help="minor review findings against this builder")
    r.add_argument("--accepted", type=int, help="reviewer: findings the builder accepted")
    r.add_argument("--minutes", type=int)
    r.add_argument("--piece")
    r.add_argument("--run")
    r.add_argument("--dispatch")
    r.add_argument("--explore", action="store_true", default=None)

    m = sub.add_parser("summary")
    m.add_argument("--task-type")
    m.add_argument("--json", action="store_true")

    args = p.parse_args()
    {"suggest": cmd_suggest, "record": cmd_record, "summary": cmd_summary}[args.cmd](args)


if __name__ == "__main__":
    main()
