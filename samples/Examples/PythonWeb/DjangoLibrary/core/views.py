# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Views of the library: list (search + genre filter + paging), detail, add/edit (ModelForm), borrow/return
(POST with CSRF), delete with confirmation, and a JSON endpoint."""
import django
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import BookForm, BorrowForm
from .models import Author, Book


def _ctx(**kw):
    return {"site_name": settings.SITE_NAME, "django_version": django.get_version(), **kw}


def book_list(request):
    q, genre = request.GET.get("q", "").strip(), request.GET.get("genre", "")
    books = Book.objects.select_related("author")
    if q:
        books = books.filter(Q(title__icontains=q) | Q(author__name__icontains=q) | Q(isbn__icontains=q))
    if genre:
        books = books.filter(genre=genre)
    page = Paginator(books, 10).get_page(request.GET.get("page"))
    stats = {"books": Book.objects.count(), "authors": Author.objects.count(),
             "out": Book.objects.filter(available=False).count()}
    top = Author.objects.annotate(n=Count("books")).order_by("-n")[:3]
    return render(request, "core/book_list.html",
                  _ctx(page=page, q=q, genre=genre, genres=Book.GENRES, stats=stats, top=top))


def book_detail(request, pk):
    book = get_object_or_404(Book.objects.select_related("author"), pk=pk)
    return render(request, "core/book_detail.html", _ctx(book=book, borrow_form=BorrowForm()))


def book_edit(request, pk=None):
    book = get_object_or_404(Book, pk=pk) if pk else None
    form = BookForm(request.POST or None, instance=book)
    if request.method == "POST" and form.is_valid():
        book = form.save()
        messages.success(request, f"Saved '{book.title}'.")
        return redirect(book)
    return render(request, "core/book_form.html", _ctx(form=form, book=book))


@require_POST
def book_borrow(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if book.available:
        form = BorrowForm(request.POST)
        if form.is_valid():
            book.available, book.borrower = False, form.cleaned_data["borrower"]
            book.save()
            messages.success(request, f"'{book.title}' is lent to {book.borrower}.")
        else:
            messages.error(request, "Type the borrower's name.")
    else:
        messages.success(request, f"'{book.title}' was returned by {book.borrower}.")
        book.available, book.borrower = True, ""
        book.save()
    return redirect(book)


def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == "POST":
        book.delete()
        messages.success(request, f"Deleted '{book.title}'.")
        return redirect("core:book_list")
    return render(request, "core/book_confirm_delete.html", _ctx(book=book))


def api_books(request):
    data = [{"id": b.pk, "title": b.title, "author": b.author.name, "year": b.year, "available": b.available}
            for b in Book.objects.select_related("author")]
    return JsonResponse({"books": data})
