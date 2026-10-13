// Turns every select[data-searchable] into a type-to-filter dropdown.
// The native <select> stays in the form (hidden) and keeps the real value.
(function () {
    function enhance(select, index) {
        var wrapper = document.createElement('div');
        wrapper.className = 'searchable-select';
        var input = document.createElement('input');
        var list = document.createElement('ul');
        var listId = 'searchable-list-' + index;
        var options = Array.from(select.options).filter(function (option) { return option.value !== ''; });
        var placeholder = 'Search…';
        var active = -1;

        input.type = 'text';
        input.className = select.className;
        input.placeholder = placeholder;
        input.autocomplete = 'off';
        input.required = select.required;
        input.setAttribute('role', 'combobox');
        input.setAttribute('aria-expanded', 'false');
        input.setAttribute('aria-controls', listId);
        input.setAttribute('aria-autocomplete', 'list');
        if (select.id) {
            input.id = 'searchable-' + select.id;
            var label = document.querySelector('label[for="' + select.id + '"]');
            if (label) { label.setAttribute('for', input.id); }
        }
        select.required = false;
        list.id = listId;
        list.className = 'searchable-select-list';
        list.setAttribute('role', 'listbox');
        list.hidden = true;

        select.hidden = true;
        select.parentNode.insertBefore(wrapper, select);
        wrapper.appendChild(select);
        wrapper.appendChild(input);
        wrapper.appendChild(list);

        function selectedLabel() {
            var option = select.options[select.selectedIndex];
            return option && option.value !== '' ? option.textContent : '';
        }

        function visibleItems() {
            return Array.from(list.querySelectorAll('li[data-value]'));
        }

        function highlight(position) {
            var items = visibleItems();
            items.forEach(function (item) { item.classList.remove('is-active'); });
            active = items.length ? (position + items.length) % items.length : -1;
            if (active >= 0) {
                items[active].classList.add('is-active');
                items[active].scrollIntoView({ block: 'nearest' });
            }
        }

        function render(query) {
            var needle = query.trim().toLowerCase();
            list.textContent = '';
            var group = null;
            options.forEach(function (option) {
                var meta = option.dataset.meta || '';
                var haystack = (option.textContent + ' ' + meta).toLowerCase();
                if (needle && haystack.indexOf(needle) === -1) { return; }
                if (option.dataset.group && option.dataset.group !== group) {
                    group = option.dataset.group;
                    var heading = document.createElement('li');
                    heading.className = 'searchable-select-group';
                    heading.setAttribute('role', 'presentation');
                    heading.textContent = group;
                    list.appendChild(heading);
                }
                var item = document.createElement('li');
                item.setAttribute('role', 'option');
                item.dataset.value = option.value;
                var text = document.createElement('span');
                text.textContent = option.textContent;
                item.appendChild(text);
                if (meta) {
                    var note = document.createElement('small');
                    note.textContent = meta;
                    item.appendChild(note);
                }
                if (option.value === select.value) { item.setAttribute('aria-selected', 'true'); }
                list.appendChild(item);
            });
            if (!list.children.length) {
                var empty = document.createElement('li');
                empty.className = 'searchable-select-empty';
                empty.textContent = 'No matches';
                list.appendChild(empty);
            }
            highlight(0);
        }

        function open() {
            render(input.value === selectedLabel() ? '' : input.value);
            list.hidden = false;
            input.setAttribute('aria-expanded', 'true');
        }

        function close() {
            list.hidden = true;
            input.setAttribute('aria-expanded', 'false');
            input.value = selectedLabel();
        }

        function choose(value) {
            select.value = value;
            select.dispatchEvent(new Event('change', { bubbles: true }));
            close();
        }

        input.value = selectedLabel();
        input.addEventListener('focus', function () { input.select(); open(); });
        input.addEventListener('click', function () { if (list.hidden) { open(); } });
        input.addEventListener('input', function () {
            if (input.value === '') { select.value = ''; }
            render(input.value);
            list.hidden = false;
            input.setAttribute('aria-expanded', 'true');
        });
        input.addEventListener('keydown', function (event) {
            if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                event.preventDefault();
                if (list.hidden) { open(); }
                highlight(active + (event.key === 'ArrowDown' ? 1 : -1));
            } else if (event.key === 'Enter' && !list.hidden) {
                event.preventDefault();
                var item = visibleItems()[active];
                if (item) { choose(item.dataset.value); }
            } else if (event.key === 'Escape' && !list.hidden) {
                event.stopPropagation();
                close();
            }
        });
        list.addEventListener('mousedown', function (event) {
            // mousedown (not click) so the input's blur does not close the list first.
            var item = event.target.closest('li[data-value]');
            if (item) {
                event.preventDefault();
                choose(item.dataset.value);
            }
        });
        input.addEventListener('blur', close);
    }

    document.querySelectorAll('select[data-searchable]').forEach(enhance);
})();
