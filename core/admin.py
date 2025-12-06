from django.contrib import admin
from .models import (
    Lesson, Test, Progress, Portfolio, TeachingPlan,
    VaultLessonPlan, VaultLessonPlanUsage, VaultComment, YearlyBreakdown,
    VaultExercise, VaultMaterial,
    ForumCategory, ForumTopic, ForumReply, ForumLike, ForumBookmark,
    ForumTag, TopicTag, ForumNotification, StudentNotebook, NotebookPage,
    CNPTeacherGuide,
    Region, InspectorRegionAssignment, TeacherComplaint,
    InspectionVisit, InspectionReport, MonthlyReport, TeacherRatingHistory
)

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'school', 'created_at')
    list_filter = ('school', 'created_at')
    search_fields = ('title', 'content')

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'created_at')
    list_filter = ('lesson__school', 'created_at')
    search_fields = ('title',)

@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'lesson', 'score', 'completed_at')
    list_filter = ('lesson__school', 'completed_at')
    search_fields = ('student__username', 'lesson__title')

@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('student', 'created_at', 'updated_at')
    search_fields = ('student__username', 'summary')


@admin.register(TeachingPlan)
class TeachingPlanAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'subject', 'grade_level', 'date', 'time', 'status')
    list_filter = ('subject', 'grade_level', 'status', 'date', 'teacher')
    search_fields = ('title', 'description', 'teacher__username')
    date_hierarchy = 'date'
    ordering = ('-date', '-time')


@admin.register(VaultLessonPlan)
class VaultLessonPlanAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'grade_level', 'created_by', 'school', 'is_featured', 'view_count', 'use_count', 'created_at')
    list_filter = ('subject', 'grade_level', 'is_active', 'is_featured', 'school', 'created_at')
    search_fields = ('title', 'description', 'content', 'tags', 'created_by__username')
    readonly_fields = ('view_count', 'use_count', 'created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'subject', 'grade_level')
        }),
        ('Content', {
            'fields': ('content', 'objectives', 'materials_needed', 'duration_minutes', 'tags')
        }),
        ('Metadata', {
            'fields': ('created_by', 'school', 'is_active', 'is_featured')
        }),
        ('Statistics', {
            'fields': ('view_count', 'use_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(VaultLessonPlanUsage)
class VaultLessonPlanUsageAdmin(admin.ModelAdmin):
    list_display = ('lesson_plan', 'teacher', 'used_at', 'rating')
    list_filter = ('rating', 'used_at', 'teacher')
    search_fields = ('lesson_plan__title', 'teacher__username', 'notes', 'feedback')
    readonly_fields = ('used_at',)


@admin.register(VaultComment)
class VaultCommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson_plan', 'comment_preview', 'parent_comment', 'created_at', 'is_edited')
    list_filter = ('is_edited', 'created_at', 'user__role')
    search_fields = ('comment', 'user__username', 'lesson_plan__title')
    readonly_fields = ('created_at', 'updated_at')
    
    def comment_preview(self, obj):
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    comment_preview.short_description = 'Comment'


@admin.register(YearlyBreakdown)
class YearlyBreakdownAdmin(admin.ModelAdmin):
    list_display = ('advisor', 'subject', 'grade_level', 'status', 'generated_plans_count', 'created_at')
    list_filter = ('status', 'subject', 'grade_level', 'created_at')
    search_fields = ('advisor__username', 'custom_instructions')
    readonly_fields = ('created_at', 'updated_at', 'processed_at', 'generated_plans_count')
    
    def has_add_permission(self, request):
        # Only allow creation through API
        return False


@admin.register(VaultExercise)
class VaultExerciseAdmin(admin.ModelAdmin):
    list_display = ('title', 'vault_lesson_plan', 'exercise_type', 'difficulty_level', 'num_questions', 'created_by', 'usage_count', 'is_active')
    list_filter = ('exercise_type', 'difficulty_level', 'is_active', 'created_at')
    search_fields = ('title', 'description', 'vault_lesson_plan__title', 'created_by__username')
    readonly_fields = ('usage_count', 'created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('vault_lesson_plan', 'title', 'description', 'exercise_type')
        }),
        ('Exercise Settings', {
            'fields': ('num_questions', 'difficulty_level', 'time_limit')
        }),
        ('Questions', {
            'fields': ('questions',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'is_active', 'usage_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(VaultMaterial)
class VaultMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'vault_lesson_plan', 'material_type', 'created_by', 'download_count', 'file_size_display', 'is_active')
    list_filter = ('material_type', 'is_active', 'created_at')
    search_fields = ('title', 'description', 'vault_lesson_plan__title', 'created_by__username')
    readonly_fields = ('file_size', 'mime_type', 'download_count', 'created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('vault_lesson_plan', 'title', 'description', 'material_type')
        }),
        ('File/Link', {
            'fields': ('file', 'external_link')
        }),
        ('Metadata', {
            'fields': ('file_size', 'mime_type', 'created_by', 'is_active', 'download_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_display(self, obj):
        if obj.file_size:
            # Convert bytes to human-readable format
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "N/A"
    file_size_display.short_description = 'File Size'


# Forum Admin
@admin.register(ForumCategory)
class ForumCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_type', 'order', 'is_active', 'created_at')
    list_filter = ('category_type', 'is_active', 'created_at')
    search_fields = ('name', 'name_ar', 'description')
    ordering = ('order', 'name')


@admin.register(ForumTopic)
class ForumTopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'status', 'is_pinned', 'views_count', 'created_at', 'last_activity')
    list_filter = ('status', 'is_pinned', 'category', 'related_subject', 'created_at')
    search_fields = ('title', 'content', 'author__username')
    readonly_fields = ('views_count', 'created_at', 'updated_at', 'last_activity')
    date_hierarchy = 'created_at'
    ordering = ('-is_pinned', '-last_activity')


@admin.register(ForumReply)
class ForumReplyAdmin(admin.ModelAdmin):
    list_display = ('topic', 'author', 'is_solution', 'is_edited', 'created_at')
    list_filter = ('is_solution', 'is_edited', 'created_at')
    search_fields = ('content', 'author__username', 'topic__title')
    readonly_fields = ('created_at', 'edited_at')
    date_hierarchy = 'created_at'


@admin.register(ForumTag)
class ForumTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_ar', 'usage_count', 'created_at')
    search_fields = ('name', 'name_ar')
    readonly_fields = ('usage_count', 'created_at')
    ordering = ('-usage_count', 'name')


@admin.register(TopicTag)
class TopicTagAdmin(admin.ModelAdmin):
    list_display = ('topic', 'tag', 'created_at')
    list_filter = ('tag', 'created_at')
    search_fields = ('topic__title', 'tag__name')


@admin.register(ForumLike)
class ForumLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_type', 'topic', 'reply', 'created_at')
    list_filter = ('content_type', 'created_at')
    search_fields = ('user__username',)


@admin.register(ForumBookmark)
class ForumBookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'topic', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'topic__title')


@admin.register(ForumNotification)
class ForumNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'topic', 'triggered_by', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'topic__title', 'message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(CNPTeacherGuide)
class CNPTeacherGuideAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'grade_level', 'guide_type', 'status', 'uploaded_by', 'usage_count', 'created_at')
    list_filter = ('subject', 'grade_level', 'guide_type', 'status', 'academic_year', 'created_at')
    search_fields = ('title', 'description', 'keywords', 'topics_covered', 'uploaded_by__username')
    readonly_fields = ('usage_count', 'download_count', 'file_size', 'created_at', 'updated_at', 'approved_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'subject', 'grade_level', 'guide_type', 'academic_year')
        }),
        ('File', {
            'fields': ('pdf_file', 'file_size', 'page_count')
        }),
        ('Metadata', {
            'fields': ('keywords', 'topics_covered', 'learning_objectives'),
            'classes': ('collapse',)
        }),
        ('Status & Tracking', {
            'fields': ('status', 'uploaded_by', 'approved_by', 'approved_at', 'usage_count', 'download_count')
        }),
        ('Notes', {
            'fields': ('cnp_notes', 'admin_notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


# ============================================================
# INSPECTION SYSTEM ADMIN
# ============================================================

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'governorate', 'is_active', 'get_school_count', 'get_inspector_count', 'get_teacher_count']
    list_filter = ['is_active', 'governorate']
    search_fields = ['name', 'code', 'governorate']
    ordering = ['code']
    
    def get_school_count(self, obj):
        return obj.get_school_count()
    get_school_count.short_description = 'Schools'
    
    def get_inspector_count(self, obj):
        return obj.get_inspector_count()
    get_inspector_count.short_description = 'Inspectors'
    
    def get_teacher_count(self, obj):
        return obj.get_teacher_count()
    get_teacher_count.short_description = 'Teachers'


@admin.register(InspectorRegionAssignment)
class InspectorRegionAssignmentAdmin(admin.ModelAdmin):
    list_display = ['inspector', 'region', 'assigned_by', 'assigned_at']
    list_filter = ['region', 'assigned_at']
    search_fields = ['inspector__first_name', 'inspector__last_name', 'region__name']
    raw_id_fields = ['inspector', 'assigned_by']
    ordering = ['-assigned_at']


@admin.register(TeacherComplaint)
class TeacherComplaintAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'title', 'severity', 'status', 'filed_by', 'filed_at', 'resolved_at']
    list_filter = ['severity', 'status', 'filed_at', 'resolved_at']
    search_fields = ['teacher__first_name', 'teacher__last_name', 'title', 'description']
    raw_id_fields = ['teacher', 'filed_by', 'assigned_inspector']
    readonly_fields = ['filed_at', 'resolved_at']
    ordering = ['-filed_at']
    fieldsets = (
        ('Complaint Information', {
            'fields': ('teacher', 'filed_by', 'title', 'description', 'severity', 'status', 'category')
        }),
        ('Investigation', {
            'fields': ('assigned_inspector', 'resolution_notes', 'resolved_at')
        }),
        ('Additional Data', {
            'fields': ('evidence',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('filed_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(InspectionVisit)
class InspectionVisitAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'inspector', 'inspection_type', 'visit_date', 'visit_time', 'status', 'duration_minutes']
    list_filter = ['inspection_type', 'status', 'visit_date']
    search_fields = ['teacher__first_name', 'teacher__last_name', 'inspector__first_name', 'inspector__last_name']
    raw_id_fields = ['teacher', 'inspector', 'related_complaint']
    date_hierarchy = 'visit_date'
    ordering = ['-visit_date', '-visit_time']
    fieldsets = (
        ('Visit Information', {
            'fields': ('teacher', 'inspector', 'school', 'inspection_type', 'related_complaint')
        }),
        ('Schedule', {
            'fields': ('visit_date', 'visit_time', 'duration_minutes', 'status')
        }),
        ('Details', {
            'fields': ('notes', 'cancellation_reason', 'completed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']


@admin.register(InspectionReport)
class InspectionReportAdmin(admin.ModelAdmin):
    list_display = ['get_visit_info', 'get_inspector', 'get_teacher', 'final_rating', 'gpi_status', 'submitted_at', 'gpi_reviewed_at']
    list_filter = ['gpi_status', 'final_rating', 'submitted_at', 'gpi_reviewed_at']
    search_fields = ['teacher__first_name', 'teacher__last_name', 'inspector__first_name', 'summary']
    raw_id_fields = ['visit', 'inspector', 'teacher', 'gpi_reviewer']
    date_hierarchy = 'submitted_at'
    ordering = ['-submitted_at']
    fieldsets = (
        ('Report Information', {
            'fields': ('visit', 'inspector', 'teacher', 'summary')
        }),
        ('Observations', {
            'fields': ('classroom_observations', 'pedagogical_evaluation', 'student_engagement', 'material_quality')
        }),
        ('Evaluation', {
            'fields': ('teacher_strengths', 'improvement_points', 'final_rating')
        }),
        ('Recommendations', {
            'fields': ('recommendations', 'follow_up_required', 'follow_up_date')
        }),
        ('GPI Review', {
            'fields': ('gpi_status', 'gpi_feedback', 'gpi_reviewer', 'gpi_reviewed_at')
        }),
        ('Attachments', {
            'fields': ('attachments',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('submitted_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['submitted_at', 'updated_at', 'gpi_reviewed_at']
    
    def get_visit_info(self, obj):
        return f"{obj.visit.get_inspection_type_display()} - {obj.visit.visit_date}"
    get_visit_info.short_description = 'Visit'
    
    def get_inspector(self, obj):
        return obj.inspector.get_full_name()
    get_inspector.short_description = 'Inspector'
    
    def get_teacher(self, obj):
        return obj.teacher.get_full_name()
    get_teacher.short_description = 'Teacher'


@admin.register(MonthlyReport)
class MonthlyReportAdmin(admin.ModelAdmin):
    list_display = ['inspector', 'get_month_year', 'status', 'total_visits', 'completed_visits', 'get_avg_rating', 'submitted_at']
    list_filter = ['status', 'month', 'submitted_at']
    search_fields = ['inspector__first_name', 'inspector__last_name']
    raw_id_fields = ['inspector', 'gpi_reviewer']
    ordering = ['-month', 'inspector']
    fieldsets = (
        ('Report Information', {
            'fields': ('inspector', 'month')
        }),
        ('Statistics', {
            'fields': ('total_visits', 'completed_visits', 'pending_visits', 'cancelled_visits', 'rating_distribution')
        }),
        ('Analysis', {
            'fields': ('recurring_issues', 'positive_trends', 'challenges_faced', 'recommendations')
        }),
        ('GPI Review', {
            'fields': ('status', 'gpi_feedback', 'gpi_reviewer', 'gpi_reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'submitted_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'submitted_at', 'updated_at', 'gpi_reviewed_at', 'total_visits', 'completed_visits', 'pending_visits', 'cancelled_visits', 'rating_distribution']
    
    def get_month_year(self, obj):
        return obj.month.strftime('%B %Y')
    get_month_year.short_description = 'Month'
    
    def get_avg_rating(self, obj):
        if obj.rating_distribution:
            total_ratings = sum(count for count in obj.rating_distribution.values())
            if total_ratings > 0:
                weighted_sum = sum(int(rating) * count for rating, count in obj.rating_distribution.items())
                return round(weighted_sum / total_ratings, 2)
        return '-'
    get_avg_rating.short_description = 'Avg Rating'


@admin.register(TeacherRatingHistory)
class TeacherRatingHistoryAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'inspection_report', 'rating', 'inspection_date', 'inspector', 'inspection_type']
    list_filter = ['rating', 'inspection_date', 'inspection_type']
    search_fields = ['teacher__first_name', 'teacher__last_name', 'inspector__first_name', 'inspector__last_name']
    raw_id_fields = ['teacher', 'inspection_report', 'inspector']
    date_hierarchy = 'inspection_date'
    ordering = ['-inspection_date']
    readonly_fields = ['teacher', 'inspection_report', 'inspector', 'rating', 'inspection_date', 'inspection_type', 'created_at']
    
    def has_add_permission(self, request):
        # History is auto-generated, prevent manual creation
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Preserve history, prevent deletion
        return False


