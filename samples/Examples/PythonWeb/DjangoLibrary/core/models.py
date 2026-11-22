# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""The library's data: authors and books (SQLite through the Django ORM)."""
from django.db import models
from django.urls import reverse


class Author(models.Model):
    name = models.CharField(max_length=100, unique=True)
    country = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Book(models.Model):
    GENRES = [("novel", "Novel"), ("science", "Science"), ("history", "History"), ("kids", "Children"),
              ("other", "Other")]
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="books")
    year = models.PositiveIntegerField(null=True, blank=True)
    genre = models.CharField(max_length=20, choices=GENRES, default="novel")
    isbn = models.CharField("ISBN", max_length=20, blank=True)
    available = models.BooleanField(default=True)
    borrower = models.CharField(max_length=100, blank=True)
    added = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.author})"

    def get_absolute_url(self):
        return reverse("core:book_detail", args=[self.pk])
