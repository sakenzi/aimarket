from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from .models import Product, Category, Review, ProductView, Wishlist
from .forms import ReviewForm, ProductFilterForm
from apps.recommendations.engine import get_recommendations


def home_view(request):
    featured = Product.objects.filter(is_active=True, is_featured=True).prefetch_related('images')[:8]
    new_arrivals = Product.objects.filter(is_active=True).order_by('-created_at').prefetch_related('images')[:8]
    top_categories = Category.objects.filter(is_active=True, parent=None).prefetch_related('children')[:8]

    # Personalized recommendations
    recommendations = []
    if request.user.is_authenticated:
        recommendations = get_recommendations(request.user, limit=8)

    context = {
        'featured': featured,
        'new_arrivals': new_arrivals,
        'top_categories': top_categories,
        'recommendations': recommendations,
    }
    return render(request, 'products/home.html', context)


def catalog_view(request):
    queryset = Product.objects.filter(is_active=True).prefetch_related('images').select_related('category', 'brand')

    # Category filter
    category_slug = request.GET.get('category')
    category = None
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug, is_active=True)
        # Include all subcategories
        all_cat_ids = [category.id] + [c.id for c in category.get_all_children()]
        queryset = queryset.filter(category_id__in=all_cat_ids)

    # Search
    search_query = request.GET.get('q', '').strip()
    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(brand__name__icontains=search_query)
        )

    # Price filter
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    if price_min:
        queryset = queryset.filter(price__gte=price_min)
    if price_max:
        queryset = queryset.filter(price__lte=price_max)

    # Rating filter
    min_rating = request.GET.get('rating')
    if min_rating:
        queryset = queryset.filter(avg_rating__gte=min_rating)

    # In stock filter
    if request.GET.get('in_stock'):
        queryset = queryset.filter(stock__gt=0)

    # Sorting
    sort = request.GET.get('sort', '-created_at')
    sort_options = {
        'price_asc': 'price',
        'price_desc': '-price',
        'rating': '-avg_rating',
        'popular': '-views_count',
        'new': '-created_at',
        'reviews': '-reviews_count',
    }
    sort_field = sort_options.get(sort, '-created_at')
    queryset = queryset.order_by(sort_field)

    # Pagination
    paginator = Paginator(queryset, settings.PRODUCTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'category': category,
        'search_query': search_query,
        'sort': sort,
        'total_count': paginator.count,
        'filter_params': request.GET.urlencode(),
    }
    return render(request, 'products/catalog.html', context)


def product_detail_view(request, slug):
    product = get_object_or_404(
        Product.objects.prefetch_related('images', 'attributes__attribute', 'reviews__user'),
        slug=slug, is_active=True
    )

    # Track view
    if request.user.is_authenticated:
        ProductView.objects.get_or_create(
            product=product, user=request.user,
            defaults={'session_key': request.session.session_key or ''}
        )
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        ProductView.objects.get_or_create(
            product=product, session_key=session_key, user=None
        )

    # Increment view count
    Product.objects.filter(pk=product.pk).update(views_count=product.views_count + 1)

    # Reviews
    reviews = product.reviews.filter(is_approved=True).select_related('user')
    user_review = None
    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()

    # Review form
    review_form = ReviewForm()
    if request.method == 'POST' and request.user.is_authenticated:
        if not user_review:
            review_form = ReviewForm(request.POST)
            if review_form.is_valid():
                review = review_form.save(commit=False)
                review.product = product
                review.user = request.user
                review.save()
                product.update_rating()
                messages.success(request, 'Отзыв добавлен!')
                return redirect('products:detail', slug=slug)

    # Wishlist status
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()

    # Similar products
    similar = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(pk=product.pk).prefetch_related('images')[:6]

    # Recommendations
    recommendations = get_recommendations(request.user if request.user.is_authenticated else None, limit=6, exclude_id=product.pk)

    # Rating distribution
    rating_dist = {}
    for i in range(1, 6):
        rating_dist[i] = reviews.filter(rating=i).count()

    context = {
        'product': product,
        'reviews': reviews,
        'user_review': user_review,
        'review_form': review_form,
        'similar': similar,
        'recommendations': recommendations,
        'in_wishlist': in_wishlist,
        'rating_dist': rating_dist,
    }
    return render(request, 'products/detail.html', context)


@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if not created:
        wishlist_item.delete()
        added = False
    else:
        added = True
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'added': added})
    return redirect(request.META.get('HTTP_REFERER', 'products:home'))


@login_required
def wishlist_view(request):
    wishlist = Wishlist.objects.filter(user=request.user).select_related('product').prefetch_related('product__images')
    return render(request, 'products/wishlist.html', {'wishlist': wishlist})


def search_suggestions(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'suggestions': []})
    products = Product.objects.filter(
        name__icontains=q, is_active=True
    ).values('name', 'slug')[:10]
    return JsonResponse({'suggestions': list(products)})