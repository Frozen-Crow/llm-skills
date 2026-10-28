#!/usr/bin/env python3
"""Audit Orca for stale agent terminals. Read-only: prints what to release or
close, and never releases or closes anything itself.

Sorts every live terminal into:
  release  - settled workers Orca still owes a release (safe to run now)
  recover  - releases that are pending or unknown (run Orca's recovery step)
  ask      - settled workers whose terminals Orca retained, and orphaned
             terminals (close only with the user's OK, or cleanup=auto)
  idle     - idle terminals no orchestration run owns: hand-off agents,
             setup shells, default tabs (list them; close only on request)
  keep     - active workers, user-taken-over live workers, external terminals

Usage: python3 stale_terminals.py [--run RUN_ID] [--idle-hours 6] [--json]
"""
import datetime
import json
import os
import shlex
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from workspace_map import resolve_orca  # noqa: E402

SETTLED = {"succeeded", "failed", "stopped"}


def call(orca, *args):
    r = subprocess.run(orca + list(args) + ["--json"], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(args)}: {(r.stderr or r.stdout).strip()[:300]}")
    return json.loads(r.stdout).get("result", {})


def list_runs(orca, only):
    if only:
        return [only]
    res = call(orca, "orchestration", "run-list")
    return [r["id"] for r in (res.get("runs", res) if isinstance(res, dict) else res)]


def list_workers(orca, run):
    rows, cursor = [], None
    while True:
        args = ["orchestration", "worker-list", "--run", run, "--limit", "100"]
        if cursor:
            args += ["--cursor", cursor]
        res = call(orca, *args)
        rows += res.get("workers", res.get("rows", []))
        page = res.get("page") or {}
        if not page.get("hasMore") or not page.get("nextCursor"):
            return rows
        cursor = page["nextCursor"]


def hours_since(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        seconds = value / 1000
    else:
        seconds = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    return round((time.time() - seconds) / 3600, 1)


def command(orca, argv):
    return shlex.join(orca + list(argv) + ["--json"])


def main():
    args = sys.argv[1:]
    as_json = "--json" in args
    only_run = args[args.index("--run") + 1] if "--run" in args else None
    idle_hours = float(args[args.index("--idle-hours") + 1]) if "--idle-hours" in args else 6.0

    orca = resolve_orca()
    if not orca:
        sys.exit("Orca CLI not found.")
    terminals = call(orca, "terminal", "list").get("terminals", [])
    live = {t["handle"]: t for t in terminals}

    out = {"release": [], "recover": [], "ask": [], "idle": [], "keep": []}
    owned = set()
    for run in list_runs(orca, only_run):
        for w in list_workers(orca, run):
            handle = w.get("agentTerminalHandle") or (w.get("resource") or {}).get("terminalHandle")
            if handle:
                owned.add(handle)
            state = w.get("terminalState")
            if state == "released":
                continue
            proj = w.get("projection") or {}
            nxt = proj.get("nextAction") or {}
            term = live.get(handle)
            row = {
                "run": run,
                "dispatch": w.get("dispatchId"),
                "workerState": w.get("workerState"),
                "terminalState": state,
                "retainedReason": (w.get("resource") or {}).get("retainedReason"),
                "attention": (proj.get("attention") or {}).get("categories") or [],
                "handle": handle,
                "worktree": (w.get("resource") or {}).get("worktreeId"),
                "idleHours": hours_since(term.get("lastOutputAt")) if term else None,
            }
            if state == "reclaimable" and nxt.get("kind") == "release":
                row["command"] = command(orca, nxt["argv"])
                out["release"].append(row)
            elif state in ("release_pending", "release_unknown"):
                argv = nxt.get("argv") or ["orchestration", "worker-show", "--dispatch", w.get("dispatchId")]
                row["command"] = command(orca, argv)
                out["recover"].append(row)
            elif (state == "retained" and w.get("workerState") in SETTLED
                    and row["retainedReason"] != "external_terminal" and term):
                row["command"] = command(orca, ["terminal", "close", "--terminal", handle])
                out["ask"].append(row)
            elif term or state == "active":
                out["keep"].append(row)

    for t in terminals:
        if t["handle"] in owned:
            continue
        idle = hours_since(t.get("lastOutputAt"))
        row = {"handle": t["handle"], "title": t.get("title"), "worktree": t.get("worktreePath"),
               "orphaned": bool(t.get("orphaned")), "idleHours": idle,
               "command": command(orca, ["terminal", "close", "--terminal", t["handle"]])}
        if row["orphaned"]:
            out["ask"].append(row)
        elif idle is not None and idle >= idle_hours:
            out["idle"].append(row)

    if as_json:
        print(json.dumps({"liveTerminals": len(terminals), **out}, indent=2))
        return
    print(f"{len(terminals)} live terminals")
    labels = {
        "release": "Release now (safe; Orca owes these releases)",
        "recover": "Recover (follow Orca's recovery command; never substitute terminal close)",
        "ask": "Ask before closing (settled workers Orca retained, and orphaned terminals)",
        "idle": f"Idle {idle_hours:g}h+ and not owned by a run (hand-offs, setup shells, tabs): close only on request",
        "keep": "Keep",
    }
    for key, label in labels.items():
        rows = out[key]
        print(f"\n{label}: {len(rows)}")
        if key == "keep":
            continue
        for r in rows:
            who = r.get("worktree") or ""
            detail = ", ".join(str(x) for x in (r.get("workerState"), r.get("retainedReason"),
                               "orphaned" if r.get("orphaned") else None,
                               f"idle {r['idleHours']}h" if r.get("idleHours") is not None else None) if x)
            print(f"  - {who} ({detail})\n      {r['command']}")


if __name__ == "__main__":
    main()
