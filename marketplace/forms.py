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
    size = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., S, M, L, XL'}),
    )
    color = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Black, Blue, Red'}),
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
    is_on_sale = forms.BooleanField(
        required=False,
        label='Put this product on sale',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    sale_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Sale price in Rs.',
            'min': '0',
            'step': '0.01',
        }),
        help_text='Discounted price. Must be lower than the original price.',
    )

    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'size', 'color', 'category', 'location', 'programme', 'module_code', 'image', 'is_on_sale', 'sale_price']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Category
        self.fields['category'].queryset = Category.objects.filter(is_active=True)

    def clean(self):
        cleaned = super().clean()
        price = cleaned.get('price')
        is_on_sale = cleaned.get('is_on_sale')
        sale_price = cleaned.get('sale_price')

        if is_on_sale:
            if sale_price is None:
                self.add_error('sale_price', 'Enter a sale price when the product is on sale.')
            elif sale_price <= 0:
                self.add_error('sale_price', 'Sale price must be greater than 0.')
            elif price is not None and sale_price >= price:
                self.add_error('sale_price', 'Sale price must be lower than the original price.')
        else:
            cleaned['sale_price'] = None
        return cleaned
