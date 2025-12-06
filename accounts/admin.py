from django.contrib import admin
from .models import (
    School, User, TeacherStudentRelationship, AdvisorReview, GroupChat, ChatMessage,
    ParentStudentRelationship, ParentTeacherChat, ParentTeacherMessage,
    TeacherProgress, ChapterProgressNotification, TeacherAnalytics,
    TeacherAdvisorAssignment, TeacherInspection, InspectionReview, 
    DelegationTeacherMetrics, DelegationDashboardStats, Notification,
    TeacherAttendance, StudentAttendance, AttendanceSummary, TeacherTimetable,
    InspectorAssignment
)

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'created_at')
    search_fields = ('name',)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'school', 'is_active')
    list_filter = ('role', 'school', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('username',)

@admin.register(TeacherStudentRelationship)
class TeacherStudentRelationshipAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'student', 'rating_by_teacher', 'rating_by_student', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'teacher__school')
    search_fields = ('teacher__username', 'student__username')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(AdvisorReview)
class AdvisorReviewAdmin(admin.ModelAdmin):
    list_display = ('advisor', 'review_type', 'rating', 'created_at')
    list_filter = ('review_type', 'rating', 'created_at', 'advisor__subjects')
    search_fields = ('advisor__username', 'remarks')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(GroupChat)
class GroupChatAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'advisor', 'is_active', 'created_at')
    list_filter = ('subject', 'is_active', 'created_at')
    search_fields = ('name', 'advisor__username')
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('teachers',)

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'chat', 'message_preview', 'read_count', 'created_at')
    list_filter = ('created_at', 'chat')
    search_fields = ('sender__username', 'message')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'read_by_list')
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message Preview'
    
    def read_count(self, obj):
        return obj.read_by.count()
    read_count.short_description = 'Read By Count'
    
    def read_by_list(self, obj):
        return ', '.join([user.username for user in obj.read_by.all()])
    read_by_list.short_description = 'Read By Users'


@admin.register(ParentStudentRelationship)
class ParentStudentRelationshipAdmin(admin.ModelAdmin):
    list_display = ('parent', 'student', 'relationship_type', 'is_primary', 'is_active', 'created_at')
    list_filter = ('relationship_type', 'is_primary', 'is_active', 'created_at')
    search_fields = ('parent__username', 'student__username', 'parent__email', 'student__email')
    ordering = ('-is_primary', '-created_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ParentTeacherChat)
class ParentTeacherChatAdmin(admin.ModelAdmin):
    list_display = ('parent', 'teacher', 'student', 'subject', 'is_active', 'created_at')
    list_filter = ('subject', 'is_active', 'created_at')
    search_fields = ('parent__username', 'teacher__username', 'student__username')
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ParentTeacherMessage)
class ParentTeacherMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'chat', 'message_preview', 'is_read', 'is_edited', 'created_at')
    list_filter = ('is_read', 'is_edited', 'created_at')
    search_fields = ('sender__username', 'message')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message Preview'


@admin.register(TeacherProgress)
class TeacherProgressAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'subject', 'grade_level', 'chapter_number', 'total_chapters', 'progress_percentage', 'updated_at')
    list_filter = ('subject', 'grade_level', 'teacher__school')
    search_fields = ('teacher__username', 'current_chapter')
    ordering = ('-updated_at',)
    readonly_fields = ('started_at', 'updated_at')
    
    def progress_percentage(self, obj):
        return f"{obj.get_progress_percentage():.1f}%"
    progress_percentage.short_description = 'Progress'


@admin.register(ChapterProgressNotification)
class ChapterProgressNotificationAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'advisor', 'previous_chapter_number', 'new_chapter_number', 'status', 'ai_confidence', 'created_at')
    list_filter = ('status', 'ai_detected', 'created_at', 'advisor__school')
    search_fields = ('teacher_progress__teacher__username', 'advisor__username', 'new_chapter')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'reviewed_at')
    
    def teacher(self, obj):
        return obj.teacher_progress.teacher.username
    teacher.short_description = 'Teacher'


@admin.register(TeacherAnalytics)
class TeacherAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'overall_rating', 'total_students', 'total_lessons_created', 'total_mcq_tests_created', 'updated_at')
    list_filter = ('teacher__school', 'updated_at')
    search_fields = ('teacher__username',)
    ordering = ('-overall_rating', '-updated_at')
    readonly_fields = ('updated_at',)


# Delegation (Inspector/Advisor) Admin
@admin.register(TeacherAdvisorAssignment)
class TeacherAdvisorAssignmentAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'advisor', 'subject', 'assigned_by', 'is_active', 'assigned_at')
    list_filter = ('is_active', 'subject', 'school', 'assigned_at')
    search_fields = ('teacher__username', 'advisor__username', 'assigned_by__username')
    ordering = ('-assigned_at',)
    readonly_fields = ('assigned_at', 'updated_at', 'deactivated_at')


@admin.register(TeacherInspection)
class TeacherInspectionAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'delegator', 'subject', 'scheduled_date', 'status', 'has_review', 'created_at')
    list_filter = ('status', 'subject', 'school', 'scheduled_date')
    search_fields = ('teacher__username', 'delegator__username', 'purpose')
    ordering = ('-scheduled_date', '-scheduled_time')
    readonly_fields = ('created_at', 'updated_at', 'started_at', 'completed_at')
    
    def has_review(self, obj):
        return hasattr(obj, 'review')
    has_review.boolean = True
    has_review.short_description = 'Has Review'


@admin.register(InspectionReview)
class InspectionReviewAdmin(admin.ModelAdmin):
    list_display = ('inspection_teacher', 'overall_score', 'requires_follow_up', 'teacher_acknowledged', 'submitted_at')
    list_filter = ('requires_follow_up', 'teacher_acknowledged', 'submitted_at')
    search_fields = ('inspection__teacher__username', 'strengths', 'areas_for_improvement')
    ordering = ('-submitted_at',)
    readonly_fields = ('overall_score', 'submitted_at', 'updated_at', 'teacher_viewed_at')
    
    def inspection_teacher(self, obj):
        return obj.inspection.teacher.username
    inspection_teacher.short_description = 'Teacher'


@admin.register(DelegationTeacherMetrics)
class DelegationTeacherMetricsAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'total_inspections', 'average_inspection_score', 'improvement_trend', 'needs_attention', 'updated_at')
    list_filter = ('improvement_trend', 'needs_attention', 'teacher__school')
    search_fields = ('teacher__username',)
    ordering = ('-needs_attention', '-average_inspection_score')
    readonly_fields = ('updated_at',)


@admin.register(DelegationDashboardStats)
class DelegationDashboardStatsAdmin(admin.ModelAdmin):
    list_display = ('delegator', 'total_teachers_assigned', 'teachers_needing_attention', 'pending_inspections', 'average_teacher_score', 'updated_at')
    list_filter = ('delegator__school', 'updated_at')
    search_fields = ('delegator__username',)
    ordering = ('-updated_at',)
    readonly_fields = ('updated_at',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('recipient__username', 'title', 'message')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'read_at')
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(request, f'{queryset.count()} notifications marked as read.')
    mark_as_read.short_description = 'Mark selected notifications as read'
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False, read_at=None)
        self.message_user(request, f'{queryset.count()} notifications marked as unread.')
    mark_as_unread.short_description = 'Mark selected notifications as unread'


@admin.register(TeacherAttendance)
class TeacherAttendanceAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'date', 'status', 'check_in_time', 'is_planned', 'verified_by_delegator', 'verified_by_advisor')
    list_filter = ('status', 'is_planned', 'verified_by_delegator', 'verified_by_advisor', 'date')
    search_fields = ('teacher__username', 'teacher__first_name', 'teacher__last_name', 'reason')
    ordering = ('-date',)
    readonly_fields = ('created_at', 'updated_at', 'planned_at')
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('teacher', 'date', 'status')
        }),
        ('Time Tracking', {
            'fields': ('check_in_time', 'check_out_time')
        }),
        ('Absence Details', {
            'fields': ('reason', 'is_planned', 'planned_at'),
            'classes': ('collapse',)
        }),
        ('Verification', {
            'fields': ('verified_by_delegator', 'delegator_notes', 'verified_by_advisor', 'advisor_notes'),
            'classes': ('collapse',)
        }),
        ('Links', {
            'fields': ('teaching_plan',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(StudentAttendance)
class StudentAttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'teacher', 'date', 'status', 'marked_at')
    list_filter = ('status', 'date', 'teacher__school')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'teacher__username')
    ordering = ('-date', 'student__username')
    readonly_fields = ('marked_at', 'created_at', 'updated_at')
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('student', 'teacher', 'date', 'status')
        }),
        ('Details', {
            'fields': ('notes', 'teacher_attendance', 'lesson')
        }),
        ('Metadata', {
            'fields': ('marked_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(AttendanceSummary)
class AttendanceSummaryAdmin(admin.ModelAdmin):
    list_display = ('user', 'month', 'total_days', 'present_days', 'absent_days', 'attendance_rate', 'last_updated')
    list_filter = ('month', 'user__role', 'user__school')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    ordering = ('-month', 'user__username')
    readonly_fields = ('last_updated',)
    
    actions = ['refresh_summaries']
    
    def refresh_summaries(self, request, queryset):
        for summary in queryset:
            summary.refresh_stats()
        self.message_user(request, f'{queryset.count()} summaries refreshed.')
    refresh_summaries.short_description = 'Refresh selected summaries'


@admin.register(TeacherTimetable)
class TeacherTimetableAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'day_of_week_display', 'start_time', 'end_time', 'is_active', 'created_by', 'created_at')
    list_filter = ('day_of_week', 'is_active', 'created_at', 'teacher__school')
    search_fields = ('teacher__username', 'teacher__first_name', 'teacher__last_name')
    ordering = ('teacher', 'day_of_week', 'start_time')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('teacher', 'day_of_week', 'start_time', 'end_time', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def day_of_week_display(self, obj):
        return obj.get_day_of_week_display()
    day_of_week_display.short_description = 'Day'


@admin.register(InspectorAssignment)
class InspectorAssignmentAdmin(admin.ModelAdmin):
    list_display = ('inspector_name', 'assignment_type', 'assigned_region', 'school_level', 'schools_count', 'is_active', 'assigned_at')
    list_filter = ('assignment_type', 'school_level', 'is_active', 'assigned_at')
    search_fields = ('inspector__username', 'inspector__first_name', 'inspector__last_name', 'assigned_region', 'assigned_subject')
    ordering = ('-assigned_at', 'inspector__username')
    readonly_fields = ('assigned_at', 'updated_at', 'schools_count')
    date_hierarchy = 'assigned_at'
    
    fieldsets = (
        ('Inspector Information', {
            'fields': ('inspector', 'is_active')
        }),
        ('Assignment Details', {
            'fields': ('assignment_type', 'school_level', 'assigned_region', 'assigned_subject')
        }),
        ('Additional Information', {
            'fields': ('notes', 'schools_count'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('assigned_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def inspector_name(self, obj):
        return f"{obj.inspector.first_name} {obj.inspector.last_name}" if obj.inspector.first_name else obj.inspector.username
    inspector_name.short_description = 'Inspector'
    
    def schools_count(self, obj):
        return obj.get_assigned_schools().count()
    schools_count.short_description = 'Schools Count'
