#!/usr/bin/env python3
"""Map a product workspace for Orca orchestration. Read-only.

Finds the monogit workspace root (a .monogit.json at or above PATH), lists each
piece (linked repo), and reports whether Orca has every piece registered as its
own repo and in one project group. Flags the case Orca's folder scan misses: a
workspace root that is itself a git repo whose sub-repos are gitignored.

Usage: python3 workspace_map.py [PATH] [--json]
"""
import json
import os
import shlex
import shutil
import subprocess
import sys

MAC_APP_CLI = "/Applications/Orca.app/Contents/Resources/bin/orca"


def find_root(start):
    d = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(d, ".monogit.json")):
            return d, True
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    r = subprocess.run(["git", "-C", start, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if r.returncode == 0:
        return r.stdout.strip(), False
    return os.path.abspath(start), False


def monogit_pieces(root):
    with open(os.path.join(root, ".monogit.json")) as f:
        cfg = json.load(f)
    pieces = []
    for entry in cfg.get("repos", []):
        rel = entry if isinstance(entry, str) else entry.get("path") or entry.get("name")
        if rel:
            pieces.append(rel)
    return pieces, cfg.get("groups") or {}


def resolve_orca():
    env = os.environ.get("ORCA_CLI_COMMAND")
    if env:
        return shlex.split(env)
    if sys.platform.startswith("linux"):
        # Bare `orca` on Linux is usually the GNOME screen reader.
        found = shutil.which("orca-ide")
        return [found] if found else None
    found = shutil.which("orca")
    if found:
        return [found]
    if os.path.exists(MAC_APP_CLI):
        return [MAC_APP_CLI]
    return None


def orca_repos(orca):
    try:
        r = subprocess.run(orca + ["repo", "list", "--json"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e)
    if r.returncode != 0:
        return None, (r.stderr or r.stdout).strip()[:300]
    data = json.loads(r.stdout)
    result = data.get("result", data)
    repos = result.get("repos", []) if isinstance(result, dict) else result
    return {os.path.realpath(x["path"]): x for x in repos}, None


def main():
    args = [a for a in sys.argv[1:] if a != "--json"]
    as_json = "--json" in sys.argv
    root, is_monogit = find_root(args[0] if args else os.getcwd())
    parent_is_git = os.path.exists(os.path.join(root, ".git"))

    rel_pieces, monogit_groups = monogit_pieces(root) if is_monogit else ([], {})
    orca = resolve_orca()
    registered, orca_error = (orca_repos(orca) if orca else (None, "Orca CLI not found"))

    def orca_info(path):
        if registered is None:
            return None
        repo = registered.get(os.path.realpath(path))
        if not repo:
            return {"registered": False}
        return {
            "registered": True,
            "repoId": repo.get("id"),
            "displayName": repo.get("displayName"),
            "projectGroupId": repo.get("projectGroupId"),
        }

    pieces = []
    for rel in rel_pieces:
        path = os.path.join(root, rel)
        ignored = None
        if parent_is_git:
            ignored = subprocess.run(["git", "-C", root, "check-ignore", "-q", rel]).returncode == 0
        pieces.append({
            "name": os.path.basename(rel.rstrip("/")),
            "path": path,
            "exists": os.path.isdir(path),
            "isGitRepo": os.path.exists(os.path.join(path, ".git")),
            "ignoredByParent": ignored,
            "orca": orca_info(path),
        })

    problems, notes, next_steps = [], [], []
    if orca_error:
        problems.append(f"Orca not reachable: {orca_error}")
        next_steps.append("Start Orca (`orca open --json`), then run this again.")
    missing = [p for p in pieces if not p["exists"]]
    if missing:
        problems.append("Pieces missing locally: " + ", ".join(p["name"] for p in missing))
        next_steps.append("Clone them from the workspace root: `monogit clone`.")
    hidden_children = parent_is_git and any(p["ignoredByParent"] for p in pieces)
    if hidden_children:
        notes.append(
            "Workspace root is a git repo with gitignored sub-repos: a worktree of the root will not "
            "contain them, and Orca's folder scan will not group them. Place piece work only in each "
            "piece's own repo, never in a worktree of the root."
        )
    unregistered = [p for p in pieces if p["exists"] and p["orca"] and not p["orca"]["registered"]]
    for p in unregistered:
        next_steps.append(f"orca repo add --path {shlex.quote(p['path'])} --json")
    if unregistered:
        problems.append("Not registered in Orca: " + ", ".join(p["name"] for p in unregistered))

    root_orca = orca_info(root) if parent_is_git else None
    members = [p["orca"] for p in pieces if p["orca"] and p["orca"].get("registered")]
    if root_orca and root_orca.get("registered"):
        members.append(root_orca)
    groups = {m.get("projectGroupId") for m in members}
    grouped = bool(members) and len(groups) == 1 and None not in groups and not unregistered
    if pieces and registered is not None and not grouped:
        problems.append("Pieces are not all in one Orca project group.")
        next_steps.append(
            "Ask the developer to create one project group in Orca's sidebar for this product and move "
            "the workspace root (if registered) and every piece into it; the CLI cannot set groups."
        )

    report = {
        "root": root,
        "isMonogitWorkspace": is_monogit,
        "rootIsGitRepo": parent_is_git,
        "rootHidesSubRepos": hidden_children,
        "rootOrca": root_orca,
        "monogitGroups": monogit_groups,
        "pieces": pieces,
        "orcaGroupIds": sorted(g for g in groups if g),
        "ready": not problems,
        "problems": problems,
        "notes": notes,
        "nextSteps": next_steps,
    }
    if as_json:
        print(json.dumps(report, indent=2))
        return
    print(f"Workspace root: {root} ({'monogit' if is_monogit else 'single repo'}"
          f"{', root is a git repo' if parent_is_git and is_monogit else ''})")
    for p in pieces:
        o = p["orca"] or {}
        status = "not checked" if not p["orca"] else (
            f"orca repo {o.get('repoId')} group {o.get('projectGroupId')}" if o.get("registered") else "NOT in Orca")
        flag = " [gitignored by root]" if p["ignoredByParent"] else ""
        print(f"  - {p['name']}{flag}: {status}")
    for msg in notes:
        print(f"Note: {msg}")
    print("Ready for orchestration." if not problems else "Problems:")
    for msg in problems:
        print(f"  * {msg}")
    for step in next_steps:
        print(f"  -> {step}")


if __name__ == "__main__":
    main()
