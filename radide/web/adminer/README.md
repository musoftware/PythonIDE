# Adminer for RAD IDE

`adminer.php` = Adminer 6.3.0 (single-file database manager, Apache-2.0 / GPL-2.0, see LICENSE.txt).
`index.php` = launcher used by Databases > "Open in Adminer" (radide/web_site/databases.py `AdminerServer`):
served with `php -S 127.0.0.1:<private port>`, logs in automatically with a per-session random token.

Update: download `adminer-<version>.php` from https://github.com/vrana/adminer/releases and save it as `adminer.php`.
