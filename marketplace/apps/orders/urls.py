from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout_view, name='checkout'),
    path('success/<uuid:pk>/', views.order_success_view, name='success'),
    path('', views.order_list_view, name='list'),
    path('<uuid:pk>/', views.order_detail_view, name='detail'),
    path('<uuid:pk>/cancel/', views.cancel_order_view, name='cancel'),
]