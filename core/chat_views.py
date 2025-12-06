"""
Views for AI Chat functionality
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ChatConversation, ChatMessage
from .chat_serializers import (
    ChatConversationSerializer,
    ChatConversationListSerializer,
    ChatMessageSerializer,
    ChatRequestSerializer
)
from .gemini_service import GeminiTeachingAssistant


class ChatViewSet(viewsets.ViewSet):
    """
    API endpoints for AI chat functionality
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get all conversations for the current user"""
        conversations = ChatConversation.objects.filter(user=request.user)
        serializer = ChatConversationListSerializer(conversations, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """Get a specific conversation with all messages"""
        try:
            conversation = ChatConversation.objects.get(id=pk, user=request.user)
            serializer = ChatConversationSerializer(conversation)
            return Response(serializer.data)
        except ChatConversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def destroy(self, request, pk=None):
        """Delete a conversation"""
        try:
            conversation = ChatConversation.objects.get(id=pk, user=request.user)
            conversation.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ChatConversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def chat(self, request):
        """
        Send a message to the AI assistant
        
        POST /api/chatbot/chat/
        Body: {
            "message": "Create a lesson plan for photosynthesis",
            "conversation_id": 1  # Optional
        }
        """
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        message = serializer.validated_data['message']
        conversation_id = serializer.validated_data.get('conversation_id')
        
        # Initialize AI assistant
        assistant = GeminiTeachingAssistant(request.user)
        
        # Get response
        result = assistant.chat(message, conversation_id)
        
        if result['success']:
            return Response({
                "success": True,
                "response": result['response'],
                "conversation_id": result['conversation_id'],
                "function_calls": result.get('function_calls', [])
            })
        else:
            return Response({
                "success": False,
                "error": result.get('error', 'Unknown error'),
                "response": result['response']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
