"""
Serializers for Attendance System
"""
from rest_framework import serializers
from .models import TeacherAttendance, StudentAttendance, AttendanceSummary, User


class TeacherAttendanceSerializer(serializers.ModelSerializer):
    """Serializer for teacher attendance records"""
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    teacher_username = serializers.CharField(source='teacher.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    teaching_plan_title = serializers.CharField(source='teaching_plan.title', read_only=True, allow_null=True)
    
    class Meta:
        model = TeacherAttendance
        fields = [
            'id', 'teacher', 'teacher_name', 'teacher_username', 'date', 'status', 'status_display',
            'check_in_time', 'check_out_time', 'reason', 'is_planned', 'planned_at',
            'verified_by_delegator', 'verified_by_advisor', 'delegator_notes', 'advisor_notes',
            'teaching_plan', 'teaching_plan_title', 'created_at', 'updated_at'
        ]
        read_only_fields = ['teacher', 'created_at', 'updated_at']


class CreateTeacherAttendanceSerializer(serializers.ModelSerializer):
    """Serializer for creating teacher attendance"""
    
    class Meta:
        model = TeacherAttendance
        fields = ['date', 'status', 'check_in_time', 'check_out_time', 'reason', 'is_planned', 'teaching_plan']
    
    def validate(self, attrs):
        # If marking planned absence, reason is required
        if attrs.get('status') == 'planned_absence' and not attrs.get('reason'):
            raise serializers.ValidationError({
                'reason': 'Reason is required for planned absences'
            })
        
        # If marking present, check_in_time is recommended
        if attrs.get('status') == 'present' and not attrs.get('check_in_time'):
            from django.utils import timezone
            attrs['check_in_time'] = timezone.now().time()
        
        return attrs


class StudentAttendanceSerializer(serializers.ModelSerializer):
    """Serializer for student attendance records"""
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_username = serializers.CharField(source='student.username', read_only=True)
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    lesson_title = serializers.CharField(source='lesson.title', read_only=True, allow_null=True)
    
    class Meta:
        model = StudentAttendance
        fields = [
            'id', 'student', 'student_name', 'student_username', 
            'teacher', 'teacher_name', 'date', 'status', 'status_display',
            'notes', 'teacher_attendance', 'lesson', 'lesson_title',
            'marked_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['teacher', 'marked_at', 'created_at', 'updated_at']


class StudentAttendanceDataSerializer(serializers.Serializer):
    """Individual student attendance data"""
    student_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=['present', 'absent', 'late', 'excused'])
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class BulkStudentAttendanceSerializer(serializers.Serializer):
    """Serializer for bulk marking student attendance"""
    date = serializers.DateField()
    lesson = serializers.IntegerField(required=False, allow_null=True)
    students = StudentAttendanceDataSerializer(many=True)
    
    def validate_students(self, value):
        """Validate students list - ensure we have at least one student"""
        if not value:
            raise serializers.ValidationError("Must provide at least one student")
        return value


class AttendanceSummarySerializer(serializers.ModelSerializer):
    """Serializer for attendance summary"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    month_display = serializers.SerializerMethodField()
    
    class Meta:
        model = AttendanceSummary
        fields = [
            'id', 'user', 'user_name', 'user_username', 'user_role',
            'month', 'month_display', 'total_days', 'present_days', 'absent_days',
            'late_days', 'excused_days', 'attendance_rate', 'last_updated'
        ]
        read_only_fields = ['last_updated']
    
    def get_month_display(self, obj):
        return obj.month.strftime('%B %Y')


class TeacherAttendanceVerificationSerializer(serializers.Serializer):
    """Serializer for delegator/advisor verification"""
    verified = serializers.BooleanField()
    notes = serializers.CharField(required=False, allow_blank=True)


class PlannedAbsenceSerializer(serializers.Serializer):
    """Serializer for reporting planned absence"""
    date = serializers.DateField()
    reason = serializers.CharField(max_length=500)
    end_date = serializers.DateField(required=False, help_text="For multi-day absences")
    
    def validate(self, attrs):
        from datetime import date
        
        # Date must be in the future or today
        if attrs['date'] < date.today():
            raise serializers.ValidationError({
                'date': 'Cannot report planned absence for past dates'
            })
        
        # If end_date provided, must be after start date
        if 'end_date' in attrs and attrs['end_date'] < attrs['date']:
            raise serializers.ValidationError({
                'end_date': 'End date must be after start date'
            })
        
        return attrs
