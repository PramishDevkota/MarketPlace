from django.urls import path
from . import views

app_name = 'marketplace'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('marketplace/', views.product_list_view, name='product_list'),
    path('marketplace/overview/', views.marketplace_overview, name='overview'),
    path('marketplace/ai-finder/', views.ai_product_finder_view, name='ai_finder'),
    path('marketplace/product/<int:pk>/', views.product_detail_view, name='product_detail'),
    path('marketplace/product/add/', views.create_product_view, name='create_product'),
    path('marketplace/product/<int:pk>/edit/', views.edit_product_view, name='edit_product'),
    path('marketplace/product/<int:pk>/delete/', views.delete_product_view, name='delete_product'),
    path('marketplace/product/<int:pk>/restock/', views.restock_product_view, name='restock_product'),
    path('marketplace/product/<int:pk>/buy/', views.buy_now_view, name='buy_now'),
    path('marketplace/product/<int:product_id>/add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/item/<int:item_id>/update/', views.update_cart_item_view, name='update_cart_item'),
    path('cart/item/<int:item_id>/remove/', views.remove_cart_item_view, name='remove_cart_item'),
    path('seller/dashboard/', views.seller_dashboard_view, name='seller_dashboard'),
    path('dashboard/', views.buyer_dashboard_view, name='buyer_dashboard'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
]
