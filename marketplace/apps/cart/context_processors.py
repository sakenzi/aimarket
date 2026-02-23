from .services import get_or_create_cart


def cart_count(request):
    try:
        cart = get_or_create_cart(request)
        return {'cart_count': cart.get_total_items()}
    except Exception:
        return {'cart_count': 0}