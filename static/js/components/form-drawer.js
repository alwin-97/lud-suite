(function () {
    var drawer = document.getElementById('form-drawer');
    if (!drawer) return;
    var content = drawer.querySelector('.form-drawer-content');
    var error = drawer.querySelector('.form-drawer-error');
    var loader = drawer.querySelector('.form-drawer-loader');
    var close = drawer.querySelector('[data-close-drawer]');
    var createPaths = drawer.dataset.createUrls.trim().split(/\s+/);
    var resourcePrefix = drawer.dataset.resourcePrefix;
    var controller;
    var opener;
    var saving = false;
    var resourcesChanged = false;

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
        loader.hidden = false;
        content.setAttribute('aria-busy', 'true');
        drawer.setAttribute('aria-labelledby', 'form-drawer-loading-title');
        error.hidden = true;
        try {
            var response = await request(url);
            var html = await response.text();
            if (current !== controller) return;
            content.innerHTML = html;
            drawer.setAttribute('aria-labelledby', 'form-drawer-title');
            drawer.scrollTop = 0;
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
                content.innerHTML = await response.text();
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
