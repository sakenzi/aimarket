from .models import Cart, CartItem
from apps.products.models import Product


def get_or_create_cart(request):
    """Get or create cart for current user/session"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        # Merge session cart if exists
        if created and request.session.session_key:
            session_cart = Cart.objects.filter(
                session_key=request.session.session_key, user=None
            ).first()
            if session_cart:
                for item in session_cart.items.all():
                    cart_item, _ = CartItem.objects.get_or_create(
                        cart=cart, product=item.product,
                        defaults={'quantity': 0}
                    )
                    cart_item.quantity += item.quantity
                    cart_item.save()
                session_cart.delete()
    else:
        if not request.session.session_key:
            request.session.create()
        cart, _ = Cart.objects.get_or_create(
            session_key=request.session.session_key, user=None
        )
    return cart


def add_to_cart(request, product_id, quantity=1):
    """Add product to cart, return (cart_item, created)"""
    product = Product.objects.get(pk=product_id, is_active=True)
    cart = get_or_create_cart(request)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, defaults={'quantity': 0}
    )
    cart_item.quantity += quantity
    if cart_item.quantity > product.stock:
        cart_item.quantity = product.stock
    cart_item.save()
    return cart_item, created


def remove_from_cart(request, item_id):
    cart = get_or_create_cart(request)
    CartItem.objects.filter(cart=cart, pk=item_id).delete()


def update_cart_item(request, item_id, quantity):
    cart = get_or_create_cart(request)
    try:
        item = CartItem.objects.get(cart=cart, pk=item_id)
        if quantity <= 0:
            item.delete()
        else:
            item.quantity = min(quantity, item.product.stock)
            item.save()
        return item
    except CartItem.DoesNotExist:
        return None