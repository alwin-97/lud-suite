# Let Us Dream — Application Suite

Django 6.0.3 + django-allauth (Google sign-in) app for the Let Us Dream programme.
Single app `core`, SQLite, custom user `core.CustomUser`. Users are provisioned by an
admin and assigned roles per cohort (`CohortMembership`); only provisioned users can sign in.

Data hierarchy: `Program` → `Location` → `Chapter` → `Cohort` → `CohortMembership`. A program owns its whole tree (only `Location` holds the FK; chapter and cohort reach it through the location) and sets `duration_months`, which drives each cohort's `end_date`. Roles are global (`CustomUser.role = admin`) or local (`CohortMembership.role`, per cohort and so per program). A membership only grants access while the program, location, chapter and cohort are all active (`ACTIVE_MEMBERSHIP_FILTER`).

## Commands

```bash
source venv/bin/activate
python manage.py runserver          # http://127.0.0.1:8000
python manage.py test               # must stay green (19+ tests in core/tests.py)
python manage.py check
```

## Where things live

- Views: `core/views/{admin,auth,workspace}.py`, re-exported in `core/views/__init__.py`; URLs by hand in `core/urls.py`.
- Access: `@admin_required` (`core/decorators.py`) on every admin view.
- Forms: `core/forms.py`. Model forms extend `StyledModelForm`, which adds `form-control` / `checkbox-input` classes.
- Templates:
  - `templates/core/admin/base_admin.html` is the admin shell.
  - `templates/base.html` is used by the sign-in page, the member workspace and the socialaccount error pages.
  - `templates/403.html`, `404.html` and `500.html` are standalone pages.
- Shared footer: `templates/partials/site_footer.html`.
- Static:
  - `static/css/admin.css` holds the design tokens and all admin UI.
  - `static/css/login.css` styles the sign-in page, and `static/css/footer.css` the footer.
  - `static/js/admin.js` sets up DataTables, the sidebar toggle and the account menu.
- Version: `core/context_processors.app_version` gives templates `APP_VERSION` = `v1.<git commit count>`. It is computed once when the server starts. The `APP_VERSION` environment variable overrides it.

## Planned refactor — read before adding pages

`docs/component-architecture.md` is the agreed component-based plan. It is **planned, not yet implemented**; check its phase list to see what is done. When you build something new:
- Build it the way the plan describes, so later phases don't have to redo it. Use layouts, `{% include … only %}` components, `ui` template tags, `core/navigation.py`, and class-based views with shared mixins.
- Don't start a later phase unless asked.
- If the user asks you to "do phase N", follow that phase's steps and verification exactly, one commit per phase.

## Design system

The layout copies Gmail's; the colours come from the logo: leaf-green banner, blue globe, navy text.

### Colour tokens

Defined in `:root` of `static/css/admin.css`. Always use the `var(--…)` token, never a raw hex value.

| Token | Value | Use |
|---|---|---|
| `--green` / `--green-dark` | `#2e7d1f` / `#1f5c14` | primary buttons, active state, numbers, avatar |
| `--green-soft` / `--green-faint` | `#dcefd2` / `#eef7ea` | active nav pill, "Active" badge / hover and sub-nav active |
| `--blue` / `--blue-soft` | `#1a67b8` / `#e2edf9` | eyebrow labels, text links (Edit), role chips / search box |
| `--ink` / `--muted` | `#1c2733` / `#5f6b76` | body text / secondary text |
| `--danger` | `#b3261e` | Delete, errors |
| `--line` / `--line-strong` | `#e1e6ea` / `#c4ccd3` | borders / input and outline-button borders |
| `--background` / `--surface` | `#f3f7f9` / `#fff` | app background (also app bar and sidebar) / content panel and cards |
| `--hover` | `rgba(28,39,51,.06)` | hover fill for icon buttons, nav items, pagination |

The old teal palette (`#0b5d52`, `#073f38`) is retired; never reintroduce it. `login.css` repeats a subset of these tokens.

### Rules

- **Font:** Outfit (Google Fonts), weights 400 to 700. Headings use weight 600 and modest sizes: page h1 is `clamp(1.5rem, 2.4vw, 1.9rem)`, section h2 is `1.15rem`.
- **No shadows on cards or panels.** Cards are flat: `1px solid var(--line)`, radius `12px`, white. The hover state changes the fill (`--green-faint`) or the border, never adds a shadow or a transform. Only floating layers get a soft shadow: the account menu and the collapsed-sidebar flyout.
- **Radii:** content panel `16px`; cards and table cards `12px`; inputs `8px`; badges `6px`. Buttons, nav items, pagination buttons and the search box are pills (`999px`). Sidebar links are rounded on the right side only (`0 999px 999px 0`), like Gmail.
- **Shell:**
  - The sticky app bar is 64px tall. It holds the menu button (collapses the sidebar), the logo, "Let Us Dream / ADMIN", and the avatar button, which opens the account menu with Sign out.
  - The sidebar has the same colour as the background and no border.
  - Content sits on one white `.admin-surface`. The footer sits below the surface, on the background colour.
  - The collapsed sidebar is 72px wide and shows icons only; tooltips come from `data-tooltip` and the submenu pops out. At 640px and narrower it is always collapsed and the toggle is hidden.
- **Page header pattern:** every admin page starts with this block.
  ```html
  <section class="page-heading page-heading--split">   <!-- --split only when there is an action -->
      <div><p class="eyebrow">Section</p><h1>Title</h1><p>One-line description.</p></div>
      <a href="{% url '…' %}" class="button button--primary">Add …</a>
  </section>
  ```
- **Buttons:** `.button .button--primary` (solid green pill) or `.button .button--secondary` (outlined). Inline row actions are `.text-link` (blue) or `.text-button .text-button--danger` (red).
- **Badges:** `.status-badge` plus `.status-badge--active` when active, with the text "Active"/"Inactive". Roles use `.role-chip`.
- **Responsive:** use one column at 640px and narrower (`.page-heading--split` stacks, grids collapse). Keep every page usable at 400px width.
- **Sign-in page** (`login.html` / `login.css`):
  - Split screen: a green gradient intro on the left, the sign-in form on the right.
  - The form sits directly on the background, with no card.
  - "Continue with Google" is a white outlined pill.
  - "Signin with Username & Password" is centred, and the footer sits under the form inside `.login-panel`, not across the full page.
  - Tests assert the exact strings "Continue with Google", "Recommended sign-in" and "Signin with Username &amp; Password".

## Icons — Flaticon UIcons only

- Use one set only: **UIcons 3.0.0, Regular Rounded** (`fi-rr-*`). It is loaded from the CDN in `base.html`, `base_admin.html` and the 403/404/500 heads:
  ```html
  <link rel="stylesheet" href="https://cdn-uicons.flaticon.com/3.0.0/uicons-regular-rounded/css/uicons-regular-rounded.css">
  ```
- Markup: `<i class="fi fi-rr-NAME" aria-hidden="true"></i>`. Size it with `font-size` on the `.fi` element. `.fi` is `display:inline-flex; line-height:1`.
- Never use inline `<svg>`, other icon sets, or other UIcons styles (solid, bold, straight) unless the user asks.
- Check that a name exists before using it: `curl -s <css-url> | grep -c '\.fi-rr-NAME:before'`.
- Icon-only buttons need an `aria-label`. For collapsed-sidebar items, also set `data-tooltip`.
- Current mapping:

  | Where | Icon |
  |---|---|
  | menu button | `menu-burger` |
  | Dashboard | `apps` |
  | Configuration | `settings-sliders` |
  | Users | `users` |
  | submenu chevron | `angle-small-down` |
  | Sign out | `sign-out-alt` |
  | 403 / 404 / 500 | `ban` / `search` / `triangle-warning` |
  | "home" and "back" buttons | `home` / `arrow-left` |
  | login errors | `lock` |

- The Google "G" (`static/images/icons/g-logo.png`) is a brand asset and stays an image.

## Tables — always DataTables

Every data table is a DataTables 2.1.8 table (jQuery 3.7.1 + DataTables from CDN, loaded in `base_admin.html`). `static/js/admin.js` sets up every `table.data-table` with search, a rows-per-page selector (10/25/50/100) and pagination. To add one:

```html
<div class="table-card">
  <table class="data-table" data-empty-message="No widgets yet.">
    <thead><tr><th>Name</th>…<th class="actions-column">Actions</th></tr></thead>
    <tbody>{% for w in widgets %}<tr>…</tr>{% endfor %}</tbody>
  </table>
</div>
```

- **Empty rows:** never add a `{% empty %}` row with a `colspan`, because DataTables fails on it. Put the message in `data-empty-message` instead.
- **Actions column:** `th.actions-column` is excluded from sorting and search automatically.
- **Sorting:** give date and other formatted cells a sortable value, e.g. `<td data-order="{{ d|date:'Y-m-d' }}">`. All columns are left-aligned, including numbers and dates.
- **Row actions:** use `<td class="table-actions">`. Edit is a link; Delete is a POST `<form>` with a `{% csrf_token %}` and a confirm. The children are laid out with margins; never make the cell `display:flex`.

### Multi-select filters on every DataTable page

- Put the shared filter control beside the Add button in `.page-heading-actions`, inside the page heading. Use `{% include "components/table_filters.html" with table_id="widgets-table" fields="Location,Status" only %}` and give the associated table the matching unique `id`.
- Every new DataTable page must offer relevant categorical filters. Current pages: Programs — Status; Locations — Program and Status; Chapters — Program, Location and Status; Cohorts — Program, Location, Chapter and Status; Users — Role, Program, Cohort and Status.
- The control uses checkbox groups for multi-selection. Selected values within one category match **any** value (OR); separate categories must **all** match (AND). No selection means no restriction. Changes apply immediately alongside DataTables search, sorting and pagination, resetting to the first page. Show the selected-option count, matching-record count, and a Clear filters action; clearing filters preserves the text search.
- Supply exact, escaped values with `data-filter-status="Active"`, `data-filter-location="…"`, etc., on each `<tr>`. For multi-valued fields, put attributes on child elements (e.g. role chips with `data-filter-role` and `data-filter-cohort`). Field names in `fields` map to lowercase attribute suffixes. Use qualified labels for chapters/cohorts to distinguish repeated names across locations. Prefetch any related objects used by these labels in the view.
- `static/js/admin.js` builds options from **all** rows, not just the visible page, and applies a table-scoped DataTables `search.fixed()` predicate using exact values, never substring matching or user-built regexes. Options stay available after filtering. Filters start unselected on each page load. If JavaScript is unavailable, hide the control and retain the table.
- Keep the filter panel keyboard-accessible (native details/summary and labelled checkboxes), close it on Escape/outside click, and make it fit at 400px width. Use the Regular Rounded `filter` icon. Verify multiple selections, combined categories, search, clear, pagination, empty results, and desktop/mobile layouts when changing this behavior.

## Footer and version

- Include the footer on every page type with `{% include "partials/site_footer.html" %}`.
  - **Admin:** the footer comes after `.admin-surface` inside `.admin-main`. It sits at the bottom of the window on short pages and after the content on long ones.
  - **Member workspace:** the body has the `has-site-footer` class and the footer follows `<main>`.
  - **Sign-in page:** the footer goes inside `.login-panel`.
- The credit text is fixed: "Designed, Developed & Maintained by / CHRIST Infotech (Software Research & Development Center), / CHRIST University, Pune - Lavasa, India", plus the `{{ APP_VERSION }}` badge.

## Django conventions

- Every admin view: `@admin_required`. Deletes: `@require_POST`, catch `ProtectedError` and show `messages.error(... "Deactivate it instead.")`, redirect to the list page. Report success with `messages.success`.
- URL names are the contract used by templates and tests (`location_list`, `location_create`, `location_edit`, `location_delete`, …). Don't rename them without updating tests in the same change.
- Keep database queries in views. Pass annotated querysets (e.g. `chapter_count`) to templates; templates never trigger extra queries in loops (use `select_related` / `prefetch_related`).
- Templates: no inline `<style>`, no `style=""`, no inline `<svg>`. The existing inline `onsubmit="return confirm(…)"` stays until phase 2 of the plan replaces it with `data-confirm`.
- A new page extends the right base and uses the page-header pattern and existing CSS classes. Add CSS only as tokens-based rules in the matching section of `admin.css`.
- CDN assets allowed today: Google Fonts, Flaticon UIcons, code.jquery.com, cdn.datatables.net. Pin exact versions.

## Verifying UI changes

Always check a UI change visually before reporting it done:
1. Run `python manage.py test` and `python manage.py check`.
2. Render the page with seeded data inside a rolled-back transaction:
   - Use `python manage.py shell -c`, with `transaction.atomic()`, a `Client().force_login(staff_user)`, and a raised exception at the end to roll back.
   - Rewrite `/static/` to `file://$PWD/static/` in the HTML and save it to the scratchpad.
3. Screenshot the saved page with headless Chrome:
   ```bash
   google-chrome --headless=new --window-size=1400,900 --virtual-time-budget=5000 --screenshot=out.png file://…/page.html
   ```
   - Check desktop width and 400px width.
   - For the collapsed sidebar, inject `document.documentElement.classList.add('sidebar-collapsed')`.
4. Tell the user to hard-refresh (Ctrl+Shift+R) after CSS or JS changes.
