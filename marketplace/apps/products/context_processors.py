from .models import Category


def categories_ctx(request):
    categories = Category.objects.filter(is_active=True, parent=None).prefetch_related('children')
    return {'nav_categories': categories}