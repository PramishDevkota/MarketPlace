from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('create/<int:product_id>/', views.create_review_view, name='create_review'),
    path('order/<int:order_id>/', views.add_review, name='add_review'),
]
