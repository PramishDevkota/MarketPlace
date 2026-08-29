from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.conversation_list_view, name='conversation_list'),
    path('requests/sent/', views.sent_requests_view, name='sent_requests'),
    path('requests/received/', views.received_requests_view, name='received_requests'),
    path('<int:pk>/', views.conversation_detail_view, name='conversation_detail'),
    path('start/<int:product_id>/', views.start_conversation_view, name='start_conversation'),
]
