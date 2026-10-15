---
name: dev-standards
description: Frozen Crow developer standards — use monogit for all git work across repos and agent-vault for every credential. Use this skill whenever a Frozen Crow developer is doing coding work that touches git (branching, committing, pushing, opening PRs, checking repo status, cloning the workspace), needs an API key, token or other secret, is setting up a new machine or onboarding, or asks how the team does things — even if they don't mention monogit or agent-vault by name. Also use it when a .monogit.json file is present, or when you're about to write a secret into a .env file, config, code or chat.
---

# Frozen Crow Developer Standards

Two standards, and they apply to every Frozen Crow developer and every agent working on their behalf:

1. **Git goes through monogit.** Our work spans several repos that change together. monogit gives us a monorepo workflow without a monorepo: one command branches, commits, pushes and opens PRs across every linked repo, and links related commits with a shared `Monogit-Change-Id` so a change that spans repos can be found again as one unit.
2. **Secrets go through agent-vault.** An agent should never hold a real credential. agent-vault stores the secret, hands the agent a placeholder, and swaps the real value in only at the network layer, only for the hosts it is allowed to reach. A key that never enters the agent's context can't be leaked by a prompt injection, a log, or a commit.

Start every session by checking both are in place (next section). If either is missing, recommend it, explain the why in a sentence, and offer to walk the developer through setup. Don't silently fall back to plain git or a `.env` file.

## Step 0: Check the environment

Run the bundled check script from the skill directory:

```bash
bash scripts/check_env.sh
```

It reports Node version, whether `monogit`, `gh` and `agent-vault` are installed, whether you're inside a monogit workspace (a `.monogit.json` above the current directory), and agent-vault's status. Read its output and act on what's missing:

- monogit missing, or no `.monogit.json` → walk through `references/monogit-setup.md`
- agent-vault missing, or status shows no passphrase / human factor → walk through `references/agent-vault-setup.md`
- `gh` missing → only needed for `monogit pr` and `monogit push --wait-ci`; mention it, install when they need PRs

When walking someone through setup, go one step at a time: give the command, say what it does, ask them to run it and paste the result, then confirm it worked before moving on. Many steps are interactive or prompt for secrets, so the developer runs them in their own terminal.

## Standard 1: monogit for git

Inside a monogit workspace, use monogit instead of looping plain `git` over repos. Plain `git` inside a single repo is fine for read-only inspection (`git log` in one repo, `git blame`), but anything that changes branches, commits or remotes goes through monogit so every repo stays in step.

If the monogit MCP server is connected (tools named `monogit_status`, `monogit_commit`, etc.), prefer those tools over shelling out. Otherwise use the CLI.

### The everyday flow

```bash
monogit status                          # always look first: branch, ahead/behind, dirty state per repo
monogit checkout -b feature/short-name  # branch everywhere
# ...make changes...
monogit add .
monogit commit --link -m "feat: concise summary"
monogit push                            # pushes current branch to origin with tracking
monogit pr --fill                       # opens a PR in every repo that has new commits
```

Conventions:

- **Look before you act.** Run `monogit status` at the start of a task and before committing. If a repo shows a rebase or merge in progress, or is behind its upstream, stop and tell the developer rather than committing over it.
- **Link cross-repo commits.** Use `--link` (or set `"commit": { "link": true }` in `.monogit.json`) so commits that belong together share a `Monogit-Change-Id`. Find them later with `monogit show <change-id>`.
- **Scope when you mean a subset.** `--only api,web`, `--except docs`, or `--group backend`. Don't commit to every repo when the change touches one.
- **Respect push order.** If repos declare `dependsOn` in `.monogit.json`, `monogit push` already orders them; use `monogit push --wait-ci` when a dependent's build needs the dependency's CI to pass first.
- **Running things everywhere.** `monogit run "npm test"` runs a shell command in each repo with labelled output; `monogit exec -- <git args>` covers git commands monogit doesn't wrap.
- **Confirm destructive operations.** Ask before `monogit tidy` without `--dry-run`, `monogit exec -- reset --hard ...`, force pushes, or branch deletion. Run `monogit tidy --dry-run` first and show the result.
- **New teammate or new machine?** If `.monogit.json` is committed, `monogit clone` pulls every repo in the workspace.

For the full command list, see `references/monogit-setup.md` (it covers commands as well as setup).

## Standard 2: agent-vault for secrets

### The rules

- **Never ask the developer to paste a secret into chat.** If a task needs a key, the developer adds it to agent-vault themselves.
- **Never write a real secret into a file** — not `.env`, not config, not code, not test fixtures, not commit messages. If you find one already there, flag it, suggest moving it into the vault, and suggest rotating it since it's been exposed.
- **Use placeholders, not values.** With the agent-vault MCP tools connected, use `vault_list_creds` to see what's available, `vault_get_placeholder` to get a placeholder, and `vault_http` to make the call. Without MCP, use the env route: `eval "$(agent-vault env)"` then send requests to `$AGENT_VAULT_URL/p/<cred>/...` with `Authorization: Bearer $AGENT_VAULT_PLACEHOLDER`.
- **When you need access you don't have**, use `vault_request_session` with a clear, honest reason and the narrowest paths and methods that will do the job, then tell the developer a request is waiting for their approval.
- **If a call is refused**, use `vault_explain_denial` and relay the reason. Don't try to route around a refusal (different encoding, different host, a raw token from somewhere else). The refusal is the system working.

### Things only the human does

Some agent-vault actions are deliberately gated on a human, and an agent doing them would defeat the whole design. Give the developer the command and let them run it — never run these yourself:

- `agent-vault passphrase set` — and it must be the first thing they do after installing, before any agent touches the vault. Whoever sets the first passphrase owns the vault.
- `agent-vault cred add ...` — it reads the secret value from their terminal
- `agent-vault session create ...` and `agent-vault approve ...` — granting and widening access
- `sudo` steps in `agent-vault setup`
- Touch ID / authenticator enrollment in `agent-vault ui`

### Route the model key too

The Anthropic API key an agent runs on is usually the most valuable secret on the machine. Recommend routing it through the vault as well — the steps are in `references/agent-vault-setup.md`.

## When something conflicts

If a repo's own README or a developer's explicit instruction says to do something differently, follow the developer, but mention the team standard once so it's a conscious choice. If a tool behaves differently from what's described here (a flag was renamed, a command moved), trust `monogit --help` / `agent-vault docs` over this skill and tell the developer so the skill can be updated.
