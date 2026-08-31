from django.contrib import admin
from .models import Category, Product, ProductImage, Cart, CartItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['name']


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]
    list_display = ['name', 'seller', 'category', 'price', 'location', 'programme', 'module_code', 'status', 'is_available', 'created_at']
    list_filter = ['status', 'is_available', 'category', 'location', 'programme', 'created_at']
    search_fields = ['name', 'description', 'seller__username', 'module_code', 'programme']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']

    def has_add_permission(self, request):
        return False

    def approve_products(self, request, queryset):
        queryset.filter(status='PENDING').update(status='APPROVED')
        self.message_user(request, 'Selected products have been approved.')
    approve_products.short_description = 'Approve selected products'

    def reject_products(self, request, queryset):
        queryset.filter(status='PENDING').update(status='REJECTED')
        self.message_user(request, 'Selected products have been rejected.')
    reject_products.short_description = 'Reject selected products'

    actions = [approve_products, reject_products]


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'session_key', 'total_items', 'total_price', 'created_at', 'updated_at']
    search_fields = ['user__username', 'session_key']
    inlines = [CartItemInline]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'subtotal', 'added_at']
    search_fields = ['product__name', 'cart__user__username']
