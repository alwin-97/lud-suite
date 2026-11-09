// Dismiss individual alerts and remove the empty container's spacing.
(function () {
    document.addEventListener('click', function (event) {
        var button = event.target.closest('[data-dismiss-message]');
        if (!button) return;

        var message = button.closest('[data-flash-message]');
        if (!message) return;

        var container = message.parentElement;
        message.remove();
        if (!container.querySelector('[data-flash-message]')) {
            container.remove();
        }
    });
})();
