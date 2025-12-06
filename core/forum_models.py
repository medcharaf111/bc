"""
Professional Forum Models
Allows teachers, advisors, and admins to share experiences, discuss lessons, and collaborate
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class ForumCategory(models.Model):
    """
    Categories for organizing forum discussions
    """
    CATEGORY_CHOICES = [
        ('teaching_methods', 'Teaching Methods'),
        ('lesson_sharing', 'Lesson Sharing'),
        ('subject_discussion', 'Subject Discussion'),
        ('best_practices', 'Best Practices'),
        ('technology', 'Technology & Tools'),
        ('regional_exchange', 'Regional Exchange'),
        ('general', 'General Discussion'),
    ]
    
    name = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    description_ar = models.TextField(blank=True)
    category_type = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='general')
    icon = models.CharField(max_length=50, blank=True)  # Icon name for UI
    order = models.IntegerField(default=0)  # For sorting categories
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Forum Categories'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class ForumTopic(models.Model):
    """
    Discussion topics created by teachers, advisors, or admins
    """
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('pinned', 'Pinned'),
        ('archived', 'Archived'),
    ]
    
    category = models.ForeignKey(ForumCategory, on_delete=models.CASCADE, related_name='topics')
    title = models.CharField(max_length=255)
    content = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='forum_topics')
    
    # Optional attachments/references
    related_lesson = models.ForeignKey('Lesson', on_delete=models.SET_NULL, null=True, blank=True, related_name='forum_topics')
    related_subject = models.CharField(max_length=50, blank=True)  # Subject if discussing specific subject
    
    # Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    is_pinned = models.BooleanField(default=False)
    views_count = models.IntegerField(default=0)
    
    # Regional context
    region = models.CharField(max_length=100, blank=True)  # For regional discussions
    school_level = models.CharField(max_length=50, blank=True)  # Primary, secondary, etc.
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_pinned', '-last_activity']
        indexes = [
            models.Index(fields=['-last_activity']),
            models.Index(fields=['category', '-created_at']),
        ]
    
    def __str__(self):
        return self.title
    
    def increment_views(self):
        """Increment view count"""
        self.views_count += 1
        self.save(update_fields=['views_count'])
    
    def get_reply_count(self):
        """Get total number of replies"""
        return self.replies.count()
    
    def get_last_reply(self):
        """Get the most recent reply"""
        return self.replies.order_by('-created_at').first()


class ForumReply(models.Model):
    """
    Replies to forum topics
    """
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='forum_replies')
    content = models.TextField()
    
    # Optional parent reply for nested discussions
    parent_reply = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_replies')
    
    # Moderation
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_solution = models.BooleanField(default=False)  # Mark as solution/best answer
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name_plural = 'Forum Replies'
    
    def __str__(self):
        return f"Reply by {self.author.username} on {self.topic.title}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update topic's last activity
        self.topic.last_activity = timezone.now()
        self.topic.save(update_fields=['last_activity'])


class ForumLike(models.Model):
    """
    Likes/helpful marks for topics and replies
    """
    CONTENT_TYPE_CHOICES = [
        ('topic', 'Topic'),
        ('reply', 'Reply'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPE_CHOICES)
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, null=True, blank=True, related_name='likes')
    reply = models.ForeignKey(ForumReply, on_delete=models.CASCADE, null=True, blank=True, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [
            ['user', 'topic'],
            ['user', 'reply'],
        ]
    
    def __str__(self):
        if self.topic:
            return f"{self.user.username} likes topic {self.topic.id}"
        return f"{self.user.username} likes reply {self.reply.id}"


class ForumBookmark(models.Model):
    """
    Users can bookmark topics for later reference
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='forum_bookmarks')
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'topic']
    
    def __str__(self):
        return f"{self.user.username} bookmarked {self.topic.title}"


class ForumTag(models.Model):
    """
    Tags for better topic categorization and search
    """
    name = models.CharField(max_length=50, unique=True)
    name_ar = models.CharField(max_length=50, blank=True)
    usage_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-usage_count', 'name']
    
    def __str__(self):
        return self.name


class TopicTag(models.Model):
    """
    Many-to-many relationship between topics and tags
    """
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, related_name='topic_tags')
    tag = models.ForeignKey(ForumTag, on_delete=models.CASCADE, related_name='tagged_topics')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['topic', 'tag']
    
    def __str__(self):
        return f"{self.topic.title} - {self.tag.name}"


class ForumNotification(models.Model):
    """
    Notifications for forum activities
    """
    NOTIFICATION_TYPES = [
        ('reply', 'New Reply'),
        ('mention', 'Mentioned'),
        ('like', 'Like Received'),
        ('solution', 'Solution Marked'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='forum_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE)
    reply = models.ForeignKey(ForumReply, on_delete=models.CASCADE, null=True, blank=True)
    triggered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='triggered_notifications')
    
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.notification_type}"
