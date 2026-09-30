// Confirm before submitting any form[data-confirm] (e.g. row delete actions).
(function () {
    document.addEventListener('submit', function (event) {
        var form = event.target.closest('form[data-confirm]');
        if (form && !window.confirm(form.dataset.confirm)) {
            event.preventDefault();
        }
    });
})();
