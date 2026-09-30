// Account popover in the app bar: click to open, outside click or Escape to close.
(function () {
    var button = document.getElementById('accountButton');
    var popover = document.getElementById('accountPopover');
    if (!button || !popover) {
        return;
    }

    function setOpen(open) {
        popover.hidden = !open;
        button.setAttribute('aria-expanded', String(open));
    }

    button.addEventListener('click', function (event) {
        event.stopPropagation();
        setOpen(popover.hidden);
    });

    document.addEventListener('click', function (event) {
        if (!popover.hidden && !popover.contains(event.target)) {
            setOpen(false);
        }
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && !popover.hidden) {
            setOpen(false);
            button.focus();
        }
    });
})();
