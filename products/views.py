from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
# Create your views here.
from .models import Category, Product

def products(request):
    return render(request, 'products/products.html')


def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    return render(request, 'products/details.html', {'product': product})

