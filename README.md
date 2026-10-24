# Frozen Crow LLM Skills

Team skills for AI coding agents. Each skill is a standard [Agent Skills](https://agentskills.io) `SKILL.md`, so the same files work in Claude, Cursor, GitHub Copilot, Codex, Gemini CLI, Windsurf, Cline and the rest. They're packaged as a Claude plugin marketplace, which the cross-editor `skills` CLI also reads.

| Plugin | What it does |
|---|---|
| `dev-standards` | Use [monogit](https://monogit.com) for all git work across repos and [agent-vault](https://github.com/CrimsonWorks-Inc/agent-vault) for every credential. Checks the setup and walks developers through installing what's missing. |
| `api-standards` | Build every API on [@frozencrow/api-core](https://api-core.frozencrow.com) (Feathers 5, Koa, MongoDB) and add resources through its generators, so auth, RBAC and per-organization tenant isolation come for free. |
| `frontend-standards` | Nuxt or Next for SEO-driven marketing sites, Vue or React SPAs for app clients decoupled from the API, shared layouts and components built with Tailwind and Headless UI, and a Feathers client (REST or websockets) for api-core APIs. |
| `wordpress-standards` | Build WordPress sites through [WP MCP Connector](https://wpmcp.frozencrow.com). Working directly on production is fine for an initial build; large changes to a live site go through a staging clone. |
| `orchestration-standards` | Run multi-agent work through [Orca](https://github.com/stablyai/orca): one worktree and one agent per piece of the product, a coordinator that plans, routes and reviews, and a one-question preference check before anything starts. Keeps monogit sub-repos registered and grouped in Orca. |

## Install

**Claude app** (Pro, Max, Team or Enterprise): **Customize → Plugins → Add → Add marketplace → Add from a repository**, enter `Frozen-Crow/llm-skills`, then install the plugins you need.

**Claude Code:**

```
/plugin marketplace add Frozen-Crow/llm-skills
/plugin install dev-standards@frozen-crow
/plugin install api-standards@frozen-crow
/plugin install frontend-standards@frozen-crow
/plugin install wordpress-standards@frozen-crow
/plugin install orchestration-standards@frozen-crow
```

**Updates.** Third-party marketplaces don't auto-update by default.

- **Claude app:** open the marketplace under **Customize → Plugins** and use **Check for updates**. Marketplaces added from GitHub also offer **Sync automatically**.
- **Claude Code:** `/plugin` → **Marketplaces** → select `frozen-crow` → **Enable auto-update**. To update by hand, run `/plugin marketplace update frozen-crow`, then `/reload-plugins`.
- **Toggle missing?** The option is hidden when `DISABLE_AUTOUPDATER`, `DISABLE_UPDATES` or `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` is set (for example, `DISABLE_AUTOUPDATER` is set inside the Claude desktop app's Code tab). Turn it on in `~/.claude/settings.json` instead. The env entry keeps plugin updates running while Claude Code's own updater stays off:

  ```json
  {
    "env": { "FORCE_AUTOUPDATE_PLUGINS": "1" },
    "extraKnownMarketplaces": {
      "frozen-crow": {
        "source": { "source": "github", "repo": "Frozen-Crow/llm-skills" },
        "autoUpdate": true
      }
    }
  }
  ```

**Cursor, GitHub Copilot, Codex, Gemini CLI, Windsurf, Cline, Zed and 60+ other agents:** use the [`skills` CLI](https://github.com/vercel-labs/skills), which needs Node 22.20 or newer:

```bash
npx skills add Frozen-Crow/llm-skills                         # pick skills and agents interactively
npx skills add Frozen-Crow/llm-skills --skill '*' -a cursor -g  # everything, for Cursor, user-wide
npx skills update                                             # pull the latest versions
```

Without `-g`, skills install into the current project (for example `.agents/skills/` or `.windsurf/skills/`) and can be committed so the whole team gets them. With `-g`, they go into your home directory for every project. Run `npx skills add Frozen-Crow/llm-skills --list` to see what's available.

**Just the skill:** download the zip of `plugins/<plugin>/skills/<plugin>/` and upload it in **Customize → Skills → + → Upload a skill**, or copy the folder into your agent's skills directory. No automatic updates this way.

**MCP servers:** `dev-standards` uses the monogit and agent-vault MCP servers, and `wordpress-standards` uses WP MCP Connector. The skills include setup steps for each major editor.

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
  api-standards/
    .claude-plugin/plugin.json
    skills/api-standards/
      SKILL.md
      references/api-core-reference.md # condensed api-core docs
  frontend-standards/
    .claude-plugin/plugin.json
    skills/frontend-standards/
      SKILL.md
      references/feathers-client.md    # client setup for Vite, Nuxt, Next
  wordpress-standards/
    .claude-plugin/plugin.json
    skills/wordpress-standards/
      SKILL.md
  orchestration-standards/
    .claude-plugin/plugin.json
    skills/orchestration-standards/
      SKILL.md
      references/                      # preference check, worker briefs
      scripts/workspace_map.py         # read-only product map: pieces, Orca repos, groups
      scripts/change_id.py             # new Monogit-Change-Id for linked commits
```

## Releasing a change

1. Edit the skill files. Keep them editor-neutral: no editor-specific tool names or commands without equivalents for the other editors.
2. Bump `version` in `plugins/<plugin>/.claude-plugin/plugin.json`. Claude plugin users only receive changes when the version changes; `skills` CLI users get them on `npx skills update`.
3. `claude plugin validate .` and `npx skills add . --list` (all skills should be listed).
4. Commit and push.

## Adding a plugin

Add a folder under `plugins/` with its own `.claude-plugin/plugin.json` and `skills/<name>/SKILL.md`, then add an entry to `.claude-plugin/marketplace.json` whose `name` matches the plugin's `plugin.json` name.

Follow the [Agent Skills spec](https://agentskills.io/specification):

- `name` is lowercase letters, digits and single hyphens, at most 64 characters, and matches the skill's folder name.
- `description` is at most 1024 characters and says both what the skill does and when to use it.
- `SKILL.md` stays under 500 lines, with longer material in `references/` one level deep.
