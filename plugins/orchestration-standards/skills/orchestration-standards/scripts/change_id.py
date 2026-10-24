#!/usr/bin/env python3
"""Print a new Monogit-Change-Id: a 26-character Crockford base32 ULID, the same
format `monogit commit --link` writes, so `monogit show <id>` finds commits made
in Orca worktrees too."""
import secrets
import time

ENCODING = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

t = int(time.time() * 1000)
stamp = ""
for _ in range(10):
    stamp = ENCODING[t % 32] + stamp
    t //= 32
print(stamp + "".join(secrets.choice(ENCODING) for _ in range(16)))
