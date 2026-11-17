#!/usr/bin/env python3
"""Check, and fix, whether each agent trusts the folders it will work in.

An agent that doesn't trust its folder stops at a trust prompt, and Orca still
reports the worker as live. Gemini also silently downgrades --yolo to asking
before every shell command for the whole session, because it settles its
approval mode at startup. Orca pre-trusts each new workspace for Claude, Codex,
Cursor, Antigravity, Copilot and Qoder; it doesn't for Gemini, so this script
covers Gemini by adding folder rules that also trust every subfolder.

Usage:
  agent_trust.py check [--workspace PATH] [--paths A,B] [--agents a,b] [--json]
  agent_trust.py fix   [--workspace PATH] [--paths A,B]

Default paths are the product's workspace root (from --workspace, else the
current directory) and the folder Orca creates worktrees in. `fix` only writes
Gemini's trusted-folders file, backs it up first, and never removes a rule.
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
from workspace_map import find_root, resolve_orca  # noqa: E402
from scoreboard import roster  # noqa: E402

ORCA_PRETRUSTED = {"claude", "codex", "cursor", "antigravity", "copilot", "qoder"}
CASE_INSENSITIVE = sys.platform in ("darwin", "win32")


def norm(path):
    p = os.path.realpath(os.path.expanduser(path))
    return p.lower() if CASE_INSENSITIVE else p


def is_subpath(parent, child):
    return child == parent or child.startswith(parent.rstrip(os.sep) + os.sep)


def gemini_home():
    return os.environ.get("GEMINI_CLI_HOME") or os.path.expanduser("~")


def gemini_trust_file():
    return os.environ.get("GEMINI_CLI_TRUSTED_FOLDERS_PATH") or os.path.join(gemini_home(), ".gemini", "trustedFolders.json")


def gemini_folder_trust_enabled():
    try:
        with open(os.path.join(gemini_home(), ".gemini", "settings.json")) as f:
            settings = json.load(f)
    except (OSError, ValueError):
        return True
    return ((settings.get("security") or {}).get("folderTrust") or {}).get("enabled", True) is not False


def load_gemini_rules():
    try:
        with open(gemini_trust_file()) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def gemini_verdict(path, rules):
    """Same rule as Gemini's isPathTrusted: the longest matching rule wins;
    TRUST_FOLDER covers the folder and everything under it, TRUST_PARENT covers
    the rule's parent folder, DO_NOT_TRUST blocks."""
    loc = norm(path)
    best = None
    for rule, level in rules.items():
        effective = os.path.dirname(rule) if level == "TRUST_PARENT" else rule
        if is_subpath(norm(effective), loc) and (best is None or len(rule) > len(best[0])):
            best = (rule, level)
    if best is None:
        return False, "no rule covers it"
    if best[1] == "DO_NOT_TRUST":
        return False, f"blocked by DO_NOT_TRUST {best[0]}"
    return True, f"{best[1]} {best[0]}"


def orca_worktree_root():
    orca = resolve_orca()
    if orca:
        try:
            r = subprocess.run(orca + ["worktree", "list", "--json"], capture_output=True, text=True, timeout=30)
            res = json.loads(r.stdout).get("result") or {}
            worktrees = res.get("worktrees", res) if isinstance(res, dict) else res
            roots = collections.Counter(
                os.path.dirname(os.path.dirname(w["path"]))
                for w in worktrees if not w.get("isMainWorktree") and w.get("path"))
            if roots:
                return roots.most_common(1)[0][0]
        except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
            pass
    fallback = os.path.expanduser("~/orca/workspaces")
    return fallback if os.path.isdir(fallback) else None


def target_paths(args):
    if args.paths:
        return [os.path.abspath(os.path.expanduser(p.strip())) for p in args.paths.split(",") if p.strip()]
    root, _ = find_root(args.workspace or os.getcwd())
    paths = [root]
    wt = orca_worktree_root()
    if wt and not is_subpath(norm(root), norm(wt)):
        paths.append(wt)
    return paths


def check(args):
    paths = target_paths(args)
    agents, source = roster(args.agents)
    rules = load_gemini_rules()
    enabled = gemini_folder_trust_enabled()
    report = []
    for agent in agents:
        for path in paths:
            if agent == "gemini":
                if not enabled:
                    ok, why = True, "folder trust is turned off in Gemini settings"
                else:
                    ok, why = gemini_verdict(path, rules)
                    if not ok:
                        why += "; Gemini will prompt for trust and drop --yolo to asking before every command"
            elif agent in ORCA_PRETRUSTED:
                ok, why = True, "Orca trusts each new workspace for this agent before launch"
            elif agent == "grok":
                ok, why = True, "no blocking prompt; an untrusted folder only skips project-level Grok config"
            else:
                ok, why = None, "unknown; watch for a trust prompt on first launch"
            report.append({"agent": agent, "path": path, "trusted": ok, "why": why})
    missing = [r for r in report if r["trusted"] is False]
    if args.json:
        print(json.dumps({"roster": agents, "rosterSource": source, "paths": paths,
                          "geminiTrustFile": gemini_trust_file(), "results": report,
                          "needsFix": bool(missing)}, indent=2))
        return
    print(f"Roster ({source}): {', '.join(agents)}")
    for r in report:
        mark = {True: "ok     ", False: "UNTRUSTED", None: "?      "}[r["trusted"]]
        print(f"  {mark} {r['agent']:<12} {r['path']}  ({r['why']})")
    if missing:
        print("\nRun `agent_trust.py fix` with the same arguments to add the missing Gemini rules.")


def fix(args):
    paths = target_paths(args)
    if not gemini_folder_trust_enabled():
        print("Gemini folder trust is turned off, so there's nothing to add.")
        return
    rules = load_gemini_rules()
    added = []
    for path in paths:
        ok, _ = gemini_verdict(path, rules)
        if not ok:
            rules[norm(path)] = "TRUST_FOLDER"
            added.append(path)
    if not added:
        print("Gemini already trusts every path. Nothing changed.")
        return
    target = gemini_trust_file()
    os.makedirs(os.path.dirname(target), exist_ok=True)
    if os.path.exists(target):
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(target, f"{target}.bak-{stamp}")
    tmp = f"{target}.tmp-{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(rules, f, indent=2)
        f.write("\n")
    os.replace(tmp, target)
    for path in added:
        print(f"Gemini now trusts {path} and everything under it.")
    print(f"Updated {target} (backup saved next to it). Restart any Gemini session already running in these folders.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("check", "fix"):
        s = sub.add_parser(name)
        s.add_argument("--workspace", help="any path inside the product; its workspace root is checked")
        s.add_argument("--paths", help="comma-separated folders to check instead of the defaults")
        if name == "check":
            s.add_argument("--agents", help="comma-separated roster; default: saved or installed agents")
            s.add_argument("--json", action="store_true")
    args = p.parse_args()
    (check if args.cmd == "check" else fix)(args)


if __name__ == "__main__":
    main()
