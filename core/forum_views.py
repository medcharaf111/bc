"""
Forum Views
Professional discussion forum for teachers, advisors, and admins
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission, AllowAny
from django.db.models import Q, Count, Prefetch
from django.utils import timezone

from .models import (
    ForumCategory,
    ForumTopic,
    ForumReply,
    ForumLike,
    ForumBookmark,
    ForumTag,
    TopicTag,
    ForumNotification
)
from .forum_serializers import (
    ForumCategorySerializer,
    ForumTopicListSerializer,
    ForumTopicDetailSerializer,
    ForumTopicCreateSerializer,
    ForumReplySerializer,
    ForumTagSerializer,
    ForumNotificationSerializer,
    ForumBookmarkSerializer
)


class ForumPermission(IsAuthenticated):
    """
    Only teachers, advisors, and admins can access the forum
    """
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.role in ['teacher', 'advisor', 'admin', 'minister']


class ForumCategoryPermission(BasePermission):
    """
    Allow anyone to view categories, but require authentication for other actions
    """
    def has_permission(self, request, view):
        # Allow GET requests (list and retrieve) without authentication
        if request.method == 'GET':
            return True
        # For other methods, require authentication and proper role
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ['teacher', 'advisor', 'admin', 'minister']


class ForumCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for forum categories
    Read-only for users, managed by admins
    Public access allowed to view categories
    """
    queryset = ForumCategory.objects.filter(is_active=True)
    serializer_class = ForumCategorySerializer
    permission_classes = [AllowAny]  # Allow unauthenticated users to browse categories
    authentication_classes = []  # Explicitly disable authentication for this viewset


class ForumTopicViewSet(viewsets.ModelViewSet):
    """
    ViewSet for forum topics
    Allow read-only access without authentication, but require auth for write operations
    """
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content', 'author__username']
    ordering_fields = ['created_at', 'last_activity', 'views_count']
    ordering = ['-is_pinned', '-last_activity']
    
    def get_permissions(self):
        """
        Allow anyone to view topics (GET), but require authentication for other actions
        """
        if self.request.method == 'GET':
            return [AllowAny()]
        return [ForumPermission()]
    
    def get_authenticators(self):
        """
        Disable authentication for read-only actions
        """
        if self.request.method == 'GET':
            return []
        return super().get_authenticators()
    
    def get_queryset(self):
        queryset = ForumTopic.objects.select_related(
            'author', 'category', 'related_lesson'
        ).prefetch_related(
            'topic_tags__tag', 'likes', 'bookmarks'
        )
        
        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category_id=category)
        
        # Filter by subject
        subject = self.request.query_params.get('subject', None)
        if subject:
            queryset = queryset.filter(related_subject=subject)
        
        # Filter by region
        region = self.request.query_params.get('region', None)
        if region:
            queryset = queryset.filter(region=region)
        
        # Filter by status
        topic_status = self.request.query_params.get('status', None)
        if topic_status:
            queryset = queryset.filter(status=topic_status)
        else:
            # Default: show open and pinned topics
            queryset = queryset.filter(status__in=['open', 'pinned'])
        
        # Filter by tags
        tags = self.request.query_params.get('tags', None)
        if tags:
            tag_list = tags.split(',')
            queryset = queryset.filter(topic_tags__tag__name__in=tag_list).distinct()
        
        # My topics - only if user is authenticated
        if self.request.query_params.get('my_topics', None) == 'true':
            if self.request.user and self.request.user.is_authenticated:
                queryset = queryset.filter(author=self.request.user)
            else:
                # Return empty queryset for unauthenticated users
                queryset = queryset.none()
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ForumTopicListSerializer
        elif self.action == 'create':
            return ForumTopicCreateSerializer
        return ForumTopicDetailSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """Increment view count when topic is viewed"""
        instance = self.get_object()
        instance.increment_views()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        """Set the author to the current user"""
        serializer.save(author=self.request.user)
    
    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        """Like/unlike a topic"""
        topic = self.get_object()
        like, created = ForumLike.objects.get_or_create(
            user=request.user,
            content_type='topic',
            topic=topic
        )
        
        if not created:
            # Unlike
            like.delete()
            return Response({'status': 'unliked'}, status=status.HTTP_200_OK)
        
        # Create notification for topic author
        if topic.author != request.user:
            ForumNotification.objects.create(
                user=topic.author,
                notification_type='like',
                topic=topic,
                triggered_by=request.user,
                message=f"{request.user.get_full_name()} liked your topic"
            )
        
        return Response({'status': 'liked'}, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def bookmark(self, request, pk=None):
        """Bookmark/unbookmark a topic"""
        topic = self.get_object()
        bookmark, created = ForumBookmark.objects.get_or_create(
            user=request.user,
            topic=topic
        )
        
        if not created:
            # Remove bookmark
            bookmark.delete()
            return Response({'status': 'unbookmarked'}, status=status.HTTP_200_OK)
        
        return Response({'status': 'bookmarked'}, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close a topic (author or admin only)"""
        topic = self.get_object()
        
        if request.user != topic.author and request.user.role not in ['admin', 'minister']:
            return Response(
                {'error': 'You do not have permission to close this topic'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        topic.status = 'closed'
        topic.save()
        return Response({'status': 'closed'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        """Reopen a closed topic (author or admin only)"""
        topic = self.get_object()
        
        if request.user != topic.author and request.user.role not in ['admin', 'minister']:
            return Response(
                {'error': 'You do not have permission to reopen this topic'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        topic.status = 'open'
        topic.save()
        return Response({'status': 'reopened'}, status=status.HTTP_200_OK)


class ForumReplyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for forum replies
    """
    serializer_class = ForumReplySerializer
    permission_classes = [ForumPermission]
    
    def get_queryset(self):
        queryset = ForumReply.objects.select_related('author', 'topic')
        
        # Filter by topic
        topic = self.request.query_params.get('topic', None)
        if topic:
            queryset = queryset.filter(topic_id=topic)
        
        # Filter by parent (for nested replies)
        parent = self.request.query_params.get('parent', None)
        if parent:
            queryset = queryset.filter(parent_reply_id=parent)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set the author and create notifications"""
        reply = serializer.save(author=self.request.user)
        
        # Notify topic author
        if reply.topic.author != self.request.user:
            ForumNotification.objects.create(
                user=reply.topic.author,
                notification_type='reply',
                topic=reply.topic,
                reply=reply,
                triggered_by=self.request.user,
                message=f"{self.request.user.get_full_name()} replied to your topic"
            )
        
        # Notify parent reply author
        if reply.parent_reply and reply.parent_reply.author != self.request.user:
            ForumNotification.objects.create(
                user=reply.parent_reply.author,
                notification_type='reply',
                topic=reply.topic,
                reply=reply,
                triggered_by=self.request.user,
                message=f"{self.request.user.get_full_name()} replied to your comment"
            )
    
    def perform_update(self, serializer):
        """Mark reply as edited"""
        serializer.save(is_edited=True, edited_at=timezone.now())
    
    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        """Like/unlike a reply"""
        reply = self.get_object()
        like, created = ForumLike.objects.get_or_create(
            user=request.user,
            content_type='reply',
            reply=reply
        )
        
        if not created:
            # Unlike
            like.delete()
            return Response({'status': 'unliked'}, status=status.HTTP_200_OK)
        
        # Create notification
        if reply.author != request.user:
            ForumNotification.objects.create(
                user=reply.author,
                notification_type='like',
                topic=reply.topic,
                reply=reply,
                triggered_by=request.user,
                message=f"{request.user.get_full_name()} liked your reply"
            )
        
        return Response({'status': 'liked'}, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def mark_solution(self, request, pk=None):
        """Mark a reply as the solution (topic author only)"""
        reply = self.get_object()
        
        if request.user != reply.topic.author:
            return Response(
                {'error': 'Only the topic author can mark a solution'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Unmark any existing solution
        ForumReply.objects.filter(topic=reply.topic, is_solution=True).update(is_solution=False)
        
        # Mark this reply as solution
        reply.is_solution = True
        reply.save()
        
        # Create notification
        if reply.author != request.user:
            ForumNotification.objects.create(
                user=reply.author,
                notification_type='solution',
                topic=reply.topic,
                reply=reply,
                triggered_by=request.user,
                message=f"{request.user.get_full_name()} marked your reply as the solution"
            )
        
        return Response({'status': 'marked_as_solution'}, status=status.HTTP_200_OK)


class ForumTagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for forum tags
    """
    queryset = ForumTag.objects.all()
    serializer_class = ForumTagSerializer
    permission_classes = [ForumPermission]
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get most popular tags"""
        tags = ForumTag.objects.order_by('-usage_count')[:20]
        serializer = self.get_serializer(tags, many=True)
        return Response(serializer.data)


class ForumNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for forum notifications
    """
    serializer_class = ForumNotificationSerializer
    permission_classes = [ForumPermission]
    
    def get_queryset(self):
        return ForumNotification.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = ForumNotification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        return Response({'unread_count': count})
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked_as_read'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        ForumNotification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)
        return Response({'status': 'all_marked_as_read'}, status=status.HTTP_200_OK)


class ForumBookmarkViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for forum bookmarks
    """
    serializer_class = ForumBookmarkSerializer
    permission_classes = [ForumPermission]
    
    def get_queryset(self):
        return ForumBookmark.objects.filter(user=self.request.user).select_related('topic')
