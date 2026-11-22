# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""URL configuration of DjangoLibrary."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
]
