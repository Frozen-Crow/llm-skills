---
name: wordpress-standards
description: Frozen Crow WordPress standards — build and edit WordPress sites through WP MCP Connector (wpmcp.frozencrow.com). Working directly against production is fine for an initial build, but recommend a staging clone before any large change to a live site. Use this skill whenever a Frozen Crow developer is building, editing or maintaining a WordPress site, including pages, posts, custom post types, page-builder layouts (Elementor, Divi, Bricks, BeTheme/Muffin, Beaver Builder, Oxygen, WPBakery, Fusion, block editor), themes and child themes, custom plugins, WooCommerce products, options, custom CSS or media. Also use it whenever wp_* MCP tools such as wp_get_site_info are connected, even if the developer doesn't mention the connector.
---

# Frozen Crow WordPress Standards

Two standards:

1. **Build through WP MCP Connector.** All WordPress work goes through the connector's `wp_*` MCP tools, not FTP, clicking through wp-admin, or direct database edits. The connector reads and writes nine page builders in their own storage format, runs each builder's cache invalidation, and logs every write.
2. **Match the risk to the site.** Working directly against production is fine for an **initial build**. For **large changes to a live site**, recommend a staging clone first.

## Step 0: Connect and confirm the site

The connector's tools are named `wp_get_site_info`, `wp_get_posts` and so on, usually prefixed with the server's name in some form, depending on the editor. Several sites may be connected at once, so:

- **Call `wp_get_site_info` on the server you're about to use, and confirm the name and URL match the task before any write.** Note the active theme, detected builders and enabled write roots.
- **If no connector is connected,** walk the developer through setup one step at a time:
  1. Install the connector zip on the site (**Plugins → Add New → Upload Plugin**) and activate it. A unique API key is generated.
  2. Open **Dashboard → MCP** for the endpoint, key and a ready-made config block.
  3. The developer adds the server to their editor's MCP config. It's an HTTP server at `https://<site>/wp-json/custom-mcp/v1/mcp` with the key in an `x-custom-mcp-api-key` header. Each editor has a step-by-step guide at `https://wpmcp.frozencrow.com/docs/<editor>/` (claude-code, cursor, windsurf, vs-code, cline, zed, gemini-cli, antigravity, codex). In Claude Code, for example:
     ```bash
     claude mcp add --scope user --transport http acme-wp https://acme.com/wp-json/custom-mcp/v1/mcp --header "x-custom-mcp-api-key: <key from Dashboard → MCP>"
     ```
  4. Reload the editor's MCP servers, then call `wp_get_site_info`.
- **The API key is a server credential.** With a write root enabled, it can put executable PHP on the server. The developer runs the command themselves: never ask for the key in chat, and never commit it. Use the editor's user-level MCP config, or a project config file that's git-ignored. This follows the dev-standards secret rules.
- **Name servers by site and environment,** like `acme-wp` and `acme-staging-wp`, so production and staging can't be confused.

## Step 1: Initial build or live site?

Decide this before the first write, and ask if it isn't obvious:

- **Initial build:** the site hasn't launched, and has no real visitors, orders or form submissions. Working directly against production is fine.
- **Live site, small change:** editing copy on a page, adding or updating a post, uploading media, fixing a typo, or a single contained setting. Doing this directly is fine, after saving a copy of what you're replacing.
- **Live site, large change: recommend a staging clone first.** Large means any of:
  - redesigning or rebuilding layouts, especially the home page, header, footer or templates
  - edits across many pages, posts or products (bulk updates, catalog or taxonomy restructuring)
  - writing or changing plugin or theme code, or activating or deactivating plugins
  - site-wide settings: options, theme mods, permalinks, global custom CSS
  - anything that would be hard to undo

  If you're unsure whether a change is large, treat it as large.

Recommend staging; don't block. Explain the risk in one line: on a live site, a broken layout or a fatal PHP error is in front of every visitor immediately. If the developer still chooses to work on production, proceed in small steps with a backup before each one.

### Staging clone workflow

1. **The developer creates the clone** with their host's staging tool (most managed hosts have one-click staging) or a migration plugin.
2. **Regenerate the connector key on the clone** (Dashboard → MCP). A clone copies the database, so it starts with production's key. Add the clone as its own server (`acme-staging-wp`).
3. **Confirm you're on staging** with `wp_get_site_info` (check the URL) before writing anything.
4. **Build and verify on staging.**
5. **Promote deliberately.** A full database push from staging overwrites everything that changed on production since the clone was made, including orders, form entries, comments and new users. On any site that takes in data, push files only, or re-apply the changes to production through the connector. Agree the approach with the developer.

## Working rules

- **Read before you write.** Fetch the current post, layout or option before updating it. On a live site, save what you're about to replace (for example the `wp_get_builder_data` output) to a local backup file so it can be restored.
- **Builder layouts only go through `wp_get_builder_data` / `wp_update_builder_data`.** These detect the builder's encoding and run its cache invalidation. Never write builder-managed pages with `wp_update_post_meta` or raw `post_content`. Edit the decoded layout and leave the structure and IDs you aren't changing alone.
- **Stay in the site's builder.** Edit an Elementor page in Elementor's format, and build new pages with the builder the site already uses. Don't mix builders on one site.
- **Check terms before assigning them.** Call `wp_get_terms` first: `wp_set_post_terms` creates any name that doesn't exist, so a typo becomes a duplicate category or tag.
- **Custom code goes in a site plugin or a child theme.** Put functionality in a site-specific plugin (`wp-content/plugins/<site>-custom/`) and template or style overrides in a child theme. Never edit a parent theme or a third-party plugin, because updates overwrite those edits.
- **Write roots are off until the developer turns them on.** Roots (`plugins`, `themes`, `mu-plugins`, `uploads`) can only be enabled in wp-admin (Dashboard → MCP). Ask for just the root the job needs, and remind the developer to switch it off afterward.
- **PHP can take a site down.** One syntax error in an active plugin can blank the whole site. Write complete files. If PHP is available locally, run `php -l` on the file before writing it. Activate with `wp_set_plugin_active` only once the code is finished.
- **Confirm before destructive or site-breaking actions:** `wp_delete_post`, `wp_delete_term`, `wp_delete_file`, deactivating plugins, and the options `siteurl`, `home`, `permalink_structure`, `active_plugins`, `template` and `stylesheet`. A wrong value there can take the site offline or break every URL.
- **Verify on the front end.** After a change, load the page in a browser at desktop and mobile widths. Builder caches and CSS don't always show up in the data.
- **There's an audit log.** Every write is recorded in Dashboard → MCP with the tool, target and source address. Point the developer there if they need to see what changed.

## Tool reference

| Area | Tools |
|---|---|
| Site & settings | `wp_get_site_info`, `wp_get_option` / `wp_update_option`, `wp_get_theme_mods` / `wp_update_theme_mod`, `wp_get_custom_css` / `wp_update_custom_css` |
| Content | `wp_get_posts`, `wp_get_post`, `wp_get_post_types`, `wp_create_post`, `wp_update_post`, `wp_delete_post`, `wp_get_post_meta` / `wp_update_post_meta` / `wp_delete_post_meta` |
| Media | `wp_upload_media`, `wp_get_media` |
| Taxonomies | `wp_get_taxonomies`, `wp_get_terms`, `wp_set_post_terms` (by name or id, replace or append), `wp_delete_term` |
| Page builders | `wp_get_builder_data` (detects builder; returns decoded layout, storage location, encoding), `wp_update_builder_data` (re-encodes, invalidates caches). Both accept an explicit `meta_key` for unknown builders |
| Files & plugins | `wp_list_files`, `wp_read_file`, `wp_write_file`, `wp_delete_file` (enabled roots only; extensions: php, js, css, json, txt, md, svg, html, htm, xml, csv, po, pot, mo), `wp_list_plugins`, `wp_set_plugin_active`, `wp_list_themes` |

**Extending the connector:** register an unknown builder with the `custom_mcp_builders` filter (`label`, `store`, `meta_key`, `after_save`), or add tools with `custom_mcp_tools` (advertise) and `custom_mcp_execute_tool` (handle; return non-null to claim the call).

**Troubleshooting:** a `401 Invalid API Key` means the config doesn't match Dashboard → MCP, often because the key was regenerated. If tools don't appear, fully restart the editor. If the site uses an IP allowlist, the developer's current address must be on it.

## When something conflicts

If the connector's docs (https://wpmcp.frozencrow.com/docs/) or changelog disagree with this skill, trust them, and tell the developer so the skill can be updated. If a developer explicitly wants to work differently, follow them, but mention the standard once.
