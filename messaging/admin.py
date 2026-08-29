from django.contrib import admin
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ['sender', 'content', 'is_read', 'created_at']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['pk', 'buyer', 'seller', 'product', 'created_at', 'updated_at']
    list_filter = ['created_at']
    search_fields = ['buyer__username', 'seller__username', 'product__name']
    ordering = ['-updated_at']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['pk', 'conversation', 'sender', 'content', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['sender__username', 'content']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
