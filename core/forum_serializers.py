"""
Forum Serializers
"""
from rest_framework import serializers
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
from accounts.models import User


class AuthorSerializer(serializers.ModelSerializer):
    """Serializer for user information in forum contexts"""
    full_name = serializers.SerializerMethodField()
    role_display = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'role', 'role_display', 'subjects']
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_role_display(self, obj):
        return obj.get_role_display()


class ForumCategorySerializer(serializers.ModelSerializer):
    """Serializer for forum categories"""
    topic_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ForumCategory
        fields = [
            'id', 'name', 'name_ar', 'description', 'description_ar',
            'category_type', 'icon', 'order', 'is_active', 'topic_count',
            'created_at'
        ]
    
    def get_topic_count(self, obj):
        return obj.topics.filter(status__in=['open', 'pinned']).count()


class ForumTagSerializer(serializers.ModelSerializer):
    """Serializer for forum tags"""
    class Meta:
        model = ForumTag
        fields = ['id', 'name', 'name_ar', 'usage_count']


class ForumReplySerializer(serializers.ModelSerializer):
    """Serializer for forum replies"""
    author = AuthorSerializer(read_only=True)
    likes_count = serializers.SerializerMethodField()
    is_liked_by_user = serializers.SerializerMethodField()
    sub_replies_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ForumReply
        fields = [
            'id', 'topic', 'author', 'content', 'parent_reply',
            'is_edited', 'edited_at', 'is_solution', 'created_at',
            'likes_count', 'is_liked_by_user', 'sub_replies_count'
        ]
        read_only_fields = ['author', 'is_edited', 'edited_at', 'created_at']
    
    def get_likes_count(self, obj):
        return obj.likes.count()
    
    def get_is_liked_by_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False
    
    def get_sub_replies_count(self, obj):
        return obj.sub_replies.count()


class ForumTopicListSerializer(serializers.ModelSerializer):
    """Serializer for forum topic list view (summary)"""
    author = AuthorSerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_name_ar = serializers.CharField(source='category.name_ar', read_only=True)
    reply_count = serializers.SerializerMethodField()
    last_reply = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    
    class Meta:
        model = ForumTopic
        fields = [
            'id', 'category', 'category_name', 'category_name_ar', 'title',
            'author', 'status', 'is_pinned', 'views_count', 'reply_count',
            'last_reply', 'tags', 'likes_count', 'is_bookmarked',
            'related_subject', 'region', 'school_level',
            'created_at', 'updated_at', 'last_activity'
        ]
    
    def get_reply_count(self, obj):
        return obj.get_reply_count()
    
    def get_last_reply(self, obj):
        last_reply = obj.get_last_reply()
        if last_reply:
            return {
                'author': last_reply.author.get_full_name(),
                'created_at': last_reply.created_at
            }
        return None
    
    def get_likes_count(self, obj):
        return obj.likes.count()
    
    def get_tags(self, obj):
        """Get tags through the TopicTag relationship"""
        return ForumTagSerializer(
            [topic_tag.tag for topic_tag in obj.topic_tags.all()],
            many=True
        ).data
    
    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.bookmarks.filter(user=request.user).exists()
        return False


class ForumTopicDetailSerializer(serializers.ModelSerializer):
    """Serializer for forum topic detail view"""
    author = AuthorSerializer(read_only=True)
    category = ForumCategorySerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    is_liked_by_user = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    related_lesson_title = serializers.CharField(source='related_lesson.title', read_only=True)
    
    class Meta:
        model = ForumTopic
        fields = [
            'id', 'category', 'title', 'content', 'author',
            'related_lesson', 'related_lesson_title', 'related_subject',
            'status', 'is_pinned', 'views_count', 'region', 'school_level',
            'created_at', 'updated_at', 'last_activity',
            'replies', 'tags', 'likes_count', 'is_liked_by_user', 'is_bookmarked'
        ]
    
    def get_replies(self, obj):
        # Get top-level replies (no parent)
        top_level_replies = obj.replies.filter(parent_reply__isnull=True)
        return ForumReplySerializer(top_level_replies, many=True, context=self.context).data
    
    def get_likes_count(self, obj):
        return obj.likes.count()
    
    def get_tags(self, obj):
        """Get tags through the TopicTag relationship"""
        return ForumTagSerializer(
            [topic_tag.tag for topic_tag in obj.topic_tags.all()],
            many=True
        ).data
    
    def get_is_liked_by_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False
    
    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.bookmarks.filter(user=request.user).exists()
        return False


class ForumTopicCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating forum topics"""
    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=50),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = ForumTopic
        fields = [
            'category', 'title', 'content', 'related_lesson',
            'related_subject', 'region', 'school_level', 'tag_names'
        ]
    
    def create(self, validated_data):
        tag_names = validated_data.pop('tag_names', [])
        topic = ForumTopic.objects.create(**validated_data)
        
        # Add tags
        for tag_name in tag_names:
            tag, created = ForumTag.objects.get_or_create(name=tag_name.lower())
            TopicTag.objects.create(topic=topic, tag=tag)
            tag.usage_count += 1
            tag.save()
        
        return topic


class ForumNotificationSerializer(serializers.ModelSerializer):
    """Serializer for forum notifications"""
    triggered_by_name = serializers.CharField(source='triggered_by.get_full_name', read_only=True)
    topic_title = serializers.CharField(source='topic.title', read_only=True)
    
    class Meta:
        model = ForumNotification
        fields = [
            'id', 'notification_type', 'topic', 'topic_title', 'reply',
            'triggered_by', 'triggered_by_name', 'message', 'is_read', 'created_at'
        ]
        read_only_fields = ['created_at']


class ForumBookmarkSerializer(serializers.ModelSerializer):
    """Serializer for forum bookmarks"""
    topic = ForumTopicListSerializer(read_only=True)
    
    class Meta:
        model = ForumBookmark
        fields = ['id', 'topic', 'created_at']
        read_only_fields = ['created_at']
