# Sinatra_App

**rails-web, template *Sinatra App (pure Ruby)*** - a Sinatra 4 app (sinatra + rackup + webrick, no C code, so no
DevKit needed): ERB views with a layout, product list / details, a POST form and `/api/products` (JSON).

- **Ctrl+F5**: `bundle install` into `vendor/bundle` (first run), then `bundle exec ruby app.rb -p <port>`; saving a
  `.rb` file restarts the server, saving a view reloads the Preview.
- **Framework** dock: routes from `get '/x' do` lines, bundler commands. IntelliSense: `erb :` -> view names,
  `redirect '` -> routes.
