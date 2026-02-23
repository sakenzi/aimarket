from django.urls import path
from . import views

app_name = 'ai_chat'

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('send/', views.send_message, name='send'),
    path('new-session/', views.new_session, name='new_session'),
    path('session/<int:session_id>/', views.session_history, name='session_history'),
]