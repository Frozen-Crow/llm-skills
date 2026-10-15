# Feathers client for api-core APIs

`@frozencrow/api-core/client` exports `createClient(connection, authenticationOptions?)`. It configures the transport and the authentication client, and registers the core services with their custom methods (`users.impersonate`, `organizations.invite`, and so on). The app adds its own services on top.

Source: https://github.com/Frozen-Crow/api-boilerplate (`packages/api-core/src/client.ts`) · Feathers client docs: https://feathersjs.com/api/client

## Contents
1. Client module: Vite single-page app
2. Client module: Nuxt
3. Client module: Next
4. Registering and typing app services
5. Authentication flows
6. Realtime events
7. Errors

---

## 1. Client module: Vite single-page app

`src/lib/feathers.ts`, **REST**:

```ts
import rest from '@feathersjs/rest-client'
import { createClient } from '@frozencrow/api-core/client'

const connection = rest(import.meta.env.VITE_API_URL).fetch(window.fetch.bind(window))

export const client = createClient(connection)
```

`src/lib/feathers.ts`, **websockets**:

```ts
import { io } from 'socket.io-client'
import socketio from '@feathersjs/socketio-client'
import { createClient } from '@frozencrow/api-core/client'

const socket = io(import.meta.env.VITE_API_URL, { transports: ['websocket'] })

export const client = createClient(socketio(socket))
```

In the browser, the authentication client stores the JWT in `localStorage` by default. To change that, pass `createClient(connection, { storage, storageKey })`.

## 2. Client module: Nuxt

Set the URL in `nuxt.config.ts` under `runtimeConfig: { public: { apiUrl: '' } }`. It is filled from `NUXT_PUBLIC_API_URL`.

**Websockets** must be client-only, because a socket can't run during server rendering. Use `plugins/feathers.client.ts`:

```ts
import { io } from 'socket.io-client'
import socketio from '@feathersjs/socketio-client'
import { createClient } from '@frozencrow/api-core/client'

export default defineNuxtPlugin(() => {
  const { public: { apiUrl } } = useRuntimeConfig()
  const client = createClient(socketio(io(apiUrl, { transports: ['websocket'] })))
  return { provide: { feathers: client } }
})
```

**REST** can run on both sides for public data. Use `plugins/feathers.ts`:

```ts
import rest from '@feathersjs/rest-client'
import { createClient } from '@frozencrow/api-core/client'

export default defineNuxtPlugin(() => {
  const { public: { apiUrl } } = useRuntimeConfig()
  const client = createClient(rest(apiUrl).fetch(globalThis.fetch.bind(globalThis)))
  return { provide: { feathers: client } }
})
```

Use it as `const { $feathers } = useNuxtApp()`, inside composables in `composables/`.

## 3. Client module: Next

`lib/feathers.ts`, REST for public data in server components and route rendering:

```ts
import rest from '@feathersjs/rest-client'
import { createClient } from '@frozencrow/api-core/client'

export const client = createClient(
  rest(process.env.NEXT_PUBLIC_API_URL!).fetch(globalThis.fetch.bind(globalThis))
)
```

This module-level client is shared by every request on the server, so **never authenticate it server-side**. Logged-in calls and websockets belong in a `'use client'` module that creates its client in the browser, in the same way as the Vite example.

## 4. Registering and typing app services

Core services come pre-registered. Register each app service in the client module, following the same pattern api-core uses for its own:

```ts
import type { ClientService } from '@feathersjs/feathers'
import type { Invoice, InvoiceData, InvoicePatch } from '…'   // the API's invoices.schema.ts types

declare module '@frozencrow/api-core/client' {
  interface ServiceTypes {
    invoices: ClientService<Invoice, InvoiceData, InvoicePatch>
  }
}

client.use('invoices', client.get('connection').service('invoices'), {
  methods: ['find', 'get', 'create', 'patch', 'remove']
})
```

- **List every method the client calls,** including custom methods (`methods: [..., 'approve']`), and add them to the type: `ClientService<...> & { approve(data: ApproveData): Promise<Invoice> }`.
- **Types come from the API's `<name>.schema.ts`** (its exported `Static<>` types). If the API repo can't be imported from the client (as a workspace package, a path alias, or a published types package), ask the developer how they want to share types. Don't invent shapes.

Then wrap access in a composable or hook:

```ts
// Vue: composables/useInvoices.ts
export const useInvoices = () => {
  const invoices = client.service('invoices')
  return {
    list: (query = {}) => invoices.find({ query }),
    create: (data: InvoiceData) => invoices.create(data)
  }
}
```

## 5. Authentication flows

```ts
// Log in (email + password)
const { user, accessToken } = await client.authenticate({ strategy: 'local', email, password })

// On app start: restore the stored session; throws if there isn't a valid one
try { await client.reAuthenticate() } catch { /* show login */ }

// Log out
await client.logout()

// Sign up, then log in
await client.service('users').create({ email, password })
await client.authenticate({ strategy: 'local', email, password })

// Switch the active organization (must be a member): impersonate yourself into it
const { accessToken: orgToken } = await client.service('users').impersonate({ userId: user._id, organizationId })
await client.authenticate({ strategy: 'jwt', accessToken: orgToken })
```

- New users get an organization automatically on first login.
- Password reset and magic links go through the `verifications` service, and invites through `organizations.invite` and `invites`. Check the api-core docs (https://api-core.frozencrow.com/#/docs) for the payloads.

## 6. Realtime events (websockets only)

```ts
const invoices = client.service('invoices')
const onCreated = (invoice: Invoice) => { /* update local state */ }

invoices.on('created', onCreated)        // also: 'updated', 'patched', 'removed'
// on unmount (Vue onUnmounted / React effect cleanup):
invoices.removeListener('created', onCreated)
```

api-core only publishes an event to the organization it belongs to, so the client never sees another tenant's events.

## 7. Errors

Feathers errors arrive with `name`, `code` and `message`; validation errors also carry `data`.

| `name` (`code`) | Meaning | Handle by |
|---|---|---|
| `NotAuthenticated` (401) | No session, or it expired | Clearing state and sending the user to login |
| `Forbidden` (403) | Role lacks `<path>:<method>`, or not a member of the org | Showing a no-access state; fix permissions in the API's roles |
| `BadRequest` (400) | Validation failed | Mapping `data` onto form fields |
| `NotFound` (404) | Missing, or in another organization | A not-found state |
