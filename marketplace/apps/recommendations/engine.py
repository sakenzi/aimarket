"""
Recommendation Engine
- Content-based filtering: based on product attributes/categories
- Collaborative filtering: based on what similar users bought/viewed
"""
import logging
from django.db.models import Count, Q
from django.core.cache import cache

logger = logging.getLogger(__name__)


def get_recommendations(user=None, limit=8, exclude_id=None):
    """
    Main recommendation function combining multiple strategies.
    Returns queryset of recommended products.
    """
    from apps.products.models import Product, ProductView
    from apps.orders.models import OrderItem

    cache_key = f"recs_{'u'+str(user.id) if user else 'anon'}_{exclude_id or 'none'}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if user and user.is_authenticated:
        # Try collaborative filtering first
        recs = _collaborative_recommendations(user, limit, exclude_id)
        if not recs or len(recs) < limit // 2:
            # Fall back to content-based
            content_recs = _content_based_recommendations(user, limit, exclude_id)
            seen_ids = {p.id for p in recs}
            for p in content_recs:
                if p.id not in seen_ids:
                    recs.append(p)
                if len(recs) >= limit:
                    break
    else:
        recs = _popularity_recommendations(limit, exclude_id)

    cache.set(cache_key, recs, timeout=300)
    return recs[:limit]


def _collaborative_recommendations(user, limit, exclude_id=None):
    """
    Collaborative filtering: find users with similar purchase history
    and recommend what they bought.
    """
    from apps.products.models import Product
    from apps.orders.models import Order, OrderItem

    # Get products current user has bought
    user_product_ids = set(
        OrderItem.objects.filter(order__user=user)
        .values_list('product_id', flat=True)
    )

    if not user_product_ids:
        return []

    # Find similar users (bought same products)
    similar_users = (
        Order.objects.filter(items__product_id__in=user_product_ids)
        .exclude(user=user)
        .values('user_id')
        .annotate(common_products=Count('items__product_id', distinct=True))
        .order_by('-common_products')[:20]
    )

    similar_user_ids = [u['user_id'] for u in similar_users]
    if not similar_user_ids:
        return []

    # Get products bought by similar users but not by current user
    qs = Product.objects.filter(
        orders__order__user_id__in=similar_user_ids,
        is_active=True, stock__gt=0,
    ).exclude(
        id__in=user_product_ids
    )
    if exclude_id:
        qs = qs.exclude(id=exclude_id)

    recommended = (
        qs.annotate(freq=Count('orders'))
        .order_by('-freq', '-avg_rating')
        .prefetch_related('images')
        .distinct()[:limit]
    )
    return list(recommended)


def _content_based_recommendations(user, limit, exclude_id=None):
    """
    Content-based filtering: recommend based on categories user viewed/bought.
    """
    from apps.products.models import Product, ProductView
    from apps.orders.models import OrderItem

    # Get categories user interacted with
    viewed_cat_ids = (
        ProductView.objects.filter(user=user)
        .values_list('product__category_id', flat=True)
        .distinct()
    )
    bought_cat_ids = (
        OrderItem.objects.filter(order__user=user)
        .values_list('product__category_id', flat=True)
        .distinct()
    )

    all_cat_ids = list(set(list(viewed_cat_ids) + list(bought_cat_ids)))

    if not all_cat_ids:
        return _popularity_recommendations(limit, exclude_id)

    # Get viewed/bought product ids to exclude
    viewed_ids = ProductView.objects.filter(user=user).values_list('product_id', flat=True)
    bought_ids = OrderItem.objects.filter(order__user=user).values_list('product_id', flat=True)
    exclude_ids = set(list(viewed_ids) + list(bought_ids))
    if exclude_id:
        exclude_ids.add(exclude_id)

    qs = Product.objects.filter(
        category_id__in=all_cat_ids,
        is_active=True, stock__gt=0,
    ).exclude(id__in=exclude_ids).order_by('-avg_rating', '-reviews_count')

    return list(qs.prefetch_related('images')[:limit])


def _popularity_recommendations(limit, exclude_id=None):
    """Fallback: recommend popular products"""
    from apps.products.models import Product

    qs = Product.objects.filter(is_active=True, stock__gt=0)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return list(
        qs.order_by('-views_count', '-avg_rating', '-reviews_count')
        .prefetch_related('images')[:limit]
    )


def get_similar_products(product, limit=6):
    """Get products similar to given product (content-based)"""
    from apps.products.models import Product

    cache_key = f"similar_{product.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Products in same category, ordered by rating
    same_category = Product.objects.filter(
        category=product.category,
        is_active=True,
    ).exclude(id=product.id).order_by('-avg_rating', '-reviews_count').prefetch_related('images')[:limit]

    result = list(same_category)
    cache.set(cache_key, result, timeout=600)
    return result