# monogit: setup and command reference

Source: https://monogit.com · https://github.com/Frozen-Crow/monogit · npm `@frozencrow/monogit`

## Contents
1. Requirements
2. Install (walkthrough)
3. Create or join a workspace
4. Connect monogit to your editor (MCP)
5. Command reference
6. `.monogit.json` reference

---

## 1. Requirements

- **Node.js 18 or newer** (`node --version`). If missing, suggest installing it with their usual method (Homebrew `brew install node`, nvm, or nodejs.org).
- **git**
- **GitHub CLI `gh`**, signed in (`gh auth status`) — only for `monogit pr` and `monogit push --wait-ci`. Install with `brew install gh`, then `gh auth login`.

## 2. Install (walkthrough)

Walk the developer through these one at a time, confirming each before moving on.

**Step 1 — install globally**
```bash
npm i -g @frozencrow/monogit
```
Confirm with `monogit --help`. If `command not found`, their npm global bin isn't on PATH — check `npm prefix -g` and add `<prefix>/bin` to PATH.

**Step 2 — tab completion (optional, recommended)**
```bash
monogit completion install zsh     # or: bash, fish
```
PowerShell: add `monogit completion powershell | Out-String | Invoke-Expression` to `$PROFILE`. Open a new shell afterwards.

## 3. Create or join a workspace

A workspace is a parent folder holding several repos as siblings, with a `.monogit.json` at the top.

**Joining an existing workspace** (the usual case for a new teammate): clone the repo or folder that holds the committed `.monogit.json`, `cd` into it, then
```bash
monogit clone      # clones every linked repo that's missing locally
monogit status
```

**Creating a workspace** from a folder that already holds repos:
```bash
cd ~/path/to/parent-folder
monogit init       # scans up to --depth 3, lets you pick repos, asks a few questions
```
During `init`, recommend these answers for Frozen Crow:
- **Commit linking: yes** — sets `commit.link: true` so cross-repo commits share a Change-Id
- **Protected branches:** at least `main`, plus any long-lived branches like `develop` or `release/*`
- **Groups:** worth setting if repos naturally split (e.g. `backend`, `frontend`)

Then suggest committing `.monogit.json` wherever the team keeps it, so others can `monogit clone`.

Check it worked: `monogit status` should list every linked repo.

## 4. Connect monogit to your editor (MCP)

Add this server to the editor's MCP config:
```json
{
  "mcpServers": {
    "monogit": {
      "command": "monogit",
      "args": ["mcp"],
      "cwd": "/path/to/your/workspace"
    }
  }
}
```
No global install? Use `"command": "npx"`, `"args": ["-y", "@frozencrow/monogit", "mcp"]`.

Where the block goes:

- **Claude Code:** `.mcp.json` in the project
- **Cursor:** `.cursor/mcp.json`
- **Gemini CLI:** `.gemini/settings.json`
- **Windsurf, Cline:** their MCP settings file

These four all use the `mcpServers` shape above. The exceptions:

- **VS Code (Copilot)** uses a `servers` key in `.vscode/mcp.json`.
- **Codex** uses TOML (`[mcp_servers.monogit]` in `~/.codex/config.toml`).

MCP config formats change often, so if the shape doesn't load, the editor's own MCP docs win.

Tools it exposes: `monogit_status`, `monogit_list_repos`, `monogit_exec`, `monogit_commit`, `monogit_checkout`, `monogit_push`, `monogit_pull`, `monogit_show`, `monogit_tidy` (dry run unless `execute: true`), `monogit_pr`. All accept `only` / `except` / `group`.

## 5. Command reference

Every multi-repo command accepts `--only <repos>`, `--except <repos>`, `--group <groups>`, `-c/--concurrency <n>` (default 8). monogit finds the workspace from any subdirectory, like git.

| Command | What it does |
|---|---|
| `monogit status [--full] [--json]` | Dashboard: branch, ahead/behind, changes, in-progress rebase/merge |
| `monogit watch [--interval 10s]` | Live interactive dashboard with one-key actions |
| `monogit checkout <branch> [-b]` | Switch/create branch everywhere. `main`/`master` resolve to each repo's own trunk |
| `monogit add <paths...>` | Stage across repos |
| `monogit commit [-m msg] [-a] [-A] [--link/--no-link]` | Commit everywhere; omitting `-m` opens the editor once for all repos |
| `monogit show [change-id]` | Every commit sharing a Change-Id (latest if none given) |
| `monogit push / pull / fetch [remote] [branch]` | Sync; bare `push` does `push -u origin HEAD`. `push --wait-ci` waits for dependencies' CI |
| `monogit branch [name] [-d/-D]` | List, create or delete branches everywhere |
| `monogit merge <branch>` | Merge into current branch everywhere |
| `monogit tidy [--dry-run] [--stale N] [--yes]` | Clean up merged / gone branches (confirms first) |
| `monogit pr [--fill] [--title/--body] [--draft] [--base b] [--web]` | Open PRs via `gh` in every repo with new commits |
| `monogit exec -- <git args>` | Any git command across repos |
| `monogit run "<cmd>"` | Any shell command in each repo, live labelled output |
| `monogit clone` | Clone missing repos from `.monogit.json` |
| `monogit repos list / add <path> / remove <name>` | Manage linked repos |
| `monogit log` / `monogit diff` | History / unstaged changes per repo |
| `monogit link / unlink / release / ci` | Shared packages across repos (**beta** — try on a non-critical workspace first) |

## 6. `.monogit.json` reference

```json
{
  "repos": [
    "shared-lib",
    { "path": "api", "remote": "git@github.com:org/api.git", "branch": "main", "dependsOn": ["shared-lib"] },
    { "path": "web", "remote": "git@github.com:org/web.git", "branch": "main" }
  ],
  "groups": { "backend": ["api", "shared-lib"], "frontend": ["web"] },
  "protected": ["develop", "release/*"],
  "commit": { "link": true }
}
```
