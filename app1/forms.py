from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'category',
            'name',
            'img',
            'price',
            'description',
            'quantity',
            'brand',
            'size',
            'color',
            'material'
        ]

from django import forms
from .models import Category

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['categoryname', 'img']
        widgets = {
            'categoryname': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Category Name'
            }),
            'img': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
        }

from django import forms
from .models import UserAddress

class UserAddressForm(forms.ModelForm):
    class Meta:
        model = UserAddress
        fields = ['label', 'street', 'city', 'state', 'country', 'pincode']
        widgets = {
            'label': forms.Select(attrs={'class': 'form-select'}),
            'street': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pincode'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        for field in ['street', 'city', 'state', 'country', 'pincode']:
            if not cleaned_data.get(field):
                self.add_error(field, f"{field.capitalize()} is required.")
        return cleaned_data
