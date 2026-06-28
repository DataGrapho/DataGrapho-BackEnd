from django.urls import path
from chatbot.controller import ChatController, SessionsController


app_name = 'chatbot'

urlpatterns = [
    path('chat/', ChatController.as_view(), name='chat'),
    path('sessions/', SessionsController.as_view({'get': 'list'}), name='sessions-list'),
    path('sessions/<uuid:pk>/', SessionsController.as_view({'get': 'retrieve', 'delete': 'destroy'}), name='sessions-detail'),
]
