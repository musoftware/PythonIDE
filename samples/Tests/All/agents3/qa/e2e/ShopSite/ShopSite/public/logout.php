<?php
require dirname(__DIR__) . '/app/bootstrap.php';

// Logging out changes state, so it is a POST with a CSRF token (a link could be forged).
if (!is_post()) {
    render_error(405, 'Method not allowed', 'Use the Log out button.');
}
verify_csrf();
logout_user();
flash('info', 'You have been logged out.');
redirect('login.php');
