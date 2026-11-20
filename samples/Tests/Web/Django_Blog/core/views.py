from django.conf import settings
from django.shortcuts import render
import django


def about(request):
    return render(request, "core/about.html", {"site_name": settings.SITE_NAME,
                                               "django_version": django.get_version()})
