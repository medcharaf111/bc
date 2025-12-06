"""
Views for Attendance System
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta, date

from .models import (
    TeacherAttendance, StudentAttendance, AttendanceSummary, 
    User, Notification
)
from core.models import TeachingPlan
from .attendance_serializers import (
    TeacherAttendanceSerializer, CreateTeacherAttendanceSerializer,
    StudentAttendanceSerializer, BulkStudentAttendanceSerializer,
    AttendanceSummarySerializer, TeacherAttendanceVerificationSerializer,
    PlannedAbsenceSerializer
)


class IsTeacher(IsAuthenticated):
    """Permission class for Teacher role"""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'teacher'


class IsDelegationOrAdvisor(IsAuthenticated):
    """Permission class for Delegation or Advisor roles"""
    def has_permission(self, request, view):
        return (super().has_permission(request, view) and 
                request.user.role in ['delegation', 'advisor'])


class TeacherAttendanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for teacher attendance management
    Teachers can mark their own attendance
    Delegators and Advisors can view and verify
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create' or self.action == 'update':
            return CreateTeacherAttendanceSerializer
        return TeacherAttendanceSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'teacher':
            # Teachers see only their own attendance
            return TeacherAttendance.objects.filter(teacher=user).select_related(
                'teacher', 'teaching_plan'
            )
        elif user.role in ['delegation', 'advisor']:
            # Delegators and Advisors see all teachers in their school
            return TeacherAttendance.objects.filter(
                teacher__school=user.school
            ).select_related('teacher', 'teaching_plan')
        elif user.role == 'admin':
            # Admins see all
            return TeacherAttendance.objects.all().select_related('teacher', 'teaching_plan')
        
        return TeacherAttendance.objects.none()
    
    def perform_create(self, serializer):
        """Teachers mark their own attendance"""
        if self.request.user.role != 'teacher':
            raise PermissionError("Only teachers can mark their own attendance")
        
        # Set teacher to current user
        serializer.save(
            teacher=self.request.user,
            planned_at=timezone.now() if serializer.validated_data.get('is_planned') else None
        )
    
    @action(detail=False, methods=['post'])
    def mark_present(self, request):
        """Quick action to mark present for today"""
        today = date.today()
        
        # Check if already marked
        attendance, created = TeacherAttendance.objects.get_or_create(
            teacher=request.user,
            date=today,
            defaults={
                'status': 'present',
                'check_in_time': timezone.now().time()
            }
        )
        
        if not created:
            if attendance.status != 'present':
                attendance.status = 'present'
                attendance.check_in_time = timezone.now().time()
                attendance.save()
                message = 'Attendance updated to present'
            else:
                message = 'Already marked present for today'
        else:
            message = 'Marked present successfully'
        
        serializer = self.get_serializer(attendance)
        return Response({
            'message': message,
            'attendance': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def check_out(self, request):
        """Mark check-out time"""
        today = date.today()
        
        try:
            attendance = TeacherAttendance.objects.get(
                teacher=request.user,
                date=today
            )
            attendance.check_out_time = timezone.now().time()
            attendance.save()
            
            serializer = self.get_serializer(attendance)
            return Response({
                'message': 'Check-out time recorded',
                'attendance': serializer.data
            })
        except TeacherAttendance.DoesNotExist:
            return Response(
                {'error': 'No attendance record found for today. Please mark present first.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def report_absence(self, request):
        """Report a planned absence (can be future dates)"""
        serializer = PlannedAbsenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        start_date = serializer.validated_data['date']
        end_date = serializer.validated_data.get('end_date', start_date)
        reason = serializer.validated_data['reason']
        
        created_records = []
        current_date = start_date
        
        while current_date <= end_date:
            attendance, created = TeacherAttendance.objects.update_or_create(
                teacher=request.user,
                date=current_date,
                defaults={
                    'status': 'planned_absence',
                    'reason': reason,
                    'is_planned': True,
                    'planned_at': timezone.now()
                }
            )
            created_records.append(attendance)
            current_date += timedelta(days=1)
        
        # Notify delegator and advisor
        if request.user.school:
            # Notify delegators
            delegators = User.objects.filter(
                school=request.user.school,
                role='delegation'
            )
            for delegator in delegators:
                Notification.objects.create(
                    recipient=delegator,
                    notification_type='general',
                    title='Teacher Absence Reported',
                    message=f"{request.user.get_full_name() or request.user.username} reported absence from {start_date} to {end_date}. Reason: {reason}",
                    related_object_type='teacher_attendance',
                    related_object_id=created_records[0].id if created_records else None
                )
        
        return Response({
            'message': f'Absence reported for {len(created_records)} day(s)',
            'records': TeacherAttendanceSerializer(created_records, many=True).data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsDelegationOrAdvisor])
    def verify(self, request, pk=None):
        """Delegator or Advisor verifies teacher attendance"""
        attendance = self.get_object()
        serializer = TeacherAttendanceVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        verified = serializer.validated_data['verified']
        notes = serializer.validated_data.get('notes', '')
        
        if request.user.role == 'delegation':
            attendance.verified_by_delegator = verified
            attendance.delegator_notes = notes
        elif request.user.role == 'advisor':
            attendance.verified_by_advisor = verified
            attendance.advisor_notes = notes
        
        attendance.save()
        
        # Notify teacher
        Notification.objects.create(
            recipient=attendance.teacher,
            notification_type='general',
            title='Attendance Verified',
            message=f"Your attendance for {attendance.date} has been {'verified' if verified else 'flagged'} by {request.user.get_full_name() or request.user.username}",
            related_object_type='teacher_attendance',
            related_object_id=attendance.id
        )
        
        return Response({
            'message': 'Attendance verified successfully',
            'attendance': TeacherAttendanceSerializer(attendance).data
        })
    
    @action(detail=False, methods=['get'])
    def by_teacher(self, request):
        """Get attendance records for a specific teacher (for delegator/advisor)"""
        teacher_id = request.query_params.get('teacher_id')
        if not teacher_id:
            return Response(
                {'error': 'teacher_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = self.get_queryset().filter(teacher_id=teacher_id)
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        serializer = self.get_serializer(queryset, many=True)
        
        # Calculate statistics
        total = queryset.count()
        present = queryset.filter(status='present').count()
        absent = queryset.filter(status='absent').count()
        late = queryset.filter(status='late').count()
        planned = queryset.filter(status='planned_absence').count()
        
        return Response({
            'records': serializer.data,
            'statistics': {
                'total_days': total,
                'present': present,
                'absent': absent,
                'late': late,
                'planned_absence': planned,
                'attendance_rate': round((present / total * 100), 2) if total > 0 else 0
            }
        })
    
    @action(detail=False, methods=['get'])
    def weekly_status(self, request):
        """Get weekly attendance status with timetable for current teacher"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Only teachers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get date range (default to current week)
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())  # Monday
        end_of_week = start_of_week + timedelta(days=6)  # Sunday
        
        # Allow custom date range from query params
        start_date_param = request.query_params.get('start_date')
        end_date_param = request.query_params.get('end_date')
        
        if start_date_param:
            try:
                start_of_week = datetime.strptime(start_date_param, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        if end_date_param:
            try:
                end_of_week = datetime.strptime(end_date_param, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Get timetable
        from .models import TeacherTimetable
        timetables = TeacherTimetable.objects.filter(
            teacher=request.user,
            is_active=True
        ).values('day_of_week', 'start_time', 'end_time', 'id')
        
        # Get attendance records for the week
        attendance_records = TeacherAttendance.objects.filter(
            teacher=request.user,
            date__gte=start_of_week,
            date__lte=end_of_week
        ).values('date', 'status', 'check_in_time', 'check_out_time')
        
        # Build attendance map by date
        attendance_map = {}
        for record in attendance_records:
            attendance_map[record['date'].isoformat()] = {
                'status': record['status'],
                'check_in_time': record['check_in_time'].strftime('%H:%M') if record['check_in_time'] else None,
                'check_out_time': record['check_out_time'].strftime('%H:%M') if record['check_out_time'] else None,
            }
        
        # Build weekly schedule with attendance status
        weekly_schedule = {}
        for day in range(7):  # 0=Monday, 6=Sunday
            current_date = start_of_week + timedelta(days=day)
            date_str = current_date.isoformat()
            
            day_timetables = [tt for tt in timetables if tt['day_of_week'] == day]
            attendance = attendance_map.get(date_str)
            
            weekly_schedule[str(day)] = {
                'date': date_str,
                'day_of_week': day,
                'has_schedule': len(day_timetables) > 0,
                'timetables': [
                    {
                        'id': tt['id'],
                        'start_time': tt['start_time'].strftime('%H:%M'),
                        'end_time': tt['end_time'].strftime('%H:%M'),
                    }
                    for tt in day_timetables
                ],
                'attendance': attendance if attendance else None,
                'is_today': current_date == today,
            }
        
        return Response({
            'start_date': start_of_week.isoformat(),
            'end_date': end_of_week.isoformat(),
            'weekly_schedule': weekly_schedule,
        })

    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's attendance status"""
        today = date.today()
        
        try:
            attendance = TeacherAttendance.objects.get(
                teacher=request.user,
                date=today
            )
            serializer = self.get_serializer(attendance)
            return Response(serializer.data)
        except TeacherAttendance.DoesNotExist:
            return Response({
                'date': today,
                'status': None,
                'message': 'No attendance marked for today'
            })


class StudentAttendanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for student attendance management
    Only teachers can mark student attendance
    """
    permission_classes = [IsAuthenticated]
    serializer_class = StudentAttendanceSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'teacher':
            # Teachers see students they've marked
            return StudentAttendance.objects.filter(teacher=user).select_related(
                'student', 'teacher', 'lesson', 'teacher_attendance'
            )
        elif user.role == 'student':
            # Students see their own attendance
            return StudentAttendance.objects.filter(student=user).select_related(
                'student', 'teacher', 'lesson'
            )
        elif user.role == 'parent':
            # Parents see their children's attendance
            from .models import ParentStudentRelationship
            children_ids = ParentStudentRelationship.objects.filter(
                parent=user,
                is_active=True
            ).values_list('student_id', flat=True)
            return StudentAttendance.objects.filter(student_id__in=children_ids).select_related(
                'student', 'teacher', 'lesson'
            )
        elif user.role in ['delegation', 'advisor', 'admin']:
            # Can see all in their school
            return StudentAttendance.objects.filter(
                student__school=user.school
            ).select_related('student', 'teacher', 'lesson')
        
        return StudentAttendance.objects.none()
    
    def perform_create(self, serializer):
        """Only teachers can mark student attendance, and only if they're present"""
        if self.request.user.role != 'teacher':
            raise PermissionError("Only teachers can mark student attendance")
        
        # Check if teacher is present today
        attendance_date = serializer.validated_data.get('date', date.today())
        
        try:
            teacher_attendance = TeacherAttendance.objects.get(
                teacher=self.request.user,
                date=attendance_date
            )
            
            if teacher_attendance.status != 'present':
                raise PermissionError(
                    f"Cannot mark student attendance when teacher status is '{teacher_attendance.get_status_display()}'"
                )
            
            serializer.save(
                teacher=self.request.user,
                teacher_attendance=teacher_attendance
            )
        except TeacherAttendance.DoesNotExist:
            raise PermissionError(
                "Teacher must mark their own attendance as present before marking students"
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsTeacher])
    def bulk_mark(self, request):
        """Bulk mark attendance for multiple students"""
        serializer = BulkStudentAttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        attendance_date = serializer.validated_data['date']
        students_data = serializer.validated_data['students']
        lesson_id = serializer.validated_data.get('lesson')
        
        # Verify teacher is present
        try:
            teacher_attendance = TeacherAttendance.objects.get(
                teacher=request.user,
                date=attendance_date,
                status='present'
            )
        except TeacherAttendance.DoesNotExist:
            return Response(
                {'error': 'You must mark yourself as present before marking students'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_records = []
        updated_records = []
        
        for student_data in students_data:
            student_id = student_data['student_id']
            attendance_status = student_data['status']
            notes = student_data.get('notes', '')
            
            attendance, created = StudentAttendance.objects.update_or_create(
                student_id=student_id,
                teacher=request.user,
                date=attendance_date,
                defaults={
                    'status': attendance_status,
                    'notes': notes,
                    'teacher_attendance': teacher_attendance,
                    'lesson_id': lesson_id
                }
            )
            
            if created:
                created_records.append(attendance)
            else:
                updated_records.append(attendance)
        
        return Response({
            'message': f'Marked attendance for {len(created_records) + len(updated_records)} students',
            'created': len(created_records),
            'updated': len(updated_records),
            'records': StudentAttendanceSerializer(created_records + updated_records, many=True).data
        })
    
    @action(detail=False, methods=['get'])
    def by_date(self, request):
        """Get all student attendance for a specific date"""
        attendance_date = request.query_params.get('date')
        if not attendance_date:
            attendance_date = date.today()
        
        queryset = self.get_queryset().filter(date=attendance_date)
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'date': attendance_date,
            'records': serializer.data,
            'total': queryset.count(),
            'present': queryset.filter(status='present').count(),
            'absent': queryset.filter(status='absent').count(),
            'late': queryset.filter(status='late').count()
        })


class AttendanceSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for attendance summaries (read-only)
    Auto-generated monthly statistics
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AttendanceSummarySerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role in ['teacher', 'student']:
            return AttendanceSummary.objects.filter(user=user)
        elif user.role == 'parent':
            from .models import ParentStudentRelationship
            children_ids = ParentStudentRelationship.objects.filter(
                parent=user,
                is_active=True
            ).values_list('student_id', flat=True)
            return AttendanceSummary.objects.filter(user_id__in=children_ids)
        elif user.role in ['delegation', 'advisor', 'admin']:
            return AttendanceSummary.objects.filter(user__school=user.school)
        
        return AttendanceSummary.objects.none()
    
    @action(detail=False, methods=['post'])
    def refresh(self, request):
        """Refresh attendance summary for current month"""
        current_month = date.today().replace(day=1)
        
        summary, created = AttendanceSummary.objects.get_or_create(
            user=request.user,
            month=current_month
        )
        
        summary.refresh_stats()
        
        serializer = self.get_serializer(summary)
        return Response({
            'message': 'Summary refreshed',
            'summary': serializer.data
        })
