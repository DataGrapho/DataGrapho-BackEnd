from django.urls import path
from chatbot.controller import ChatController


app_name = 'chatbot'

urlpatterns = [
    path('chat/', ChatController.as_view(), name='chat'),
]
