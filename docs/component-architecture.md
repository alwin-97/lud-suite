# Component architecture plan

Status: **planned, not yet implemented.** Current templates still use `templates/base.html`, `templates/core/admin/base_admin.html` and `templates/partials/site_footer.html`. Work through the phases in order. Each phase is one commit and keeps `python manage.py test` green.

Chosen approach: **Django-native components, right-sized: layouts + include/only + a small ui tag library + 6.0 partials, thin CBV CRUD, zero new dependencies**

Use only Django 6.0.3 built-ins, choosing the lightest mechanism per component. {% include 'components/x.html' with ... only %} handles plain markup. An inclusion_tag handles components that need Python (csrf, reverse, active nav state). A simple_block_tag handles wrappers with a slot. {% partialdef %} handles page-local fragments and the icon set. Three layouts (base, admin shell, centered) remove all duplicated <html>/<head>/inline <style>. A NavItem list in core/navigation.py drives the sidebar by URL name. On the Python side, 12 near-copy Location/Chapter/Cohort views become explicit thin CBV subclasses over three mixins plus a crud_urls() helper. Forms render through one project field template. A RoleRequiredMixin prepares for the coming role workspaces. URL names, page text and CSS class names stay the same, so the 19 existing tests stay green at every phase.

> Icon decision (2026-09-30): the project uses **Flaticon UIcons** (regular-rounded) instead of the inline-SVG `components/icons.html` partials described in the original plan. Everything else stands.

## Target directory layout

```text
templates/
  layouts/base.html  layouts/admin.html  layouts/centered.html
  components/
    shell/app_bar.html  shell/account_menu.html  shell/sidebar.html  shell/site_footer.html
    brand_mark.html flash_messages.html page_header.html data_table.html row_actions.html
    role_chip.html cell_stack.html stat_card.html link_card.html section_heading.html status_card.html
    forms/field.html  forms/assignment_grid.html  forms/admin_form.html
  core/
    auth/login.html            # brand_mark, flash_messages(variant=auth)
    workspace/dashboard.html   # brand_mark, role_chip, partialdef membership_row
    admin/dashboard.html  admin/form.html (single create/edit page)
    admin/configuration/index.html location_list.html chapter_list.html cohort_list.html
    admin/users/list.html
  403.html 404.html 500.html  socialaccount/login_error.html authentication_error.html  # extend layouts/centered.html
  (templates/base.html, core/admin/base_admin.html, partials/ removed in phase 5)

static/
  css/tokens.css               # :root vars from admin.css (green #2e7d1f, blue #1a67b8, radii, shadows)
  css/base.css                 # reset, typography, .button, .eyebrow, .text-link
  css/shell.css                # app bar, sidebar, flyout, surface, account menu, footer (absorbs footer.css)
  css/components.css           # one /* === page-header === */ banner per component, same order as templates/components
  css/pages/login.css  css/pages/status.css
  js/components/data-table.js sidebar.js account-menu.js confirm.js   # IIFEs, init only when their root selector exists

core/
  navigation.py                # NavItem + ADMIN_NAV + is_active(url_name)
  permissions.py               # check_role(), RoleRequiredMixin, AdminRequiredMixin
  decorators.py                # admin_required re-exported/thin wrapper (unchanged behaviour)
  context_processors.py        # app_version (existing)
  forms/__init__.py            # re-exports LocationForm etc. so imports keep working
  forms/base.py                # StyledModelForm (+ full_width_fields = ())
  forms/renderers.py           # LudFormRenderer(TemplatesSetting): field_template_name
  forms/configuration.py  forms/users.py
  templatetags/ui.py           # page_header, data_table, status_badge, row_actions
  templatetags/nav.py          # admin_sidebar
  views/mixins.py              # AdminFormMixin (PageMeta + SuccessMessage + cancel_url), ProtectedDeleteMixin
  views/auth.py workspace.py dashboard.py configuration.py users.py
  views/__init__.py            # empty
  urls.py                      # crud_urls() helper, module imports, include() groups; same names and paths
  tests/base.py test_auth.py test_configuration.py test_users.py test_components.py test_navigation.py test_smoke.py
```

## Component inventory

| Component | Mechanism | Path | Replaces | Usage |
|---|---|---|---|---|
| layouts/base.html | extends (root layout) | `templates/layouts/base.html` | templates/base.html and the <head> of base_admin.html (old paths kept as 1-line {% extends %} shims until phase 5) | {% extends 'layouts/base.html' %} blocks: title, styles, vendor_scripts, body_class, body, scripts |
| layouts/admin.html | extends layouts/base.html; composes shell includes and tags | `templates/layouts/admin.html` | templates/core/admin/base_admin.html (app bar, sidebar, popover, flash, footer) | {% extends 'layouts/admin.html' %}{% block page_content %}...{% endblock %}; the shell subtitle comes from {% block shell_subtitle %}Admin{% endblock %} so role workspaces can reuse it |
| layouts/centered.html | extends layouts/base.html | `templates/layouts/centered.html + static/css/pages/status.css` | Standalone documents with inline <style> in 403.html, 404.html, 500.html, socialaccount/login_error.html, socialaccount/authentication_error.html | {% extends 'layouts/centered.html' %}{% block card %}{% include 'components/status_card.html' with code='404' title='Page not found' text='...' action_url='/' action_label='Go home' only %}{% endblock %}. The layout must not depend on request, user or APP_VERSION (500 has no RequestContext); guard with \|default |
| app_bar + account_menu | include ... only; {% partialdef avatar %} inside account_menu for the initial-letter avatar used twice | `templates/components/shell/app_bar.html, templates/components/shell/account_menu.html` | <header class="app-bar"> and the account-button/account-popover markup in base_admin.html, including the duplicated full_name\|slice\|upper expression | {% include 'components/shell/app_bar.html' with user=user subtitle='Admin' only %} |
| admin_sidebar | inclusion_tag(takes_context=True) reading request.resolver_match.url_name, fed by core/navigation.py | `core/templatetags/nav.py + templates/components/shell/sidebar.html (partialdefs nav_link, nav_group)` | The hand-written <aside class="admin-sidebar"> in base_admin.html (lines ~70-115), its inline SVGs and the '/admin/configuration/' in request.path checks | {% load nav %}{% admin_sidebar %}. It must emit the same classes and attributes admin.js and CSS rely on: sidebar-group/open, sidebar-group-link, sidebar-group-toggle, aria-expanded, sidebar-submenu, sidebar-sublink, data-tooltip |
| icons | Flaticon UIcons font (CDN) | — | every inline `<svg>` (done) | Superseded: icons are Flaticon UIcons (`<i class="fi fi-rr-NAME" aria-hidden="true"></i>`), not SVG partials. See CLAUDE.md > Icons. |
| flash_messages | include ... only with a variant | `templates/components/flash_messages.html` | .flash-messages loop in base_admin.html and the .messages loop in core/auth/login.html | {% include 'components/flash_messages.html' with messages=messages variant='admin' only %} (variant='auth' keeps the login classes) |
| site_footer | include (moved) | `templates/components/shell/site_footer.html (from templates/partials/site_footer.html)` | templates/partials/site_footer.html and its 3 include sites | {% include 'components/shell/site_footer.html' %} (reads APP_VERSION from the context processor, with \|default for 500) |
| brand_mark | include ... only with variant | `templates/components/brand_mark.html` | The lud.png + 'Let Us Dream' block in base_admin.html (.admin-brand), login.html (.brand-mark) and workspace/dashboard.html (.member-logo) | {% include 'components/brand_mark.html' with variant='app-bar' subtitle='Admin' only %} |
| page_header | simple_block_tag; the body is the actions slot, rendered via render_to_string (SafeString) | `core/templatetags/ui.py + templates/components/page_header.html` | <section class="page-heading[ page-heading--split]"> eyebrow/h1/p in admin dashboard, configuration/index, the 4 list pages and the 2 form pages | {% page_header eyebrow='Configuration' title='Locations' description='Manage reusable chapter locations.' %}<a class="button button--primary" href="{% url 'location_create' %}">Add location</a>{% endpage_header %} (adds --split when content.strip() is non-empty) |
| data_table | simple_block_tag; the caller writes <thead>/<tbody> | `core/templatetags/ui.py + templates/components/data_table.html` | <div class="table-card"><table class="data-table" data-empty-message=...> wrappers in location_list, chapter_list, cohort_list, users/list | {% data_table empty='No locations yet. Add the first location to continue.' %}<thead>...</thead><tbody>{% partialdef rows inline %}...{% endpartialdef %}</tbody>{% enddata_table %} |
| status_badge | simple_tag returning format_html | `core/templatetags/ui.py` | <span class="status-badge {% if x.is_active %}status-badge--active{% endif %}">Active/Inactive</span> in all 4 list templates | {% status_badge location.is_active %} / {% status_badge flag on='Enabled' off='Disabled' %} |
| row_actions | inclusion_tag(takes_context=True) (needs csrf_token) | `core/templatetags/ui.py + templates/components/row_actions.html` | <td class="table-actions"> Edit link + Delete <form onsubmit="return confirm(...)"> in 3 config lists; the 'Edit access' link in users/list | {% row_actions edit_url=edit_url delete_url=delete_url confirm='Delete this location?' %}, with URLs from {% url 'location_edit' location.pk as edit_url %}. It emits form[data-confirm], handled by static/js/components/confirm.js |
| role_chip / cell_stack | include ... only | `templates/components/role_chip.html, templates/components/cell_stack.html` | <span class="role-chip"> in users/list and workspace/dashboard; value<small class="cell-note"> cells in chapter/cohort/users lists | {% include 'components/cell_stack.html' with primary=cohort.chapter.name note=cohort.chapter.location.name only %} |
| stat_card / link_card / section_heading | include ... only | `templates/components/stat_card.html, link_card.html, section_heading.html` | 4x <article class="stat-card"> in admin/dashboard.html; .action-card (dashboard) and .configuration-card (configuration/index) as two variants of one link card; .section-block heading | {% include 'components/link_card.html' with href=location_url title='Locations' text='Reusable places where chapters operate.' badge=location_count variant='configuration' only %} |
| status_card | include ... only | `templates/components/status_card.html` | .error-card/.error-code/.error-btn markup in 403/404/500 and socialaccount/* | {% include 'components/status_card.html' with code='403' title='Access restricted' text='...' action_url='/' action_label='Back to sign in' only %} |
| form field + admin form | Django form renderer (TemplatesSetting subclass with field_template_name) + include ... only for the card; Field.template_name for special fields | `core/forms/renderers.py, templates/components/forms/field.html, templates/components/forms/assignment_grid.html, templates/components/forms/admin_form.html` | The duplicated per-field loops in configuration/form.html and users/form.html, plus the {% if field.name == 'assignments' %} branch | {% include 'components/forms/admin_form.html' with form=form submit_label=submit_label cancel_url=cancel_url layout=form_layout only %}; inside it: {% for field in form %}{{ field.as_field_group }}{% endfor %}. field.html uses field.widget_type == 'checkbox' and field.name in form.full_width_fields; PlatformUserForm sets assignments template_name='components/forms/assignment_grid.html' |
| core/admin/form.html | extends layouts/admin.html + page_header + admin_form | `templates/core/admin/form.html` | templates/core/admin/configuration/form.html and templates/core/admin/users/form.html (both deleted) | The views pass eyebrow, title, description, form, cancel_url, submit_label and form_layout |
| NAV registry | python dataclasses | `core/navigation.py` | Hand-written sidebar links and request.path substring active checks | ADMIN_NAV = [NavItem('Dashboard','admin_dashboard',icon='dashboard'), NavItem('Configuration','configuration_home',icon='sliders', children=[NavItem('Locations','location_list',match_prefix='location_'), NavItem('Chapters','chapter_list',match_prefix='chapter_'), NavItem('Cohorts','cohort_list',match_prefix='cohort_')]), NavItem('Users','platform_user_list',icon='users',match_prefix='platform_user_')] |
| Admin CRUD mixins + crud_urls | python: AdminRequiredMixin, PageMetaMixin, ProtectedDeleteMixin + thin explicit CBV subclasses | `core/views/mixins.py, core/views/configuration.py, core/urls.py (crud_urls helper)` | The 12 location/chapter/cohort functions, _configuration_form and the ProtectedError try/except duplicated in 2 delete views | class LocationList(AdminRequiredMixin, ListView): queryset = Location.objects.annotate(chapter_count=Count('chapters')); template_name='core/admin/configuration/location_list.html'; context_object_name='locations'. class LocationCreate(AdminFormMixin, CreateView): model=Location; form_class=LocationForm; prefix='location'. class LocationDelete(ProtectedDeleteMixin, DeleteView): model=Location; protected_message='This location is in use by a chapter. Deactivate it instead.'. urls: *crud_urls('locations/', 'location', LocationList, LocationCreate, LocationUpdate, LocationDelete) |
| RoleRequiredMixin | python mixin sharing one check function with the existing decorator | `core/permissions.py (core/decorators.admin_required re-exported from it)` | The admin check in core/decorators.py (kept as an alias) and the ad-hoc access and logout checks in workspace_home_view | class MentorHome(RoleRequiredMixin, TemplateView): required_roles={'mentor'}; AdminRequiredMixin = RoleRequiredMixin with platform-admin check |

## Python side

1) Permissions (core/permissions.py). Extract check_role(request, roles=None, admin=False) from core/decorators.admin_required. It returns redirect_to_login for anonymous users and raises PermissionDenied otherwise. admin_required and a RoleRequiredMixin.dispatch() both call it, so FBVs and CBVs share one rule. AdminRequiredMixin is the admin flavour. The role workspaces (leader, mentor, mentee) will use RoleRequiredMixin(required_roles=...) instead of repeating checks.

2) CRUD (core/views/mixins.py + configuration.py). Three small mixins:
- AdminFormMixin (AdminRequiredMixin + SuccessMessageMixin): template 'core/admin/form.html'; get_context_data adds eyebrow, title ('Add location' or 'Edit location' from model._meta.verbose_name and self.object), cancel_url=reverse(f'{prefix}_list') and submit_label; success_url is reverse_lazy of the list.
- ProtectedDeleteMixin: http_method_names=['post'], preserving require_POST. It wraps form_valid in try/except ProtectedError and calls messages.error(protected_message), keeping the exact 'Deactivate it instead.' text.
- AdminRequiredMixin on ListViews, keeping the context names locations, chapters and cohorts and the per-list querysets written out explicitly.
Each resource is 4 visible classes of 3-5 lines in configuration.py (~60 lines total), with no factory. core/urls.py gets crud_urls(path_prefix, name_prefix, list, create, update, delete, pk_kwarg=f'{name_prefix}_id'), which returns the same 4 paths, names and kwargs (location_id, etc.), so nothing observable changes. Users stay explicit CBVs in users.py because of the custom queryset (excluding admins and superusers) and the custom save. They reuse AdminFormMixin, core/admin/form.html (form_layout='grid') and users/list.html. There is no delete view.

3) Views and urls layout. Split core/views/admin.py into dashboard.py, configuration.py and users.py. Empty core/views/__init__.py (46 lines of re-exports). urls.py does `from core.views import auth, dashboard, configuration, users, workspace` and groups admin/configuration/ with include(). Paths and names stay byte-identical, with no namespaces for now.

4) Navigation (core/navigation.py). NavItem(label, url_name, icon=None, match_prefix=None, children=()). is_active(url_name) compares against request.resolver_match.url_name. A group is open when it or a child is active. The {% admin_sidebar %} tag passes precomputed dicts to the template. It is safe when resolver_match is None (404) and not used on 500. Adding a menu entry becomes one line. Role workspaces later get their own list, e.g. MENTOR_NAV, and pass it via the same tag with an argument.

5) Forms. Turn core/forms.py into a package whose __init__ re-exports the public names. StyledModelForm keeps its widget-class injection and gains full_width_fields = (). PlatformUserForm sets full_width_fields=('assignments',) and assignments template_name. settings: add 'django.forms' to INSTALLED_APPS (required for TemplatesSetting to find widget templates) and FORM_RENDERER='core.forms.renderers.LudFormRenderer'. Verify that allauth login/password forms render unchanged.

6) Template tags. Only the four tags that need Python go in core/templatetags/ui.py: page_header and data_table (simple_block_tag, return render_to_string output so it is not escaped, check content.strip()), status_badge (format_html) and row_actions (inclusion_tag, takes_context for csrf). The sidebar tag goes in nav.py. Everything else is an include with `only`.

7) Tests. Split core/tests.py into core/tests/ with a PlatformTestCase in base.py, moving tests verbatim. Add test_components.py (Template('{% load ui %}...') + assertInHTML for each tag and include), test_navigation.py (every NAV url_name reverses; location_edit opens Configuration with Locations active), and test_smoke.py. The smoke test loops over the admin URL names: admin gets 200, non-admin gets 403, anonymous gets a login redirect. It also calls get_template() on every file under templates/ to catch broken includes and '#partial' names.

## CSS and JS

Each component has one template in templates/components/ and one banner section /* === <name> === */ in css/components.css, and keeps today's BEM-ish class names (.page-heading--split, .status-badge--active, .button--primary). This is a file split, not a rename. Cut admin.css (~1.2k lines) at its existing section boundaries into tokens.css (the :root vars), base.css, shell.css (app bar, sidebar, flyout, surface, account menu, footer) and components.css. Keep the original cascade order as the <link> order: tokens, base, shell, components, pages. login.css becomes css/pages/login.css and uses the tokens instead of repeating colours. The inline <style> blocks in 403/404/500/socialaccount become css/pages/status.css, which also retires the old teal (#0b5d52) in favour of the logo tokens. Use plain <link> tags, no @import and no bundler. Add ManifestStaticFilesStorage in production for cache busting.

JS: split static/js/admin.js by responsibility into static/js/components/data-table.js (reads data-empty-message), sidebar.js (localStorage 'lud-admin-sidebar', group toggle and flyout), account-menu.js, and a new confirm.js (a delegated submit listener for form[data-confirm] that replaces inline onsubmit). Each file is an IIFE that initialises only when its root selector exists, loaded with <script defer> from layouts/admin.html. Move the jQuery and DataTables CDN tags into {% block vendor_scripts %}, filled only by list pages, so the dashboard and form pages stop downloading them. The inline pre-paint sidebar script stays in <head>. With no inline handlers left, Django 6.0's CSP middleware can be adopted later with a nonce for that single script.

## Migration phases

### 0. Safety net

- Split core/tests.py into core/tests/ (base.py, test_auth.py, test_configuration.py, test_users.py), moving tests verbatim
- Add test_smoke.py: every admin URL name as admin/non-admin/anonymous, plus a get_template() walk over templates/
- Take baseline headless-Chrome screenshots: login, dashboard (sidebar expanded and collapsed with flyout), each list, each form with errors, 404

**Risk:** Very low: only test files change.

**Verify:** python manage.py test passes (19 existing + new); python manage.py check is clean; screenshots saved in the scratchpad

### 1. Layouts and shell

- Create layouts/base.html and layouts/admin.html; turn templates/base.html and core/admin/base_admin.html into 1-line extends shims
- Extract components/shell/app_bar.html, account_menu.html (partialdef avatar), site_footer.html (moved; update the 3 include sites), flash_messages.html, brand_mark.html
- Create components/icons.html (a partialdef per SVG) and replace inline SVGs with {% include 'components/icons.html#name' %} — **Done differently:** all SVGs were already replaced with Flaticon `<i class="fi fi-rr-…">`; NavItem.icon holds the UIcons name (e.g. `apps`).
- Add core/navigation.py, core/templatetags/nav.py ({% admin_sidebar %}) and components/shell/sidebar.html; delete the hand-written sidebar; add test_navigation.py

**Risk:** Low to medium. Active and open state moves from path substrings to url_name matching, and the collapsed flyout depends on exact classes and data-tooltip attributes.

**Verify:** Tests green; screenshot diff of dashboard, list and edit pages (Configuration open, sublink active) and the collapsed flyout; account popover closes on outside click and Escape

### 2. Page UI components

- Add core/templatetags/ui.py: page_header, data_table, status_badge, row_actions
- Add includes: stat_card, link_card, section_heading, cell_stack, role_chip
- Add static/js/components/confirm.js; row_actions emits data-confirm
- Convert the 4 list pages (tbody loop in {% partialdef rows inline %}), admin/dashboard.html and configuration/index.html
- Add test_components.py

**Risk:** Low to medium. Block-tag output escaping (must return SafeString), the confirm dialog must still block the POST, and DataTables needs a thead column count that matches the rows.

**Verify:** Tests green, including test_location_in_use_cannot_be_deleted; manual check that delete-cancel and delete-confirm behave, sorting on cohort Duration (data-order) and empty-message rows work; screenshot diff

### 3. Form rendering

- Turn core/forms.py into a package with re-exports; add full_width_fields and LudFormRenderer
- settings: add 'django.forms' to INSTALLED_APPS and set FORM_RENDERER
- Create components/forms/field.html, assignment_grid.html, admin_form.html and core/admin/form.html
- Point _configuration_form and _platform_user_form at core/admin/form.html; delete configuration/form.html and users/form.html

**Risk:** Medium. The renderer change is global (it also touches allauth forms), and the assignments grid and checkbox modifier classes must survive.

**Verify:** Create/provision/edit-user tests pass; add assertions for form-field--checkbox, assignment-grid and field-error spans on an invalid POST; login password fallback renders identically

### 4. Python CRUD and URLs

- Add core/permissions.py (check_role, RoleRequiredMixin, AdminRequiredMixin); make the decorator delegate to it
- Add core/views/mixins.py (AdminFormMixin, ProtectedDeleteMixin)
- Create dashboard.py, configuration.py (explicit thin CBVs) and users.py; delete core/views/admin.py; empty views/__init__.py
- Rewrite core/urls.py with crud_urls() and include() groups, keeping every name, path and kwarg

**Risk:** Medium. Delete must stay POST-only (GET returns 405), the users UpdateView must keep excluding admins and superusers, and success and protected messages must match exactly.

**Verify:** All tests green unchanged; new tests for GET-on-delete returning 405 and editing an admin user returning 404; the dump of get_resolver().reverse_dict is identical before and after

### 5. Standalone pages and cleanup

- Create layouts/centered.html, components/status_card.html, css/pages/status.css
- Rewrite 403/404/500 and socialaccount/*.html on it, removing inline <style>
- Move login.html and workspace/dashboard.html onto brand_mark and flash_messages(variant='auth'); partialdef membership_row
- Delete the base.html and base_admin.html shims and templates/partials/ once grep finds no references

**Risk:** Low to medium. 500.html renders without a RequestContext.

**Verify:** With DEBUG=False, check a missing URL (404), a non-admin on /admin/users/ (403) and a forced exception (500); trigger an allauth error; tests asserting 'Continue with Google' and 'Signin with Username &amp; Password' pass; screenshot diff

### 6. CSS/JS split

- Cut admin.css into tokens.css, base.css, shell.css and components.css (keep the original order via <link> order); move login.css to pages/ using tokens; fold footer.css into shell.css
- Split admin.js into js/components/*.js with defer; move jQuery/DataTables into {% block vendor_scripts %} on list pages only

**Risk:** Low to medium: visual regressions only, from cascade order.

**Verify:** collectstatic succeeds; pixel diff against phase-0 screenshots; sidebar collapse persists across reloads; a test asserts dashboard HTML has no dataTables.min.js and list pages do

### 7. Conventions and role workspaces

- Add a short 'Components' section to README: each component, how to call it, its CSS section
- Build new role-workspace pages only from existing components with RoleRequiredMixin and a per-role NavItem list; a new component needs its test first

**Risk:** Very low: additive.

**Verify:** Per-role access tests; component tests for any new component; grep finds no inline <svg>, <style> or on*= in templates/

## Conventions

- Choose the mechanism by need. Plain markup with inputs uses {% include 'components/x.html' with ... only %}, always with `only`. Anything needing csrf, reverse or request logic uses an inclusion_tag. A wrapper with a slot uses a simple_block_tag. A fragment used on one page, or a table's rows, uses {% partialdef name inline %} in that page.
- A block of markup that appears on 2 or more pages becomes a component. Markup used once stays in the page.
- One component means one template in templates/components/ (snake_case), one root CSS class (kebab-case, BEM --modifiers) and one banner section in css/components.css. Interactive ones get one static/js/components/<name>.js bound via data-* attributes.
- Templates contain no inline <style>, style="" attributes, on* handlers or <svg>. Icons are Flaticon UIcons `<i class="fi fi-rr-NAME" aria-hidden="true"></i>`.
- Every page extends exactly one of layouts/base.html, layouts/admin.html or layouts/centered.html. Only layouts write <html>/<head>/<body>, and centered.html must render without request context (500).
- Sidebar entries live only in core/navigation.py. Active state uses URL names, never request.path.
- Access control only goes through core/permissions.py (mixins/decorator), with no ad-hoc is_platform_admin checks in views or templates.
- Views pass already-reversed URLs (cancel_url, edit_url) and page copy (eyebrow, title, description) to templates. Components never query the ORM.
- Form layout decisions live in Python (full_width_fields, Field.template_name, widget classes in StyledModelForm), never as field-name if-branches in templates.
- URL names are the public contract for templates and tests. Renaming one needs a deliberate change with test updates in the same commit.
- Every new component gets an assertInHTML test in core/tests/test_components.py, and every new view is covered by the smoke test (admin 200, non-admin 403, anonymous redirect).
- Every phase or PR keeps `python manage.py test` green, and UI-affecting PRs include before/after screenshots.

## Trade-offs

Pros: nothing to install or upgrade beyond Django 6.0.3. Anyone who can read Django templates can maintain the components. allauth and error handlers keep working through plain inheritance. Partials make later HTMX-style fragment refreshes ('list.html#rows') possible without extra files.

Cons: there are no typed or validated props. A mistyped `with` argument renders as an empty string, which is only partly offset by the component tests. simple_block_tag has one unnamed slot, so a component needing two slots falls back to keyword arguments. The four tag-based components are split across Python and a template.

Explicit thin CBV subclasses are slightly more lines than a factory, but they stay greppable and easy to deviate per resource. If a fourth or fifth resource appears, a small factory can be introduced then.

The FORM_RENDERER switch is global and needs 'django.forms' in INSTALLED_APPS, so it gets its own phase and tests.

Un-namespaced URL names and a single core app postpone collision safety and cleaner app boundaries. That is deliberate, until a second feature area with its own models justifies a split.

Five CSS files instead of per-component files keep requests low without a bundler, at the cost of a less strict one-file-per-component mapping (banner sections compensate).

data-confirm depends on JS. Without it the delete still requires POST and the ProtectedError guard still applies.

## Rejected ideas (and why)

- django-cotton / django-components (library plan): they add a third-party loader or compiler plus new syntax, and neither is installed or verified. Django 6.0's include-with-only, inclusion_tag, simple_block_tag and partials cover every duplicated block in a ~20-template app. Revisit only if components start needing props validation at scale.
- Splitting into accounts/console/workspace apps plus app_name namespacing now (pragmatic): it is a broad breaking sweep through templates, tests and LOGIN_REDIRECT_URL for no present benefit. Defer until a second real feature area with its own models exists. Put new role-workspace code in core/views/workspace/ for now.
- Column/cell-template data_table DSL, Resource REGISTRY and a single generic resource_list.html (pragmatic): this is a mini Django admin. List pages differ enough (annotations, stacked cells, role chips, data-order dates) that explicit <thead>/<tbody> inside a data_table block tag is clearer.
- AdminCrud factory that builds the classes and URL patterns dynamically (native): it is too much indirection for three resources. Replaced with explicit thin CBV subclasses over three small mixins and a crud_urls() helper, which keeps the code greppable.
- core/selectors.py query layer (native): it adds a layer with one caller each. Keep annotated querysets as class attributes or get_queryset() on the views. Add QuerySet methods on the models only when a second caller appears.
- Custom StyledBoundField with wrapper_classes (native): forms/field.html can use field.widget_type and form.full_width_fields, and Field.template_name covers the assignments grid. No BoundField subclass is needed.
- button and link_card inclusion tags that reverse URL names (native): they save one {% url %} call but make the markup harder to read. .button is a CSS component. link_card becomes a plain include with href passed in.
- Per-component CSS files (15-20) joined with @import, and CSS @layer (native, pragmatic): too fragmented for ~1.5k lines of CSS, and @import is serial. Use 5 files (tokens, base, shell, components, pages) with section banners per component instead.
- DEBUG-only /_components/ catalogue view (native): nice to have, but it is extra code to maintain. Component render tests give most of the value. Add it only if designers join.
- services.py for sync_cohort_memberships and a model-free app split (pragmatic): the membership diff can stay in PlatformUserForm.save() until a second caller exists.
- SVG sprite in static/ (library): it splits icons away from templates and depends on <use href> origin behaviour. A partial-per-icon file keeps them inline, themable with currentColor, and needs no extra request.
- Emptying core/views/__init__.py and restructuring all imports in one step: done, but only in the CRUD phase, not as a separate refactor.
- Dropping jQuery right now: optional follow-up only. DataTables 2 works without it, but it is unrelated to the component work.

## Verified Django 6.0.3 facts

- Verified in venv/lib/python3.14/site-packages/django (6.0.3): Library.simple_block_tag exists (template/library.py:159); {% partialdef %} and {% partial %} are built-in tags (defaulttags.py:1204, 1268); Engine.get_template splits 'file.html#partial' (engine.py:179); BoundField.as_field_group exists via RenderableFieldMixin (forms/utils.py:62); bound_field_class is supported on Form, Field and BaseRenderer (forms.py:71, fields.py:94, renderers.py:22); BoundField.widget_type exists; Field(template_name=...) is honoured (boundfield.py:80); CSP middleware ships in 6.0 (middleware/csp.py). All three plans' claims about these are correct.
- Native plan: the '{% icon %} simple_tag that calls get_template(...#name)' is unnecessary. {% include 'components/icons.html#menu' %} already works because include goes through engine.get_template, which parses '#'.
- Native plan: the reason for moving templates/partials/ ('the name clashes with 6.0 partials') is wrong. Partials are addressed by tag and '#name', and directory names do not matter. Moving it is still fine for consistency (components/), but it is not required.
- Native and pragmatic plans: 'add --split automatically when the slot is non-empty' must test content.strip(), because the block body always contains whitespace or newlines. SimpleNode.render applies conditional_escape (library.py:329-330), so the tag must return a SafeString (render_to_string / format_html) or its markup gets escaped. The native plan flagged this correctly.
- Library plan: django-cotton and django-components are not installed in the venv. The Django 6 compatibility and loader auto-configuration claims come from PyPI metadata only and were not checked in this repo. The plan also says '9 near-copy views'. There are 12 (list/create/edit/delete x 3), although the three list views legitimately differ in their annotations.
- TemplatesSetting needs 'django.forms' in INSTALLED_APPS, which is currently absent in settings.py. The switch is also needed only because the component templates live in project-level DIRS (templates/). The default DjangoTemplates renderer does not search DIRS. It does search app template dirs.
- Pragmatic plan: '26 migrations' is correct (0001-0026). Native plan: 'schools, mentees, assessments were modelled before' is correct (0014), but 0025 removed several of them. The CRUD growth argument holds, but it is not proof of imminent resources.
- All plans: existing URL kwargs are location_id, chapter_id, cohort_id and user_id. Tests use reverse(name, args=[pk]), so renaming to pk is safe for tests, but it is still a visible change. There is also an existing 'role-redirect' URL name with a hyphen, which is inconsistent with the rest.
- base_admin.html loads jQuery 3.7.1 and DataTables 2.1.8 globally (lines 140-142) and has an inline pre-paint <script> in <head> (line 14). The sidebar active state uses request.path substrings (lines 78-108). Both are confirmed as described.
