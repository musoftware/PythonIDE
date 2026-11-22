from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import ProductForm
from .models import Product


def home(request):
    return render(request, "core/home.html")


def products(request):
    q = request.GET.get("q", "")
    rows = Product.objects.filter(name__icontains=q)
    return render(request, "core/products.html", {"products": rows, "q": q})


@login_required
def add(request):
    form = ProductForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect(reverse("core:products"))
    return render(request, "core/product_form.html", {"form": form, "title": "Add product"},
                  status=422 if form.errors else 200)


@login_required
def edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("core:products")
    return render(request, "core/product_form.html", {"form": form, "title": "Edit product", "product": product},
                  status=422 if form.errors else 200)


@login_required
@require_POST
def delete(request, pk):
    get_object_or_404(Product, pk=pk).delete()
    return redirect("core:products")


def arabic(request):
    return render(request, "core/ar.html", {"count": Product.objects.count()})


def api_products(request):
    data = [{"id": p.id, "name": p.name, "price": float(p.price)} for p in Product.objects.all()]
    return JsonResponse(data, safe=False, json_dumps_params={"ensure_ascii": False})
