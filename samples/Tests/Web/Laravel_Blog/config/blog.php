<?php

return [

    /* The blog's name in the header (defaults to APP_NAME). */
    'title' => env('BLOG_TITLE', env('APP_NAME', 'Laravel Blog')),

    /* Posts per page on /posts and /api/posts. */
    'per_page' => (int) env('BLOG_PER_PAGE', 6),

    'comments' => [
        'enabled' => (bool) env('BLOG_COMMENTS', true),
        'max_length' => 2000,
    ],

];
