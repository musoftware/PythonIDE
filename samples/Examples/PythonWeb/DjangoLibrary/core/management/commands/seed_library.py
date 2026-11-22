# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""python manage.py seed_library  (View > Django > Run command... seed_library): a few sample books."""
from django.core.management.base import BaseCommand

from core.models import Author, Book

BOOKS = [
    ("Naguib Mahfouz", "Egypt", "Palace Walk", 1956, "novel"),
    ("Naguib Mahfouz", "Egypt", "The Cairo Trilogy: Sugar Street", 1957, "novel"),
    ("Ibn Khaldun", "Tunisia", "The Muqaddimah", 1377, "history"),
    ("Carl Sagan", "USA", "Cosmos", 1980, "science"),
    ("Antoine de Saint-Exupery", "France", "The Little Prince", 1943, "kids"),
]


class Command(BaseCommand):
    help = "Add sample authors and books"

    def handle(self, *args, **options):
        n = 0
        for author, country, title, year, genre in BOOKS:
            a, _ = Author.objects.get_or_create(name=author, defaults={"country": country})
            _, created = Book.objects.get_or_create(title=title, author=a, defaults={"year": year, "genre": genre})
            n += created
        self.stdout.write(self.style.SUCCESS(f"Added {n} books."))
