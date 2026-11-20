from django.http import HttpResponse
from django.urls import path


def home(request):
    return HttpResponse("<h1>Hello from Django in Docker</h1>")


urlpatterns = [path("", home)]
