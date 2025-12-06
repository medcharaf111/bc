from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Task, Meeting, Decision, Document
from .secretary_serializers import TaskSerializer, MeetingSerializer, DecisionSerializer, DocumentSerializer


class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Tasks for the Secretary Dashboard.
    """
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Task.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class MeetingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Meetings for the Secretary Dashboard.
    """
    serializer_class = MeetingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Meeting.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class DecisionViewSet(viewsets.ModelViewSet):
    serializer_class = DecisionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Decision.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
