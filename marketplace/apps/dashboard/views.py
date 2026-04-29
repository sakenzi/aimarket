from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
import json

from apps.orders.models import Order, OrderStatusHistory
from apps.products.models import Product, Category, Review, ProductImage
from apps.users.models import User
from apps.ai_chat.models import ChatSession
from .forms import DashboardProductForm


# ── Helpers ───────────────────────────────────────────────────────────────────

def staff_required(view_func):
    return staff_member_required(view_func, login_url='/users/login/')


# ── Dashboard home ─────────────────────────────────────────────────────────────

@staff_required
def dashboard_home(request):
    now = timezone.now()
    today = now.date()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    # Key metrics
    stats = {
        'orders_today': Order.objects.filter(created_at__date=today).count(),
        'orders_month': Order.objects.filter(created_at__gte=month_start).count(),
        'revenue_today': Order.objects.filter(
            created_at__date=today
        ).exclude(status='cancelled').aggregate(s=Sum('total'))['s'] or 0,
        'revenue_month': Order.objects.filter(
            created_at__gte=month_start
        ).exclude(status='cancelled').aggregate(s=Sum('total'))['s'] or 0,
        'new_users_month': User.objects.filter(created_at__gte=month_start).count(),
        'total_users': User.objects.count(),
        'total_products': Product.objects.filter(is_active=True).count(),
        'low_stock': Product.objects.filter(is_active=True, stock__lte=5).count(),
        'pending_reviews': Review.objects.filter(is_approved=False).count(),
        'pending_orders': Order.objects.filter(status='pending').count(),
    }

    # Revenue chart — last 14 days
    revenue_data = (
        Order.objects
        .filter(created_at__gte=now - timedelta(days=14))
        .exclude(status='cancelled')
        .annotate(day=TruncDay('created_at'))
        .values('day')
        .annotate(total=Sum('total'), count=Count('id'))
        .order_by('day')
    )
    chart_labels = []
    chart_revenue = []
    chart_orders = []
    for row in revenue_data:
        chart_labels.append(row['day'].strftime('%d.%m'))
        chart_revenue.append(float(row['total']))
        chart_orders.append(row['count'])

    # Orders by status
    status_counts = {
        s: Order.objects.filter(status=s).count()
        for s, _ in Order.Status.choices
    }

    # Recent orders
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:8]

    # Top products by revenue
    top_products = (
        Product.objects
        .filter(is_active=True)
        .annotate(revenue=Sum('orderitem__price'))
        .order_by('-revenue')[:5]
    )

    context = {
        'stats': stats,
        'chart_labels': json.dumps(chart_labels),
        'chart_revenue': json.dumps(chart_revenue),
        'chart_orders': json.dumps(chart_orders),
        'status_counts': status_counts,
        'recent_orders': recent_orders,
        'top_products': top_products,
        'section': 'home',
    }
    return render(request, 'dashboard/home.html', context)


# ── Orders ─────────────────────────────────────────────────────────────────────

@staff_required
def orders_list(request):
    qs = Order.objects.select_related('user').prefetch_related('items').order_by('-created_at')

    # Filters
    status = request.GET.get('status')
    search = request.GET.get('q', '').strip()
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(
            Q(order_number__icontains=search) |
            Q(full_name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(phone__icontains=search)
        )
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    from django.core.paginator import Paginator
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'status_choices': Order.Status.choices,
        'current_status': status,
        'search': search,
        'total': qs.count(),
        'section': 'orders',
    }
    return render(request, 'dashboard/orders.html', context)


@staff_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related('items__product', 'history__created_by'), pk=pk)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        comment = request.POST.get('comment', '')
        if new_status and new_status != order.status:
            old_status = order.get_status_display()
            order.status = new_status
            order.save()
            OrderStatusHistory.objects.create(
                order=order,
                status=new_status,
                comment=comment or f'Статус изменён администратором с "{old_status}"',
                created_by=request.user,
            )
            messages.success(request, f'Статус заказа обновлён: {order.get_status_display()}')
            return redirect('dashboard:order_detail', pk=pk)

    context = {
        'order': order,
        'status_choices': Order.Status.choices,
        'section': 'orders',
    }
    return render(request, 'dashboard/order_detail.html', context)


# ── Products ───────────────────────────────────────────────────────────────────

@staff_required
def products_list(request):
    qs = Product.objects.select_related('category', 'brand').prefetch_related('images').order_by('-created_at')

    search = request.GET.get('q', '').strip()
    category_id = request.GET.get('category')
    stock_filter = request.GET.get('stock')

    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(sku__icontains=search))
    if category_id:
        qs = qs.filter(category_id=category_id)
    if stock_filter == 'low':
        qs = qs.filter(stock__lte=5)
    elif stock_filter == 'out':
        qs = qs.filter(stock=0)

    from django.core.paginator import Paginator
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    categories = Category.objects.filter(is_active=True, parent=None)

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'search': search,
        'section': 'products',
    }
    return render(request, 'dashboard/products.html', context)


@staff_required
def product_create(request):
    if request.method == 'POST':
        form = DashboardProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            image = form.cleaned_data.get('main_image')
            if image:
                ProductImage.objects.create(
                    product=product,
                    image=image,
                    alt=product.name,
                    is_main=True,
                )
            messages.success(request, 'Product created.')
            return redirect('dashboard:products')
    else:
        form = DashboardProductForm()

    context = {
        'form': form,
        'section': 'products',
    }
    return render(request, 'dashboard/product_form.html', context)


@staff_required
def product_toggle(request, pk):
    """Toggle product active status via AJAX"""
    product = get_object_or_404(Product, pk=pk)
    product.is_active = not product.is_active
    product.save(update_fields=['is_active'])
    return JsonResponse({'is_active': product.is_active})


@staff_required
def product_update_stock(request, pk):
    """Quick stock update via AJAX"""
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=pk)
        try:
            stock = int(request.POST.get('stock', 0))
            product.stock = max(0, stock)
            product.save(update_fields=['stock'])
            return JsonResponse({'success': True, 'stock': product.stock})
        except (ValueError, TypeError):
            return JsonResponse({'success': False}, status=400)
    return JsonResponse({'success': False}, status=405)


# ── Users ──────────────────────────────────────────────────────────────────────

@staff_required
def users_list(request):
    qs = User.objects.annotate(
        orders_count=Count('orders'),
        total_spent=Sum('orders__total'),
    ).order_by('-created_at')

    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )

    from django.core.paginator import Paginator
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'search': search,
        'section': 'users',
    }
    return render(request, 'dashboard/users.html', context)


@staff_required
def user_detail(request, pk):
    user = get_object_or_404(User, pk=pk)
    orders = Order.objects.filter(user=user).order_by('-created_at')
    reviews = Review.objects.filter(user=user).select_related('product').order_by('-created_at')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'toggle_active':
            user.is_active = not user.is_active
            user.save(update_fields=['is_active'])
            status = 'активирован' if user.is_active else 'заблокирован'
            messages.success(request, f'Пользователь {status}.')
            return redirect('dashboard:user_detail', pk=pk)

    context = {
        'profile_user': user,
        'orders': orders[:10],
        'reviews': reviews[:10],
        'total_spent': orders.exclude(status='cancelled').aggregate(s=Sum('total'))['s'] or 0,
        'section': 'users',
    }
    return render(request, 'dashboard/user_detail.html', context)


# ── Reviews ────────────────────────────────────────────────────────────────────

@staff_required
def reviews_list(request):
    qs = Review.objects.select_related('user', 'product').order_by('-created_at')

    approved = request.GET.get('approved')
    if approved == '0':
        qs = qs.filter(is_approved=False)
    elif approved == '1':
        qs = qs.filter(is_approved=True)

    from django.core.paginator import Paginator
    paginator = Paginator(qs, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'pending_count': Review.objects.filter(is_approved=False).count(),
        'section': 'reviews',
    }
    return render(request, 'dashboard/reviews.html', context)


@staff_required
def review_action(request, pk):
    """Approve or delete review via AJAX POST"""
    review = get_object_or_404(Review, pk=pk)
    action = request.POST.get('action')

    if action == 'approve':
        review.is_approved = True
        review.save()
        review.product.update_rating()
        return JsonResponse({'success': True, 'action': 'approved'})
    elif action == 'reject':
        review.is_approved = False
        review.save()
        review.product.update_rating()
        return JsonResponse({'success': True, 'action': 'rejected'})
    elif action == 'delete':
        product = review.product
        review.delete()
        product.update_rating()
        return JsonResponse({'success': True, 'action': 'deleted'})

    return JsonResponse({'success': False}, status=400)


# ── AI Chats ───────────────────────────────────────────────────────────────────

@staff_required
def chats_list(request):
    qs = ChatSession.objects.select_related('user').annotate(
        msg_count=Count('messages')
    ).order_by('-updated_at')

    from django.core.paginator import Paginator
    paginator = Paginator(qs, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'section': 'chats',
    }
    return render(request, 'dashboard/chats.html', context)


@staff_required
def chat_detail(request, pk):
    session = get_object_or_404(ChatSession.objects.select_related('user'), pk=pk)
    messages_qs = session.messages.order_by('created_at')
    context = {
        'session': session,
        'chat_messages': messages_qs,
        'section': 'chats',
    }
    return render(request, 'dashboard/chat_detail.html', context)
