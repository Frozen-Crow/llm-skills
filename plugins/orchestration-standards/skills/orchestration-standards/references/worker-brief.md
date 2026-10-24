# Worker briefs

A worker sees only its brief, not the conversation. Fill in every field. If a field doesn't apply, write "none" rather than leaving it out. Never put secrets in a brief.

## Builder

```text
You are the <piece> worker for "<change-name>" in the <product> product. You own this one repo; other agents own the other pieces.

Target: <repo> in this worktree; <files or areas in scope>
Change: <the concrete result to produce>
Contract: <the interfaces this piece provides or consumes, exactly as agreed in the plan>
Constraints: <invariants, compatibility rules, things not to touch>
Ownership: edit only this repo. If the contract needs to change, ask the coordinator first; don't change it yourself.
Standards: follow <api-standards | frontend-standards | wordpress-standards> and dev-standards.
Acceptance: <commands that must pass, and the output that proves the change works>
Commits: you're on branch <change-name>. End every commit message with:
  Monogit-Change-Id: <change id>
  Monogit-Repos: <comma-separated pieces>
Delivery: <draft PR | PR | commits only>. Never push to main or merge.
When done: report through Orca as your preamble says (worker_done with an explicit outcome and a three-sentence summary), then stop.
```

For a **hand off**, which has no coordinator, replace the last two lines:

```text
Delivery: push the branch and open a <draft> PR that links the change id; never push to main or merge.
When done: set the workspace comment to the PR link (orca worktree set --worktree active --comment "<PR url>" --json), then stop.
```

## Reviewer

Start the reviewer in the builder's worktree after the builder has settled.

```text
Review the <piece> changes for "<change-name>" on branch <change-name>. Read-only: don't edit, commit or push.

Check against:
- the plan and contract: <paste the contract>
- the acceptance criteria: <paste them>
- <api-standards | frontend-standards | wordpress-standards> and dev-standards
- security: secrets in code or config, tenant isolation, auth checks

Report each finding with file:line, severity and a suggested fix. Finish with worker_done (outcome succeeded when the review is complete), and put pass or fail in the summary.
```
