"""
Chat URLs for AI Teaching Assistant
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .chat_views import ChatViewSet

router = DefaultRouter()
router.register(r'conversations', ChatViewSet, basename='chat')

urlpatterns = [
    path('', include(router.urls)),
]
