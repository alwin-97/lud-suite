// Delegation also supports forms loaded into the drawer.
(function () {
    document.addEventListener('input', function (event) {
        if (!event.target.matches('[data-member-search]')) return;
        var query = event.target.value.trim().toLowerCase();
        var select = event.target.closest('.form-field').querySelector('select');
        Array.from(select.options).forEach(function (option) {
            option.hidden = !option.selected && !option.textContent.toLowerCase().includes(query);
        });
    });
})();
