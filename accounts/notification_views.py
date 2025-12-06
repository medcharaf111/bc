"""
Views for Notification system
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Notification
from .notification_serializers import NotificationSerializer, NotificationCreateSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notifications
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return NotificationCreateSerializer
        return NotificationSerializer
    
    def get_queryset(self):
        """Get notifications for current user"""
        return Notification.objects.filter(
            recipient=self.request.user
        ).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread notifications"""
        unread = self.get_queryset().filter(is_read=False)
        serializer = self.get_serializer(unread, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'count': count})
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        notifications = self.get_queryset().filter(is_read=False)
        for notification in notifications:
            notification.mark_as_read()
        return Response({'message': f'{notifications.count()} notifications marked as read'})
    
    @action(detail=True, methods=['delete'])
    def clear(self, request, pk=None):
        """Delete a notification"""
        notification = self.get_object()
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['delete'])
    def clear_all(self, request):
        """Delete all read notifications"""
        notifications = self.get_queryset().filter(is_read=True)
        count = notifications.count()
        notifications.delete()
        return Response({'message': f'{count} notifications cleared'})
