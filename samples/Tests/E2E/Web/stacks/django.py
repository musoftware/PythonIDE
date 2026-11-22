# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""RAD Store in Django 5 (New Project > Web > Django App): Product model + migrations from the Django panel,
ModelForm validation, django.contrib.auth login, class-free views, JSON API, Arabic RTL page."""
TITLE = "Python Django + SQLite"
LANG, TEMPLATE, NAME = "python-django", "django-app", "DjangoStore"
TOOLS = []
WEBROOT = "."
DB_FILE = "db.sqlite3"
DESIGN = "templates/core/home.html"
DESIGN_TARGET = "#home"
DESIGN_KEEP = ["{% load static %}", "{% static 'css/site.css' %}"]
ROUTES = {"home": "/", "products": "/products/", "add": "/products/add/", "edit": "/products/{id}/edit/",
          "login": "/accounts/login/", "ar": "/ar/", "api": "/api/products/", "css": "/static/css/site.css"}
LOGIN_ERROR = "correct username and password"
DEBUG = {"file": "core/views.py", "match": "rows = Product.objects.filter(", "path": "/products/"}
INTELLI = {"file": "core/views.py", "after": "def products(request):", "type": 'reverse("core:pro',
           "expect": "core:products", "html_file": "templates/core/ar.html", "css_file": "static/css/site.css"}
PUBLISH_EXPECT = ["manage.py", "config/settings.py", "core/models.py", "core/views.py", "templates/core/home.html",
                  "static/css/site.css", "core/migrations/0001_initial.py"]
PUBLISH_FORBID = [".venv"]
RUN_TIMEOUT = 600
CTX: dict = {}


def serve_published(dest, port, **_):
    """The host: migrate + seed, then the server (the project's venv stands in for the host's Python)."""
    import os
    import subprocess
    from radide.web_site.frameworks.python_web import venv_python
    py = venv_python(CTX.get("folder", "")) if CTX.get("folder") else ""
    if not py:
        return None, "the project's .venv was not created", None
    for argv in (["manage.py", "migrate", "--noinput"], ["manage.py", "seed_store"]):
        r = subprocess.run([py, *argv], cwd=str(dest), capture_output=True, text=True, timeout=300)
        if r.returncode:
            return None, f"{' '.join(argv)} failed on the published copy: {(r.stdout + r.stderr)[-300:]}", None
    return [py, "manage.py", "runserver", f"127.0.0.1:{port}", "--noreload", "--insecure"], str(dest), \
        dict(os.environ)


def after_create(j, win, project, folder):
    CTX["folder"] = str(folder)
    return ""


SETTINGS_EXTRA = """

# ---- RAD Store
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/products/"
LOGOUT_REDIRECT_URL = "/"
"""


def panel_run(j, win, cid, values=None, timeout=300):
    import e2e_lib as E
    panel = win.python_web
    win.dock_python_web.show()
    panel.sync_project(force=True)
    E.pump(0.5)
    ok = panel.run_command(cid, values)
    j.check(ok, f"Django panel command {cid} did not start")
    code = panel.wait(timeout)
    j.check(code == 0, f"{cid} exit code {code}; output: {j.output_text()[-800:]}")
    return code


def after_code(j, win, project, folder):
    """settings.py edit, then the Django panel: makemigrations, migrate, createsuperuser (admin / secret)."""
    sp = folder / "config" / "settings.py"
    text = sp.read_text(encoding="utf-8")
    if "RAD Store" not in text:
        j.edit(sp, text.rstrip() + "\n" + SETTINGS_EXTRA)
    import e2e_lib as E
    E.pump(0.5)
    panel_run(j, win, "makemigrations")
    panel_run(j, win, "migrate")
    panel_run(j, win, "createsuperuser", {"username": "admin", "email": "admin@example.com", "password": "secret"})
    j.check((folder / "core" / "migrations" / "0001_initial.py").exists(), "makemigrations wrote no migration")
    j.shot(win.dock_python_web, "django_panel")
    return "Django panel: makemigrations, migrate, createsuperuser"


# the products table is made by the migration: the Databases workspace adds the demo rows
DB_SQL = """-- RAD Store demo rows (the products table comes from core/migrations/0001_initial.py)
INSERT INTO products (name, price) VALUES ('Laptop', 999.5), ('Phone', 450);
"""

MODELS = '''from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "products"
        ordering = ["id"]

    def __str__(self):
        return self.name
'''

FORMS = '''from django import forms

from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "price"]

    def clean_price(self):
        price = self.cleaned_data["price"]
        if price is not None and price < 0:
            raise forms.ValidationError("Price must be a positive number")
        return price
'''

VIEWS = '''from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import ProductForm
from .models import Product


def home(request):
    return render(request, "core/home.html")


def products(request):
    q = request.GET.get("q", "")
    rows = Product.objects.filter(name__icontains=q)
    return render(request, "core/products.html", {"products": rows, "q": q})


@login_required
def add(request):
    form = ProductForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect(reverse("core:products"))
    return render(request, "core/product_form.html", {"form": form, "title": "Add product"},
                  status=422 if form.errors else 200)


@login_required
def edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("core:products")
    return render(request, "core/product_form.html", {"form": form, "title": "Edit product", "product": product},
                  status=422 if form.errors else 200)


@login_required
@require_POST
def delete(request, pk):
    get_object_or_404(Product, pk=pk).delete()
    return redirect("core:products")


def arabic(request):
    return render(request, "core/ar.html", {"count": Product.objects.count()})


def api_products(request):
    data = [{"id": p.id, "name": p.name, "price": float(p.price)} for p in Product.objects.all()]
    return JsonResponse(data, safe=False, json_dumps_params={"ensure_ascii": False})
'''

URLS = '''from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.products, name="products"),
    path("products/add/", views.add, name="add"),
    path("products/<int:pk>/edit/", views.edit, name="edit"),
    path("products/<int:pk>/delete/", views.delete, name="delete"),
    path("ar/", views.arabic, name="arabic"),
    path("api/products/", views.api_products, name="api_products"),
]
'''

PROJECT_URLS = '''"""URL configuration of RAD Store."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("core.urls")),
]
'''

ADMIN = '''from django.contrib import admin

from .models import Product

admin.site.register(Product)
'''

SEED = '''"""manage.py seed_store - demo rows + the admin account on a new host."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import Product


class Command(BaseCommand):
    help = "Create the RAD Store demo products and the admin / secret account when missing"

    def handle(self, *args, **options):
        if not Product.objects.exists():
            Product.objects.create(name="Laptop", price=999.5)
            Product.objects.create(name="Phone", price=450)
        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "secret")
        self.stdout.write(f"{Product.objects.count()} products")
'''

BASE = """{% load static %}<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}RAD Store{% endblock %} - RAD Store</title>
<link rel="stylesheet" href="{% static 'css/site.css' %}">
</head>
<body>
<nav class="top"><a href="{% url 'core:home' %}">Home</a> <a href="{% url 'core:products' %}">Products</a>
<a href="{% url 'core:arabic' %}">العربية</a>
{% if user.is_authenticated %}<span class="user">{{ user.username }}</span>
<form method="post" action="{% url 'logout' %}" class="inline">{% csrf_token %}<button type="submit">Log out</button></form>
{% else %}<a href="{% url 'login' %}">Log in</a>{% endif %}</nav>
<main>{% block content %}{% endblock %}</main>
</body>
</html>
"""

HOME = """{% load static %}<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RAD Store</title>
<link rel="stylesheet" href="{% static 'css/site.css' %}">
</head>
<body>
<nav class="top"><a href="/">Home</a> <a href="/products/">Products</a> <a href="/ar/">العربية</a> <a href="/accounts/login/">Log in</a></nav>
<main id="home">
</main>
</body>
</html>
"""

PRODUCTS = """{% extends "base.html" %}
{% block title %}Products{% endblock %}
{% block content %}
<h1>Products</h1>
<form method="get" class="search"><input name="q" value="{{ q }}" placeholder="Search"><button>Search</button></form>
{% if user.is_authenticated %}<p><a class="btn" href="{% url 'core:add' %}">Add product</a></p>{% endif %}
<table id="products"><thead><tr><th>Name</th><th>Price</th><th></th></tr></thead><tbody>
{% for p in products %}
<tr data-id="{{ p.id }}"><td class="name">{{ p.name }}</td><td>{{ p.price }}</td>
<td>{% if user.is_authenticated %}<a href="{% url 'core:edit' p.id %}">Edit</a>{% endif %}</td></tr>
{% endfor %}
</tbody></table>
<p class="count">{{ products|length }} products</p>
{% endblock %}
"""

FORM = """{% extends "base.html" %}
{% block title %}{{ title }}{% endblock %}
{% block content %}
<h1>{{ title }}</h1>
<form method="post" class="product">{% csrf_token %}
{{ form.as_p }}
<button type="submit">Save</button>
</form>
{% if product %}
<form method="post" action="{% url 'core:delete' product.id %}" class="delete">{% csrf_token %}
<button type="submit">Delete</button></form>
{% endif %}
{% endblock %}
"""

LOGIN = """{% extends "base.html" %}
{% block title %}Log in{% endblock %}
{% block content %}
<h1>Log in</h1>
{% if form.errors %}<p class="error">{{ form.non_field_errors|striptags }}</p>{% endif %}
<form method="post" class="login">{% csrf_token %}
<input type="hidden" name="next" value="{{ next }}">
<label>User name {{ form.username }}</label>
<label>Password {{ form.password }}</label>
<button type="submit">Log in</button>
</form>
{% endblock %}
"""

AR = """{% load static %}<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>متجر راد</title><link rel="stylesheet" href="{% static 'css/site.css' %}"></head>
<body>
<nav class="top"><a href="/">English</a> <a href="/products/">المنتجات</a></nav>
<main><h1>مرحبا بكم في متجر راد</h1><p id="count">عدد المنتجات: {{ count }}</p></main>
</body>
</html>
"""

CSS = """/* RAD Store */
body { font-family: "Segoe UI", Tahoma, sans-serif; margin: 0; background: #f4f6f5; color: #222; }
nav.top { background: #0c4b33; padding: 10px 16px; }
nav.top a, nav.top .user { color: #fff; margin-inline-end: 14px; text-decoration: none; }
form.inline { display: inline; }
main { max-width: 900px; margin: 20px auto; padding: 0 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; }
th, td { padding: 8px; border-bottom: 1px solid #ddd; text-align: start; }
.error, .errorlist { color: #b00020; font-weight: bold; }
.hero { padding: 40px 20px; background: linear-gradient(90deg, #0c4b33, #44b78b); color: #fff; border-radius: 12px; }
"""


def files():
    return {"core/models.py": MODELS, "core/forms.py": FORMS, "core/views.py": VIEWS, "core/urls.py": URLS,
            "core/admin.py": ADMIN, "config/urls.py": PROJECT_URLS,
            "core/management/__init__.py": "", "core/management/commands/__init__.py": "",
            "core/management/commands/seed_store.py": SEED,
            "templates/base.html": BASE, "templates/core/home.html": HOME, "templates/core/products.html": PRODUCTS,
            "templates/core/product_form.html": FORM, "templates/registration/login.html": LOGIN,
            "templates/core/ar.html": AR, "static/css/site.css": CSS}
