(function () {
    if (!window.DataTable) {
        return;
    }

    document.querySelectorAll('table.data-table').forEach(function (table) {
        new DataTable(table, {
            pageLength: 10,
            lengthMenu: [10, 25, 50, 100],
            autoWidth: false,
            order: [],
            columnDefs: [
                { targets: 'actions-column', orderable: false, searchable: false }
            ],
            language: {
                search: '',
                searchPlaceholder: 'Search…',
                lengthMenu: '_MENU_ per page',
                emptyTable: table.dataset.emptyMessage || 'No records yet.',
                zeroRecords: 'No matching records found.'
            }
        });
    });
})();

(function () {
    var toggle = document.getElementById('sidebarToggle');
    if (!toggle) {
        return;
    }

    var root = document.documentElement;
    var STORAGE_KEY = 'lud-admin-sidebar';

    function setExpandedLabel() {
        var collapsed = root.classList.contains('sidebar-collapsed');
        toggle.setAttribute('aria-expanded', String(!collapsed));
        toggle.setAttribute('aria-label', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
    }

    setExpandedLabel();

    toggle.addEventListener('click', function () {
        var collapsed = root.classList.toggle('sidebar-collapsed');
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
