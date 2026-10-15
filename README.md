# Frozen Crow LLM Skills

Team skills for Claude, packaged as a plugin marketplace.

| Plugin | What it does |
|---|---|
| `dev-standards` | Use [monogit](https://monogit.com) for all git work across repos and [agent-vault](https://github.com/CrimsonWorks-Inc/agent-vault) for every credential. Checks the setup and walks developers through installing what's missing. |

## Install

**Claude app** (Pro, Max, Team or Enterprise): **Customize → Plugins → Add → Add marketplace → Add from a repository**, enter `OWNER/llm-skills`, then install `dev-standards`.

**Claude Code:**

```
/plugin marketplace add OWNER/llm-skills
/plugin install dev-standards@frozen-crow
```

To get updates automatically, open `/plugin` → **Marketplaces** → `frozen-crow` → **Enable auto-update**. Otherwise run `/plugin marketplace update frozen-crow`.

**Just the skill:** download the zip of `plugins/dev-standards/skills/dev-standards/` and upload it in **Customize → Skills → + → Upload a skill**. No automatic updates this way.

## Layout

```
.claude-plugin/marketplace.json        # catalog (marketplace name: frozen-crow)
plugins/
  dev-standards/
    .claude-plugin/plugin.json         # bump "version" on every release
    skills/dev-standards/
      SKILL.md
      references/                      # monogit + agent-vault setup guides
      scripts/check_env.sh             # read-only environment check
```

## Releasing a change

1. Edit the skill files.
2. Bump `version` in `plugins/<plugin>/.claude-plugin/plugin.json` — users only receive changes when the version changes.
3. `claude plugin validate .`
4. Commit and push.

## Adding a plugin

Add a folder under `plugins/` with its own `.claude-plugin/plugin.json` and `skills/`, then add an entry to `.claude-plugin/marketplace.json` whose `name` matches the plugin's `plugin.json` name.
