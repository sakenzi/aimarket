from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.cart_view, name='cart'),
    path('add/<uuid:product_id>/', views.add_to_cart_view, name='add'),
    path('remove/<int:item_id>/', views.remove_from_cart_view, name='remove'),
    path('update/<int:item_id>/', views.update_cart_view, name='update'),
]