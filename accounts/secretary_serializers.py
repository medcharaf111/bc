from rest_framework import serializers
from .models import Task, Meeting, Decision, Document

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ('created_by',)

class MeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = '__all__'
        read_only_fields = ('created_by',)


class DecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Decision
        fields = '__all__'
        read_only_fields = ('created_by',)


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = '__all__'
        read_only_fields = ('created_by',)