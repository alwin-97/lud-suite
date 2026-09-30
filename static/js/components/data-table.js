// DataTables for every table.data-table: search, page size, paging, and the
// optional Filters panel (components/table_filters.html) bound via data-filter-table.
(function () {
    if (!window.DataTable) {
        return;
    }

    document.querySelectorAll('table.data-table').forEach(function (table) {
        var dataTable = new DataTable(table, {
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

        var filters = Array.from(document.querySelectorAll('[data-filter-table]')).find(function (control) {
            return control.dataset.filterTable === table.id;
        });
        if (!filters) {
            return;
        }

        var groups = filters.querySelector('.table-filter-groups');
        var clear = filters.querySelector('[data-filter-clear]');
        var label = filters.querySelector('[data-filter-label]');
        var result = filters.querySelector('.table-filter-result');
        var fields = filters.dataset.filterFields.split(',').map(function (name) {
            var attribute = 'data-filter-' + name.toLowerCase();
            var rows = new Map();
            var options = new Set();
            dataTable.rows().every(function () {
                var row = this.node();
                var values = [];
                if (row.hasAttribute(attribute)) {
                    values.push(row.getAttribute(attribute));
                }
                row.querySelectorAll('[' + attribute + ']').forEach(function (item) {
                    values.push(item.getAttribute(attribute));
                });
                rows.set(this.index(), values);
                values.forEach(function (value) { options.add(value); });
            });

            var fieldset = document.createElement('fieldset');
            var legend = document.createElement('legend');
            legend.textContent = name;
            fieldset.appendChild(legend);
            var choices = document.createElement('div');
            choices.className = 'table-filter-options';
            fieldset.appendChild(choices);
            Array.from(options).sort(function (a, b) { return a.localeCompare(b); }).forEach(function (value) {
                var option = document.createElement('label');
                var checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.value = value;
                option.appendChild(checkbox);
                option.appendChild(document.createTextNode(value));
                choices.appendChild(option);
            });
            if (!options.size) {
                var empty = document.createElement('p');
                empty.textContent = 'No options available.';
                choices.appendChild(empty);
            }
            groups.appendChild(fieldset);
            return { fieldset: fieldset, rows: rows, selected: new Set() };
        });

        dataTable.search.fixed('page-filters', function (search, data, index) {
            return fields.every(function (field) {
                return !field.selected.size || (field.rows.get(index) || []).some(function (value) {
                    return field.selected.has(value);
                });
            });
        });

        function updateResult() {
            var info = dataTable.page.info();
            result.textContent = info.recordsDisplay + ' of ' + info.recordsTotal + ' records match.';
        }

        function applyFilters() {
            var count = 0;
            fields.forEach(function (field) {
                field.selected = new Set(Array.from(field.fieldset.querySelectorAll('input:checked')).map(function (input) {
                    return input.value;
                }));
                count += field.selected.size;
            });
            label.textContent = count ? 'Filters (' + count + ')' : 'Filters';
            clear.disabled = count === 0;
            dataTable.draw();
        }

        filters.addEventListener('change', applyFilters);
        clear.addEventListener('click', function () {
            filters.querySelectorAll('input:checked').forEach(function (input) { input.checked = false; });
            applyFilters();
        });
        document.addEventListener('click', function (event) {
            if (!filters.contains(event.target)) {
                filters.open = false;
            }
        });
        filters.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') {
                filters.open = false;
                filters.querySelector('summary').focus();
            }
        });
        dataTable.on('draw', updateResult);
        updateResult();
        filters.hidden = false;
    });
})();
