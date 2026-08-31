from django import forms
from django.forms import inlineformset_factory
from .models import Product, ProductImage


ProductImageFormSet = inlineformset_factory(
    Product,
    ProductImage,
    fields=('image',),
    extra=3,
)


class ProductForm(forms.ModelForm):
    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product name'}),
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe your product...'}),
    )
    price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Price in Rs.', 'min': '0', 'step': '0.01'}),
    )
    category = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Select a category',
    )
    location = forms.ChoiceField(
        choices=Product.LOCATION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    programme = forms.ChoiceField(
        choices=Product.PROGRAMME_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
    )
    module_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., CS4001, CS5002, CU4055',
        }),
        help_text="e.g., CS4001, CS5002, CU4055",
    )
    image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'category', 'location', 'programme', 'module_code', 'image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Category
        self.fields['category'].queryset = Category.objects.filter(is_active=True)
