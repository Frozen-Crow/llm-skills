---
name: frontend-standards
description: Frozen Crow frontend standards — Nuxt or Next for marketing sites that need SEO, Vue or React single-page apps for app clients that stay decoupled from the API, a shared folder of reusable layouts and components built with Tailwind CSS and Headless UI, and a Feathers client (REST or websockets, the developer's choice) for talking to @frozencrow/api-core APIs. Use this skill whenever a Frozen Crow developer is starting or changing a website, landing page, marketing site, web app, dashboard or admin panel; choosing a frontend framework; building pages, layouts or UI components; styling with Tailwind; or connecting a frontend to a Feathers or api-core backend (login, data fetching, realtime updates) — even if they don't name the stack.
---

# Frozen Crow Frontend Standards

Three standards:

1. **Pick the stack by what the site is for.** Use SEO-first frameworks for marketing sites, and single-page apps for app clients that stay decoupled from the API.
2. **Build from shared layouts and components.** Everything is built with Tailwind and Headless UI, and nothing is written twice.
3. **Talk to our APIs through a Feathers client** over the transport the developer chooses.

## 1. Choose the stack

| Building | Use | Why |
|---|---|---|
| Marketing site, landing pages, blog: anything that has to rank | **Nuxt** (Vue) or **Next** (React) | Server rendering and static generation give crawlers real HTML, meta tags and a fast first paint |
| App client: dashboard, admin, logged-in product | **Vue** or **React** single-page app (Vite) | The client stays decoupled from the API, so each deploys and scales on its own and the API can serve other clients too |

- **If it's unclear which kind of project it is, ask.** If a product needs both, build two projects (for example a Nuxt site at `example.com` and a Vue app at `app.example.com`) rather than stretching one framework over both.
- **Vue or React:** match the existing project, or the client's other projects. For something new, ask the developer. Keeping a product's site and app in the same family (Nuxt + Vue, or Next + React) lets them share components.
- **Business logic lives in the API,** not in Nuxt server routes or Next route handlers and server actions. The SSR framework renders pages; data and rules belong to the API layer (see api-standards).
- **SEO basics on marketing sites:** set a title, description and Open Graph tags on every page (Nuxt `useSeoMeta`, Next `metadata` / `generateMetadata`). Statically generate pages whose content doesn't change per request, ship a sitemap, use semantic HTML, and use the framework's image component.

## 2. Shared layouts and components (modular and DRY)

Every project has one home for reusable UI:

```
layouts/              page shells: MarketingLayout, AppLayout, AuthLayout
components/
  ui/                 primitives: Button, Input, Select, Modal, Dropdown, Tabs, Badge…
  <feature>/          composed pieces built from ui/ primitives
```

Put this under `src/` in a Vite app. Nuxt uses its own `layouts/` and `components/` directories (under `app/` in Nuxt 4), which are auto-imported. In Next, the route `layout.tsx` files compose shells from `components/layouts/`.

- **Look before you build.** Search `components/` and `layouts/` before writing a new component. If something close exists, extend it with a prop or variant instead of copying it.
- **Pages compose, components style.** Pages assemble layouts and components. A long Tailwind class string in a page usually means a component is missing. Extract one the second time the same markup appears.
- **Use Tailwind for all styling.** Define colors, fonts and spacing once in the Tailwind theme and use those tokens; never hardcode hex values. Don't recreate component classes with `@apply` or stylesheets; make a component instead. Use the Tailwind version already in the project, and for a new project follow Tailwind's current install guide for the framework.
- **Variants are props.** Use props like `variant="primary"` and `size="sm"`, mapped to class sets in one place inside the component.
- **Use Headless UI for anything interactive.** Use `@headlessui/vue` or `@headlessui/react` for dialogs, menus, listboxes, comboboxes, popovers, tabs, switches and disclosures. Don't hand-roll these: Headless UI handles focus, keyboard navigation and ARIA. Wrap each one in a styled `components/ui/` primitive so the rest of the app uses `<Modal>` instead of raw `Dialog`.
- **Make everything responsive and accessible by default.** Use mobile-first breakpoints, labels on every input, alt text on images, and visible focus states.

## 3. Connecting to an api-core API

**Ask first: REST or websockets?** Don't pick for the developer. Give them the trade-off in a line each and build to their answer:

- **REST:** plain HTTP requests. It's the simplest option, works during server rendering, and has no live updates.
- **Websockets (Socket.io):** a persistent connection that also receives realtime events. api-core already scopes those events to the user's organization. Good for dashboards and live views.

Then build the integration around api-core's own typed client, `createClient` from `@frozencrow/api-core/client`, which already registers the core services (`users`, `organizations`, `roles`, `invites`, `verifications`):

```bash
npm install @frozencrow/api-core @feathersjs/feathers
npm install @feathersjs/rest-client                       # REST
npm install @feathersjs/socketio-client socket.io-client  # websockets
```

- **One module owns the client** (`src/lib/feathers.ts`, a Nuxt plugin, or `lib/feathers.ts` in Next). Register the app's own services there with their methods, and type them by augmenting `ServiceTypes` from `@frozencrow/api-core/client`.
- **Wrap data access** in composables (Vue/Nuxt) or hooks (React), like `useInvoices()`, so components never call `client.service(...)` directly and the same query isn't written twice.
- **Read the API URL from config,** never hardcode it: `VITE_API_URL`, `NEXT_PUBLIC_API_URL`, or Nuxt `runtimeConfig.public`. Make sure the client's origin is in the API's `origins`, or CORS will block it.
- **Authentication:** call `client.authenticate(...)` to log in, `client.reAuthenticate()` on app start, and `client.logout()` to log out. Authenticated calls happen in the browser. Server-rendered marketing pages fetch public data only, so one user's session can't leak into another's render.
- **Realtime (websockets only):** subscribe with `service.on('created', fn)` and always remove the listener when the component unmounts.
- **Errors:** handle `NotAuthenticated` (401) by sending the user to login. A `Forbidden` (403) means the user's role lacks `<path>:<method>`; fix that in the API's roles, not by hiding the error.

`references/feathers-client.md` has the full client module for Vite, Nuxt and Next, both transports, service typing, auth flows (including switching organizations) and realtime cleanup.

## When something conflicts

If a project already follows a different structure, follow it, but point out the standard once so it's a conscious choice. If a framework or library API has moved on from what's written here, trust its current docs and tell the developer so the skill can be updated.
