# Rails_App

**rails-web (Ruby on Rails 8.1, Ruby 4.0, SQLite)** - made with New Project > Web > Ruby on Rails / Sinatra >
*Ruby on Rails App*. The first F5 of that template installed the RubyInstaller **DevKit** (MSYS2 + UCRT gcc, per user in
`%LOCALAPPDATA%\RADIDE\toolchains\msys64`) and the `rails` gem (private GEM_HOME `tools\rails-gems`), ran `rails new .`
and `bundle install` (gems in `vendor/bundle`). `Product` was added with the CLI panel's *Generate scaffold*
(`rails generate scaffold Product name:string price:decimal`).

What it shows:
- **Ctrl+F5 / F5**: `bundle install` (first time), `bin/rails db:prepare`, `bin/rails server` behind the dev server;
  Rails reloads code by itself. Try `/products` (scaffold CRUD) and `/up`.
- **Framework** dock: routes from `bin/rails routes` (fallback: config/routes.rb), generators / migrations / bundler
  commands, tools (Ruby, DevKit, rails gem - with Install buttons).
- IntelliSense: `render "` -> view names, `link_to 'x', ` / `redirect_to ` -> `*_path` route helpers.
- No debugger for Ruby web apps yet (F5 runs without breakpoints).

Removed: `vendor/bundle`, `tmp`, `log`, the SQLite files, `config/master.key` + `credentials.yml.enc` (Rails makes a
development secret by itself).
