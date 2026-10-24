# Preference check

The goal is one question, usually answered with one click, before any agent starts. Ask more only when the user picks Customize.

## 1. Work out what's already decided

- **Saved defaults:** read `~/.frozencrow/orchestration.json` if it exists (format below). An entry for this workspace's root path overrides `default`.
- **The request itself:** anything it already says ("have Codex do the API", "no review", "just hand it off") is decided. Don't ask it again.
- **The recommended shape:** a small change to one piece is **Solo**. Two or more pieces, or one large piece, is a **Supervised team**.

## 2. Ask the one question

Ask with the editor's multiple-choice question tool if it has one. Otherwise send a short numbered list and treat "go", "1" or "yes" as the first option.

**How should I run this?**

1. **Recommended:** a one-line summary of the resolved profile, for example: "Supervised team: a Claude worker per piece (api, client), you approve the plan, a reviewer checks each piece, draft PRs."
2. **Solo:** one agent in one worktree.
3. **Hand off:** start one agent per piece and leave them to it, with no supervision.
4. **Customize**

For options 1–3, start immediately. Anything not set comes from the saved profile, or else the defaults in section 4.

## 3. Customize (only when asked)

Ask these together:

| Question | Options (first is the default) |
|---|---|
| Workers | Same agent as me for every piece · Claude for every piece · Codex for every piece · Mix (say which piece gets which agent) |
| Review | A reviewer agent checks each piece · I review the diffs myself · No review |
| Approval | Approve the plan before workers start · Approve before PRs open · Both · Fully autonomous |
| Delivery | Draft PR per piece · Ready-for-review PR per piece · Commits on branches only |

Then ask one more: **Remember these?** Options: for this workspace, for all workspaces, or just this once.

Don't ask about models or effort. Pass them only when the user names them.

## 4. Defaults

When nothing is saved or said:

- **shape:** `auto` (Solo or Supervised team, by size)
- **workers:** the agent you are running as, for every piece
- **review:** `reviewer`
- **approval:** `["plan"]`
- **delivery:** `draft-prs`
- **maxWorkers:** 5

## 5. Saved file

`~/.frozencrow/orchestration.json`:

```json
{
  "default": {
    "shape": "auto",
    "workers": { "*": "claude", "api": "codex" },
    "review": "reviewer",
    "approval": ["plan"],
    "delivery": "draft-prs",
    "maxWorkers": 5
  },
  "workspaces": {
    "/Users/me/Projects/acme": { "workers": { "*": "codex" } }
  }
}
```

| Key | Values |
|---|---|
| `shape` | `auto`, `supervised`, `solo`, `handoff` |
| `workers` | Piece name → Orca agent id (`claude`, `codex`, `cursor`, …). `*` covers every other piece. |
| `review` | `reviewer`, `coordinator`, `none` |
| `approval` | Any of `"plan"` and `"prs"`. Empty means fully autonomous. |
| `delivery` | `draft-prs`, `prs`, `branches` |
| `maxWorkers` | Maximum workers running at once |

Write the file only when the user chose to remember their answers. Merge into the existing file rather than replacing it, and leave other workspaces' entries untouched.
