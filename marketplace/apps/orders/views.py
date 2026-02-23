from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import Order, OrderItem, OrderStatusHistory
from .forms import CheckoutForm
from apps.cart.services import get_or_create_cart


@login_required
def checkout_view(request):
    cart = get_or_create_cart(request)
    items = cart.items.select_related('product').prefetch_related('product__images')

    if not items.exists():
        messages.warning(request, 'Ваша корзина пуста.')
        return redirect('cart:cart')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                subtotal = cart.get_total_price()
                delivery = 0 if subtotal >= 1000 else 299
                total = subtotal + delivery

                order = Order.objects.create(
                    user=request.user,
                    full_name=form.cleaned_data['full_name'],
                    email=form.cleaned_data['email'],
                    phone=form.cleaned_data['phone'],
                    address=form.cleaned_data['address'],
                    city=form.cleaned_data['city'],
                    postal_code=form.cleaned_data['postal_code'],
                    comment=form.cleaned_data.get('comment', ''),
                    subtotal=subtotal,
                    delivery_cost=delivery,
                    total=total,
                )

                for item in items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        product_name=item.product.name,
                        product_sku=item.product.sku,
                        price=item.product.price,
                        quantity=item.quantity,
                    )
                    # Reduce stock
                    item.product.__class__.objects.filter(pk=item.product.pk).update(
                        stock=item.product.stock - item.quantity
                    )

                OrderStatusHistory.objects.create(
                    order=order, status=order.status, created_by=request.user
                )

                # Clear cart
                cart.items.all().delete()

            messages.success(request, f'Заказ #{order.order_number} успешно оформлен!')
            return redirect('orders:success', pk=order.pk)
    else:
        initial = {
            'full_name': request.user.get_full_name(),
            'email': request.user.email,
            'phone': request.user.phone,
            'address': request.user.address,
            'city': request.user.city,
        }
        form = CheckoutForm(initial=initial)

    subtotal = cart.get_total_price()
    delivery = 0 if subtotal >= 1000 else 299

    return render(request, 'orders/checkout.html', {
        'form': form,
        'items': items,
        'subtotal': subtotal,
        'delivery': delivery,
        'total': subtotal + delivery,
    })


@login_required
def order_success_view(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, 'orders/success.html', {'order': order})


@login_required
def order_list_view(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'orders/list.html', {'orders': orders})


@login_required
def order_detail_view(request, pk):
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product', 'history'),
        pk=pk, user=request.user
    )
    return render(request, 'orders/detail.html', {'order': order})


@login_required
def cancel_order_view(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if order.status in (Order.Status.PENDING, Order.Status.PAID):
        order.status = Order.Status.CANCELLED
        order.save()
        OrderStatusHistory.objects.create(
            order=order, status=Order.Status.CANCELLED,
            comment='Отменён пользователем', created_by=request.user
        )
        # Restore stock
        for item in order.items.all():
            item.product.__class__.objects.filter(pk=item.product.pk).update(
                stock=item.product.stock + item.quantity
            )
        messages.success(request, 'Заказ отменён.')
    else:
        messages.error(request, 'Невозможно отменить этот заказ.')
    return redirect('orders:detail', pk=pk)