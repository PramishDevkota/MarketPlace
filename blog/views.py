from django.shortcuts import render

# Create your views here.

from django.http import HttpResponse



def blog(request):
    return HttpResponse("Hi! This is blog page")
