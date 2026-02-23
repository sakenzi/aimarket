from django.db import models
from apps.users.models import User


class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions', null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True)
    title = models.CharField(max_length=200, default='Новый чат')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Сессия чата'
        verbose_name_plural = 'Сессии чатов'

    def __str__(self):
        return f"{self.title} - {self.user or self.session_key}"

    def get_context(self, limit=10):
        """Get recent messages for context"""
        messages = self.messages.order_by('-created_at')[:limit]
        return list(reversed(messages))


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = 'user', 'Пользователь'
        ASSISTANT = 'assistant', 'Ассистент'
        SYSTEM = 'system', 'Система'

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional: linked products mentioned in response
    mentioned_products = models.ManyToManyField(
        'products.Product', blank=True, related_name='chat_mentions'
    )

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Сообщение чата'

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"