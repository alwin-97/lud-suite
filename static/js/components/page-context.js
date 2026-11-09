// Keep anchor targets visible below the sticky heading and mark the current section.
(function () {
    var content = document.querySelector('.admin-content');
    var header = content && content.querySelector(':scope > .page-context');
    if (!header) return;
    var appBar = document.querySelector('.app-bar');
    var toggle = header.querySelector('[data-page-context-toggle]');
    var currentLabel = header.querySelector('[data-current-section]');
    var preferenceKey = 'lud-page-heading-minimized';
    var sections = Array.from(header.querySelectorAll('.detail-nav a[href^="#"]')).map(function (link) {
        return {link: link, target: document.getElementById(link.hash.slice(1))};
    }).filter(function (section) { return section.target; });
    var pending = false;

    function update() {
        pending = false;
        var appHeight = appBar ? appBar.getBoundingClientRect().height : 0;
        var headerHeight = header.getBoundingClientRect().height;
        content.style.setProperty('--page-context-height', headerHeight + 'px');
        var cutoff = appHeight + headerHeight + 24;
        var current = sections[0];
        sections.forEach(function (section) {
            if (section.target.getBoundingClientRect().top <= cutoff) current = section;
        });
        // The last section may be too short to reach the top of the viewport.
        if (window.scrollY > 0 && window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2) {
            current = sections[sections.length - 1];
        }
        sections.forEach(function (section) {
            if (section === current) section.link.setAttribute('aria-current', 'location');
            else section.link.removeAttribute('aria-current');
        });
        var label = current ? '· ' + current.link.textContent : '';
        if (currentLabel && currentLabel.textContent !== label) currentLabel.textContent = label;
    }

    function setMinimized(minimized, persist) {
        document.documentElement.classList.toggle('page-context-minimized', minimized);
        toggle.setAttribute('aria-expanded', String(!minimized));
        toggle.querySelector('[data-toggle-label]').textContent = minimized ? 'Expand' : 'Minimize';
        if (persist) {
            try { localStorage.setItem(preferenceKey, String(minimized)); } catch (err) {}
        }
        update();
    }

    if (toggle) {
        var minimized = document.documentElement.classList.contains('page-context-minimized');
        try {
            var saved = localStorage.getItem(preferenceKey);
            if (saved !== null) minimized = saved === 'true';
        } catch (err) {}
        setMinimized(minimized, false);
        toggle.addEventListener('click', function () {
            setMinimized(!document.documentElement.classList.contains('page-context-minimized'), true);
        });
    }

    function schedule() {
        if (!pending) {
            pending = true;
            window.requestAnimationFrame(update);
        }
    }

    if (window.ResizeObserver) {
        var observer = new ResizeObserver(schedule);
        observer.observe(header);
        if (appBar) observer.observe(appBar);
    }
    window.addEventListener('scroll', schedule, {passive: true});
    window.addEventListener('resize', schedule);
    window.addEventListener('load', function () {
        update();
        // Restore deep links after the actual header height is known.
        var id = window.location.hash.slice(1);
        var target = id && document.getElementById(id);
        if (target && content.contains(target)) target.scrollIntoView();
    });
    update();
})();
