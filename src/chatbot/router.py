from django.urls import path
from chatbot.controller import ChatController, SessionsController


app_name = 'chatbot'

urlpatterns = [
    path('health/', ChatController.health_check, name='health-check'),
    path('chat/', ChatController.as_view(), name='chat'),
    path('sessions/', SessionsController.as_view({'get': 'list', 'post': 'create'}), name='sessions-list'),
    path('sessions/<uuid:pk>/', SessionsController.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}), name='sessions-detail'),
]
