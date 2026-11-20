"""URL configuration of Django_Blog."""
from django.contrib import admin
from django.urls import include, path

from blog import views as blog_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/signup/", blog_views.signup, name="signup"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("about/", include("core.urls")),
    path("", include("blog.urls")),
]
