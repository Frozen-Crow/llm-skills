# agent-vault: setup and usage reference

Source: https://github.com/CrimsonWorks-Inc/agent-vault (Apache-2.0). Once installed, `agent-vault docs` opens docs written against the developer's actual install (their port, their credential names) — prefer that over this file for exact commands.

## Contents
1. How it works (one paragraph)
2. Requirements
3. Install (walkthrough)
4. Lock it down — passphrase first
5. Add credentials and grant a session
6. Connect Claude
7. Route the model key
8. Day-to-day and troubleshooting

---

## 1. How it works

The agent sends a **placeholder** (`av1.…`) instead of a secret. The agent-vault daemon checks the session and grant, swaps in the real credential only at the declared spot (e.g. the `Authorization` header), only for hosts the credential allows, and only while the placeholder has uses left. Responses are scrubbed before they come back. Every use is in a hash-chained audit log. Anything that widens what an agent can do needs a human: a passphrase or a fingerprint.

## 2. Requirements

- **Node.js 20.10 or newer** (`node --version`). No other dependencies.
- macOS is the tested platform for the full (privileged) install. On Linux it has not been run yet — use `--dry-run` first and review every change.

## 3. Install (walkthrough)

The developer runs these in their own terminal; the installer uses `sudo` and asks before running it.

**Step 1 — get the code**
```bash
git clone https://github.com/CrimsonWorks-Inc/agent-vault.git ~/agent-vault
cd ~/agent-vault
```

**Step 2 — optional: see it work first**
```bash
node demo/demo.js
```
Runs a real daemon against a stand-in API and shows a normal call, a prompt-injection attempt being refused, budget exhaustion and the audit chain.

**Step 3 — put the CLI on PATH**
```bash
npm install -g .
```
Confirm with `agent-vault --help`.

**Step 4 — run setup**
```bash
agent-vault setup
```
It prints the plan and the exact program root will run, then asks before calling `sudo`. This creates a dedicated `_agentvault` system user, a root-owned install, a vault only that user can read, and a background service.

Tell the developer: the first install runs code from a folder they own, so it should be a fresh clone with no agent running against it. `--dev` mode exists for a quick try but keeps the vault readable by their account — don't use it for real credentials.

**Step 5 — confirm the boundary**
```bash
cat /var/db/agent-vault/vault/vault.json   # this SHOULD be refused
agent-vault doctor
```

## 4. Lock it down — passphrase first

```bash
agent-vault passphrase set
```
**This must be the very next thing after install, done by the human.** A fresh vault has no human factor, and whoever sets the first passphrase owns it. `agent-vault status` and `agent-vault doctor` will keep warning until it's set.

Optional: in `agent-vault ui`, enroll Touch ID so approvals in the web UI need a fingerprint, and enable Touch ID unlock.

## 5. Add credentials and grant a session

The developer runs these — the secret value is read from the terminal, never passed as an argument and never shown to an agent.

```bash
agent-vault cred add gh --kind github
agent-vault session create --cred gh --paths "/repos/<org>/**"
```
Run either with no arguments for a wizard. Built-in kinds include `github`, `slack`, `anthropic`, `openai`, `google-genai` and generic `http`. Keep grants narrow: specific paths and methods rather than `/**` where possible.

## 6. Connect Claude

**Claude Code (recommended):**
```bash
agent-vault mcp install --agent claude-code
```
Merges into the config (keeps a backup; safe to rerun). `--scope project|user` picks the file, `--print` shows the block without writing. Claude gains `vault_status`, `vault_list_creds`, `vault_get_placeholder`, `vault_http`, `vault_explain_denial`, `vault_request_session`.

**Anything that can make HTTP requests:**
```bash
eval "$(agent-vault env)"
curl "$AGENT_VAULT_URL/p/gh/user" -H "Authorization: Bearer $AGENT_VAULT_PLACEHOLDER"
```

**Claude Desktop custom connector** (needs https even on localhost):
```bash
agent-vault tls setup
agent-vault listen add mcp-tls --address 127.0.0.1:7449 --surfaces mcp --tls managed
agent-vault mcp install --agent claude-code --transport http --tls
export NODE_EXTRA_CA_CERTS="$HOME/.agent-vault/agent-vault-ca.pem"
```

## 7. Route the model key

```bash
agent-vault cred add anthropic-key --kind anthropic
eval "$(agent-vault env)"
export ANTHROPIC_BASE_URL="$AGENT_VAULT_URL/p/anthropic-key"
export ANTHROPIC_API_KEY="$AGENT_VAULT_PLACEHOLDER"
```
Then remove the real key from shell profiles and `.env` files, and consider rotating it if it's been sitting in plain text. `OPENAI_*` and `GEMINI_*` work the same way.

## 8. Day-to-day and troubleshooting

| Command | Use |
|---|---|
| `agent-vault status` | Locked/unlocked, human factor set, active sessions |
| `agent-vault doctor` | Proves the install boundary holds; fails if no passphrase |
| `agent-vault ui` | Web UI: credentials, sessions, approvals, audit (one-time link) |
| `agent-vault approve sr_… --methods GET --paths "/user"` | Approve (and narrow) an agent's session request |
| `agent-vault audit tail` / `audit verify` | Read and verify the audit log |
| `agent-vault docs` | Docs for this install (`docs connect`, `models`, `refused`, `commands`) |

- **`AV_LOCKED`** — the vault is locked; the developer unlocks it.
- **`AV_BAD_LOCATION`** — a placeholder was sent somewhere other than its declared spot (e.g. in a body instead of a header). Fix the request; don't encode around it.
- **Refused host** — the credential isn't allowed to reach that host. Use a credential meant for it.
- **Placeholder exhausted** — get a fresh one with `vault_get_placeholder`.

Known limits worth knowing (from the project's own README): JavaScript daemon rather than the planned Rust, JSON storage rather than SQLite, no Postgres/MySQL/SSH connectors yet, request bodies over 16 MiB are refused.
