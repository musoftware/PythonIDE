# My Blog (WordPress)

Created by the RAD IDE App Gallery: WordPress from wordpress.org with the SQLite Database Integration plugin 2.2.23 (no MySQL needed).

- Web root: `wordpress/`. Press F5 and finish the 5-minute install (site title, admin user).
- The database is `database/wordpress.sqlite`, outside the web root.
- Pretty permalinks need a web server with URL rewriting; with `php -S` keep the default ("Plain") permalinks.

## After cloning: get the WordPress core

The repository keeps only this site's own files (`wp-config.php`, the SQLite Database Integration plugin, `db.php`, uploads, the `database` folder). Run `get_wordpress_core.bat` (or `python get_wordpress_core.py`) once: it downloads WordPress 7.1.5 from wordpress.org, checks its SHA-1 and extracts wp-admin, wp-includes, the default themes and Akismet without overwriting your files. Then open the project and press F5.

