import httpx
import json
import logging
from django.conf import settings
from apps.products.models import Product, Category

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = getattr(settings, 'OLLAMA_MODEL', 'llama3.2')

SYSTEM_PROMPT = """Ты — дружелюбный AI-помощник маркетплейса. Твоя задача — помогать покупателям найти нужные товары, отвечать на вопросы об ассортименте, ценах и категориях.

Правила:
1. Отвечай на русском языке
2. Будь кратким и конкретным
3. Если пользователь ищет товар — предложи конкретные варианты из нашего каталога
4. Указывай примерные цены и характеристики
5. Если чего-то нет в каталоге — честно скажи об этом
6. Помогай с навигацией по сайту

Ты имеешь доступ к информации о товарах магазина и можешь помочь найти нужные позиции."""


def get_catalog_context():
    """Get brief catalog context for AI"""
    categories = Category.objects.filter(is_active=True, parent=None).values_list('name', flat=True)[:20]
    top_products = Product.objects.filter(is_active=True, stock__gt=0).order_by('-avg_rating')[:10]

    context = f"Доступные категории: {', '.join(categories)}\n\n"
    context += "Популярные товары:\n"
    for p in top_products:
        context += f"- {p.name} | Цена: {p.price}₽ | Рейтинг: {p.avg_rating}\n"
    return context


def search_products_for_context(query: str, limit: int = 5) -> list:
    """Search products relevant to query"""
    from django.db.models import Q
    products = Product.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query) | Q(category__name__icontains=query),
        is_active=True
    ).order_by('-avg_rating')[:limit]
    return list(products)


def chat_with_ollama(messages: list, user_message: str, search_products: bool = True) -> tuple[str, list]:
    """
    Send message to Ollama and get response.
    Returns (response_text, mentioned_products)
    """
    # Search for relevant products
    relevant_products = []
    product_context = ""
    if search_products:
        relevant_products = search_products_for_context(user_message)
        if relevant_products:
            product_context = "\n\nРелевантные товары из каталога:\n"
            for p in relevant_products:
                product_context += (
                    f"- {p.name} | Цена: {p.price}₽ | "
                    f"Рейтинг: {p.avg_rating}/5 | "
                    f"{'В наличии' if p.in_stock else 'Нет в наличии'}\n"
                )

    # Build messages for Ollama
    ollama_messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + get_catalog_context() + product_context}
    ]

    # Add conversation history
    for msg in messages[-8:]:  # Last 8 messages for context
        ollama_messages.append({
            "role": msg.role,
            "content": msg.content,
        })

    # Add current message
    ollama_messages.append({"role": "user", "content": user_message})

    try:
        response = httpx.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": ollama_messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 512,
                }
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        reply = data.get('message', {}).get('content', 'Извините, не могу ответить прямо сейчас.')
        return reply, relevant_products
    except httpx.ConnectError:
        logger.error("Cannot connect to Ollama. Is it running?")
        return (
            "Извините, AI-ассистент временно недоступен. "
            "Попробуйте воспользоваться поиском по каталогу или обратитесь в поддержку.",
            []
        )
    except Exception as e:
        logger.exception(f"Ollama error: {e}")
        return f"Произошла ошибка: {str(e)[:100]}", []


def is_ollama_available() -> bool:
    """Check if Ollama is available"""
    try:
        response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3.0)
        return response.status_code == 200
    except Exception:
        return False