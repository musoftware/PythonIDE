// Shop - small progressive enhancements (the site works without JavaScript).
document.addEventListener('DOMContentLoaded', function () {
    // mobile navigation toggle
    var toggle = document.querySelector('.nav-toggle');
    var nav = document.getElementById('site-nav');
    if (toggle && nav) {
        toggle.addEventListener('click', function () {
            var open = nav.classList.toggle('open');
            toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        });
    }
    // confirmation before destructive form posts: <form data-confirm="Delete X?">
    document.querySelectorAll('form[data-confirm]').forEach(function (form) {
        form.addEventListener('submit', function (ev) {
            if (!window.confirm(form.getAttribute('data-confirm'))) {
                ev.preventDefault();
            }
        });
    });
    // flash messages fade out after a few seconds
    document.querySelectorAll('.flash-success, .flash-info').forEach(function (el) {
        setTimeout(function () { el.style.transition = 'opacity .6s'; el.style.opacity = '0'; }, 5000);
        setTimeout(function () { el.remove(); }, 5700);
    });
});
