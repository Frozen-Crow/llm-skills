# @frozencrow/api-core: condensed reference

Source: https://api-core.frozencrow.com/#/docs · https://github.com/Frozen-Crow/api-boilerplate · npm `@frozencrow/api-core`, `@frozencrow/create-api`

This is a snapshot of the docs. If it disagrees with the site or the installed package's types, trust those instead.

## Contents
1. Install and bootstrap
2. Configuration options
3. Built-in services
4. Authentication
5. RBAC and multitenancy
6. The three-file service pattern
7. generateDefaultHooks / generateHooks options
8. Extending built-in services
9. CLI
10. Organizations, impersonation, invites, verifications
11. Email, serial IDs, realtime
12. Exports

---

## 1. Install and bootstrap

```bash
npm install @frozencrow/api-core          # library: Node >= 20, reachable MongoDB
npm create @frozencrow/api my-app         # or scaffold a whole project
npm create @frozencrow/api my-app -- --services posts,comments,work-orders
```

Recommended bootstrap reads `./config` via `@feathersjs/configuration`:

```ts
import { createConfiguredApp } from '@frozencrow/api-core'

const app = createConfiguredApp()
app.configure(myServices)
await app.listen(app.get('port'))
```

`config/default.json`:

```json
{
  "appName": "My API",
  "host": "localhost",
  "port": 3030,
  "public": "./public",
  "origins": ["http://localhost:5173"],
  "seed": true,
  "paginate": { "default": 10, "max": 50 },
  "mongodb": "mongodb://localhost:27017/my-api",
  "authentication": {
    "entity": "user", "service": "users", "secret": "CHANGE_ME_IN_PRODUCTION",
    "authStrategies": ["jwt", "local"],
    "jwtOptions": { "header": { "typ": "access" }, "audience": "https://example.com", "algorithm": "HS256", "expiresIn": "1d" },
    "local": { "usernameField": "email", "passwordField": "password" }
  }
}
```

Secrets go in the git-ignored `config/local.json`. Production overrides are env vars mapped in `config/custom-environment-variables.json`. No `.env` files.

Programmatic alternative (same resulting config):

```ts
import { createApp } from '@frozencrow/api-core'
const app = createApp({ mongodb: process.env.MONGODB_URI!, authSecret: process.env.AUTH_SECRET!, origins: ['http://localhost:5173'], seed: true })
```

Neither function calls `listen` for you. Both go through `configureCore(app)`.

## 2. Configuration options (`CoreOptions`)

Only `mongodb` and `authSecret` are required. Each option maps 1:1 onto a config-module key and is readable via `app.get(key)`.

| Option | Default | Notes |
|---|---|---|
| `mongodb` | — | Connection string; db name taken from the path |
| `authSecret` | — | JWT signing secret; must be strong in production |
| `appName` | `'API'` | |
| `host` / `port` | `'localhost'` / `3030` | |
| `public` | `'./public'` | Static dir; falsy disables |
| `apiHost` | — | Absolute base URL of this API (OAuth callbacks) |
| `clientHost` | — | Frontend base URL (email links) |
| `origins` | `[]` | CORS allow-list (REST + socket.io) |
| `paginate` | `{ default: 10, max: 50 }` | |
| `jwtOptions` | 1d, HS256 | Merged into `authentication.jwtOptions` |
| `apiKeys` | — | Accepted by the `api-key` strategy |
| `oauth` | — | `{ google: { key, secret, scope? }, redirect? }` |
| `authentication` | — | Deep overrides merged last |
| `mail` | — | `{ host, port, secure?, auth?, from?, fromName? }` |
| `seed` | off | `true` seeds Admin/Member; `{ roles }` customizes |
| `templatesDir` | bundled | Directory of `.dot` templates |
| `defaultOrgName` | `"…'s Organization"` | `(user) => string` for the auto-created org |
| `services` | all | Subset of built-in services to register |
| `channels` | tenant-scoped | Extend (object), replace (fn) or disable (`false`) |
| `extend` | — | Add fields/resolvers/hooks to built-in services |
| `bodyParser` | 1MB | Koa body-parser options, e.g. `jsonLimit` |

The config schema (`configurationValidator`) allows extra keys. Pass a custom validator to `createConfiguredApp(validator)` to type them.

## 3. Built-in services

| Path | Purpose | Notable methods |
|---|---|---|
| `users` | Accounts; `restrictToUser` externally; roles populated on read | find, get, create, patch, remove, `impersonate` |
| `organizations` | Tenants: `members[]` of `{ userId, role, joinedAt }`, `ownerId`, `onboarded` | standard + `invite`, `removeMember`, `updateMemberRole`, `getMembers` |
| `roles` | `{ name, permissions[] }`, world-readable | standard |
| `invites` | Org invitations (email or link), backed by a verification token | standard |
| `verifications` | Reset / magic-link / invite tokens; external reads blocked | create, patch |
| `serial-ids` | Atomic per-org counters behind `generateShortId` | standard + `next` |

A new user with no organization gets one automatically (as its Admin) on first authentication (`ensureUserHasOrganization`).

## 4. Authentication

Registered strategies: `jwt`, `local`, `google`, `google-one-tap`, `api-key`, `anonymous`. The default `authStrategies` is `['jwt', 'local']`. Extend it to allow more:

```ts
createApp({
  mongodb, authSecret,
  apiKeys: ['service-key-123'],
  oauth: { google: { key: GOOGLE_CLIENT_ID, secret: GOOGLE_CLIENT_SECRET } },
  authentication: { authStrategies: ['jwt', 'local', 'api-key', 'google'] }
})
```

- **Local:** `POST /authentication { "strategy": "local", "email", "password" }` → `{ accessToken, user }`. Send `Authorization: Bearer <accessToken>` after that. Passwords are always stripped from responses.
- **API key:** `Authorization: <one-of-apiKeys>` with the `api-key` strategy.
- **Google One Tap:** `POST /authentication { strategy: 'google-one-tap', credential }`.
- **Anonymous:** used internally so services can opt into public access (`allowAnonymous`).

## 5. RBAC and multitenancy

Permissions are strings: exact `"<path>:<method>"`, path wildcard `"<path>:*"`, or global `"*"`.

- **Global admin:** the user's populated roles include one named `Admin` (case-insensitive). Global admins bypass tenant scoping. Check with `isGlobalAdmin(user)`.
- **Org role:** within `activeOrganization`, permissions come from the role in that org's `members[]` entry.

`teamAccessControl` (applied by `generateDefaultHooks`) checks on every request that the user is authenticated, is a member of the active org, and holds `<path>:<method>`. For reads and writes it also constrains the query to `organizationId === activeOrganization`, and on create it stamps the active organization.

For custom methods:

```ts
import { isGlobalAdmin, assertOrgMembership, assertOrgPermission } from '@frozencrow/api-core'
await assertOrgMembership(app, user, organizationId)
await assertOrgPermission(app, user, organizationId, 'widgets:patch')
```

Seeded roles (`seed: true`): Admin `['*']`; Member `['users:get','users:patch','organizations:get','organizations:find']`.

## 6. The three-file service pattern

`widgets.schema.ts`:

```ts
import { resolve } from '@feathersjs/schema'
import { Type, getValidator, querySyntax, ObjectIdSchema } from '@feathersjs/typebox'
import type { Static } from '@feathersjs/typebox'
import { dataValidator, queryValidator, type HookContext } from '@frozencrow/api-core'

export const widgetSchema = Type.Object({
  _id: ObjectIdSchema(),
  name: Type.String(),
  organizationId: ObjectIdSchema(),
  createdAt: Type.Number(),
  updatedAt: Type.Number()
}, { $id: 'Widget', additionalProperties: false })
export type Widget = Static<typeof widgetSchema>

// Server-set fields must be permitted here: resolveData runs before validateData.
export const widgetDataSchema = Type.Intersect([
  Type.Pick(widgetSchema, ['name']),
  Type.Object({
    organizationId: Type.Optional(ObjectIdSchema()),
    createdAt: Type.Optional(Type.Number()),
    updatedAt: Type.Optional(Type.Number())
  })
], { $id: 'WidgetData' })
export type WidgetData = Static<typeof widgetDataSchema>

export const widgetDataValidator = getValidator(widgetDataSchema, dataValidator)
export const widgetDataResolver = resolve<Widget, HookContext>({
  organizationId: async (v, _d, ctx) => v || (ctx.params as any).user?.activeOrganization,
  createdAt: async () => Date.now(),
  updatedAt: async () => Date.now()
})
// patch + query schemas/validators/resolvers follow the same shape
```

`widgets.class.ts`:

```ts
import { MongoDBService } from '@feathersjs/mongodb'
import type { MongoDBAdapterOptions } from '@feathersjs/mongodb'
import type { Application } from '@frozencrow/api-core'
import type { Widget, WidgetData, WidgetPatch, WidgetQuery } from './widgets.schema'

export class WidgetService extends MongoDBService<Widget, WidgetData, any, WidgetPatch> {}

export const getOptions = (app: Application): MongoDBAdapterOptions => ({
  paginate: app.get('paginate'),
  Model: (app.get('mongodbClient') as Promise<any>).then((db) => db.collection('widgets'))
})
```

`widgets.ts`:

```ts
import { generateDefaultHooks } from '@frozencrow/api-core'
import type { Application } from '@frozencrow/api-core'
import { WidgetService, getOptions } from './widgets.class'
import * as schema from './widgets.schema'

export const widgetPath = 'widgets'

declare module '@frozencrow/api-core/lib/declarations' {
  interface ServiceTypes { widgets: WidgetService }
}

export const widgets = (app: Application) => {
  app.use(widgetPath, new WidgetService(getOptions(app)), {
    methods: ['find', 'get', 'create', 'patch', 'remove'],
    events: []
  })
  app.service(widgetPath).hooks(generateDefaultHooks({
    schema: {
      dataValidator: schema.widgetDataValidator,
      patchValidator: schema.widgetPatchValidator,
      queryValidator: schema.widgetQueryValidator,
      dataResolver: schema.widgetDataResolver,
      patchResolver: schema.widgetPatchResolver,
      queryResolver: schema.widgetQueryResolver,
      resultResolver: schema.widgetResolver,
      externalResolver: schema.widgetExternalResolver
    }
  }))
}
```

Then `app.configure(widgets)`. The service is now JWT-protected, tenant-scoped, validated, and requires `widgets:<method>`.

## 7. generateDefaultHooks / generateHooks options

`generateDefaultHooks` is `generateHooks` with `teamAccessControl` as the default mode.

| Option | Default | Description |
|---|---|---|
| `schema` | — | Any subset of `{ dataValidator, patchValidator, queryValidator, dataResolver, patchResolver, queryResolver, resultResolver, externalResolver }` |
| `methods` | all 6 | Service methods to wire |
| `requireAuth` | `true` | Adds `authenticate('jwt', 'anonymous')` |
| `accessControl.mode` | `teamAccessControl` | `teamAccessControl`, `'restrictToUser'`, `'forbidden'`, `'ignore'`, or `(context) => …` |
| `accessControl.methods` | all 6 | Methods access control applies to |
| `accessControl.restrictToUserFrom` / `restrictToUserAs` | `params.user._id` / `params.query.userId` | For `restrictToUser` |
| `allowAnonymous` | `false` | Permit unauthenticated access |
| `discardVirtuals` | `['create','update','patch']` | Strip virtual props before persistence |
| `logErrors` | `true` | Wrap methods in error logging |
| `overrides` | — | Replace a hook slot, e.g. `{ before: { all: [...] } }` |
| `extensions` | — | Append to a hook slot, e.g. `{ before: { create: [myHook] } }` |

Public, non-tenant service:

```ts
generateDefaultHooks({ schema, requireAuth: false, allowAnonymous: true, accessControl: { mode: 'ignore' } })
```

## 8. Extending built-in services

```ts
import { Type } from '@feathersjs/typebox'

createConfiguredApp({
  extend: {
    users: {
      properties: {                                   // stored + returned; CLIENT-WRITABLE
        phone: Type.Optional(Type.String()),
        stripeCustomerId: Type.Optional(Type.String())
      },
      queryProperties: { phone: Type.String() },      // filterable
      resolvers: {
        data: { source: async (v) => v ?? 'signup' },
        result: { displayName: async (_v, u) => `${u.firstName} ${u.lastName}` }
      },
      hooks: { after: { create: [syncToCrm] } }
    }
  }
})
```

Keys are service paths: `users`, `organizations`, `roles`, `invites`, `verifications`. Declare the types once:

```ts
declare module '@frozencrow/api-core/lib/declarations' {
  interface UserExtensions { phone?: string; stripeCustomerId?: string }
}
```

The matching interfaces are `UserExtensions`, `OrganizationsExtensions`, `RolesExtensions`, `InvitesExtensions` and `VerificationsExtensions`. `additionalProperties: false` still holds for anything not declared.

## 9. CLI (`frozencrow`, ships with api-core)

```bash
npx frozencrow generate service invoices --fields "amount:number,paid?:boolean" --wire
npx frozencrow generate hook audit-log
npx frozencrow secret --write
npx frozencrow list services
```

| Command | Description |
|---|---|
| `generate service <name>` (`g s`) | Creates `<name>.schema.ts`, `<name>.class.ts` and the registration file |
| `generate hook <name>` (`g h`) | Hook stub under `src/hooks` |
| `secret` | Prints a strong secret; `--write` sets `authentication.secret` in `config/local.json` |
| `list services` (`ls`) | Lists services in the project |

`generate service` flags:

| Flag | Default | Notes |
|---|---|---|
| `--fields "a:string,b:number"` | `name:string` | `string`, `number`, `boolean`, `integer`; `?` suffix = optional |
| `--access team\|user\|public` | `team` | team = multitenant, user = owner-scoped, public = anonymous read/write |
| `--wire` | off | Adds the import + `app.configure(...)` to `src/app.ts` |
| `--dir <path>` | `src/services` | |
| `--force` | off | Overwrite existing files |

Scaffolded projects also have `npm run generate` and `npm run secret`.

## 10. Organizations, impersonation, invites, verifications

The organizations custom methods require membership plus `organizations:patch`, or global admin:

```ts
await app.service('organizations').invite({ organizationId, roleId, email, inviteType: 'email' }, { user })
await app.service('organizations').updateMemberRole({ organizationId, userId, roleId }, { user })
await app.service('organizations').removeMember({ organizationId, userId }, { user })
await app.service('organizations').getMembers({ organizationId }, { user })
```

- **Impersonation:** `users.impersonate({ userId, organizationId }, { user })` → `{ accessToken }`. Global admins can impersonate anyone into any org. Everyone else can only refresh their own session into an org they belong to.
- **Invites:** to accept, `patch` the invite to `status: 'accepted'`. An email invite requires a matching email; a link invite accepts any authenticated user. Expired or consumed invites are rejected.
- **Verifications:** external `create` is allowed for `magic-link` and `password-reset` (`invite` is server-only). Reset a password by `patch`ing with `{ token, password }` (no id). Look tokens up server-side with `verificationsService.verifyToken(app, token, type)`. External find, get and remove are blocked.

## 11. Email, serial IDs, realtime

```ts
import { sendTemplatedEmail, sendTextEmail, generateShortId } from '@frozencrow/api-core'

await sendTemplatedEmail('user@example.com', 'welcome', { name: 'Ada' }, app, { subject: 'Welcome!' })
await sendTextEmail('user@example.com', 'Hi', 'Plain body', app)

const id = await generateShortId(app, organizationId, 'work-order', 'WO')   // "WO-2607-0001"
```

The bundled templates are `welcome`, `invitation`, `notification` and `password-reset`, wrapped by `layout.{html,text}.dot`. `appName`, `clientUrl` and `logoUrl` are injected automatically. Replace the whole set with `templatesDir`.

**Realtime.** On login, a connection joins the `authenticated`, `userId/<id>` and `org/<activeOrganization>` channels. Each event is published only to its organization (or to the affected user, for user events).

```ts
createConfiguredApp({
  channels: {
    onConnection: (connection, app) => app.channel('lobby').join(connection),
    onLogin: (authResult, connection, app) => app.channel(`team/${authResult.user.teamId}`).join(connection),
    publish: (data, context) => {
      if (context.path === 'announcements') return context.app.channel('authenticated')
      // returning undefined falls through to the tenant-scoped default
    }
  }
})
```

To replace the setup, pass `channels: (app) => { ... }`; to disable it, pass `channels: false` and build your own from `configureChannels`, `defaultPublisher` and `buildPublisher`. Per-service publishers (`app.service('x').publish(...)`) override the global one.

## 12. Exports

- **App:** `createConfiguredApp`, `createApp`, `configureCore`, `resolveConfiguration`, `configurationValidator`, `CoreOptions`, `ConfiguredAppOptions`
- **Channels:** `configureChannels`, `defaultPublisher`, `buildPublisher`, `ChannelsOptions`
- **Services:** `coreServices`, `services`, `ALL_CORE_SERVICES`, plus `usersService`, `organizationsService`, `rolesService`, `invitesService`, `verificationsService` and `serialIdsService`
- **Extending:** `resolveServiceSchema`, `withExtensionHooks`, `ServiceExtension`, `CoreExtend`
- **Hooks & access:** `generateHooks`, `generateDefaultHooks`, `teamAccessControl`, `isGlobalAdmin`, `assertOrgMembership`, `assertOrgPermission`, `populateUserRoles`, `preventRoleChange`, `filterOrganizationsByMembership`, `filterUsersByOrganization`, `setupOrganization`, `ensureUserHasOrganization`
- **Strategies:** `CustomJWTStrategy`, `ApiKeyStrategy`, `AnonymousStrategy`, `GoogleStrategy`, `GoogleOneTapStrategy`
- **Utilities:** `generateShortId`, `sendTemplatedEmail`, mail helpers, `logger`, `dataValidator`, `queryValidator`
- **Types:** `Application`, `HookContext`
- **Client entry:** `@frozencrow/api-core/client`
