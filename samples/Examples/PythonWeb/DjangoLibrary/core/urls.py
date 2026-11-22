# (c) 2026 Musoftware - https://musoftwares.com - MIT License
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.book_list, name="book_list"),
    path("books/new/", views.book_edit, name="book_new"),
    path("books/<int:pk>/", views.book_detail, name="book_detail"),
    path("books/<int:pk>/edit/", views.book_edit, name="book_edit"),
    path("books/<int:pk>/borrow/", views.book_borrow, name="book_borrow"),
    path("books/<int:pk>/delete/", views.book_delete, name="book_delete"),
    path("api/books/", views.api_books, name="api_books"),
]
