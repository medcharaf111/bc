"""
Forum URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .forum_views import (
    ForumCategoryViewSet,
    ForumTopicViewSet,
    ForumReplyViewSet,
    ForumTagViewSet,
    ForumNotificationViewSet,
    ForumBookmarkViewSet
)

router = DefaultRouter()
router.register(r'categories', ForumCategoryViewSet, basename='forum-category')
router.register(r'topics', ForumTopicViewSet, basename='forum-topic')
router.register(r'replies', ForumReplyViewSet, basename='forum-reply')
router.register(r'tags', ForumTagViewSet, basename='forum-tag')
router.register(r'notifications', ForumNotificationViewSet, basename='forum-notification')
router.register(r'bookmarks', ForumBookmarkViewSet, basename='forum-bookmark')

urlpatterns = [
    path('', include(router.urls)),
]
