"""
Serializers for Delegation (Inspector/Advisor) functionality
"""
from rest_framework import serializers
from .models import (
    TeacherInspection, InspectionReview,
    DelegationTeacherMetrics, DelegationDashboardStats,
    TeacherAdvisorAssignment, User, School
)
from core.models import Lesson, Test, QATest, TestSubmission, QASubmission


class TeacherBasicSerializer(serializers.ModelSerializer):
    """Basic teacher info for listings"""
    full_name = serializers.SerializerMethodField()
    school_name = serializers.CharField(source='school.name', read_only=True)
    subjects_display = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 
                  'school', 'school_name', 'subjects', 'subjects_display', 'phone']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    
    def get_subjects_display(self, obj):
        if not obj.subjects:
            return []
        subject_dict = dict(User.SUBJECT_CHOICES)
        return [subject_dict.get(s, s) for s in obj.subjects]


class AdvisorBasicSerializer(serializers.ModelSerializer):
    """Basic advisor info for listings"""
    full_name = serializers.SerializerMethodField()
    school_name = serializers.CharField(source='school.name', read_only=True)
    subjects_display = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 
                  'school', 'school_name', 'subjects', 'subjects_display', 'phone']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    
    def get_subjects_display(self, obj):
        if not obj.subjects:
            return []
        subject_dict = dict(User.SUBJECT_CHOICES)
        return [subject_dict.get(s, s) for s in obj.subjects]


class TeacherMetricsSerializer(serializers.ModelSerializer):
    """Teacher performance metrics for Delegation"""
    teacher = TeacherBasicSerializer(read_only=True)
    
    class Meta:
        model = DelegationTeacherMetrics
        fields = '__all__'


class InspectionReviewSerializer(serializers.ModelSerializer):
    """Detailed inspection review"""
    
    class Meta:
        model = InspectionReview
        fields = '__all__'
        read_only_fields = ['overall_score', 'submitted_at', 'updated_at']


class TeacherInspectionSerializer(serializers.ModelSerializer):
    """Teacher inspection with optional review details"""
    teacher = TeacherBasicSerializer(read_only=True)
    teacher_id = serializers.IntegerField(write_only=True)
    teacher_info = TeacherBasicSerializer(source='teacher', read_only=True)
    advisor = AdvisorBasicSerializer(read_only=True)
    advisor_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    advisor_info = AdvisorBasicSerializer(source='advisor', read_only=True)
    delegator_info = serializers.SerializerMethodField()
    delegator_name = serializers.CharField(source='delegator.get_full_name', read_only=True)
    advisor_name = serializers.SerializerMethodField()
    school_name = serializers.CharField(source='school.name', read_only=True)
    school_info = serializers.SerializerMethodField()
    subject_display = serializers.CharField(source='get_subject_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    review = InspectionReviewSerializer(read_only=True)
    has_review = serializers.SerializerMethodField()
    
    class Meta:
        model = TeacherInspection
        fields = '__all__'
        read_only_fields = [
            'delegator', 'school', 'created_at', 'updated_at', 'created_by', 
            'started_at', 'completed_at', 'advisor_started_at', 'advisor_completed_at',
            'start_verified_by_delegator', 'start_verified_at',
            'completion_verified_by_delegator', 'completion_verified_at'
        ]
    
    def get_has_review(self, obj):
        return hasattr(obj, 'review')
    
    def get_advisor_name(self, obj):
        if obj.advisor:
            return obj.advisor.get_full_name() or obj.advisor.username
        return None
    
    def get_delegator_info(self, obj):
        if obj.delegator:
            return {
                'id': obj.delegator.id,
                'username': obj.delegator.username,
                'first_name': obj.delegator.first_name,
                'last_name': obj.delegator.last_name,
                'full_name': obj.delegator.get_full_name() or obj.delegator.username,
            }
        return None
    
    def get_school_info(self, obj):
        if obj.school:
            return {
                'id': obj.school.id,
                'name': obj.school.name,
            }
        return None


class DelegationDashboardStatsSerializer(serializers.ModelSerializer):
    """Dashboard statistics for Delegation"""
    
    class Meta:
        model = DelegationDashboardStats
        fields = '__all__'


class TeacherDetailForDelegationSerializer(serializers.ModelSerializer):
    """Comprehensive teacher details for Delegation inspection view"""
    full_name = serializers.SerializerMethodField()
    school_name = serializers.CharField(source='school.name', read_only=True)
    subjects_display = serializers.SerializerMethodField()
    metrics = TeacherMetricsSerializer(source='delegation_metrics', read_only=True)
    
    # Recent activity
    recent_lessons_count = serializers.SerializerMethodField()
    recent_tests_count = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
    average_student_performance = serializers.SerializerMethodField()
    
    # Inspection history
    total_inspections = serializers.SerializerMethodField()
    latest_inspection = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'school', 'school_name', 'subjects', 'subjects_display', 'phone',
            'date_of_birth', 'metrics', 'recent_lessons_count', 'recent_tests_count',
            'student_count', 'average_student_performance', 'total_inspections',
            'latest_inspection'
        ]
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    
    def get_subjects_display(self, obj):
        if not obj.subjects:
            return []
        subject_dict = dict(User.SUBJECT_CHOICES)
        return [subject_dict.get(s, s) for s in obj.subjects]
    
    def get_recent_lessons_count(self, obj):
        from datetime import timedelta
        from django.utils import timezone
        thirty_days_ago = timezone.now() - timedelta(days=30)
        return Lesson.objects.filter(
            created_by=obj,
            created_at__gte=thirty_days_ago
        ).count()
    
    def get_recent_tests_count(self, obj):
        from datetime import timedelta
        from django.utils import timezone
        thirty_days_ago = timezone.now() - timedelta(days=30)
        mcq_count = Test.objects.filter(
            created_by=obj,
            created_at__gte=thirty_days_ago
        ).count()
        qa_count = QATest.objects.filter(
            created_by=obj,
            created_at__gte=thirty_days_ago
        ).count()
        return mcq_count + qa_count
    
    def get_student_count(self, obj):
        from accounts.models import TeacherStudentRelationship
        return TeacherStudentRelationship.objects.filter(
            teacher=obj,
            is_active=True
        ).count()
    
    def get_average_student_performance(self, obj):
        from accounts.models import TeacherStudentRelationship
        from django.db.models import Avg
        
        # Get students
        student_ids = TeacherStudentRelationship.objects.filter(
            teacher=obj,
            is_active=True
        ).values_list('student_id', flat=True)
        
        if not student_ids:
            return None
        
        # Calculate average from MCQ submissions
        mcq_avg = TestSubmission.objects.filter(
            student_id__in=student_ids,
            is_final=True
        ).aggregate(avg=Avg('score'))['avg']
        
        # Calculate average from Q&A submissions
        qa_avg = QASubmission.objects.filter(
            student_id__in=student_ids,
            status='finalized'
        ).aggregate(avg=Avg('final_score'))['avg']
        
        # Combine averages
        scores = [s for s in [mcq_avg, qa_avg] if s is not None]
        return round(sum(scores) / len(scores), 2) if scores else None
    
    def get_total_inspections(self, obj):
        return TeacherInspection.objects.filter(teacher=obj).count()
    
    def get_latest_inspection(self, obj):
        latest = TeacherInspection.objects.filter(teacher=obj).order_by('-scheduled_date').first()
        if not latest:
            return None
        
        return {
            'id': latest.id,
            'scheduled_date': latest.scheduled_date,
            'status': latest.status,
            'status_display': latest.get_status_display(),
            'has_review': hasattr(latest, 'review'),
            'score': latest.review.overall_score if hasattr(latest, 'review') else None
        }


class CreateInspectionReviewSerializer(serializers.ModelSerializer):
    """Serializer for creating inspection reviews"""
    
    class Meta:
        model = InspectionReview
        exclude = ['overall_score', 'submitted_at', 'updated_at', 'teacher_viewed_at', 
                   'teacher_acknowledged', 'teacher_comments']
    
    def validate(self, data):
        # Ensure inspection exists and doesn't already have a review
        inspection = data.get('inspection')
        if hasattr(inspection, 'review'):
            raise serializers.ValidationError("This inspection already has a review")
        
        if inspection.status != 'completed':
            raise serializers.ValidationError("Can only review completed inspections")
        
        return data
    
    def create(self, validated_data):
        review = super().create(validated_data)
        
        # Update inspection status
        review.inspection.status = 'completed'
        review.inspection.save()
        
        # Update teacher metrics
        teacher = review.inspection.teacher
        metrics, created = DelegationTeacherMetrics.objects.get_or_create(teacher=teacher)
        metrics.update_metrics()
        
        return review


class TeacherAdvisorAssignmentSerializer(serializers.ModelSerializer):
    """Teacher-Advisor assignment with full details"""
    teacher = TeacherBasicSerializer(read_only=True)
    teacher_id = serializers.IntegerField(write_only=True)
    teacher_info = TeacherBasicSerializer(source='teacher', read_only=True)
    advisor = AdvisorBasicSerializer(read_only=True)
    advisor_id = serializers.IntegerField(write_only=True)
    advisor_info = AdvisorBasicSerializer(source='advisor', read_only=True)
    assigned_by_info = serializers.SerializerMethodField()
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    subject_display = serializers.CharField(source='get_subject_display', read_only=True)
    
    class Meta:
        model = TeacherAdvisorAssignment
        fields = '__all__'
        read_only_fields = ['assigned_at', 'updated_at', 'deactivated_at', 'assigned_by', 'school']
    
    def get_assigned_by_info(self, obj):
        if obj.assigned_by:
            return {
                'id': obj.assigned_by.id,
                'username': obj.assigned_by.username,
                'first_name': obj.assigned_by.first_name,
                'last_name': obj.assigned_by.last_name,
                'full_name': obj.assigned_by.get_full_name() or obj.assigned_by.username,
            }
        return None
