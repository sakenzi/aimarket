from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from .models import ChatSession, ChatMessage
from .ollama_service import chat_with_ollama, is_ollama_available


def get_or_create_session(request):
    """Get or create chat session"""
    if request.user.is_authenticated:
        session = ChatSession.objects.filter(user=request.user, is_active=True).first()
        if not session:
            session = ChatSession.objects.create(user=request.user, title='Новый чат')
    else:
        if not request.session.session_key:
            request.session.create()
        session = ChatSession.objects.filter(
            session_key=request.session.session_key, user=None, is_active=True
        ).first()
        if not session:
            session = ChatSession.objects.create(session_key=request.session.session_key)
    return session


def chat_view(request):
    session = get_or_create_session(request)
    messages = session.get_context(limit=50)
    sessions = []
    if request.user.is_authenticated:
        sessions = ChatSession.objects.filter(user=request.user).order_by('-updated_at')[:10]

    context = {
        'session': session,
        'messages': messages,
        'sessions': sessions,
        'ollama_available': is_ollama_available(),
    }
    return render(request, 'ai_chat/chat.html', context)


@require_POST
def send_message(request):
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not user_message:
        return JsonResponse({'error': 'Empty message'}, status=400)

    if len(user_message) > 1000:
        return JsonResponse({'error': 'Message too long'}, status=400)

    # Get session
    if session_id and request.user.is_authenticated:
        session = get_object_or_404(ChatSession, pk=session_id, user=request.user)
    else:
        session = get_or_create_session(request)

    # Save user message
    ChatMessage.objects.create(session=session, role='user', content=user_message)

    # Get history
    history = list(session.messages.order_by('-created_at')[1:9])  # exclude just-added
    history.reverse()

    # Get AI response
    ai_response, mentioned_products = chat_with_ollama(history, user_message)

    # Save assistant message
    ai_msg = ChatMessage.objects.create(session=session, role='assistant', content=ai_response)
    if mentioned_products:
        ai_msg.mentioned_products.set(mentioned_products)

    # Update session title if first message
    if session.messages.count() == 2:
        session.title = user_message[:50]
        session.save()
    else:
        session.save(update_fields=['updated_at'])

    # Serialize mentioned products
    products_data = []
    for p in mentioned_products:
        img = p.get_main_image()
        products_data.append({
            'id': str(p.id),
            'name': p.name,
            'price': str(p.price),
            'slug': p.slug,
            'image': img.image.url if img else None,
            'rating': str(p.avg_rating),
        })

    return JsonResponse({
        'response': ai_response,
        'products': products_data,
        'session_id': str(session.id),
    })


def new_session(request):
    if request.user.is_authenticated:
        session = ChatSession.objects.create(user=request.user, title='Новый чат')
    else:
        if not request.session.session_key:
            request.session.create()
        session = ChatSession.objects.create(session_key=request.session.session_key)
    return JsonResponse({'session_id': str(session.id)})


def session_history(request, session_id):
    if request.user.is_authenticated:
        session = get_object_or_404(ChatSession, pk=session_id, user=request.user)
    else:
        session = get_object_or_404(ChatSession, pk=session_id, session_key=request.session.session_key)

    messages = session.messages.order_by('created_at').values('role', 'content', 'created_at')
    return JsonResponse({'messages': list(messages), 'title': session.title})