# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Forms: a ModelForm for books (with an "author name" text field that creates the author if needed)."""
from django import forms

from .models import Author, Book


class BookForm(forms.ModelForm):
    author_name = forms.CharField(label="Author", max_length=100)

    class Meta:
        model = Book
        fields = ["title", "author_name", "year", "genre", "isbn"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["author_name"].initial = self.instance.author.name

    def clean_year(self):
        year = self.cleaned_data.get("year")
        if year is not None and not 600 <= year <= 2100:
            raise forms.ValidationError("Enter a year between 600 and 2100.")
        return year

    def save(self, commit=True):
        self.instance.author, _ = Author.objects.get_or_create(name=self.cleaned_data["author_name"].strip())
        return super().save(commit)


class BorrowForm(forms.Form):
    borrower = forms.CharField(max_length=100)
