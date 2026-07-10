from django.shortcuts import render
from django.http import HttpResponse
from products.models import Category, Product


def home(request):
    products = Product.objects.all()

    
    return render(request, 'home/home.html', {'products': products})