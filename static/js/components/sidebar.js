// Sidebar collapse (persisted in localStorage 'lud-admin-sidebar') and group toggles.
(function () {
    var toggle = document.getElementById('sidebarToggle');
    if (!toggle) {
        return;
    }

    var root = document.documentElement;
    var STORAGE_KEY = 'lud-admin-sidebar';
    var narrowViewport = window.matchMedia('(max-width: 1100px)');
    var preferredCollapsed = false;
    try { preferredCollapsed = localStorage.getItem(STORAGE_KEY) === 'collapsed'; } catch (e) {}

    function setExpandedLabel() {
        var collapsed = root.classList.contains('sidebar-collapsed');
        toggle.setAttribute('aria-expanded', String(!collapsed));
        toggle.setAttribute('aria-label', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
    }

    function adaptSidebar() {
        root.classList.toggle('sidebar-collapsed', narrowViewport.matches || preferredCollapsed);
        setExpandedLabel();
    }

    adaptSidebar();
    narrowViewport.addEventListener('change', adaptSidebar);

    toggle.addEventListener('click', function () {
        var collapsed = root.classList.toggle('sidebar-collapsed');
        preferredCollapsed = collapsed;
        try {
            localStorage.setItem(STORAGE_KEY, collapsed ? 'collapsed' : 'expanded');
        } catch (e) {}
        setExpandedLabel();
    });

    document.querySelectorAll('.sidebar-group-toggle').forEach(function (groupToggle) {
        groupToggle.addEventListener('click', function () {
            var group = groupToggle.closest('.sidebar-group');
            if (!group) {
                return;
            }
            var open = group.classList.toggle('open');
            groupToggle.setAttribute('aria-expanded', String(open));
        });
    });
})();
