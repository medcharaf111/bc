"""
Serializers for Notification system
"""
from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications"""
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['created_at', 'read_at']


class NotificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating notifications"""
    
    class Meta:
        model = Notification
        fields = ['recipient', 'notification_type', 'title', 'message', 'related_object_type', 'related_object_id']
