from django import forms

from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "price"]

    def clean_price(self):
        price = self.cleaned_data["price"]
        if price is not None and price < 0:
            raise forms.ValidationError("Price must be a positive number")
        return price
