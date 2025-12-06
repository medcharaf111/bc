from django.contrib.auth.models import AbstractUser
from django.db import models

class School(models.Model):
    name = models.CharField(max_length=255, unique=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Geodata fields
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    school_code = models.CharField(max_length=50, blank=True)
    school_type = models.CharField(max_length=100, blank=True)
    delegation = models.CharField(max_length=100, blank=True)
    cre = models.CharField(max_length=100, blank=True)
    name_ar = models.CharField(max_length=255, blank=True)
    
    # Region assignment for inspector access
    region = models.ForeignKey(
        'core.Region',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schools',
        help_text='Geographic region for inspection purposes'
    )

    def __str__(self):
        return self.name

class User(AbstractUser):
    ROLE_CHOICES = [
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('parent', 'Parent'),
        ('admin', 'Administrator'),
        ('advisor', 'Advisor'),
        ('director', 'School Director'),
        ('cnp', 'CNP Agent'),
        ('inspector', 'Inspector'),
        ('gpi', 'GPI (General Pedagogical Inspectorate)'),
        ('delegation', 'Inspector/Advisor (Delegation)'),
        ('gdhr', 'GDHR (Human Resources)'),
        ('minister', 'Minister'),
        ("secretary", "General Secretary")  ]
    
    SUBJECT_CHOICES = [
        ('math', 'Mathematics'),
        ('science', 'Science'),
        ('english', 'English'),
        ('arabic', 'Arabic'),
        ('social_studies', 'Social Studies'),
        ('art', 'Art'),
        ('music', 'Music'),
        ('physical_education', 'Physical Education'),
        ('computer_science', 'Computer Science'),
        ('religious_studies', 'Religious Studies'),
    ]
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    GRADE_LEVEL_CHOICES = [
        ('1', '1st Grade'),
        ('2', '2nd Grade'),
        ('3', '3rd Grade'),
        ('4', '4th Grade'),
        ('5', '5th Grade'),
        ('6', '6th Grade'),
        ('7', '7th Grade'),
        ('8', '8th Grade'),
        ('9', '9th Grade'),
        ('10', '10th Grade'),
        ('11', '11th Grade'),
        ('12', '12th Grade'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='users')
    date_of_birth = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    subjects = models.JSONField(default=list, blank=True, help_text='Teacher subjects (1-3 subjects)')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    grade_level = models.CharField(max_length=2, choices=GRADE_LEVEL_CHOICES, null=True, blank=True, help_text='Student grade level')
    assigned_delegation = models.CharField(max_length=100, blank=True, null=True, help_text='Assigned delegation for delegator role')
    assigned_region = models.CharField(max_length=100, blank=True, null=True, help_text='Assigned region for inspector/GPI role')

    def __str__(self):
        return f"{self.username} ({self.role})"


class TeacherStudentRelationship(models.Model):
    """Bidirectional relationship between teachers and students with ratings"""
    teacher = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='student_relationships',
        limit_choices_to={'role': 'teacher'}
    )
    student = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='teacher_relationships',
        limit_choices_to={'role': 'student'}
    )
    
    # Rating from teacher to student (1-5 scale)
    rating_by_teacher = models.IntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)])
    comments_by_teacher = models.TextField(blank=True, help_text='Teacher comments about the student')
    
    # Rating from student to teacher (1-5 scale)
    rating_by_student = models.IntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)])
    comments_by_student = models.TextField(blank=True, help_text='Student comments about the teacher')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, help_text='Whether this relationship is currently active')
    
    class Meta:
        unique_together = ['teacher', 'student']
        ordering = ['-created_at']
        verbose_name = 'Teacher-Student Relationship'
        verbose_name_plural = 'Teacher-Student Relationships'
    
    def __str__(self):
        return f"{self.teacher.get_full_name() or self.teacher.username} ↔ {self.student.get_full_name() or self.student.username}"
    
    def get_average_rating(self):
        """Calculate average rating from both sides"""
        ratings = [r for r in [self.rating_by_teacher, self.rating_by_student] if r is not None]
        return sum(ratings) / len(ratings) if ratings else None


class AdvisorReview(models.Model):
    """Reviews/remarks left by advisors on lessons, MCQ tests, or Q&A tests"""
    REVIEW_TYPE_CHOICES = [
        ('lesson', 'Lesson'),
        ('mcq_test', 'MCQ Test'),
        ('qa_test', 'Q&A Test'),
    ]
    
    advisor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='advisor_reviews',
        limit_choices_to={'role': 'advisor'}
    )
    review_type = models.CharField(max_length=10, choices=REVIEW_TYPE_CHOICES)
    
    # Generic relationship to handle different content types
    lesson = models.ForeignKey(
        'core.Lesson',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='advisor_reviews'
    )
    mcq_test = models.ForeignKey(
        'core.Test',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='advisor_reviews'
    )
    qa_test = models.ForeignKey(
        'core.QATest',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='advisor_reviews'
    )
    
    # Review content
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], help_text='Rating from 1-5')
    remarks = models.TextField(help_text='Advisor comments and feedback')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Advisor Review'
        verbose_name_plural = 'Advisor Reviews'
    
    def __str__(self):
        target = self.lesson or self.mcq_test or self.qa_test
        return f"Review by {self.advisor.username} on {target}"
    
    def clean(self):
        """Ensure exactly one target is set"""
        from django.core.exceptions import ValidationError
        targets = [self.lesson, self.mcq_test, self.qa_test]
        if sum(t is not None for t in targets) != 1:
            raise ValidationError("Review must target exactly one item (lesson, MCQ test, or Q&A test)")


class GroupChat(models.Model):
    """Group chat between advisor and teacher(s) for a specific subject"""
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=50, choices=User.SUBJECT_CHOICES)
    advisor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='advisor_chats',
        limit_choices_to={'role': 'advisor'}
    )
    teachers = models.ManyToManyField(
        User,
        related_name='teacher_chats',
        limit_choices_to={'role': 'teacher'}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Group Chat'
        verbose_name_plural = 'Group Chats'
    
    def __str__(self):
        return f"{self.name} - {self.get_subject_display()}"


class ChatMessage(models.Model):
    """Individual messages in a group chat"""
    chat = models.ForeignKey(GroupChat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    message = models.TextField(blank=True)  # Allow blank if sending file only
    file_attachment = models.FileField(upload_to='chat_attachments/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Track message edits
    is_edited = models.BooleanField(default=False)  # Flag if message was edited
    read_by = models.ManyToManyField(User, related_name='read_messages', blank=True)  # Track who has read the message
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Chat Message'
        verbose_name_plural = 'Chat Messages'
    
    def __str__(self):
        return f"{self.sender.username}: {self.message[:50]}"
    
    def is_read_by(self, user):
        """Check if a specific user has read this message"""
        return self.read_by.filter(id=user.id).exists()
    
    def mark_as_read_by(self, user):
        """Mark message as read by a specific user"""
        if user != self.sender and not self.is_read_by(user):
            self.read_by.add(user)


class ParentStudentRelationship(models.Model):
    """Link parents to their children/students they want to track"""
    parent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tracked_students',
        limit_choices_to={'role': 'parent'}
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tracking_parents',
        limit_choices_to={'role': 'student'}
    )
    relationship_type = models.CharField(
        max_length=20,
        choices=[
            ('parent', 'Parent'),
            ('guardian', 'Guardian'),
            ('relative', 'Relative'),
            ('other', 'Other')
        ],
        default='parent'
    )
    is_primary = models.BooleanField(default=False, help_text='Primary parent/guardian')
    can_view_grades = models.BooleanField(default=True)
    can_chat_teachers = models.BooleanField(default=True)
    notes = models.TextField(blank=True, help_text='Additional notes about the relationship')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['parent', 'student']
        ordering = ['-is_primary', '-created_at']
        verbose_name = 'Parent-Student Relationship'
        verbose_name_plural = 'Parent-Student Relationships'
    
    def __str__(self):
        return f"{self.parent.get_full_name() or self.parent.username} → {self.student.get_full_name() or self.student.username}"


class ParentTeacherChat(models.Model):
    """Private chat between parent and teacher about a specific student"""
    parent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='parent_teacher_chats',
        limit_choices_to={'role': 'parent'}
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_parent_chats',
        limit_choices_to={'role': 'teacher'}
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='parent_teacher_chats_about',
        limit_choices_to={'role': 'student'},
        help_text='The student this chat is about'
    )
    subject = models.CharField(
        max_length=50,
        choices=User.SUBJECT_CHOICES,
        blank=True,
        help_text='Optional: specific subject being discussed'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['parent', 'teacher', 'student']
        ordering = ['-updated_at']
        verbose_name = 'Parent-Teacher Chat'
        verbose_name_plural = 'Parent-Teacher Chats'
    
    def __str__(self):
        return f"{self.parent.username} ↔ {self.teacher.username} (re: {self.student.username})"


class ParentTeacherMessage(models.Model):
    """Individual messages in parent-teacher chats"""
    chat = models.ForeignKey(ParentTeacherChat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pt_messages_sent')
    message = models.TextField(blank=True)
    file_attachment = models.FileField(upload_to='parent_teacher_attachments/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Parent-Teacher Message'
        verbose_name_plural = 'Parent-Teacher Messages'
    
    def __str__(self):
        return f"{self.sender.username}: {self.message[:50]}"


class TeacherProgress(models.Model):
    """Track teacher's curriculum progress for a subject"""
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subject_progress',
        limit_choices_to={'role': 'teacher'}
    )
    subject = models.CharField(max_length=50, choices=User.SUBJECT_CHOICES)
    grade_level = models.CharField(
        max_length=20,
        choices=[
            ('grade_1', 'Grade 1'),
            ('grade_2', 'Grade 2'),
            ('grade_3', 'Grade 3'),
            ('grade_4', 'Grade 4'),
            ('grade_5', 'Grade 5'),
            ('grade_6', 'Grade 6'),
            ('grade_7', 'Grade 7'),
            ('grade_8', 'Grade 8'),
            ('grade_9', 'Grade 9'),
            ('grade_10', 'Grade 10'),
            ('grade_11', 'Grade 11'),
            ('grade_12', 'Grade 12'),
        ]
    )
    current_chapter = models.CharField(max_length=255, help_text='Current chapter/unit being taught')
    chapter_number = models.IntegerField(default=1, help_text='Chapter number in curriculum')
    total_chapters = models.IntegerField(default=10, help_text='Total chapters in curriculum')
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['teacher', 'subject', 'grade_level']
        ordering = ['-updated_at']
        verbose_name = 'Teacher Progress'
        verbose_name_plural = 'Teacher Progress Records'
    
    def __str__(self):
        return f"{self.teacher.username} - {self.get_subject_display()} Grade {self.grade_level}: Chapter {self.chapter_number}"
    
    def get_progress_percentage(self):
        """Calculate progress percentage"""
        return (self.chapter_number / self.total_chapters) * 100 if self.total_chapters > 0 else 0


class ChapterProgressNotification(models.Model):
    """Notification to advisor when teacher moves to new chapter"""
    STATUS_CHOICES = [
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed by Advisor'),
        ('rejected', 'Rejected - Revert to Previous'),
    ]
    
    teacher_progress = models.ForeignKey(
        TeacherProgress,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    advisor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chapter_notifications',
        limit_choices_to={'role': 'advisor'}
    )
    previous_chapter = models.CharField(max_length=255)
    previous_chapter_number = models.IntegerField()
    new_chapter = models.CharField(max_length=255)
    new_chapter_number = models.IntegerField()
    ai_detected = models.BooleanField(default=True, help_text='Whether this was detected by AI')
    ai_confidence = models.FloatField(default=0.0, help_text='AI confidence score (0-1)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    advisor_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Chapter Progress Notification'
        verbose_name_plural = 'Chapter Progress Notifications'
    
    def __str__(self):
        return f"{self.teacher_progress.teacher.username}: Chapter {self.previous_chapter_number} → {self.new_chapter_number} ({self.status})"


class TeacherAnalytics(models.Model):
    """Aggregate analytics for teacher performance"""
    teacher = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='analytics',
        limit_choices_to={'role': 'teacher'}
    )
    
    # Lesson metrics
    total_lessons_created = models.IntegerField(default=0)
    total_mcq_tests_created = models.IntegerField(default=0)
    total_qa_tests_created = models.IntegerField(default=0)
    
    # Student performance metrics
    total_students = models.IntegerField(default=0)
    average_student_score = models.FloatField(default=0.0, help_text='Average score across all students')
    
    # Rating metrics
    average_student_rating = models.FloatField(default=0.0, help_text='Average rating from students (1-5)')
    total_student_ratings = models.IntegerField(default=0)
    average_advisor_rating = models.FloatField(default=0.0, help_text='Average rating from advisors (1-5)')
    total_advisor_ratings = models.IntegerField(default=0)
    
    # Combined rating (weighted: 60% students, 40% advisors)
    overall_rating = models.FloatField(default=0.0, help_text='Weighted average rating')
    
    # Activity metrics
    last_lesson_created = models.DateTimeField(null=True, blank=True)
    last_test_created = models.DateTimeField(null=True, blank=True)
    
    # Progress metrics
    subjects_taught = models.JSONField(default=list, help_text='List of subjects taught')
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Teacher Analytics'
        verbose_name_plural = 'Teacher Analytics'
    
    def __str__(self):
        return f"Analytics for {self.teacher.username}"
    
    def calculate_overall_rating(self):
        """Calculate weighted overall rating"""
        if self.total_student_ratings == 0 and self.total_advisor_ratings == 0:
            return 0.0
        
        student_weight = 0.6
        advisor_weight = 0.4
        
        student_contribution = self.average_student_rating * student_weight if self.total_student_ratings > 0 else 0
        advisor_contribution = self.average_advisor_rating * advisor_weight if self.total_advisor_ratings > 0 else 0
        
        # If only one rating type exists, use 100% of that
        if self.total_student_ratings == 0:
            return self.average_advisor_rating
        if self.total_advisor_ratings == 0:
            return self.average_student_rating
        
        return student_contribution + advisor_contribution


class TeacherGradeAssignment(models.Model):
    """Tracks which teachers are assigned to teach which grades"""
    GRADE_CHOICES = [
        ('grade_1', 'Grade 1'),
        ('grade_2', 'Grade 2'),
        ('grade_3', 'Grade 3'),
        ('grade_4', 'Grade 4'),
        ('grade_5', 'Grade 5'),
        ('grade_6', 'Grade 6'),
        ('grade_7', 'Grade 7'),
        ('grade_8', 'Grade 8'),
        ('grade_9', 'Grade 9'),
        ('grade_10', 'Grade 10'),
        ('grade_11', 'Grade 11'),
        ('grade_12', 'Grade 12'),
    ]
    
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='grade_assignments',
        limit_choices_to={'role': 'teacher'}
    )
    grade_level = models.CharField(max_length=20, choices=GRADE_CHOICES)
    subject = models.CharField(max_length=50, choices=User.SUBJECT_CHOICES)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='grade_assignments')
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assignments_made',
        limit_choices_to={'role': 'director'}
    )
    academic_year = models.CharField(
        max_length=20,
        default='2024-2025',
        help_text='Academic year, e.g., 2024-2025'
    )
    is_active = models.BooleanField(default=True, help_text='Whether this assignment is currently active')
    notes = models.TextField(blank=True, help_text='Additional notes about this assignment')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['teacher', 'grade_level', 'subject', 'academic_year']
        ordering = ['grade_level', 'subject']
        verbose_name = 'Teacher Grade Assignment'
        verbose_name_plural = 'Teacher Grade Assignments'
    
    def __str__(self):
        return f"{self.teacher.get_full_name() or self.teacher.username} - {self.get_subject_display()} - {self.get_grade_level_display()}"
    
    def clean(self):
        """Validate that teacher and school match"""
        from django.core.exceptions import ValidationError
        if self.teacher.school != self.school:
            raise ValidationError("Teacher must belong to the same school as the assignment")


# ============================================================
# DELEGATION (INSPECTOR/ADVISOR) MODELS
# ============================================================

class TeacherAdvisorAssignment(models.Model):
    """
    Assignment of advisors to teachers by Delegation
    Tracks which advisor is responsible for which teacher
    """
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='advisor_assignments',
        limit_choices_to={'role': 'teacher'}
    )
    advisor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_assignments',
        limit_choices_to={'role': 'advisor'}
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='advisor_assignments_made',
        limit_choices_to={'role': 'delegation'}
    )
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='teacher_advisor_assignments')
    subject = models.CharField(max_length=50, choices=User.SUBJECT_CHOICES, help_text='Subject for this assignment')
    
    # Status
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, help_text='Assignment notes or instructions')
    
    # Metadata
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-assigned_at']
        unique_together = ['teacher', 'advisor', 'subject']
        indexes = [
            models.Index(fields=['teacher', 'is_active']),
            models.Index(fields=['advisor', 'is_active']),
            models.Index(fields=['school', 'subject']),
        ]
        verbose_name = 'Teacher-Advisor Assignment'
        verbose_name_plural = 'Teacher-Advisor Assignments'
    
    def __str__(self):
        return f"{self.advisor.username} → {self.teacher.username} ({self.subject})"


class TeacherInspection(models.Model):
    """
    Track when a Delegation (inspector/advisor) is assigned to inspect a teacher
    """
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='inspections',
        limit_choices_to={'role': 'teacher'}
    )
    delegator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='conducted_inspections',
        limit_choices_to={'role': 'delegation'}
    )
    advisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_inspections',
        limit_choices_to={'role': 'advisor'},
        help_text='Advisor assigned to conduct the inspection'
    )
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='inspections')
    subject = models.CharField(max_length=50, choices=User.SUBJECT_CHOICES)
    
    # Scheduling
    scheduled_date = models.DateField(help_text='Date of the inspection')
    scheduled_time = models.TimeField(null=True, blank=True, help_text='Time of the inspection')
    duration_minutes = models.IntegerField(default=60, help_text='Expected duration in minutes')
    
    # Purpose and notes
    purpose = models.TextField(help_text='Purpose and objectives of this inspection')
    pre_inspection_notes = models.TextField(blank=True, help_text='Notes before the inspection')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Advisor reporting
    advisor_started_at = models.DateTimeField(null=True, blank=True, help_text='When advisor reported starting inspection')
    advisor_completed_at = models.DateTimeField(null=True, blank=True, help_text='When advisor reported completing inspection')
    advisor_notes = models.TextField(blank=True, help_text='Notes from advisor about the inspection')
    
    # Delegator verification
    start_verified_by_delegator = models.BooleanField(default=False, help_text='Whether Delegator verified the start')
    start_verified_at = models.DateTimeField(null=True, blank=True)
    completion_verified_by_delegator = models.BooleanField(default=False, help_text='Whether Delegator verified completion')
    completion_verified_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_inspections'
    )
    
    class Meta:
        ordering = ['-scheduled_date', '-scheduled_time']
        indexes = [
            models.Index(fields=['delegator', 'status']),
            models.Index(fields=['teacher', 'status']),
            models.Index(fields=['school', 'scheduled_date']),
        ]
        verbose_name = 'Teacher Inspection'
        verbose_name_plural = 'Teacher Inspections'
    
    def __str__(self):
        return f"Inspection: {self.teacher.username} by {self.delegator.username} on {self.scheduled_date}"


class InspectionReview(models.Model):
    """
    Detailed review submitted by Delegator after inspecting a teacher
    This is permanently saved to the teacher's profile
    """
    inspection = models.OneToOneField(
        TeacherInspection,
        on_delete=models.CASCADE,
        related_name='review'
    )
    
    # Overall ratings (1-5 scale)
    teaching_quality = models.IntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text='Quality of teaching delivery (1-5)'
    )
    lesson_planning = models.IntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text='Lesson planning and organization (1-5)'
    )
    student_engagement = models.IntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text='Student engagement level (1-5)'
    )
    classroom_management = models.IntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text='Classroom management skills (1-5)'
    )
    content_knowledge = models.IntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text='Subject matter expertise (1-5)'
    )
    use_of_resources = models.IntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text='Effective use of teaching resources (1-5)'
    )
    
    # Calculated overall score
    overall_score = models.FloatField(
        help_text='Average of all ratings',
        editable=False
    )
    
    # Detailed feedback
    strengths = models.TextField(help_text='Observed strengths and positive aspects')
    areas_for_improvement = models.TextField(help_text='Areas that need improvement')
    specific_observations = models.TextField(help_text='Specific observations during the inspection')
    recommendations = models.TextField(help_text='Recommendations for professional development')
    
    # Action items
    action_items = models.JSONField(
        default=list,
        help_text='List of action items: [{item: str, deadline: date, completed: bool}]'
    )
    
    # Follow-up
    requires_follow_up = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True)
    
    # Attachments/Evidence
    evidence_photos = models.JSONField(
        default=list,
        blank=True,
        help_text='URLs to evidence photos from the inspection'
    )
    lesson_materials_reviewed = models.TextField(blank=True, help_text='Notes on reviewed lesson materials')
    
    # Metadata
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    teacher_viewed_at = models.DateTimeField(null=True, blank=True)
    teacher_acknowledged = models.BooleanField(default=False)
    teacher_comments = models.TextField(blank=True, help_text='Teacher response to the review')
    
    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Inspection Review'
        verbose_name_plural = 'Inspection Reviews'
    
    def __str__(self):
        return f"Review for {self.inspection.teacher.username} - Score: {self.overall_score}/5"
    
    def save(self, *args, **kwargs):
        # Calculate overall score
        scores = [
            self.teaching_quality,
            self.lesson_planning,
            self.student_engagement,
            self.classroom_management,
            self.content_knowledge,
            self.use_of_resources,
        ]
        self.overall_score = sum(scores) / len(scores)
        super().save(*args, **kwargs)


class DelegationTeacherMetrics(models.Model):
    """
    Aggregate metrics for teachers tracked by Delegation
    Provides a quick overview of teacher performance over time
    """
    teacher = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='delegation_metrics',
        limit_choices_to={'role': 'teacher'}
    )
    
    # Inspection history
    total_inspections = models.IntegerField(default=0)
    last_inspection_date = models.DateField(null=True, blank=True)
    average_inspection_score = models.FloatField(default=0.0, help_text='Average overall score from all inspections')
    
    # Improvement tracking
    improvement_trend = models.CharField(
        max_length=20,
        choices=[
            ('improving', 'Improving'),
            ('stable', 'Stable'),
            ('declining', 'Declining'),
            ('new', 'New - Insufficient Data'),
        ],
        default='new'
    )
    
    # Strengths and weaknesses (aggregated from reviews)
    common_strengths = models.JSONField(default=list, help_text='Most frequently noted strengths')
    common_weaknesses = models.JSONField(default=list, help_text='Most frequently noted weaknesses')
    
    # Student outcomes
    average_student_score = models.FloatField(default=0.0, help_text='Average student test scores')
    student_count = models.IntegerField(default=0)
    
    # Professional development
    completed_action_items = models.IntegerField(default=0)
    pending_action_items = models.IntegerField(default=0)
    
    # Latest review summary
    latest_review_score = models.FloatField(null=True, blank=True)
    latest_review_date = models.DateField(null=True, blank=True)
    needs_attention = models.BooleanField(default=False, help_text='Flagged for immediate attention')
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Delegation Teacher Metrics'
        verbose_name_plural = 'Delegation Teacher Metrics'
    
    def __str__(self):
        return f"Metrics for {self.teacher.username} - Avg Score: {self.average_inspection_score}"
    
    def update_metrics(self):
        """Recalculate all metrics based on inspection reviews"""
        reviews = InspectionReview.objects.filter(
            inspection__teacher=self.teacher
        ).order_by('-submitted_at')
        
        self.total_inspections = reviews.count()
        
        if reviews.exists():
            # Calculate average score
            total_score = sum(review.overall_score for review in reviews)
            self.average_inspection_score = total_score / self.total_inspections
            
            # Get latest review info
            latest = reviews.first()
            self.latest_review_score = latest.overall_score
            self.latest_review_date = latest.submitted_at.date()
            self.last_inspection_date = latest.inspection.scheduled_date
            
            # Calculate improvement trend (compare last 2 reviews)
            if self.total_inspections >= 2:
                latest_score = reviews[0].overall_score
                previous_score = reviews[1].overall_score
                
                if latest_score > previous_score + 0.5:
                    self.improvement_trend = 'improving'
                elif latest_score < previous_score - 0.5:
                    self.improvement_trend = 'declining'
                else:
                    self.improvement_trend = 'stable'
            
            # Flag if needs attention (low scores)
            self.needs_attention = self.average_inspection_score < 2.5
        
        self.save()


class DelegationDashboardStats(models.Model):
    """
    Cached dashboard statistics for Delegation users
    Updated periodically to improve dashboard performance
    """
    delegator = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='dashboard_stats',
        limit_choices_to={'role': 'delegation'}
    )
    
    # Teacher oversight
    total_teachers_assigned = models.IntegerField(default=0)
    teachers_needing_attention = models.IntegerField(default=0)
    
    # Inspection stats
    total_inspections_conducted = models.IntegerField(default=0)
    inspections_this_month = models.IntegerField(default=0)
    pending_inspections = models.IntegerField(default=0)
    
    # Performance overview
    average_teacher_score = models.FloatField(default=0.0)
    teachers_improving = models.IntegerField(default=0)
    teachers_declining = models.IntegerField(default=0)
    
    # Recent activity
    last_inspection_date = models.DateField(null=True, blank=True)
    pending_reviews = models.IntegerField(default=0)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Delegation Dashboard Stats'
        verbose_name_plural = 'Delegation Dashboard Stats'
    
    def __str__(self):
        return f"Dashboard stats for {self.delegator.username}"
    
    def refresh_stats(self):
        """Recalculate all dashboard statistics"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Get all teachers in Delegator's school(s)
        teachers = User.objects.filter(
            role='teacher',
            school=self.delegator.school
        )
        
        self.total_teachers_assigned = teachers.count()
        
        # Count teachers needing attention
        self.teachers_needing_attention = DelegationTeacherMetrics.objects.filter(
            teacher__in=teachers,
            needs_attention=True
        ).count()
        
        # Inspection stats
        inspections = TeacherInspection.objects.filter(delegator=self.delegator)
        self.total_inspections_conducted = inspections.filter(status='completed').count()
        self.pending_inspections = inspections.filter(status__in=['scheduled', 'in_progress']).count()
        
        # This month's inspections
        first_of_month = timezone.now().replace(day=1).date()
        self.inspections_this_month = inspections.filter(
            scheduled_date__gte=first_of_month,
            status='completed'
        ).count()
        
        # Performance overview
        metrics = DelegationTeacherMetrics.objects.filter(teacher__in=teachers)
        if metrics.exists():
            avg_scores = [m.average_inspection_score for m in metrics if m.average_inspection_score > 0]
            self.average_teacher_score = sum(avg_scores) / len(avg_scores) if avg_scores else 0.0
            
            self.teachers_improving = metrics.filter(improvement_trend='improving').count()
            self.teachers_declining = metrics.filter(improvement_trend='declining').count()
        
        # Recent activity
        last_inspection = inspections.filter(status='completed').order_by('-completed_at').first()
        if last_inspection:
            self.last_inspection_date = last_inspection.completed_at.date()
        
        # Pending reviews (completed inspections without reviews)
        self.pending_reviews = inspections.filter(
            status='completed',
            review__isnull=True
        ).count()
        
        self.save()


# ============================================================
# NOTIFICATION SYSTEM
# ============================================================

class Notification(models.Model):
    """
    General notification system for all users
    """
    NOTIFICATION_TYPES = [
        ('inspection_scheduled', 'Inspection Scheduled'),
        ('inspection_started', 'Inspection Started'),
        ('inspection_completed', 'Inspection Completed'),
        ('inspection_cancelled', 'Inspection Cancelled'),
        ('review_submitted', 'Review Submitted'),
        ('advisor_assigned', 'Advisor Assigned to Teacher'),
        ('message_received', 'Message Received'),
        ('test_submitted', 'Test Submitted'),
        ('test_reviewed', 'Test Reviewed'),
        ('general', 'General Notification'),
    ]
    
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Optional link to related object
    related_object_type = models.CharField(max_length=50, blank=True, help_text='e.g., inspection, review, test')
    related_object_id = models.IntegerField(null=True, blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', 'created_at']),
        ]
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
    
    def __str__(self):
        return f"{self.recipient.username}: {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


# ATTENDANCE SYSTEM

class TeacherAttendance(models.Model):
    """
    Daily attendance record for teachers
    Teachers mark their own attendance and can report planned absences
    """
    ATTENDANCE_STATUS = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('planned_absence', 'Planned Absence'),
    ]
    
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'teacher'},
        related_name='teacher_attendance'
    )
    date = models.DateField()
    status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS, default='absent')
    
    # Time tracking
    check_in_time = models.TimeField(null=True, blank=True, help_text='Time teacher marked present')
    check_out_time = models.TimeField(null=True, blank=True, help_text='Time teacher marked departure')
    
    # For planned absences
    reason = models.TextField(blank=True, help_text='Reason for absence (sick leave, training, etc.)')
    is_planned = models.BooleanField(default=False, help_text='Was this absence reported in advance?')
    planned_at = models.DateTimeField(null=True, blank=True, help_text='When the absence was reported')
    
    # For verification
    verified_by_delegator = models.BooleanField(default=False)
    verified_by_advisor = models.BooleanField(default=False)
    delegator_notes = models.TextField(blank=True)
    advisor_notes = models.TextField(blank=True)
    
    # Link to teaching plan if exists
    teaching_plan = models.ForeignKey(
        'core.TeachingPlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_records'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['teacher', 'date']
        indexes = [
            models.Index(fields=['teacher', 'date']),
            models.Index(fields=['date', 'status']),
        ]
        verbose_name = 'Teacher Attendance'
        verbose_name_plural = 'Teacher Attendance Records'
    
    def __str__(self):
        return f"{self.teacher.get_full_name() or self.teacher.username} - {self.date} - {self.get_status_display()}"


class TeacherTimetable(models.Model):
    """
    Weekly schedule/timetable for teachers
    Defines expected working hours for automatic attendance tracking
    """
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'teacher'},
        related_name='timetables'
    )
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField(help_text='Expected check-in time')
    end_time = models.TimeField(help_text='Expected check-out time')
    is_active = models.BooleanField(default=True, help_text='Whether this schedule is currently active')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'director'},
        related_name='timetables_created'
    )
    
    class Meta:
        ordering = ['teacher', 'day_of_week', 'start_time']
        unique_together = ['teacher', 'day_of_week']
        indexes = [
            models.Index(fields=['teacher', 'day_of_week']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.get_day_of_week_display()} ({self.start_time}-{self.end_time})"
    
    def is_within_schedule(self, check_time):
        """Check if a given time falls within this schedule"""
        return self.start_time <= check_time <= self.end_time


class StudentAttendance(models.Model):
    """
    Daily attendance record for students
    Marked by teachers, only if teacher is present
    """
    ATTENDANCE_STATUS = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused Absence'),
    ]
    
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'},
        related_name='student_attendance'
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'teacher'},
        related_name='students_marked_by_teacher'
    )
    date = models.DateField()
    status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS, default='absent')
    
    # Time tracking
    marked_at = models.DateTimeField(auto_now_add=True, help_text='When attendance was marked')
    
    # Notes
    notes = models.TextField(blank=True, help_text='Additional notes about attendance')
    
    # Link to teacher's attendance
    teacher_attendance = models.ForeignKey(
        TeacherAttendance,
        on_delete=models.CASCADE,
        related_name='student_attendance_records',
        null=True,
        blank=True
    )
    
    # Link to lesson if exists
    lesson = models.ForeignKey(
        'core.Lesson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_records'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', 'student__username']
        unique_together = ['student', 'teacher', 'date']
        indexes = [
            models.Index(fields=['student', 'date']),
            models.Index(fields=['teacher', 'date']),
            models.Index(fields=['date', 'status']),
        ]
        verbose_name = 'Student Attendance'
        verbose_name_plural = 'Student Attendance Records'
    
    def __str__(self):
        return f"{self.student.get_full_name() or self.student.username} - {self.date} - {self.get_status_display()}"


class AttendanceSummary(models.Model):
    """
    Monthly summary of attendance statistics
    Auto-generated for reporting
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_summaries')
    month = models.DateField(help_text='First day of the month')
    
    # Statistics
    total_days = models.IntegerField(default=0)
    present_days = models.IntegerField(default=0)
    absent_days = models.IntegerField(default=0)
    late_days = models.IntegerField(default=0)
    excused_days = models.IntegerField(default=0)
    
    # Calculated fields
    attendance_rate = models.FloatField(default=0.0, help_text='Percentage of present days')
    
    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-month', 'user__username']
        unique_together = ['user', 'month']
        verbose_name = 'Attendance Summary'
        verbose_name_plural = 'Attendance Summaries'
    
    def __str__(self):
        return f"{self.user.username} - {self.month.strftime('%B %Y')} - {self.attendance_rate}%"
    
    def refresh_stats(self):
        """Recalculate attendance statistics"""
        from django.db.models import Count, Q
        from datetime import datetime, timedelta
        
        # Get first and last day of month
        first_day = self.month
        if first_day.month == 12:
            last_day = datetime(first_day.year + 1, 1, 1).date() - timedelta(days=1)
        else:
            last_day = datetime(first_day.year, first_day.month + 1, 1).date() - timedelta(days=1)
        
        # Get attendance records for the month
        if self.user.role == 'teacher':
            records = TeacherAttendance.objects.filter(
                teacher=self.user,
                date__gte=first_day,
                date__lte=last_day
            )
        else:  # student
            records = StudentAttendance.objects.filter(
                student=self.user,
                date__gte=first_day,
                date__lte=last_day
            )
        
        # Count by status
        self.total_days = records.count()
        self.present_days = records.filter(status='present').count()
        self.absent_days = records.filter(status='absent').count()
        self.late_days = records.filter(status='late').count()
        self.excused_days = records.filter(Q(status='excused') | Q(status='planned_absence')).count()
        
        # Calculate attendance rate
        if self.total_days > 0:
            self.attendance_rate = round((self.present_days / self.total_days) * 100, 2)
        else:
            self.attendance_rate = 0.0
        
        self.save()


class InspectorAssignment(models.Model):
    """
    Track inspector assignments to schools based on:
    - Primary schools: by region/district (e.g., Tunis 1, Sfax 1)
    - Middle/Secondary schools: by subject
    """
    ASSIGNMENT_TYPE_CHOICES = [
        ('region', 'Regional Assignment (Primary Schools)'),
        ('subject', 'Subject Assignment (Middle/Secondary Schools)'),
    ]
    
    SCHOOL_LEVEL_CHOICES = [
        ('primary', 'Primary (E.PRIMAIRE)'),
        ('middle', 'Middle (E.PREP, E.PREP.TECH)'),
        ('secondary', 'Secondary (LYCEE)'),
    ]
    
    inspector = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='inspector_assignments',
        limit_choices_to={'role': 'inspector'},
        help_text='Inspector being assigned'
    )
    
    # Assignment type determines how inspector is assigned
    assignment_type = models.CharField(
        max_length=10,
        choices=ASSIGNMENT_TYPE_CHOICES,
        help_text='Type of assignment: by region or by subject'
    )
    
    # For primary schools - assign by region
    assigned_region = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Region/District (CRE) for primary schools (e.g., Tunis 1, Sfax 1)'
    )
    
    # For middle/secondary schools - assign by subject
    assigned_subject = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=User.SUBJECT_CHOICES,
        help_text='Subject for middle/secondary schools'
    )
    
    # School level this assignment applies to
    school_level = models.CharField(
        max_length=20,
        choices=SCHOOL_LEVEL_CHOICES,
        help_text='School level this assignment applies to'
    )
    
    # Assignment metadata
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='inspector_assignments_made',
        limit_choices_to={'role__in': ['minister', 'secretary']},
        help_text='Minister or secretary who made the assignment'
    )
    
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this assignment is currently active'
    )
    
    notes = models.TextField(
        blank=True,
        help_text='Additional notes about this assignment'
    )
    
    class Meta:
        ordering = ['-assigned_at']
        verbose_name = 'Inspector Assignment'
        verbose_name_plural = 'Inspector Assignments'
        # Ensure unique active assignments
        unique_together = [
            ['inspector', 'assignment_type', 'assigned_region', 'school_level', 'is_active'],
            ['inspector', 'assignment_type', 'assigned_subject', 'school_level', 'is_active'],
        ]
    
    def __str__(self):
        if self.assignment_type == 'region':
            return f"{self.inspector.username} → {self.assigned_region} ({self.get_school_level_display()})"
        else:
            return f"{self.inspector.username} → {self.get_assigned_subject_display()} ({self.get_school_level_display()})"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validate that the appropriate field is set based on assignment_type
        if self.assignment_type == 'region':
            if not self.assigned_region:
                raise ValidationError({
                    'assigned_region': 'Region is required for regional assignments'
                })
            if self.school_level != 'primary':
                raise ValidationError({
                    'school_level': 'Regional assignments are only for primary schools'
                })
            # Clear subject field
            self.assigned_subject = None
            
        elif self.assignment_type == 'subject':
            if not self.assigned_subject:
                raise ValidationError({
                    'assigned_subject': 'Subject is required for subject-based assignments'
                })
            if self.school_level == 'primary':
                raise ValidationError({
                    'school_level': 'Subject assignments are only for middle/secondary schools'
                })
            # Clear region field
            self.assigned_region = None
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def get_assigned_schools(self):
        """Get schools that match this inspector's assignment"""
        if self.assignment_type == 'region':
            # Primary schools in the assigned region
            return School.objects.filter(
                cre__iexact=self.assigned_region,
                school_type='E.PRIMAIRE'
            )
        else:
            # Middle/Secondary schools (need to check teachers' subjects)
            if self.school_level == 'middle':
                school_types = ['E.PREP', 'E.PREP.TECH']
            else:  # secondary
                school_types = ['LYCEE']
            
            # Get schools that have teachers teaching this subject
            from django.db.models import Q
            return School.objects.filter(
                school_type__in=school_types,
                users__role='teacher',
                users__subjects__contains=[self.assigned_subject]
            ).distinct()


class Task(models.Model):
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    owner = models.CharField(max_length=255, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='high')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='not_started')
    due_date = models.DateField(blank=True, null=True)
    tags = models.JSONField(default=list, blank=True, help_text='List of tag strings for flexible categorization')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title

class Meeting(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('followup_pending', 'Follow-up Pending'),
    ]

    title = models.CharField(max_length=255)
    agenda = models.TextField(blank=True, null=True)
    organizer = models.CharField(max_length=255, blank=True)
    meeting_type = models.CharField(max_length=100, blank=True)
    meeting_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    followup_completed = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meetings')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-meeting_date']

    def __str__(self):
        return self.title


# Secretary Dashboard: Decisions & Documents
class Decision(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('in_review', 'In Review'),
        ('in_implementation', 'In Implementation'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
    ]

    ref = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    sector = models.CharField(max_length=100)
    unit = models.CharField(max_length=150)
    deadline = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    progress = models.IntegerField(default=0)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='decisions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.ref} - {self.title}"


class Document(models.Model):
    STAGE_CHOICES = [
        ('received', 'Received'),
        ('processing', 'Processing'),
        ('waiting_signature', 'Waiting Signature'),
        ('archived', 'Archived'),
    ]

    ref = models.CharField(max_length=50, unique=True)
    document_type = models.CharField(max_length=100)
    origin = models.CharField(max_length=150)
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='received')
    deadline = models.DateField(null=True, blank=True)
    is_urgent = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.ref} - {self.document_type}"
