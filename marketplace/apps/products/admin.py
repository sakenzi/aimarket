from django.contrib import admin
from .models import Category, Brand, Product, ProductImage, Attribute, ProductAttribute, Review


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_active', 'order')
    list_filter = ('is_active', 'parent')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name',)
    prepopulated_fields = {'slug': ('name',)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3


class ProductAttributeInline(admin.TabularInline):
    model = ProductAttribute
    extra = 3


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock', 'avg_rating', 'is_active', 'is_featured')
    list_filter = ('is_active', 'is_featured', 'category')
    search_fields = ('name', 'sku')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_active', 'is_featured', 'stock', 'price')
    inlines = [ProductImageInline, ProductAttributeInline]
    readonly_fields = ('views_count', 'avg_rating', 'reviews_count', 'created_at', 'updated_at')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'is_approved', 'created_at')
    list_filter = ('rating', 'is_approved')
    list_editable = ('is_approved',)
    actions = ['approve_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
        for review in queryset:
            review.product.update_rating()
    approve_reviews.short_description = 'Одобрить выбранные отзывы'