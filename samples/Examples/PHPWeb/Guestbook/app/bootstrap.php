<?php
// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Guestbook - shared code: session, CSRF token, the SQLite database (PDO) and the two interface languages.
// This folder is outside the web root (public/), so neither this code nor data/guestbook.sqlite can be
// downloaded through the web server.

declare(strict_types=1);

session_start();

const PAGE_SIZE = 5;

/** The PDO connection; the table is created on the first request. */
function db(): PDO
{
    static $pdo = null;
    if ($pdo === null) {
        $dir = dirname(__DIR__) . DIRECTORY_SEPARATOR . 'data';
        if (!is_dir($dir)) {
            mkdir($dir, 0775, true);
        }
        $pdo = new PDO('sqlite:' . $dir . DIRECTORY_SEPARATOR . 'guestbook.sqlite');
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
        $pdo->exec('CREATE TABLE IF NOT EXISTS messages (
                        id      INTEGER PRIMARY KEY AUTOINCREMENT,
                        name    TEXT NOT NULL,
                        message TEXT NOT NULL,
                        created TEXT NOT NULL DEFAULT (datetime(\'now\')))');
    }
    return $pdo;
}

function csrf_token(): string
{
    if (empty($_SESSION['csrf'])) {
        $_SESSION['csrf'] = bin2hex(random_bytes(16));
    }
    return $_SESSION['csrf'];
}

function csrf_ok(): bool
{
    return isset($_POST['csrf']) && hash_equals(csrf_token(), (string)$_POST['csrf']);
}

function e(string $s): string
{
    return htmlspecialchars($s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

/** Ids of the messages written in this browser session (only those can be deleted). */
function my_ids(): array
{
    return $_SESSION['mine'] ?? [];
}

// ------------------------------------------------------------------ languages (?lang=ar switches to Arabic, RTL)
const TEXTS = [
    'en' => ['title' => 'Guestbook', 'name' => 'Your name', 'message' => 'Message', 'sign' => 'Sign the guestbook',
             'delete' => 'Delete', 'empty' => 'No messages yet - be the first!', 'newer' => 'Newer', 'older' => 'Older',
             'thanks' => 'Thank you, your message was added.', 'deleted' => 'The message was deleted.',
             'bad' => 'Please write your name (max 60) and a message (max 1000 characters).',
             'expired' => 'The form expired, please try again.', 'count' => 'messages', 'other' => 'العربية'],
    'ar' => ['title' => 'سجل الزوار', 'name' => 'اسمك', 'message' => 'الرسالة', 'sign' => 'اكتب في السجل',
             'delete' => 'حذف', 'empty' => 'لا توجد رسائل بعد - كن أول من يكتب!', 'newer' => 'الأحدث', 'older' => 'الأقدم',
             'thanks' => 'شكرا لك، تمت إضافة رسالتك.', 'deleted' => 'تم حذف الرسالة.',
             'bad' => 'اكتب اسمك (حتى 60 حرفا) ورسالة (حتى 1000 حرف).',
             'expired' => 'انتهت صلاحية النموذج، حاول مرة أخرى.', 'count' => 'رسالة', 'other' => 'English'],
];

function lang(): string
{
    if (isset($_GET['lang']) && isset(TEXTS[$_GET['lang']])) {
        $_SESSION['lang'] = $_GET['lang'];
    }
    return $_SESSION['lang'] ?? 'en';
}

function t(string $key): string
{
    return TEXTS[lang()][$key];
}
