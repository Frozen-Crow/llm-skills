---
name: orchestration-standards
description: Frozen Crow orchestration standards for Orca — run multi-agent work through Orca with one worktree and one agent per piece of the product (api, client, marketing, mobile, shared), a coordinator that plans, routes and reviews, and a one-question preference check before anything starts. Use this skill whenever a Frozen Crow developer starts a feature or task that spans more than one repo or piece of a product, asks to spin up, coordinate, supervise or hand work off to agents, mentions Orca, worktrees, a coordinator or a team of agents, or says "orchestrate", "parallelize" or "split this up" — even with no other instructions. Also use it when a .monogit.json workspace is present and the work is bigger than one small change.
---

# Frozen Crow Orchestration Standards

Orca runs our multi-agent work. Orca's own skills (`orca-cli` and `orchestration`, served version-matched by the `orca` binary) explain the mechanics. This skill sets Frozen Crow's policy on top of them: how work is split, where each agent runs, what the user decides, and how the pieces land together. If this skill and Orca's guide disagree on a command or flag, Orca's guide wins. On policy, this skill wins.

Six rules:

1. **Orca does the orchestration.** Agents, worktrees and supervision go through the `orca` CLI. Don't use the editor's built-in subagents, raw `git worktree`, or ad hoc terminals.
2. **One piece, one worktree, one agent.** Every piece of the product that changes gets its own Orca worktree, in its own repo, with its own agent. Two agents never share a checkout. Treat this as the user asking for separate worktrees, which Orca's guide otherwise only creates on request.
3. **Ask once, then run.** Start with the preference check, which is one question and usually one click. After that, work without check-ins except at the approval points the user chose.
4. **Contracts before code.** The coordinator settles the interfaces between pieces before workers start, so the pieces can be built in parallel.
5. **The coordinator routes; workers build.** In a supervised run the coordinator plans, answers questions, reviews and integrates. It doesn't edit piece code.
6. **Leave nothing running.** Orca doesn't close finished agents' terminals on its own, and idle ones pile up until the machine lags. The coordinator releases each worker as it finishes, sweeps before it reports, and clears leftovers before starting new work. See "Cleaning up stale workers".

## Step 0: Preflight

1. **Resolve the CLI the way Orca's skills say.** Use `ORCA_CLI_COMMAND` if it's set. On Linux use `orca-ide`, because a bare `orca` there is the screen reader. Otherwise use `orca`. On macOS, if `orca` isn't on PATH, use `/Applications/Orca.app/Contents/Resources/bin/orca`. Use that one executable for the whole task.
2. **Check Orca is running** with `orca status --json`. If it isn't, run `orca open --json`.
3. **Load Orca's guides** with `orca skills get orca-cli`, plus `orca skills get orchestration` for supervised runs. If Orca's skills aren't installed for this editor, `orca skills install` adds them.
4. **Map the product** with `python3 scripts/workspace_map.py <path>`. It's read-only. It finds the workspace root, lists every piece, and checks that Orca has each one registered and grouped. Fix anything it reports before planning (Step 1).
5. **Clear leftovers before adding more.** Run `python3 scripts/stale_terminals.py` and handle what it finds, as described in "Cleaning up stale workers". Release-now items need no question. If anything lands in Ask, raise it once, alongside the preference check.

## Step 1: Every piece registered and grouped

A product is a monogit workspace: a root folder with `.monogit.json` and one repo per piece. Orca needs every piece registered as its own repo, and all of them in one project group so the product appears together in Orca's sidebar.

- **Register missing pieces** by running the `orca repo add --path <abs path> --json` commands the map prints.
- **Watch for a root that is itself a git repo** that gitignores its sub-repos (for example `language-learning`). The map flags this.
  - **A worktree of the root contains none of the pieces.** Never place piece work in a worktree of the root. The root's own repo only gets work that changes the root's files.
  - **Orca's folder scan won't group them.** It only groups sub-repos automatically when the root is a plain folder, so these pieces start out ungrouped.
- **Grouping is manual.** The CLI reports each repo's `projectGroupId` but can't set it. If the map says the pieces aren't in one group, ask the developer to create a project group in Orca's sidebar, named for the product, and move the root (if registered) and every piece into it. Then run the map again. Never edit Orca's state files.

## Step 2: Preference check

Follow `references/preferences.md`:

- **Read what's already decided:** saved defaults in `~/.frozencrow/orchestration.json`, and anything the request already says ("have Codex do the API").
- **Ask one question:** **Recommended** (the saved profile), **Solo**, **Hand off** or **Customize**.
- **Only Customize asks more:** up to four quick choices covering workers, review, approval and delivery, plus whether to remember them.

A small change to a single piece defaults to Solo. Don't assemble a team for a one-file fix.

## Step 3: Plan

- **Pieces.** List the pieces that change, using the map. Untouched pieces get no worker.
- **Contracts first.** Before any worker starts, write the interfaces between pieces into the plan: API endpoints and payloads, shared types in the `*-shared` package, events, and config keys. Workers then build against the contract in parallel instead of waiting on each other.
- **Order only what must be ordered.** A change to a shared package runs first, and the pieces that consume it depend on it. Everything else runs in one parallel wave. Keep dependency chains to three steps or fewer.
- **Name the change once.** Pick one short kebab-case name, like `invoice-export`. Every piece's worktree uses it, and Orca turns the name into the branch, so every repo gets the same branch. Generate one change id with `python3 scripts/change_id.py`. Every commit in every piece carries it.
- **Brief each worker** using `references/worker-brief.md`. A brief must be self-contained, because workers never see this conversation. Never put secrets in a brief.
- **Plan approval.** If the user chose it, show the plan (pieces, contracts, order, agents) and wait.

## Step 4: Launch

| Shape | How |
|---|---|
| Supervised team | `orca orchestration run-create --objective "<goal>" --json`. Then create one `orca orchestration task-create --spec "<brief>" --json` per piece, adding `--deps` only for real ordering. Then, for each ready task: `orca orchestration worker-start --task <id> --worktree new-child --repo id:<piece repo id> --name <change-name> --agent <agent> --setup run --json` |
| Hand off | For each piece: `orca worktree create --repo id:<piece repo id> --name <change-name> --agent <agent> --prompt "<brief>" --json`. Report each worktree id and agent handle, then stop. |
| Solo | `orca worktree create --repo id:<piece repo id> --name <change-name> --agent <agent> --prompt "<brief>" --json`, or work in the current worktree if the user prefers. |

- **Start the whole ready wave before waiting.** Run at most one worker per changed piece, and no more than five at a time unless the user asks for more.
- **Model and effort:** pass `--model` and `--effort` only when the user named them.
- **Failed launch:** if `worker-start` exits non-zero, don't relaunch. Follow Orca's `recovery-and-cleanup` reference.

## Step 5: Supervise

Run Orca's coordinator loop (`check --wait`, reply, validate each `worker_done`). Frozen Crow adds:

- **Release as you go.** Right after accepting a worker's `worker_done`, run `orca orchestration worker-release --dispatch <id> --json`. The only exception is reusing that terminal for the worker's next task straight away. Never run `worker-retain` unless the user asked to keep a terminal open.
- **Handle stale workers on evidence, not silence.** A worker is stale when Orca reports its agent `exited`, or when `worker-read` shows its last turn ended without a `worker_done`. Send it one nudge with `orca orchestration send --to dispatch:<id>`. If the next wait still brings nothing, run `worker-stop`, then retry with `--retry-of` or report the piece as failed. Idleness, a timeout or `unverifiable` liveness never justify stopping a worker on their own; that's Orca's safety rule.

- **Answer from the plan.** Answer worker questions from the plan and contracts. Go to the user only for decisions their approval points reserve, or anything that changes scope, a contract, data or security. Use `orca orchestration gate-create` to block a task while the user decides.
- **Contract changes go through the coordinator.** Approve the change, update the contract, and message every affected worker with `orca orchestration send --to dispatch:<id>`.
- **Keep the sidebar current.** Update each workspace's comment at checkpoints with `orca worktree set --worktree <id> --comment "<status>" --json`.
- **Review**, if it's on: once a piece's builder settles, start a reviewer in that piece's worktree (`--worktree id:<worktree id>`) with the reviewer brief. Reviewers don't edit. Send their findings back to the builder by reusing its terminal.
- **Integrate.** After every piece settles, run the cross-piece check: build and test each piece, and exercise the contract end to end, such as the client against the API. Send any fix to the piece's worker; don't make it yourself.
- **Silence isn't failure.** Timeouts and empty waits are checkpoints, as Orca's guide says.

## Step 6: Deliver

- **Commit with the change id.** Each worker commits in its own worktree with plain git. A worktree holds one repo, so monogit doesn't apply there. Every commit message ends with these trailers:
  ```
  Monogit-Change-Id: <change id>
  Monogit-Repos: <comma-separated pieces in this change>
  ```
  Worktrees share their repo's history, so `monogit show <change id>` from the workspace root lists the whole change across repos.
- **Open PRs** as the delivery preference says, for example draft PRs with `gh pr create --draft` from each worktree. Each PR links its sibling PRs and the change id. Record each PR on its workspace with `orca worktree set --worktree <id> --pr <number> --json`.
- **Sweep before you report.** Run `python3 scripts/stale_terminals.py --run <run id>` and clear it as described in "Cleaning up stale workers". Don't end the coordinator turn while this run still has release-now or recover items.
- **Report.** Give the user, per piece: the outcome, the evidence (which tests ran), and the PR link. Add the change id, any open blockers, and what was closed or is still running.
- **Keep the worktrees.** Leave them until their PRs merge, and never remove a worktree that has unpushed work. Closing terminals doesn't touch worktrees.
- **Hand off runs can't clean up.** No coordinator stays behind, so tell the user the agents' terminals stay open until they close them or the next orchestration's sweep offers to.

## Cleaning up stale workers

`scripts/stale_terminals.py` is read-only. It checks every orchestration run and every live terminal, then sorts the terminals into five groups. Pass `--run <id>` to check one run only, or `--idle-hours <n>` to change the idle threshold (the default is 6 hours).

| Group | What it is | What to do |
|---|---|---|
| **Release now** | Settled workers Orca still owes a release | Run the printed `worker-release` commands. No question needed. |
| **Recover** | Releases that are pending or have an unknown outcome | Run the printed recovery command. Never substitute `terminal close`. |
| **Ask** | Settled workers whose terminals Orca retained, usually because the user clicked into them (`user_takeover`), plus orphaned terminals with no tab | Ask once, as a batch: "Close 12 finished-worker terminals?" Under `cleanup: auto` (see the preferences reference), close those idle for an hour or more without asking. Close them one at a time with the printed `terminal close --terminal <handle>` command. If a handle is stale, re-run the audit and skip it. |
| **Idle** | Idle terminals no run owns: hand-off agents, setup shells, default tabs | List them in the report. Close only the ones the user names. These can be deliberate, so `cleanup: auto` never touches them. |
| **Keep** | Active workers, live workers the user took over, and terminals Orca didn't create | Leave them. |

Never run `orca terminal close --worktree <id> --all` or `orca orchestration reset` as cleanup. The first wipes a workspace's tabs and resume records, and the second destroys the coordination state.

## Rules for every worker

- **Follow the piece's standards skill:** api-standards for API pieces, frontend-standards for client, marketing and app pieces, and wordpress-standards for WordPress sites. dev-standards applies everywhere.
- **One owner per file.** Only one worker edits a given file, and a shared package has a single owner.
- **No pushing or merging to main.** Workers don't push to `main` and don't merge PRs.
- **api-core problems follow api-standards:** open an issue first, and send security problems to security@frozencrow.com.

## When something conflicts

If Orca's version-matched guide or `orca <command> --help` disagrees with this skill, follow Orca, and tell the developer so the skill can be updated. If the developer explicitly wants something different, follow them, but mention the standard once.
