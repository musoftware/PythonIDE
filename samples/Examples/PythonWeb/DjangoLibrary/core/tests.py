# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""python manage.py test core"""
from django.test import TestCase
from django.urls import reverse

from .models import Book


class LibraryTests(TestCase):
    def test_add_borrow_return(self):
        r = self.client.post(reverse("core:book_new"), {"title": "Test Book", "author_name": "Someone",
                                                         "year": 2020, "genre": "novel", "isbn": ""})
        book = Book.objects.get(title="Test Book")
        self.assertRedirects(r, book.get_absolute_url())
        self.client.post(reverse("core:book_borrow", args=[book.pk]), {"borrower": "Omar"})
        book.refresh_from_db()
        self.assertFalse(book.available)
        self.client.post(reverse("core:book_borrow", args=[book.pk]))
        book.refresh_from_db()
        self.assertTrue(book.available)

    def test_year_validation(self):
        r = self.client.post(reverse("core:book_new"), {"title": "X", "author_name": "Y", "year": 99,
                                                         "genre": "novel"})
        self.assertContains(r, "between 600 and 2100")
