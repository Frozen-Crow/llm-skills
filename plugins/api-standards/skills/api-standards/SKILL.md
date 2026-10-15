---
name: api-standards
description: Frozen Crow API standards — every API is built on @frozencrow/api-core (FeathersJS 5 + Koa + MongoDB + TypeScript), and new resources are added through its generator so auth, RBAC and per-organization tenant isolation come for free. Use this skill whenever a Frozen Crow developer is starting a new API or backend, adding a service, resource, endpoint or custom method, working on authentication, roles, permissions, organizations, invites, password reset, transactional email or realtime events, configuring an API for production, or wanting to fix, change or report a problem in api-core itself — even if they don't mention api-core by name. Also use it when package.json depends on @frozencrow/api-core or @feathersjs/*, or when you're about to hand-roll auth, tenancy or access control in Express, Nest, Fastify or bare Feathers.
---

# Frozen Crow API Standards

Every Frozen Crow API is built on **@frozencrow/api-core**: FeathersJS 5 + Koa + MongoDB + TypeScript, with authentication, role-based access control, per-organization data isolation and transactional email already built in. That plumbing is security-critical and easy to get subtly wrong, so we build it once in the core and never again per project.

The standard comes down to three rules:

1. **Use the core, don't rebuild it.** If api-core provides it (login, JWT, OAuth, API keys, orgs, invites, roles, password reset, magic links, email, realtime, short IDs), use the core's version.
2. **Add resources through the core's patterns.** Generate services with the `frozencrow` CLI and wire them with `generateDefaultHooks`, so every resource gets the same auth, tenant scoping, validation and permissions without per-service code.
3. **Changes to the core start as a GitHub issue, never as a PR.** Security problems never go in public; they're emailed to security@frozencrow.com. See "Changing api-core itself" below.

**Source of truth:** https://api-core.frozencrow.com/#/docs (library) and `#/docs/create-api` (scaffolder). The site renders with JavaScript, so a plain fetch returns only the title. Open it in a browser tool, or read the installed package (`node_modules/@frozencrow/api-core`: README and `.d.ts` files) for exact signatures. `references/api-core-reference.md` has a condensed copy of the docs: config options, the built-in services, the hook options, CLI flags and exports.

## Starting a new API

```bash
npm create @frozencrow/api my-app -- --services posts,comments   # omit --services to be prompted
cd my-app && npm install && npm run dev
```

The scaffolder sets the package and database name, writes a strong secret to the git-ignored `config/local.json`, and creates one multitenant service per name. Requirements are Node 20 or newer and a reachable MongoDB.

Don't start a Frozen Crow API from bare Feathers, Express, Nest or Fastify. If the developer explicitly wants a different stack, follow them, but mention the standard once so it's a conscious choice.

## Configuration

- **Use `createConfiguredApp()` with the Feathers config module.** Config lives in `config/*.json`, and production overrides come from environment variables mapped in `config/custom-environment-variables.json`. **No `.env` files.** `createApp(options)` is the alternative for when config files aren't wanted; both resolve to the same `app.get(...)` keys.
- **`config/default.json` is committed and holds no real secrets.** `CHANGE_ME_IN_PRODUCTION` is fine there because the core refuses to boot in production with it.
- **`config/local.json` is git-ignored** and holds local values. Generate the JWT secret with `npx frozencrow secret --write` (or `npm run secret`). Always use `--write`, so the value goes straight into the file and never appears in the conversation.
- **Third-party credentials** (Google OAuth secret, SMTP password, partner API keys): the developer puts these into `config/local.json` or production env vars themselves. Never ask for the value in chat and never write it into a file yourself. This follows the dev-standards secret rules.
- **Adding your own config keys is fine**, since the config schema allows extras. Pass a custom validator to `createConfiguredApp(validator)` to type them.

## Adding a resource

Generate it rather than writing the three files by hand:

```bash
npx frozencrow generate service invoices --fields "amount:number,paid?:boolean" --wire
```

- **Access model.** `--access team` (the default) makes the service multitenant, and almost everything should be `team`. Use `user` for data owned by one person across orgs (`restrictToUser`). Use `public` only for data that is genuinely meant to be anonymous, and confirm that with the developer first.
- **Generated files.** `<name>.schema.ts` holds TypeBox schemas, validators and resolvers. `<name>.class.ts` holds the `MongoDBService`. `<name>.ts` registers the service, wires hooks and augments `ServiceTypes`. Edit these after generating; don't rewrite them from scratch.
- **Schema rules:**
  - Every tenant-scoped resource has `organizationId: ObjectIdSchema()`.
  - Keep `additionalProperties: false`.
  - The data schema must allow the server-set fields (`organizationId`, `createdAt`, `updatedAt`) as optional, because `resolveData` runs *before* `validateData`. Otherwise valid creates get rejected.
  - Build validators from the core's shared `dataValidator` / `queryValidator` via `getValidator`.
  - Timestamps are numbers (`Date.now()`).
- **Hooks.** Make one `generateDefaultHooks({ schema })` call. Add behavior with `extensions` (which appends to a slot). Use `overrides` (which replaces a slot) only with a clear reason: replacing `before.all` can silently drop authentication and tenant scoping.
- **Permissions.** Access is checked as `<path>:<method>` (for example `invoices:create`, `invoices:*`). Admin has `*`, but the seeded Member role only covers users and organizations. **A new service is unreachable for non-admins until a role grants it.** Ask the developer which roles should get which methods, then add the permissions to `seed: { roles: [...] }` or the existing role documents.
- **Hook stubs.** Generate them with `npx frozencrow generate hook <name>`; they go in `src/hooks`.

## Access control: never weaken it

- **Don't strip or rewrite `organizationId` in queries,** and don't use `accessControl: { mode: 'ignore' }` on tenant data. `teamAccessControl` is what keeps one customer's data away from another's.
- **Custom methods need explicit checks.** Access control covers the six standard methods. In a custom method, call `assertOrgMembership(app, user, orgId)` and `assertOrgPermission(app, user, orgId, '<path>:<method>')` before doing anything.
- **Use `isGlobalAdmin(user)`** rather than comparing role names yourself. **Never rename or delete the `Admin` role**, since its name is the global-admin signal.
- **`requireAuth: false` / `allowAnonymous: true`** are only for resources that are meant to be public. Confirm with the developer first.
- **Realtime stays tenant-scoped.** Extend it through the `channels` option. A custom `publish` that returns `undefined` falls through to the tenant-scoped default; keep it that way rather than broadcasting to `authenticated` by accident.

## Extending built-in services

To add fields to `users`, `organizations`, `roles`, `invites` or `verifications`, use the `extend` option, then declare the types once by augmenting `UserExtensions` (or `OrganizationsExtensions`, etc.) from `@frozencrow/api-core/lib/declarations`. Never copy or fork a core service, and never loosen `additionalProperties`.

Fields added through `extend.properties` are **client-writable**. If a field is server-only (for example `stripeCustomerId`), add a hook that blocks external writes to it.

## Use the built-in, don't rebuild

| Need | Use |
|---|---|
| Login, signup, JWT | Built-in `local` + `jwt`; enable `google`, `google-one-tap`, `api-key` via `authentication.authStrategies` |
| Teams / org membership | `organizations` service: `invite`, `updateMemberRole`, `removeMember`, `getMembers` |
| Password reset, magic links | `verifications` service (tokens never leave the server) |
| Transactional email | `sendTemplatedEmail` / `sendTextEmail`; override templates with `templatesDir` |
| "Login as" / org switching | `users.impersonate` |
| Human-readable IDs | `generateShortId(app, orgId, 'work-order', 'WO')` → `WO-2607-0001` |
| Realtime | Default tenant-scoped channels, extended through `channels` |

## Changing api-core itself

Sometimes the core has a bug, is missing something, or its docs are wrong. Its source is at https://github.com/Frozen-Crow/api-boilerplate. Every Frozen Crow API depends on it, so changes go through the maintainers first.

**First decide: is it a security problem?** Examples are an authentication or authorization bypass, data crossing between organizations, a leaked token or secret, privilege escalation, injection, or a realtime event reaching the wrong tenant. Treat anything that could expose one customer's data or access to another as one. If it might be security-sensitive, treat it as sensitive.

- **Security problem: email security@frozencrow.com.** Don't mention it in a public issue, PR, commit message, branch name or discussion. Help the developer write the report: affected version, what an attacker could do, steps to reproduce, and a suggested fix if they have one. Hold back any fix branch until the maintainers say how they want it handled. The developer sends the email; you never send it yourself.
- **Anything else: open a GitHub issue before writing code.** Don't start building a PR to the core, even a small one. Draft the issue with the developer, covering:
  - the api-core version
  - what happened and what they expected
  - a minimal reproduction
  - the change they'd propose

  The developer files it, or you run `gh issue create --repo Frozen-Crow/api-boilerplate` once they've approved the text, since it posts publicly. Build a PR only after the maintainers agree on the approach in the issue, and link the PR to the issue.

**While waiting,** work around the problem in the app through the core's extension points: `extend`, hook `extensions`, the `channels` option, or a custom `accessControl.mode`. Never patch `node_modules`, vendor a copy of the core, or point `package.json` at a fork. Leave a comment at the workaround that links the issue, so it can be removed once the fix ships.

## Production checklist

Before anything ships, confirm:

- `AUTH_SECRET` is set, strong, and at least 32 characters. The app refuses to boot in production otherwise.
- `origins` lists the real browser origins (CORS and socket.io are restricted to them).
- `mail` is configured if the app uses invites, password reset or magic links.
- The `Admin` role name is intact.

## When something conflicts

If the docs site, the installed package's types or `npx frozencrow --help` disagree with this skill, trust them, and tell the developer so the skill can be updated. Check the project's `@frozencrow/api-core` version in `package.json` too: the docs describe the latest release. If a developer explicitly wants to do something differently, follow them, but mention the standard once.
