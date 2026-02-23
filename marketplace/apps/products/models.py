from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.users.models import User
import uuid


class Category(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название')
    slug = models.SlugField(unique=True, max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='children', verbose_name='Родительская категория'
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_all_children(self):
        children = list(self.children.filter(is_active=True))
        result = children.copy()
        for child in children:
            result.extend(child.get_all_children())
        return result


class Brand(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to='brands/', null=True, blank=True)

    class Meta:
        verbose_name = 'Бренд'
        verbose_name_plural = 'Бренды'

    def __str__(self):
        return self.name


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=500, verbose_name='Название')
    slug = models.SlugField(unique=True, max_length=500)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name='products', verbose_name='Категория'
    )
    brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='products', verbose_name='Бренд'
    )
    description = models.TextField(verbose_name='Описание')
    short_description = models.CharField(max_length=500, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    old_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Старая цена'
    )
    stock = models.PositiveIntegerField(default=0, verbose_name='Остаток')
    sku = models.CharField(max_length=100, unique=True, verbose_name='Артикул')
    weight = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    is_featured = models.BooleanField(default=False, verbose_name='Рекомендуемый')
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Computed fields cached
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    reviews_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['price']),
            models.Index(fields=['avg_rating']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
            # Ensure unique slug
            base_slug = self.slug
            n = 1
            while Product.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{n}"
                n += 1
        super().save(*args, **kwargs)

    @property
    def discount_percent(self):
        if self.old_price and self.old_price > self.price:
            return int((1 - self.price / self.old_price) * 100)
        return 0

    @property
    def in_stock(self):
        return self.stock > 0

    def update_rating(self):
        reviews = self.reviews.filter(is_approved=True)
        count = reviews.count()
        if count > 0:
            total = sum(r.rating for r in reviews)
            self.avg_rating = round(total / count, 2)
        else:
            self.avg_rating = 0
        self.reviews_count = count
        self.save(update_fields=['avg_rating', 'reviews_count'])

    def get_main_image(self):
        img = self.images.filter(is_main=True).first()
        if not img:
            img = self.images.first()
        return img

    def get_attributes(self):
        return self.attributes.select_related('attribute')


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/%Y/%m/')
    alt = models.CharField(max_length=200, blank=True)
    is_main = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Фото {self.product.name}"


class Attribute(models.Model):
    name = models.CharField(max_length=200)
    unit = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = 'Характеристика'
        verbose_name_plural = 'Характеристики'

    def __str__(self):
        return self.name


class ProductAttribute(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='attributes')
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE)
    value = models.CharField(max_length=500)

    class Meta:
        unique_together = ('product', 'attribute')

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=300, blank=True)
    text = models.TextField()
    pros = models.TextField(blank=True, verbose_name='Достоинства')
    cons = models.TextField(blank=True, verbose_name='Недостатки')
    is_approved = models.BooleanField(default=True)
    helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        unique_together = ('product', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"Отзыв {self.user.email} на {self.product.name}"


class ProductView(models.Model):
    """Track product views for recommendations"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='view_history')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'viewed_at'])]


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')