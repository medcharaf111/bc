"""
Serializers for AI Chat functionality
"""
from rest_framework import serializers
from .models import ChatConversation, ChatMessage
from accounts.serializers import UserSerializer


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages"""
    
    class Meta:
        model = ChatMessage
        fields = [
            'id',
            'role',
            'content',
            'function_name',
            'function_args',
            'function_result',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ChatConversationSerializer(serializers.ModelSerializer):
    """Serializer for chat conversations"""
    messages = ChatMessageSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatConversation
        fields = [
            'id',
            'user',
            'title',
            'message_count',
            'messages',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def get_message_count(self, obj):
        return obj.messages.count()


class ChatConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for conversation list"""
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatConversation
        fields = [
            'id',
            'title',
            'message_count',
            'last_message',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_message_count(self, obj):
        return obj.messages.count()
    
    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            return {
                'role': last_msg.role,
                'content': last_msg.content[:100] + '...' if len(last_msg.content) > 100 else last_msg.content,
                'created_at': last_msg.created_at
            }
        return None


class ChatRequestSerializer(serializers.Serializer):
    """Serializer for chat requests"""
    message = serializers.CharField(required=True)
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
