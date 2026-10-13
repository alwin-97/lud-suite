// Program -> location -> cohort role picker (components/forms/assignment_picker.html).
// All checkboxes stay in the form; only the chosen location's group is shown.
(function () {
    document.querySelectorAll('[data-assignment-picker]').forEach(function (picker) {
        var program = picker.querySelector('[data-picker-program]');
        var location = picker.querySelector('[data-picker-location]');
        if (!program || !location) { return; }

        var locationOptions = Array.from(location.options);
        var groups = Array.from(picker.querySelectorAll('[data-picker-group]'));
        var summary = picker.querySelector('.assignment-summary');
        var summaryList = picker.querySelector('[data-picker-summary-list]');

        function showGroup() {
            groups.forEach(function (group) { group.hidden = group.dataset.pickerGroup !== location.value; });
        }

        function fillLocations() {
            location.textContent = '';
            locationOptions.forEach(function (option) {
                if (option.dataset.program === program.value) { location.appendChild(option); }
            });
            showGroup();
        }

        function updateSummary() {
            summaryList.textContent = '';
            picker.querySelectorAll('input[data-picker-summary]:checked').forEach(function (input) {
                var item = document.createElement('li');
                item.textContent = input.dataset.pickerSummary;
                summaryList.appendChild(item);
            });
            summary.hidden = !summaryList.children.length;
        }

        // Start on the program/location of the first already-selected role, if any.
        var first = picker.querySelector('input[data-picker-summary]:checked');
        if (first) {
            var group = first.closest('[data-picker-group]');
            var match = locationOptions.find(function (option) { return option.value === group.dataset.pickerGroup; });
            if (match) { program.value = match.dataset.program; }
        }
        program.hidden = false;
        location.hidden = false;
        fillLocations();
        if (first) {
            location.value = first.closest('[data-picker-group]').dataset.pickerGroup;
            showGroup();
        }
        updateSummary();

        program.addEventListener('change', fillLocations);
        location.addEventListener('change', showGroup);
        picker.addEventListener('change', function (event) {
            if (event.target.matches('input[data-picker-summary]')) { updateSummary(); }
        });
    });
})();
