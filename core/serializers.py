from rest_framework import serializers
from .models import (
    Lesson, Test, Progress, Portfolio, QATest, QASubmission, TestSubmission, PersonalizedTest,
    TeachingPlan, VaultLessonPlan, VaultLessonPlanUsage, VaultComment, YearlyBreakdown,
    VaultExercise, VaultMaterial, StudentNotebook, NotebookPage, CNPTeacherGuide,
    Region, InspectorRegionAssignment, TeacherComplaint, InspectionVisit,
    InspectionReport, MonthlyReport, TeacherRatingHistory
)

class LessonSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    subject_display = serializers.CharField(source='get_subject_display', read_only=True)
    grade_level_display = serializers.CharField(source='get_grade_level_display', read_only=True)
    vault_source_title = serializers.CharField(source='vault_source.title', read_only=True, allow_null=True)

    class Meta:
        model = Lesson
        fields = '__all__'
        read_only_fields = ('created_by', 'school')
    
    def to_representation(self, instance):
        """Hide lesson content from students - they only see metadata for Q&A test selection"""
        representation = super().to_representation(instance)
        request = self.context.get('request')
        
        if request and hasattr(request, 'user') and request.user.role == 'student':
            # Students only see basic info to select Q&A tests, not the actual lesson plan
            representation['content'] = '[Content hidden for students]'
            representation['objectives'] = '[Objectives hidden for students]'
            representation['materials'] = '[Materials hidden for students]'
        
        return representation

class TestSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True)
    personalized_count = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = '__all__'
        read_only_fields = ('created_by', 'reviewed_by', 'created_at', 'updated_at')
    
    def get_personalized_count(self, obj):
        """Return the number of personalized versions"""
        return obj.personalized_versions.count()

class PersonalizedTestSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    student_full_name = serializers.SerializerMethodField()
    test_title = serializers.CharField(source='base_test.title', read_only=True)
    lesson_title = serializers.CharField(source='base_test.lesson.title', read_only=True)
    question_type = serializers.CharField(source='base_test.question_type', read_only=True)
    
    class Meta:
        model = PersonalizedTest
        fields = '__all__'
        read_only_fields = ('base_test', 'student', 'created_at')
    
    def get_student_full_name(self, obj):
        return obj.student.get_full_name() or obj.student.username

class ProgressSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)

    class Meta:
        model = Progress
        fields = '__all__'
        read_only_fields = ('student',)

class PortfolioSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)

    class Meta:
        model = Portfolio
        fields = '__all__'
        read_only_fields = ('student',)

class TestSubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    test_title = serializers.CharField(source='test.title', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True)

    class Meta:
        model = TestSubmission
        fields = '__all__'
        read_only_fields = ('student', 'submitted_at', 'reviewed_by', 'reviewed_at', 'attempt_number', 'is_final')

class QATestSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True)

    class Meta:
        model = QATest
        fields = '__all__'
        read_only_fields = ('created_by', 'reviewed_by', 'created_at', 'updated_at')

class QASubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    test_title = serializers.CharField(source='test.title', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True)

    class Meta:
        model = QASubmission
        fields = '__all__'
        read_only_fields = ('student', 'submitted_at', 'reviewed_by', 'reviewed_at')


class TeachingPlanSerializer(serializers.ModelSerializer):
    """Serializer for teaching plans/timeline"""
    teacher_name = serializers.CharField(source='teacher.username', read_only=True)
    subject_display = serializers.CharField(source='get_subject_display', read_only=True)
    grade_level_display = serializers.CharField(source='get_grade_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    lesson_title = serializers.CharField(source='lesson.title', read_only=True, allow_null=True)
    
    class Meta:
        model = TeachingPlan
        fields = [
            'id', 'teacher', 'teacher_name', 'title', 'description',
            'subject', 'subject_display', 'grade_level', 'grade_level_display',
            'lesson', 'lesson_title', 'date', 'time', 'status', 'status_display',
            'duration_minutes', 'notes', 'completion_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('teacher', 'created_at', 'updated_at')


class VaultLessonPlanSerializer(serializers.ModelSerializer):
    """Serializer for vault lesson plans"""
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    created_by_full_name = serializers.SerializerMethodField()
    school_name = serializers.CharField(source='school.name', read_only=True)
    subject_display = serializers.CharField(source='get_subject_display', read_only=True)
    grade_level_display = serializers.CharField(source='get_grade_level_display', read_only=True)
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    source_teacher_name = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    exercises_count = serializers.SerializerMethodField()
    materials_count = serializers.SerializerMethodField()
    
    class Meta:
        model = VaultLessonPlan
        fields = [
            'id', 'title', 'description', 'content', 'subject', 'subject_display',
            'grade_level', 'grade_level_display', 'objectives', 'materials_needed',
            'duration_minutes', 'tags', 'grammar', 'vocabulary', 'life_skills_and_values',
            'source_type', 'source_type_display', 'source_teacher', 'source_teacher_name',
            'teacher_guide_file', 'yearly_breakdown_file', 'ai_generation_prompt',
            'created_by', 'created_by_name', 'created_by_full_name', 'school', 'school_name',
            'is_active', 'is_featured', 'view_count', 'use_count', 'comments_count',
            'average_rating', 'exercises_count', 'materials_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ('created_by', 'school', 'view_count', 'use_count', 'created_at', 'updated_at')
    
    def get_created_by_full_name(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.username
    
    def get_source_teacher_name(self, obj):
        if obj.source_teacher:
            return f"{obj.source_teacher.first_name} {obj.source_teacher.last_name}".strip() or obj.source_teacher.username
        return None
    
    def get_comments_count(self, obj):
        return obj.comments.count()
    
    def get_average_rating(self, obj):
        from django.db.models import Avg
        result = obj.usages.filter(rating__isnull=False).aggregate(Avg('rating'))
        return round(result['rating__avg'], 1) if result['rating__avg'] else None
    
    def get_exercises_count(self, obj):
        return obj.exercises.filter(is_active=True).count()
    
    def get_materials_count(self, obj):
        return obj.materials.filter(is_active=True).count()


class VaultLessonPlanUsageSerializer(serializers.ModelSerializer):
    """Serializer for tracking vault lesson plan usage"""
    teacher_name = serializers.CharField(source='teacher.username', read_only=True)
    lesson_plan_title = serializers.CharField(source='lesson_plan.title', read_only=True)
    
    class Meta:
        model = VaultLessonPlanUsage
        fields = [
            'id', 'lesson_plan', 'lesson_plan_title', 'teacher', 'teacher_name',
            'used_at', 'notes', 'rating', 'feedback'
        ]
        read_only_fields = ('teacher', 'used_at')


class VaultCommentSerializer(serializers.ModelSerializer):
    """Serializer for vault comments"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_full_name = serializers.SerializerMethodField()
    user_role = serializers.CharField(source='user.role', read_only=True)
    replies_count = serializers.SerializerMethodField()
    
    class Meta:
        model = VaultComment
        fields = [
            'id', 'lesson_plan', 'user', 'user_name', 'user_full_name', 
            'user_role', 'comment', 'parent_comment', 'replies_count',
            'created_at', 'updated_at', 'is_edited'
        ]
        read_only_fields = ('user', 'created_at', 'updated_at')
    
    def get_user_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username
    
    def get_replies_count(self, obj):
        return obj.replies.count()


class YearlyBreakdownSerializer(serializers.ModelSerializer):
    """Serializer for yearly breakdown generation requests"""
    advisor_name = serializers.CharField(source='advisor.username', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    subject_display = serializers.CharField(source='get_subject_display', read_only=True)
    grade_level_display = serializers.CharField(source='get_grade_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = YearlyBreakdown
        fields = [
            'id', 'advisor', 'advisor_name', 'school', 'school_name',
            'subject', 'subject_display', 'grade_level', 'grade_level_display',
            'input_pdf', 'custom_instructions', 'status', 'status_display',
            'error_message', 'generated_plans_count',
            'created_at', 'updated_at', 'processed_at'
        ]
        read_only_fields = ('advisor', 'school', 'status', 'error_message', 'generated_plans_count', 'processed_at')


class VaultExerciseSerializer(serializers.ModelSerializer):
    """Serializer for vault exercises (MCQ and Q&A)"""
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    created_by_full_name = serializers.SerializerMethodField()
    exercise_type_display = serializers.CharField(source='get_exercise_type_display', read_only=True)
    difficulty_level_display = serializers.CharField(source='get_difficulty_level_display', read_only=True)
    vault_lesson_plan_title = serializers.CharField(source='vault_lesson_plan.title', read_only=True)
    vault_lesson_plan_subject = serializers.CharField(source='vault_lesson_plan.get_subject_display', read_only=True)
    vault_lesson_plan_grade = serializers.CharField(source='vault_lesson_plan.get_grade_level_display', read_only=True)
    
    class Meta:
        model = VaultExercise
        fields = [
            'id', 'vault_lesson_plan', 'vault_lesson_plan_title', 
            'vault_lesson_plan_subject', 'vault_lesson_plan_grade',
            'title', 'description',
            'exercise_type', 'exercise_type_display', 'questions', 'time_limit',
            'num_questions', 'difficulty_level', 'difficulty_level_display',
            'created_by', 'created_by_name', 'created_by_full_name',
            'is_active', 'usage_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ('created_by', 'usage_count', 'created_at', 'updated_at')
    
    def get_created_by_full_name(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.username


class VaultMaterialSerializer(serializers.ModelSerializer):
    """Serializer for vault course materials"""
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    created_by_full_name = serializers.SerializerMethodField()
    material_type_display = serializers.CharField(source='get_material_type_display', read_only=True)
    vault_lesson_plan_title = serializers.CharField(source='vault_lesson_plan.title', read_only=True)
    vault_lesson_plan_subject = serializers.CharField(source='vault_lesson_plan.get_subject_display', read_only=True)
    vault_lesson_plan_grade = serializers.CharField(source='vault_lesson_plan.get_grade_level_display', read_only=True)
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    
    class Meta:
        model = VaultMaterial
        fields = [
            'id', 'vault_lesson_plan', 'vault_lesson_plan_title',
            'vault_lesson_plan_subject', 'vault_lesson_plan_grade',
            'title', 'description',
            'material_type', 'material_type_display', 'file', 'file_url', 'file_name',
            'external_link', 'file_size', 'mime_type',
            'created_by', 'created_by_name', 'created_by_full_name',
            'is_active', 'download_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ('created_by', 'file_size', 'mime_type', 'download_count', 'created_at', 'updated_at')
    
    def get_created_by_full_name(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.username
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
    
    def get_file_name(self, obj):
        if obj.file:
            return obj.file.name.split('/')[-1]
        return None


class NotebookPageSerializer(serializers.ModelSerializer):
    student_name_readonly = serializers.CharField(source='notebook.student.get_full_name', read_only=True)
    student_id = serializers.IntegerField(source='notebook.student.id', read_only=True)
    
    class Meta:
        model = NotebookPage
        fields = [
            'id', 'notebook', 'date', 'lesson_name', 'exercises_set_by_teacher', 
            'exercises_answers', 'notes', 'teacher_viewed', 'teacher_comment', 
            'teacher_viewed_at', 'created_at', 'updated_at', 'student_name_readonly', 'student_id'
        ]
        read_only_fields = ('teacher_viewed', 'teacher_viewed_at', 'created_at', 'updated_at')



class StudentNotebookSerializer(serializers.ModelSerializer):
    student_full_name = serializers.CharField(source='student.get_full_name', read_only=True)
    pages = NotebookPageSerializer(many=True, read_only=True)
    pages_count = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentNotebook
        fields = ['id', 'student', 'student_full_name', 'pages', 'pages_count', 'created_at', 'updated_at']
        read_only_fields = ('student', 'created_at', 'updated_at')
    
    def get_pages_count(self, obj):
        return obj.pages.count()


class CNPTeacherGuideSerializer(serializers.ModelSerializer):
    """Serializer for CNP Teacher Guide uploads"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True, allow_null=True)
    subject_display = serializers.CharField(source='get_subject_display', read_only=True)
    grade_level_display = serializers.CharField(source='get_grade_level_display', read_only=True)
    guide_type_display = serializers.CharField(source='get_guide_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = CNPTeacherGuide
        fields = [
            'id', 'title', 'description', 'subject', 'subject_display',
            'grade_level', 'grade_level_display', 'guide_type', 'guide_type_display',
            'academic_year', 'pdf_file', 'file_url', 'file_name', 'file_size',
            'file_size_mb', 'page_count', 'keywords', 'topics_covered',
            'learning_objectives', 'status', 'status_display', 'uploaded_by',
            'uploaded_by_name', 'uploaded_by_username', 'approved_by',
            'approved_by_name', 'usage_count', 'download_count', 'cnp_notes',
            'admin_notes', 'created_at', 'updated_at', 'approved_at'
        ]
        read_only_fields = ('uploaded_by', 'approved_by', 'usage_count', 'download_count', 
                           'file_size', 'created_at', 'updated_at', 'approved_at')
    
    def get_file_url(self, obj):
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None
    
    def get_file_name(self, obj):
        if obj.pdf_file:
            return obj.pdf_file.name.split('/')[-1]
        return None
    
    def get_file_size_mb(self, obj):
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return None


# ============================================================
# INSPECTION SYSTEM SERIALIZERS
# ============================================================

class RegionSerializer(serializers.ModelSerializer):
    """Serializer for geographic regions"""
    school_count = serializers.SerializerMethodField()
    inspector_count = serializers.SerializerMethodField()
    teacher_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Region
        fields = [
            'id', 'name', 'code', 'governorate', 'is_active',
            'school_count', 'inspector_count', 'teacher_count'
        ]
    
    def get_school_count(self, obj):
        return obj.get_school_count()
    
    def get_inspector_count(self, obj):
        return obj.get_inspector_count()
    
    def get_teacher_count(self, obj):
        return obj.get_teacher_count()


class InspectorRegionAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for inspector-region assignments"""
    inspector_name = serializers.CharField(source='inspector.get_full_name', read_only=True)
    region_name = serializers.CharField(source='region.name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)
    
    class Meta:
        model = InspectorRegionAssignment
        fields = [
            'id', 'inspector', 'inspector_name', 'region', 'region_name',
            'assigned_by', 'assigned_by_name', 'assigned_at'
        ]
        read_only_fields = ('assigned_by', 'assigned_at')


class TeacherComplaintSerializer(serializers.ModelSerializer):
    """Serializer for teacher complaints"""
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    filed_by_name = serializers.CharField(source='filed_by.get_full_name', read_only=True)
    assigned_inspector_name = serializers.CharField(source='assigned_inspector.get_full_name', read_only=True, allow_null=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    related_visits_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TeacherComplaint
        fields = [
            'id', 'teacher', 'teacher_name', 'filed_by', 'filed_by_name',
            'title', 'description', 'severity', 'severity_display',
            'status', 'status_display', 'category', 'evidence',
            'assigned_inspector', 'assigned_inspector_name',
            'resolution_notes', 'filed_at', 'resolved_at', 'related_visits_count'
        ]
        read_only_fields = ('filed_by', 'filed_at', 'resolved_at')
    
    def get_related_visits_count(self, obj):
        return obj.related_visits.count()


class InspectionVisitSerializer(serializers.ModelSerializer):
    """Serializer for inspection visits"""
    inspector_name = serializers.CharField(source='inspector.get_full_name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    teacher_subject = serializers.CharField(source='teacher.subject', read_only=True, allow_null=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    inspection_type_display = serializers.CharField(source='get_inspection_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    related_complaint_title = serializers.CharField(source='related_complaint.title', read_only=True, allow_null=True)
    has_report = serializers.SerializerMethodField()
    can_write_report = serializers.SerializerMethodField()
    
    class Meta:
        model = InspectionVisit
        fields = [
            'id', 'inspector', 'inspector_name', 'teacher', 'teacher_name',
            'teacher_subject', 'school', 'school_name', 'related_complaint',
            'related_complaint_title', 'visit_date', 'visit_time',
            'inspection_type', 'inspection_type_display', 'status', 'status_display',
            'duration_minutes', 'notes', 'cancellation_reason',
            'created_at', 'updated_at', 'completed_at',
            'has_report', 'can_write_report'
        ]
        read_only_fields = ('id', 'inspector', 'school', 'created_at', 'updated_at', 'completed_at')
    
    def get_has_report(self, obj):
        return hasattr(obj, 'report')
    
    def get_can_write_report(self, obj):
        return obj.can_write_report()


class InspectionReportSerializer(serializers.ModelSerializer):
    """Serializer for inspection reports"""
    inspector_name = serializers.CharField(source='inspector.get_full_name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    visit_date = serializers.DateField(source='visit.visit_date', read_only=True)
    visit_type = serializers.CharField(source='visit.get_inspection_type_display', read_only=True)
    gpi_status_display = serializers.CharField(source='get_gpi_status_display', read_only=True)
    gpi_reviewer_name = serializers.CharField(source='gpi_reviewer.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = InspectionReport
        fields = [
            'id', 'visit', 'visit_date', 'visit_type', 'inspector', 'inspector_name',
            'teacher', 'teacher_name', 'summary', 'classroom_observations',
            'pedagogical_evaluation', 'teacher_strengths', 'improvement_points',
            'student_engagement', 'material_quality', 'final_rating',
            'recommendations', 'follow_up_required', 'follow_up_date',
            'attachments', 'gpi_status', 'gpi_status_display',
            'gpi_reviewer', 'gpi_reviewer_name', 'gpi_feedback',
            'gpi_reviewed_at', 'submitted_at', 'updated_at'
        ]
        read_only_fields = ('inspector', 'teacher', 'submitted_at', 'updated_at', 'gpi_reviewed_at', 'gpi_reviewer')
    
    def validate(self, data):
        """Validate that report can be written"""
        visit = data.get('visit')
        if visit and not visit.can_write_report():
            raise serializers.ValidationError({
                'visit': 'Report can only be written for completed visits'
            })
        return data


class InspectionReportDetailSerializer(InspectionReportSerializer):
    """Detailed serializer with visit information"""
    visit_details = InspectionVisitSerializer(source='visit', read_only=True)
    
    class Meta(InspectionReportSerializer.Meta):
        fields = InspectionReportSerializer.Meta.fields + ['visit_details']


class MonthlyReportSerializer(serializers.ModelSerializer):
    """Serializer for monthly reports"""
    inspector_name = serializers.CharField(source='inspector.get_full_name', read_only=True)
    month_year = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    gpi_reviewer_name = serializers.CharField(source='gpi_reviewer.get_full_name', read_only=True, allow_null=True)
    average_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = MonthlyReport
        fields = [
            'id', 'inspector', 'inspector_name', 'month', 'month_year',
            'total_visits', 'completed_visits', 'cancelled_visits', 'pending_visits',
            'rating_distribution', 'average_rating', 'recurring_issues',
            'positive_trends', 'recommendations', 'challenges_faced',
            'status', 'status_display', 'gpi_reviewer', 'gpi_reviewer_name',
            'gpi_feedback', 'gpi_reviewed_at', 'created_at', 'submitted_at', 'updated_at'
        ]
        read_only_fields = ('inspector', 'total_visits', 'completed_visits', 'cancelled_visits',
                           'pending_visits', 'rating_distribution', 'gpi_reviewer',
                           'gpi_reviewed_at', 'created_at', 'submitted_at', 'updated_at')
    
    def get_month_year(self, obj):
        return obj.month.strftime('%B %Y')
    
    def get_average_rating(self, obj):
        if obj.rating_distribution:
            total_ratings = sum(count for count in obj.rating_distribution.values())
            if total_ratings > 0:
                weighted_sum = sum(int(rating) * count for rating, count in obj.rating_distribution.items())
                return round(weighted_sum / total_ratings, 2)
        return None


class TeacherRatingHistorySerializer(serializers.ModelSerializer):
    """Serializer for teacher rating history"""
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    inspector_name = serializers.CharField(source='inspector.get_full_name', read_only=True)
    inspection_type_display = serializers.SerializerMethodField()
    
    class Meta:
        model = TeacherRatingHistory
        fields = [
            'id', 'teacher', 'teacher_name', 'inspector', 'inspector_name',
            'inspection_report', 'rating', 'inspection_date', 'inspection_type',
            'inspection_type_display', 'subject_taught', 'grade_level', 'created_at'
        ]
        read_only_fields = ('teacher', 'inspector', 'inspection_report', 'rating',
                           'inspection_date', 'inspection_type', 'created_at')
    
    def get_inspection_type_display(self, obj):
        # Match the display from InspectionVisit.INSPECTION_TYPE_CHOICES
        type_map = {
            'class_visit': 'Classroom Observation',
            'follow_up': 'Follow-up Visit',
            'complaint_based': 'Complaint Investigation',
            'evaluation_renewal': 'Evaluation Renewal',
            'routine': 'Routine Inspection',
        }
        return type_map.get(obj.inspection_type, obj.inspection_type)


# Lightweight serializers for dashboard statistics
class InspectorDashboardStatsSerializer(serializers.Serializer):
    """Statistics for inspector dashboard"""
    total_visits = serializers.IntegerField()
    completed_visits = serializers.IntegerField()
    pending_visits = serializers.IntegerField()
    upcoming_visits = serializers.IntegerField()
    reports_pending_review = serializers.IntegerField()
    reports_approved = serializers.IntegerField()
    reports_revision_needed = serializers.IntegerField()
    assigned_regions = serializers.ListField(child=serializers.DictField())
    assigned_teachers_count = serializers.IntegerField()
    monthly_report_status = serializers.CharField(allow_null=True)


class GPIDashboardStatsSerializer(serializers.Serializer):
    """Statistics for GPI dashboard"""
    total_inspectors = serializers.IntegerField()
    active_inspectors = serializers.IntegerField()
    total_reports_pending = serializers.IntegerField()
    total_monthly_reports_pending = serializers.IntegerField()
    reports_approved_this_month = serializers.IntegerField()
    reports_rejected_this_month = serializers.IntegerField()
    average_rating_this_month = serializers.FloatField(allow_null=True)
    total_visits_this_month = serializers.IntegerField()
    regions_summary = serializers.ListField(child=serializers.DictField())

