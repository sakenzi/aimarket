from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .services import get_or_create_cart, add_to_cart, remove_from_cart, update_cart_item
from .models import CartItem


def cart_view(request):
    cart = get_or_create_cart(request)
    items = cart.items.select_related('product').prefetch_related('product__images')
    return render(request, 'cart/cart.html', {
        'cart': cart,
        'items': items,
    })


@require_POST
def add_to_cart_view(request, product_id):
    quantity = int(request.POST.get('quantity', 1))
    try:
        cart_item, created = add_to_cart(request, product_id, quantity)
        cart = cart_item.cart
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_count': cart.get_total_items(),
                'message': 'Товар добавлен в корзину',
            })
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

    return redirect('cart:cart')


@require_POST
def remove_from_cart_view(request, item_id):
    remove_from_cart(request, item_id)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        cart = get_or_create_cart(request)
        return JsonResponse({
            'success': True,
            'cart_count': cart.get_total_items(),
            'total': str(cart.get_total_price()),
        })
    return redirect('cart:cart')


@require_POST
def update_cart_view(request, item_id):
    quantity = int(request.POST.get('quantity', 1))
    item = update_cart_item(request, item_id, quantity)
    cart = get_or_create_cart(request)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'item_total': str(item.get_total_price()) if item else '0',
            'cart_total': str(cart.get_total_price()),
            'cart_count': cart.get_total_items(),
        })
    return redirect('cart:cart')