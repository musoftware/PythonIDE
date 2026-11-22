from django.urls import path

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
