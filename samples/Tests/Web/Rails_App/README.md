# Rails_App

**rails-web (Ruby on Rails 8.1, Ruby 4.0, SQLite)** - made with New Project > Web > Ruby on Rails / Sinatra >
*Ruby on Rails App*. The IDE installed the RubyInstaller **DevKit** (MSYS2 + UCRT gcc, per user in
`%LOCALAPPDATA%\RADIDE\toolchains\msys64`) and the `rails` gem (private GEM_HOME `tools\rails-gems`), ran `rails new .`
and `bundle install` (gems in `vendor/bundle`). `Product` was added with
`rails generate scaffold Product name:string price:decimal`.

When you open it, the IDE offers to run `bundle install` + `bin/rails db:prepare` (the gems and the database were
removed from the sample) - progress in the Output window.

What it shows:
- **Ctrl+F5**: `bin/rails server` behind the dev server + Preview; Rails reloads code by itself. Try `/products`
  (scaffold CRUD) and `/up`.
- **F5 = debugger** (the `debug` gem / rdbg over DAP): set a breakpoint (F9) in `ProductsController#index`, in
  `app/models/product.rb` or in a view such as `app/views/products/index.html.erb`, open `/products` in the Preview:
  it stops there - Locals (local variables and the `@instance` variables), Call Stack, Watch, F10 / F11 / Shift+F11.
- **Rails menu** (and right-click on folders in Solution Explorer): Server, Debug, Console; Generate (controller,
  model with an attributes form, scaffold, resource, migration, mailer, job, helper, channel, authentication,
  destroy) - the new files open in the editor; Database (db:migrate, rollback, status, seed, prepare, reset,
  db:system:change, show in Databases); Tests (run, set up minitest, new test); Bundler (install, update, outdated,
  add gem); Routes, Edit Credentials, assets:precompile. Right-click `app/views/products` > New View / New Partial,
  `db/migrate` > New Migration / Migrate, a migration file > Run / Revert this migration.
- **Rails panel** (View > Rails Panel): *Console* (Ruby with the app loaded: `Product.count`, `Product.create!(...)`;
  SQL is shown; variables are kept between lines), *Routes* (double-click = controller action), *Models* (columns
  from `db/schema.rb` + associations).
- **IntelliSense** (ruby-lsp + Rails items read from the project): `*_path` / `*_url` route helpers, `Product.` (query
  methods, scopes, `find_by_<column>`), `@product.` / `product.` inside `@products.each do |product|` (columns,
  associations), `render "` (views / partials), `t("` (locale keys), `ENV["`, `to: "` in routes.rb
  (controller#action), `permit(:` / `params.expect(product: [` (columns), `@vars` of the controller action in its view.
  **ERB** views open in the ERB language (HTML + Ruby colouring), with the same completions inside `<%= %>`.
- **F12 / Ctrl+click**: a route helper -> its controller action, `render "form"` -> `_form.html.erb`, `Product` ->
  `app/models/product.rb`, a column -> `db/schema.rb`, `@products` in a view -> its assignment in the controller.
- **Databases**: `storage/development.sqlite3` is added to the Databases workspace (tables, data, SQL).
- **Test Explorer**: Rails minitest tests (`test/**/*_test.rb`, after Rails > Tests > Set Up Tests - this sample was
  made with `--skip-test`; new apps have tests) and RSpec specs are discovered and run with pass / fail per test.

Removed: `vendor/bundle`, `tmp`, `log`, the SQLite files, `config/master.key` + `credentials.yml.enc` (Rails makes a
development secret by itself).
