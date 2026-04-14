from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),

    # Orders
    path('orders/', views.orders_list, name='orders'),
    path('orders/<uuid:pk>/', views.order_detail, name='order_detail'),

    # Products
    path('products/', views.products_list, name='products'),
    path('products/<uuid:pk>/toggle/', views.product_toggle, name='product_toggle'),
    path('products/<uuid:pk>/stock/', views.product_update_stock, name='product_stock'),

    # Users
    path('users/', views.users_list, name='users'),
    path('users/<int:pk>/', views.user_detail, name='user_detail'),

    # Reviews
    path('reviews/', views.reviews_list, name='reviews'),
    path('reviews/<int:pk>/action/', views.review_action, name='review_action'),

    # AI Chats
    path('chats/', views.chats_list, name='chats'),
    path('chats/<int:pk>/', views.chat_detail, name='chat_detail'),
]