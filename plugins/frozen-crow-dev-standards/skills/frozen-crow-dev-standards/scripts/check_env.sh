#!/usr/bin/env bash
# Frozen Crow dev standards: report what's installed and configured.
# Read-only — changes nothing.

ok()   { printf '  [ok]      %s\n' "$1"; }
miss() { printf '  [missing] %s\n' "$1"; }
warn() { printf '  [check]   %s\n' "$1"; }

echo "Frozen Crow environment check"
echo

echo "Node.js"
if command -v node >/dev/null 2>&1; then
  v=$(node --version 2>/dev/null | sed 's/^v//')
  major=${v%%.*}; rest=${v#*.}; minor=${rest%%.*}
  if [ "${major:-0}" -gt 20 ] || { [ "${major:-0}" -eq 20 ] && [ "${minor:-0}" -ge 10 ]; }; then
    ok "node $v (meets monogit >=18 and agent-vault >=20.10)"
  elif [ "${major:-0}" -ge 18 ]; then
    warn "node $v — fine for monogit, agent-vault needs 20.10+"
  else
    miss "node $v — too old (monogit needs 18+, agent-vault needs 20.10+)"
  fi
else
  miss "node — not installed"
fi
echo

echo "monogit"
if command -v monogit >/dev/null 2>&1; then
  ok "monogit installed ($(command -v monogit))"
else
  miss "monogit — install with: npm i -g @frozencrow/monogit"
fi

dir=$(pwd); found=""
while [ "$dir" != "/" ] && [ -n "$dir" ]; do
  if [ -f "$dir/.monogit.json" ]; then found="$dir/.monogit.json"; break; fi
  dir=$(dirname "$dir")
done
if [ -n "$found" ]; then
  ok "workspace config: $found"
else
  warn "no .monogit.json above $(pwd) — run 'monogit init' in the parent folder, or cd into the workspace"
fi

if command -v gh >/dev/null 2>&1; then
  if gh auth status >/dev/null 2>&1; then ok "gh installed and signed in"
  else warn "gh installed but not signed in — run: gh auth login"; fi
else
  warn "gh not installed — needed only for 'monogit pr' and 'push --wait-ci'"
fi
echo

echo "agent-vault"
if command -v agent-vault >/dev/null 2>&1; then
  ok "agent-vault installed ($(command -v agent-vault))"
  echo "  --- agent-vault status ---"
  agent-vault status 2>&1 | sed 's/^/  | /' | head -n 25
  echo "  (look for: vault unlocked, a passphrase / human factor set)"
else
  miss "agent-vault — see references/agent-vault-setup.md"
fi

if ls .env .env.* >/dev/null 2>&1; then
  warn ".env file(s) here — check none hold real secrets that belong in agent-vault"
fi
