from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.order_list_view, name='order_list'),
    path('<int:pk>/', views.order_detail_view, name='order_detail'),
    path('<int:pk>/checkout/', views.order_checkout_view, name='checkout'),
    path('khalti/initiate/<int:order_id>/', views.initiate_khalti_payment, name='initiate_khalti_payment'),
    path('khalti/verify/', views.khalti_verify_payment, name='khalti_verify'),
]
