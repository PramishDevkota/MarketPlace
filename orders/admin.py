from django.contrib import admin
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['pk', 'buyer', 'seller', 'product', 'meetup_location', 'price_at_purchase', 'amount_paid', 'payment_type', 'is_paid', 'status', 'created_at']
    list_filter = ['status', 'payment_type', 'is_paid', 'meetup_location', 'created_at']
    search_fields = ['buyer__username', 'seller__username', 'product__name', 'transaction_id', 'meetup_time_notes']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
