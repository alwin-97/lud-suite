(function () {
    var drawer = document.getElementById('form-drawer');
    if (!drawer) return;
    var content = drawer.querySelector('.form-drawer-content');
    var body = drawer.querySelector('.form-drawer-body');
    var headingTitle = drawer.querySelector('[data-drawer-heading-title]');
    var headingDetails = drawer.querySelector('[data-drawer-heading-details]');
    var headerToggle = drawer.querySelector('[data-toggle-drawer-header]');
    var error = drawer.querySelector('.form-drawer-error');
    var loader = drawer.querySelector('.form-drawer-loader');
    var close = drawer.querySelector('[data-close-drawer]');
    var createPaths = drawer.dataset.createUrls.trim().split(/\s+/);
    var resourcePrefix = drawer.dataset.resourcePrefix;
    var controller;
    var opener;
    var saving = false;
    var resourcesChanged = false;

    function minimizeHeader(minimized, persist) {
        drawer.classList.toggle('form-drawer--minimized', minimized);
        headerToggle.setAttribute('aria-expanded', String(!minimized));
        headerToggle.querySelector('[data-drawer-toggle-label]').textContent = minimized ? 'Maximize' : 'Minimize';
        if (persist) {
            try { localStorage.setItem('lud-drawer-heading-minimized', String(minimized)); } catch (err) {}
        }
    }

    var minimized = false;
    try { minimized = localStorage.getItem('lud-drawer-heading-minimized') === 'true'; } catch (err) {}
    minimizeHeader(minimized, false);
    headerToggle.addEventListener('click', function () {
        minimizeHeader(!drawer.classList.contains('form-drawer--minimized'), true);
    });

    function render(html) {
        content.innerHTML = html;
        var heading = content.querySelector('[data-drawer-heading]');
        var title = heading && heading.querySelector('[data-drawer-title]');
        headingTitle.textContent = title ? title.textContent : 'Form';
        headingDetails.replaceChildren();
        if (heading) {
            heading.querySelectorAll('[data-drawer-header-detail]').forEach(function (item) {
                headingDetails.appendChild(item);
            });
            heading.remove();
        }
        drawer.setAttribute('aria-labelledby', 'form-drawer-title');
    }

    function isResourceURL(url) {
        return url.origin === window.location.origin && (url.pathname === resourcePrefix || (
            url.pathname.startsWith(resourcePrefix) && /^(program|location|chapter|cohort)\/\d+\/$/.test(url.pathname.slice(resourcePrefix.length))
        ));
    }

    function supports(url) {
        return url.origin === window.location.origin && createPaths.some(function (path) {
            var base = path.slice(0, -4);
            return url.pathname === path || (url.pathname.startsWith(base) && /^\d+\/edit\/$/.test(url.pathname.slice(base.length)));
        });
    }

    function showError() {
        error.textContent = 'Unable to load or save. Please try again.';
        error.hidden = false;
    }

    function goToAnchor(url) {
        if (!url.hash) return;
        var id;
        try { id = decodeURIComponent(url.hash.slice(1)); } catch (err) { return; }
        var target = Array.from(content.querySelectorAll('[id]')).find(function (item) { return item.id === id; });
        if (target) target.scrollIntoView({block: 'start'});
    }

    async function request(url, options) {
        var response = await fetch(url, Object.assign({headers: {'X-Form-Drawer': 'true'}, signal: controller.signal}, options));
        if (!response.ok || response.redirected) throw new Error('Unexpected response');
        return response;
    }

    async function load(url) {
        if (controller) controller.abort();
        controller = new AbortController();
        var current = controller;
        content.innerHTML = '';
        headingTitle.textContent = 'Loading…';
        headingDetails.replaceChildren();
        loader.hidden = false;
        content.setAttribute('aria-busy', 'true');
        drawer.setAttribute('aria-labelledby', 'form-drawer-loading-title');
        error.hidden = true;
        try {
            var response = await request(url);
            var html = await response.text();
            if (current !== controller) return;
            render(html);
            body.scrollTop = 0;
            if (!content.querySelector('[data-resource-drawer-page]')) {
                var field = content.querySelector('input:not([type="hidden"]), select, textarea');
                if (field) field.focus();
            }
            goToAnchor(url);
        } catch (err) {
            if (err.name !== 'AbortError' && current === controller) showError();
        } finally {
            if (current === controller) {
                loader.hidden = true;
                content.removeAttribute('aria-busy');
            }
        }
    }

    drawer.addEventListener('cancel', function (event) { event.preventDefault(); });
    close.addEventListener('click', function () {
        if (saving) return;
        if (controller) controller.abort();
        drawer.close();
        if (resourcesChanged) window.location.reload();
        else if (opener) opener.focus();
    });

    document.addEventListener('click', async function (event) {
        var link = event.target.closest('a[href]');
        if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || link.target === '_blank') return;
        var url = new URL(link.href);
        var inside = drawer.contains(link);
        var resourcePage = content.querySelector('[data-resource-drawer-page]');
        if (inside && link.getAttribute('href').startsWith('#')) {
            event.preventDefault();
            goToAnchor(url);
            return;
        }
        if (!(supports(url) || (isResourceURL(url) && (link.hasAttribute('data-resource-drawer') || (inside && resourcePage))))) return;
        event.preventDefault();
        if (saving) return;
        if (!drawer.open) {
            opener = link;
            resourcesChanged = false;
            drawer.showModal();
        }
        await load(url);
    });

    drawer.addEventListener('submit', async function (event) {
        var form = event.target;
        if (!form.matches('form')) return;
        event.preventDefault();
        event.stopPropagation();
        if (saving || (form.dataset.confirm && !window.confirm(form.dataset.confirm))) return;
        if (form.method.toLowerCase() === 'get') {
            var url = new URL(form.action);
            url.search = new URLSearchParams(new FormData(form)).toString();
            await load(url);
            return;
        }
        saving = true;
        error.hidden = true;
        var submit = form.querySelector('[type="submit"]');
        var label = submit ? submit.textContent : '';
        if (submit) {
            submit.disabled = true;
            submit.textContent = 'Saving…';
        }
        close.disabled = true;
        try {
            var response = await request(form.action, {method: 'POST', body: new FormData(form)});
            if ((response.headers.get('content-type') || '').includes('application/json')) {
                var result = await response.json();
                if (!result.saved) throw new Error('Save failed');
                if (result.resource_url) {
                    resourcesChanged = true;
                    await load(new URL(result.resource_url, window.location.origin));
                } else window.location.reload();
            } else {
                render(await response.text());
                var invalid = content.querySelector('[aria-invalid="true"], .errorlist');
                if (invalid) invalid.scrollIntoView({block: 'center'});
            }
        } catch (err) {
            if (err.name !== 'AbortError') showError();
        } finally {
            saving = false;
            if (submit) {
                submit.disabled = false;
                submit.textContent = label;
            }
            close.disabled = false;
        }
    });
})();
