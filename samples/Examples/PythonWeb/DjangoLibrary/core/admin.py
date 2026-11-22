# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Django admin (/admin/): manage authors and books with search, filters and inline books."""
from django.contrib import admin

from .models import Author, Book


class BookInline(admin.TabularInline):
    model = Book
    extra = 0
    fields = ("title", "year", "genre", "available")


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "country")
    search_fields = ("name",)
    inlines = [BookInline]


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "year", "genre", "available", "borrower")
    list_filter = ("genre", "available")
    search_fields = ("title", "author__name", "isbn")
