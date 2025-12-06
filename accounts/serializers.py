from rest_framework import serializers
from .models import (
    School, User, TeacherStudentRelationship, AdvisorReview, GroupChat, ChatMessage,
    ParentStudentRelationship, ParentTeacherChat, ParentTeacherMessage,
    TeacherProgress, ChapterProgressNotification, TeacherAnalytics, TeacherGradeAssignment,
    TeacherTimetable, InspectorAssignment
)

class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'first_name', 'last_name', 'role', 'school', 'school_name',
                  'date_of_birth', 'phone', 'subjects', 'gender', 'grade_level', 'is_active', 'assigned_delegation', 'assigned_region')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate_subjects(self, value):
        """Validate that teachers have 1-3 subjects and advisors have exactly 1 subject"""
        role = self.initial_data.get('role')
        
        if role == 'teacher':
            if not value:
                raise serializers.ValidationError("Teachers must select at least one subject")
            if len(value) > 3:
                raise serializers.ValidationError("Teachers can select up to 3 subjects")
        elif role == 'advisor':
            if not value:
                raise serializers.ValidationError("Advisors must select exactly one subject")
            if len(value) != 1:
                raise serializers.ValidationError("Advisors must select exactly one subject")
        
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserBasicSerializer(serializers.ModelSerializer):
    """Simplified user serializer for nested relationships"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'role', 'subjects')
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class TeacherStudentRelationshipSerializer(serializers.ModelSerializer):
    teacher_info = UserBasicSerializer(source='teacher', read_only=True)
    student_info = UserBasicSerializer(source='student', read_only=True)
    average_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = TeacherStudentRelationship
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_average_rating(self, obj):
        return obj.get_average_rating()
    
    def validate(self, data):
        """Ensure teacher and student are from the same school"""
        teacher = data.get('teacher')
        student = data.get('student')
        
        if teacher and student:
            if teacher.school_id != student.school_id:
                raise serializers.ValidationError(
                    "Teacher and student must be from the same school"
                )
            if teacher.role != 'teacher':
                raise serializers.ValidationError("The teacher must have the 'teacher' role")
            if student.role != 'student':
                raise serializers.ValidationError("The student must have the 'student' role")
        
        return data


class AdvisorReviewSerializer(serializers.ModelSerializer):
    advisor_info = UserBasicSerializer(source='advisor', read_only=True)
    target_title = serializers.SerializerMethodField()
    teacher_username = serializers.SerializerMethodField()
    
    class Meta:
        model = AdvisorReview
        fields = '__all__'
        read_only_fields = ('advisor', 'created_at', 'updated_at')
    
    def get_target_title(self, obj):
        """Get the title/name of the reviewed content"""
        if obj.lesson:
            return obj.lesson.title
        elif obj.mcq_test:
            return f"MCQ Test: {obj.mcq_test.lesson.title}"
        elif obj.qa_test:
            return f"Q&A Test: {obj.qa_test.lesson.title}"
        return "Unknown"
    
    def get_teacher_username(self, obj):
        """Get the username of the teacher who created the content"""
        if obj.lesson:
            return obj.lesson.created_by.username
        elif obj.mcq_test:
            return obj.mcq_test.lesson.created_by.username
        elif obj.qa_test:
            return obj.qa_test.lesson.created_by.username
        return "Unknown"
    
    def validate(self, data):
        """Ensure exactly one target is set and advisor subject matches"""
        lesson = data.get('lesson')
        mcq_test = data.get('mcq_test')
        qa_test = data.get('qa_test')
        
        targets = [t for t in [lesson, mcq_test, qa_test] if t is not None]
        if len(targets) != 1:
            raise serializers.ValidationError(
                "Review must target exactly one item (lesson, MCQ test, or Q&A test)"
            )
        
        # Get advisor from request context
        request = self.context.get('request')
        if request and request.user:
            advisor = request.user
            if advisor.role != 'advisor':
                raise serializers.ValidationError("Only advisors can create reviews")
            
            # Check if advisor's subject matches the content subject
            advisor_subject = advisor.subjects[0] if advisor.subjects else None
            
            if lesson and lesson.subject != advisor_subject:
                raise serializers.ValidationError(
                    f"Advisor can only review lessons in their subject: {advisor_subject}"
                )
            elif mcq_test and mcq_test.lesson.subject != advisor_subject:
                raise serializers.ValidationError(
                    f"Advisor can only review tests in their subject: {advisor_subject}"
                )
            elif qa_test and qa_test.lesson.subject != advisor_subject:
                raise serializers.ValidationError(
                    f"Advisor can only review tests in their subject: {advisor_subject}"
                )
        
        return data


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_info = UserBasicSerializer(source='sender', read_only=True)
    file_attachment_url = serializers.SerializerMethodField()
    read_by_users = serializers.SerializerMethodField()
    is_read_by_current_user = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = '__all__'
        read_only_fields = ('sender', 'created_at', 'updated_at', 'is_edited', 'read_by')
    
    def get_read_by_users(self, obj):
        """Get list of usernames who have read this message"""
        return [user.username for user in obj.read_by.all()]
    
    def get_is_read_by_current_user(self, obj):
        """Check if current user has read this message"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.is_read_by(request.user)
        return False
    
    def validate(self, data):
        """Ensure at least message or file attachment is provided"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Validating data: {data}")
        
        message = data.get('message', '').strip()
        file_attachment = data.get('file_attachment')
        
        logger.info(f"Message: '{message}', File: {file_attachment}")
        
        if not message and not file_attachment:
            raise serializers.ValidationError(
                "Either message text or file attachment must be provided"
            )
        
        return data
    
    def get_file_attachment_url(self, obj):
        """Get full URL for file attachment"""
        if obj.file_attachment:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file_attachment.url)
            return obj.file_attachment.url
        return None


class GroupChatSerializer(serializers.ModelSerializer):
    advisor_info = UserBasicSerializer(source='advisor', read_only=True)
    teachers_info = UserBasicSerializer(source='teachers', many=True, read_only=True)
    latest_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    subject_display = serializers.CharField(source='get_subject_display', read_only=True)
    
    class Meta:
        model = GroupChat
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_latest_message(self, obj):
        """Get the latest message in the chat"""
        latest = obj.messages.order_by('-created_at').first()
        return ChatMessageSerializer(latest).data if latest else None
    
    def get_unread_count(self, obj):
        """Get count of unread messages for current user"""
        request = self.context.get('request')
        if request and request.user:
            # Get all messages in the chat that the current user hasn't read (excluding their own)
            unread_messages = obj.messages.exclude(sender=request.user).exclude(read_by=request.user)
            return unread_messages.count()
        return 0
    
    def validate(self, data):
        """Ensure advisor and teachers have matching subjects"""
        advisor = data.get('advisor')
        subject = data.get('subject')
        teachers = data.get('teachers', [])
        
        if advisor:
            if advisor.role != 'advisor':
                raise serializers.ValidationError("Chat must be created by an advisor")
            
            advisor_subject = advisor.subjects[0] if advisor.subjects else None
            if advisor_subject != subject:
                raise serializers.ValidationError(
                    f"Chat subject must match advisor's subject: {advisor_subject}"
                )
        
        # Validate all teachers teach the same subject
        for teacher in teachers:
            if teacher.role != 'teacher':
                raise serializers.ValidationError("Only teachers can be added to the chat")
            if subject not in (teacher.subjects or []):
                raise serializers.ValidationError(
                    f"Teacher {teacher.username} does not teach {subject}"
                )
        
        return data


class ParentStudentRelationshipSerializer(serializers.ModelSerializer):
    """Serializer for parent-student relationship"""
    parent_info = UserBasicSerializer(source='parent', read_only=True)
    student_info = UserBasicSerializer(source='student', read_only=True)
    relationship_type_display = serializers.CharField(source='get_relationship_type_display', read_only=True)
    
    class Meta:
        model = ParentStudentRelationship
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class StudentPerformanceSerializer(serializers.Serializer):
    """Aggregated student performance data for parents"""
    student = UserBasicSerializer()
    overall_average = serializers.FloatField()
    total_tests = serializers.IntegerField()
    recent_tests = serializers.ListField()
    portfolio_summary = serializers.DictField()
    assigned_teachers = serializers.ListField()
    strengths = serializers.ListField()
    weaknesses = serializers.ListField()
    xp_points = serializers.IntegerField()
    level = serializers.IntegerField()
    streak_days = serializers.IntegerField()


class ParentTeacherChatSerializer(serializers.ModelSerializer):
    """Serializer for parent-teacher chats"""
    parent_info = UserBasicSerializer(source='parent', read_only=True)
    teacher_info = UserBasicSerializer(source='teacher', read_only=True)
    student_info = UserBasicSerializer(source='student', read_only=True)
    subject_display = serializers.CharField(source='get_subject_display', read_only=True)
    latest_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ParentTeacherChat
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_latest_message(self, obj):
        """Get the latest message in the chat"""
        latest = obj.messages.order_by('-created_at').first()
        return ParentTeacherMessageSerializer(latest).data if latest else None
    
    def get_unread_count(self, obj):
        """Get count of unread messages for current user"""
        request = self.context.get('request')
        if request and request.user:
            return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
        return 0


class ParentTeacherMessageSerializer(serializers.ModelSerializer):
    """Serializer for parent-teacher messages"""
    sender_info = UserBasicSerializer(source='sender', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ParentTeacherMessage
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'sender', 'is_edited')
    
    def get_file_url(self, obj):
        """Get full URL for file attachment"""
        if obj.file_attachment:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file_attachment.url)
        return None


class TeacherProgressSerializer(serializers.ModelSerializer):
    teacher_info = UserBasicSerializer(source='teacher', read_only=True)
    subject_display = serializers.CharField(source='get_subject_display', read_only=True)
    grade_level_display = serializers.CharField(source='get_grade_level_display', read_only=True)
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = TeacherProgress
        fields = '__all__'
        read_only_fields = ('started_at', 'updated_at')
    
    def get_progress_percentage(self, obj):
        return obj.get_progress_percentage()


class ChapterProgressNotificationSerializer(serializers.ModelSerializer):
    teacher_progress_info = TeacherProgressSerializer(source='teacher_progress', read_only=True)
    advisor_info = UserBasicSerializer(source='advisor', read_only=True)
    teacher_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ChapterProgressNotification
        fields = '__all__'
        read_only_fields = ('created_at', 'reviewed_at')
    
    def get_teacher_info(self, obj):
        return UserBasicSerializer(obj.teacher_progress.teacher).data


class TeacherAnalyticsSerializer(serializers.ModelSerializer):
    teacher_info = UserBasicSerializer(source='teacher', read_only=True)
    
    class Meta:
        model = TeacherAnalytics
        fields = '__all__'
        read_only_fields = ('updated_at',)


# Administrator Serializers
class AdminUserDetailSerializer(serializers.ModelSerializer):
    """Comprehensive user details for administrator view"""
    school_name = serializers.CharField(source='school.name', read_only=True)
    full_name = serializers.SerializerMethodField()
    
    # Teacher-specific stats
    total_students = serializers.SerializerMethodField()
    total_lessons_created = serializers.SerializerMethodField()
    total_tests_created = serializers.SerializerMethodField()
    average_rating_from_students = serializers.SerializerMethodField()
    
    # Student-specific stats
    total_teachers = serializers.SerializerMethodField()
    total_lessons_completed = serializers.SerializerMethodField()
    total_tests_taken = serializers.SerializerMethodField()
    
    # Advisor-specific stats
    total_teachers_supervised = serializers.SerializerMethodField()
    total_reviews_given = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = '__all__'
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    
    def get_total_students(self, obj):
        if obj.role == 'teacher':
            return obj.student_relationships.filter(is_active=True).count()
        return None
    
    def get_total_lessons_created(self, obj):
        if obj.role == 'teacher':
            from core.models import Lesson
            return Lesson.objects.filter(created_by=obj).count()
        return None
    
    def get_total_tests_created(self, obj):
        if obj.role == 'teacher':
            from core.models import Test, QATest
            mcq_count = Test.objects.filter(created_by=obj).count()
            qa_count = QATest.objects.filter(created_by=obj).count()
            return mcq_count + qa_count
        return None
    
    def get_average_rating_from_students(self, obj):
        if obj.role == 'teacher':
            relationships = obj.student_relationships.filter(rating_by_student__isnull=False)
            if relationships.exists():
                total = sum([r.rating_by_student for r in relationships])
                return round(total / relationships.count(), 2)
        return None
    
    def get_total_teachers(self, obj):
        if obj.role == 'student':
            return obj.teacher_relationships.filter(is_active=True).count()
        return None
    
    def get_total_lessons_completed(self, obj):
        if obj.role == 'student':
            from core.models import Progress
            return Progress.objects.filter(student=obj, completed_at__isnull=False).count()
        return None
    
    def get_total_tests_taken(self, obj):
        if obj.role == 'student':
            from core.models import TestSubmission, QASubmission
            mcq_count = TestSubmission.objects.filter(student=obj).count()
            qa_count = QASubmission.objects.filter(student=obj).count()
            return mcq_count + qa_count
        return None
    
    def get_total_teachers_supervised(self, obj):
        if obj.role == 'advisor':
            # Count teachers in same subject
            if obj.subjects:
                advisor_subject = obj.subjects[0]
                # Get all teachers in the school
                all_teachers = User.objects.filter(
                    role='teacher',
                    school=obj.school
                )
                # Filter by subject using Python (SQLite doesn't support JSON __contains)
                matching_teachers = [
                    t for t in all_teachers 
                    if t.subjects and advisor_subject in t.subjects
                ]
                return len(matching_teachers)
        return None
    
    def get_total_reviews_given(self, obj):
        if obj.role == 'advisor':
            return obj.advisor_reviews.count()
        return None


class AdminSchoolStatsSerializer(serializers.ModelSerializer):
    """School statistics for administrator dashboard"""
    total_users = serializers.SerializerMethodField()
    total_teachers = serializers.SerializerMethodField()
    total_students = serializers.SerializerMethodField()
    total_advisors = serializers.SerializerMethodField()
    total_parents = serializers.SerializerMethodField()
    total_lessons = serializers.SerializerMethodField()
    total_tests = serializers.SerializerMethodField()
    avg_teacher_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = School
        fields = '__all__'
    
    def get_total_users(self, obj):
        return obj.users.count()
    
    def get_total_teachers(self, obj):
        return obj.users.filter(role='teacher').count()
    
    def get_total_students(self, obj):
        return obj.users.filter(role='student').count()
    
    def get_total_advisors(self, obj):
        return obj.users.filter(role='advisor').count()
    
    def get_total_parents(self, obj):
        return obj.users.filter(role='parent').count()
    
    def get_total_lessons(self, obj):
        from core.models import Lesson
        return Lesson.objects.filter(created_by__school=obj).count()
    
    def get_total_tests(self, obj):
        from core.models import Test, QATest
        mcq_count = Test.objects.filter(created_by__school=obj).count()
        qa_count = QATest.objects.filter(created_by__school=obj).count()
        return mcq_count + qa_count
    
    def get_avg_teacher_rating(self, obj):
        from django.db.models import Avg
        teachers = obj.users.filter(role='teacher')
        ratings = []
        for teacher in teachers:
            relationships = teacher.student_relationships.filter(rating_by_student__isnull=False)
            if relationships.exists():
                avg = relationships.aggregate(Avg('rating_by_student'))['rating_by_student__avg']
                if avg:
                    ratings.append(avg)
        if ratings:
            return round(sum(ratings) / len(ratings), 2)
        return None


class AdminAdvisorPerformanceSerializer(serializers.Serializer):
    """Advisor performance metrics for administrator"""
    advisor_id = serializers.IntegerField()
    advisor_name = serializers.CharField()
    advisor_subject = serializers.CharField()
    total_teachers_supervised = serializers.IntegerField()
    total_reviews_given = serializers.IntegerField()
    total_notifications_reviewed = serializers.IntegerField()
    average_response_time_hours = serializers.FloatField()
    teachers_list = serializers.ListField(child=serializers.DictField())


class AdminTeacherPerformanceSerializer(serializers.Serializer):
    """Teacher performance metrics for administrator"""
    teacher_id = serializers.IntegerField()
    teacher_name = serializers.CharField()
    subjects = serializers.ListField()
    total_students = serializers.IntegerField()
    total_lessons_created = serializers.IntegerField()
    total_tests_created = serializers.IntegerField()
    avg_rating = serializers.FloatField()
    advisor_name = serializers.CharField()
    latest_advisor_review = serializers.CharField(allow_null=True)
    progress_percentage = serializers.FloatField()


class TeacherGradeAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for teacher-grade assignments"""
    teacher_info = UserBasicSerializer(source='teacher', read_only=True)
    assigned_by_info = UserBasicSerializer(source='assigned_by', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    grade_level_display = serializers.CharField(source='get_grade_level_display', read_only=True)
    subject_display = serializers.CharField(source='get_subject_display', read_only=True)
    
    class Meta:
        model = TeacherGradeAssignment
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'assigned_by', 'school')
    
    def validate(self, data):
        """Validate teacher and subject match"""
        teacher = data.get('teacher')
        subject = data.get('subject')
        
        # Get school from context (set by view)
        request = self.context.get('request')
        school = request.user.school if request and hasattr(request.user, 'school') else data.get('school')
        
        if teacher:
            if teacher.role != 'teacher':
                raise serializers.ValidationError("Selected user must have 'teacher' role")
            
            # Validate teacher belongs to director's school
            if school and teacher.school != school:
                raise serializers.ValidationError(
                    f"Teacher must belong to your school ({school.name})"
                )
            
            # Validate teacher actually teaches this subject
            if subject and subject not in (teacher.subjects or []):
                raise serializers.ValidationError(
                    f"Teacher {teacher.username} does not teach {subject}. Their subjects are: {', '.join(teacher.subjects or [])}"
                )
        
        return data


class TeacherTimetableSerializer(serializers.ModelSerializer):
    """Serializer for teacher timetables/schedules"""
    teacher_info = UserBasicSerializer(source='teacher', read_only=True)
    created_by_info = UserBasicSerializer(source='created_by', read_only=True)
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = TeacherTimetable
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by')
    
    def validate(self, data):
        """Validate timetable data"""
        teacher = data.get('teacher')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        day_of_week = data.get('day_of_week')
        
        # Validate end time is after start time
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({
                'end_time': 'End time must be after start time'
            })
        
        # Validate teacher role
        if teacher and teacher.role != 'teacher':
            raise serializers.ValidationError({
                'teacher': 'Selected user must have teacher role'
            })
        
        # Validate teacher belongs to director's school
        request = self.context.get('request')
        if request and hasattr(request.user, 'school') and teacher:
            if teacher.school != request.user.school:
                raise serializers.ValidationError({
                    'teacher': f'Teacher must belong to your school ({request.user.school.name})'
                })
        
        # Check for overlapping schedules on the same day
        if teacher and day_of_week is not None and start_time and end_time:
            overlapping = TeacherTimetable.objects.filter(
                teacher=teacher,
                day_of_week=day_of_week,
                is_active=True
            ).exclude(id=self.instance.id if self.instance else None)
            
            for schedule in overlapping:
                # Check if time ranges overlap
                if not (end_time <= schedule.start_time or start_time >= schedule.end_time):
                    raise serializers.ValidationError({
                        'start_time': f'Schedule overlaps with existing timetable ({schedule.start_time}-{schedule.end_time})'
                    })
        
        return data


class InspectorAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for inspector assignments"""
    inspector_info = UserBasicSerializer(source='inspector', read_only=True)
    assigned_by_info = UserBasicSerializer(source='assigned_by', read_only=True)
    assignment_type_display = serializers.CharField(source='get_assignment_type_display', read_only=True)
    school_level_display = serializers.CharField(source='get_school_level_display', read_only=True)
    assigned_subject_display = serializers.CharField(source='get_assigned_subject_display', read_only=True)
    total_schools = serializers.SerializerMethodField()
    
    class Meta:
        model = InspectorAssignment
        fields = '__all__'
        read_only_fields = ('assigned_at', 'updated_at', 'assigned_by')
    
    def get_total_schools(self, obj):
        """Get count of schools matching this assignment"""
        return obj.get_assigned_schools().count()
    
    def validate(self, data):
        """Validate inspector assignment data"""
        inspector = data.get('inspector')
        assignment_type = data.get('assignment_type')
        assigned_region = data.get('assigned_region')
        assigned_subject = data.get('assigned_subject')
        school_level = data.get('school_level')
        
        # Validate inspector role
        if inspector and inspector.role != 'inspector':
            raise serializers.ValidationError({
                'inspector': 'Selected user must have inspector role'
            })
        
        # Validate assignment type matches school level
        if assignment_type == 'region':
            if not assigned_region:
                raise serializers.ValidationError({
                    'assigned_region': 'Region is required for regional assignments'
                })
            if school_level != 'primary':
                raise serializers.ValidationError({
                    'school_level': 'Regional assignments are only for primary schools'
                })
        elif assignment_type == 'subject':
            if not assigned_subject:
                raise serializers.ValidationError({
                    'assigned_subject': 'Subject is required for subject-based assignments'
                })
            if school_level == 'primary':
                raise serializers.ValidationError({
                    'school_level': 'Subject assignments are only for middle/secondary schools'
                })
        
        # Check for duplicate active assignments
        if inspector and data.get('is_active', True):
            from accounts.models import InspectorAssignment
            
            existing = InspectorAssignment.objects.filter(
                inspector=inspector,
                assignment_type=assignment_type,
                school_level=school_level,
                is_active=True
            )
            
            if assignment_type == 'region' and assigned_region:
                existing = existing.filter(assigned_region=assigned_region)
            elif assignment_type == 'subject' and assigned_subject:
                existing = existing.filter(assigned_subject=assigned_subject)
            
            # Exclude current instance if updating
            if self.instance:
                existing = existing.exclude(id=self.instance.id)
            
            if existing.exists():
                raise serializers.ValidationError(
                    'An active assignment with these parameters already exists for this inspector'
                )
        
        return data
