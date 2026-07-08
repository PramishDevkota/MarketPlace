from django.contrib import admin

# Register your models here.

from .models import Category, Product






class CategoryAdmin(admin.ModelAdmin):   #override 
    list_display = ('id', 'name')

admin.site.register(Category, CategoryAdmin)


class ProductAdmin(admin.ModelAdmin):
    exclude = ('created_at',)
    list_display = ('id', 'product_name', 'category', 'price', 'stock', 'status')

admin.site.register(Product, ProductAdmin)