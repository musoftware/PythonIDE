# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""RAD Store on Ruby on Rails: New Project > Web > Ruby on Rails App. The IDE prepares the app (rails new, bundle
install, db:prepare), the Framework Tools CLI generates the Product scaffold, then the user adds validations, a
login, a JSON API route and the Arabic page. Home page: public/index.html (Design View)."""
TITLE = "Ruby on Rails 8 + SQLite (scaffold)"
LANG, TEMPLATE, NAME = "rails-web", "rails-app", "RailsStore"
TOOLS = ["ruby"]
WEBROOT = "public"
DB_FILE = "storage/development.sqlite3"
DESIGN = "public/index.html"
DESIGN_TARGET = "#home"
ROUTES = {"home": "/", "products": "/products", "add": "/products/new", "edit": "/products/{id}/edit",
          "delete_page": "/products/{id}", "login": "/login", "ar": "/ar.html", "api": "/api/products",
          "css": "/css/site.css", "js": "/js/app.js"}
PRODUCT_FIELDS = ("product[name]", "product[price]")
REQUIRED_ERROR = "be blank"
DELETE_FORM_MATCH = "/products/"
PREVIEW_ROWS = "#products > div"
DEBUG = {"file": "app/controllers/products_controller.rb", "match": "@products = Product.order(:id)",
         "path": "/products"}
DEBUG_TIMEOUT = 300
DEBUG_SETTLE = 5.0
INTELLI = {"file": "app/controllers/products_controller.rb", "after": "def index", "type": "Product.whe",
           "expect": "where", "timeout": 40, "html_file": "public/index.html", "css_file": "public/css/site.css"}
PUBLISH_EXPECT = ["Gemfile", "Gemfile.lock", "config/routes.rb", "app/controllers/products_controller.rb",
                  "app/models/product.rb", "public/index.html", "db/seeds.rb"]
PUBLISH_FORBID = ["storage/development.sqlite3"]
PUBLISH_EXCLUDES = ["vendor/bundle", "tmp", "log", "storage", "node_modules"]
RUN_TIMEOUT = 900
PUBLISHED_TIMEOUT = 600
DEV: list = []

DB_SQL = """-- RAD Store demo rows (the products table comes from the scaffold's migration)
INSERT INTO products (name, price, created_at, updated_at)
VALUES ('Laptop', 999.5, datetime('now'), datetime('now')), ('Phone', 450, datetime('now'), datetime('now'));
"""


def after_create(j, win, project, folder):
    """The IDE's Rails preparation (what the 'not ready to run yet' question does), then the scaffold."""
    from radide.features import rails_ide
    from stacks._fw import cli
    DEV[:] = [str(folder)]
    needs = rails_ide.needs_setup(project)
    j.check("devkit" not in needs, f"the DevKit next to Ruby was not found: {needs}")
    runner = rails_ide.prepare_project(win, project, ask=False, wait=False)
    if runner is not None:
        import e2e_lib as E
        done = {}
        runner.finished.connect(lambda ok: done.setdefault("ok", ok))
        E.wait(lambda: "ok" in done, 3000, 0.5)
        j.check(done.get("ok"), f"Rails preparation failed ({needs}): {j.output_text()[-1500:]}")
    ok, out = cli(j, win, project, "rails generate scaffold Product name:string price:decimal", 600)
    j.check(ok, f"scaffold failed: {out[-800:]}")
    ok, out = cli(j, win, project, "rails db:migrate", 300)
    j.check(ok, f"db:migrate failed: {out[-800:]}")
    return f"prepared ({', '.join(needs) or 'nothing missing'}), scaffold Product + db:migrate"


def serve_published(dest, port, **_):
    """The host: gems already installed (BUNDLE_PATH), db:prepare (creates + seeds), rails server."""
    import os
    import subprocess
    from pathlib import Path
    from radide.web_site.frameworks.rails import ruby_env, ruby_exe
    env = dict(os.environ)
    env.update(ruby_env(Path(dest)))
    ruby = ruby_exe()
    if DEV:      # the host's gems: point the copy's bundle at an installed gem folder (.bundle/config wins over ENV)
        gems = str(Path(DEV[0]) / "vendor" / "bundle")
        subprocess.run([ruby, "-S", "bundle", "config", "set", "--local", "path", gems], cwd=str(dest), env=env,
                       capture_output=True, timeout=120)
    r = subprocess.run([ruby, "bin/rails", "db:prepare"], cwd=str(dest), env=env, capture_output=True, text=True,
                       timeout=600)
    if r.returncode != 0:
        return None, f"db:prepare failed on the published copy: {(r.stdout + r.stderr)[-500:]}", None
    return [ruby, "bin/rails", "server", "-p", str(port), "-b", "127.0.0.1", "-P", "tmp/pids/published.pid"], \
        str(dest), env


MODEL = """class Product < ApplicationRecord
  validates :name, presence: true
  validates :price, presence: true, numericality: { greater_than_or_equal_to: 0 }
end
"""

APP_CONTROLLER = """class ApplicationController < ActionController::Base
  helper_method :current_user

  private

  def current_user
    session[:user]
  end

  def require_login
    redirect_to login_path(next: request.fullpath) unless current_user
  end
end
"""

SESSIONS = """class SessionsController < ApplicationController
  def new
  end

  def create
    if params[:username] == "admin" &&
       ActiveSupport::SecurityUtils.secure_compare(params[:password].to_s, "secret")
      reset_session
      session[:user] = "admin"
      target = params[:next].to_s
      redirect_to(target.start_with?("/") ? target : products_path)
    else
      flash.now[:alert] = "Invalid user name or password"
      render :new, status: :unauthorized
    end
  end

  def destroy
    reset_session
    redirect_to root_path
  end
end
"""

LOGIN_VIEW = """<h1>Log in</h1>
<% if flash[:alert] %><p class="error"><%= flash[:alert] %></p><% end %>
<%= form_with url: login_path, method: :post, class: "login" do |f| %>
  <%= hidden_field_tag :next, params[:next] %>
  <label>User name <%= text_field_tag :username %></label>
  <label>Password <%= password_field_tag :password %></label>
  <%= f.submit "Log in" %>
<% end %>
"""

ROUTES_RB = """Rails.application.routes.draw do
  resources :products
  get "login", to: "sessions#new"
  post "login", to: "sessions#create"
  delete "logout", to: "sessions#destroy"
  get "api/products", to: "products#api"
  get "up" => "rails/health#show", as: :rails_health_check
  root to: redirect("/index.html")
end
"""

LAYOUT = """<!DOCTYPE html>
<html lang="en">
  <head>
    <title><%= content_for(:title) || "RAD Store" %></title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <%= csrf_meta_tags %>
    <%= csp_meta_tag %>
    <link rel="stylesheet" href="/css/site.css">
  </head>
  <body>
    <nav class="top"><a href="/">Home</a> <%= link_to "Products", products_path %> <a href="/ar.html">العربية</a>
    <% if current_user %><span class="user"><%= current_user %></span>
      <%= button_to "Log out", logout_path, method: :delete, form: { style: "display:inline" } %>
    <% else %><%= link_to "Log in", login_path %><% end %></nav>
    <main><%= yield %></main>
    <script src="/js/app.js"></script>
  </body>
</html>
"""

SEEDS = """# demo rows of a new database (bin/rails db:prepare / db:seed)
if Product.none?
  Product.create!(name: "Laptop", price: 999.5)
  Product.create!(name: "Phone", price: 450)
end
"""

INDEX = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RAD Store</title>
<link rel="stylesheet" href="/css/site.css">
</head>
<body>
<nav class="top"><a href="/">Home</a> <a href="/products">Products</a> <a href="/ar.html">العربية</a> <a href="/login">Log in</a></nav>
<main id="home">
</main>
<script src="/js/app.js"></script>
</body>
</html>
"""

AR = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>متجر راد</title><link rel="stylesheet" href="/css/site.css"></head>
<body>
<nav class="top"><a href="/">English</a> <a href="/products">المنتجات</a></nav>
<main><h1>مرحبا بكم في متجر راد</h1><p>أفضل الأجهزة بأفضل الأسعار.</p></main>
</body>
</html>
"""

CSS = """/* RAD Store */
body { font-family: "Segoe UI", Tahoma, sans-serif; margin: 0; background: #f6f7fb; color: #222; }
nav.top { background: #cc0000; padding: 10px 16px; }
nav.top a, nav.top .user { color: #fff; margin-inline-end: 14px; text-decoration: none; }
main { max-width: 900px; margin: 20px auto; padding: 0 16px; }
.error, #error_explanation { color: #b00020; font-weight: bold; }
.hero { padding: 40px 20px; background: linear-gradient(90deg, #990000, #e53935); color: #fff; border-radius: 12px; }
"""


def after_code(j, win, project, folder):
    """The scaffold's controller: login for the changing actions, list ordered by id, the JSON API action."""
    from pathlib import Path
    p = Path(folder) / "app/controllers/products_controller.rb"
    text = p.read_text(encoding="utf-8")
    text = text.replace("class ProductsController < ApplicationController\n",
                        "class ProductsController < ApplicationController\n"
                        "  before_action :require_login, except: %i[ index show api ]\n", 1)
    text = text.replace("@products = Product.all", "@products = Product.order(:id)")
    text = text.replace("  private\n", "  # GET /api/products\n  def api\n"
                        "    render json: Product.order(:id).map { |p| { id: p.id, name: p.name, price: p.price.to_f } }\n"
                        "  end\n\n  private\n", 1)
    j.check("def api" in text and "require_login" in text, "scaffold controller has an unexpected shape")
    j.edit(p, text)
    return "products_controller.rb edited (login, order, api)"


def files():
    return {"app/models/product.rb": MODEL, "app/controllers/application_controller.rb": APP_CONTROLLER,
            "app/controllers/sessions_controller.rb": SESSIONS, "app/views/sessions/new.html.erb": LOGIN_VIEW,
            "config/routes.rb": ROUTES_RB, "app/views/layouts/application.html.erb": LAYOUT, "db/seeds.rb": SEEDS,
            "public/index.html": INDEX, "public/ar.html": AR, "public/css/site.css": CSS,
            "public/js/app.js": "// RAD Store\ndocument.addEventListener('DOMContentLoaded', () => { document.body.dataset.ready = '1'; });\n"}
