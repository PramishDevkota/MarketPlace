from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, SellerRequest


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_buyer', 'is_seller', 'is_staff', 'is_active']
    list_filter = ['is_buyer', 'is_seller', 'is_staff', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Marketplace', {'fields': ('is_buyer', 'is_seller', 'phone_number', 'profile_image')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Marketplace', {'fields': ('is_buyer', 'is_seller', 'phone_number')}),
    )


@admin.register(SellerRequest)
class SellerRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'business_name', 'status', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'business_name', 'description']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']

    def approve_request(self, request, queryset):
        for seller_request in queryset.filter(status='PENDING'):
            seller_request.approve()
        self.message_user(request, 'Selected seller requests have been approved.')
    approve_request.short_description = 'Approve selected seller requests'

    def reject_request(self, request, queryset):
        for seller_request in queryset.filter(status='PENDING'):
            seller_request.reject()
        self.message_user(request, 'Selected seller requests have been rejected.')
    reject_request.short_description = 'Reject selected seller requests'

    actions = [approve_request, reject_request]
