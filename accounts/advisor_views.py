"""
Views for Advisor inspection management and dashboard
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q, Count, Avg, F
from datetime import timedelta
from .models import (
    TeacherInspection, User, Notification, TeacherAdvisorAssignment,
    TeacherProgress
)
from core.models import Lesson, TeachingPlan
from .mandobiya_serializers import (
    TeacherInspectionSerializer, TeacherAdvisorAssignmentSerializer
)
from .mandobiya_views import IsAdvisor


class AdvisorInspectionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for advisors to manage their assigned inspections
    """
    permission_classes = [IsAuthenticated, IsAdvisor]
    serializer_class = TeacherInspectionSerializer
    
    def get_queryset(self):
        """Get inspections assigned to this advisor"""
        return TeacherInspection.objects.filter(
            advisor=self.request.user
        ).select_related('teacher', 'school', 'delegator', 'advisor', 'review').order_by('-scheduled_date')
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming inspections for advisor"""
        upcoming = self.get_queryset().filter(
            status='scheduled',
            scheduled_date__gte=timezone.now().date()
        ).order_by('scheduled_date', 'scheduled_time')
        
        serializer = self.get_serializer(upcoming, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_verification(self, request):
        """Get inspections pending Delegator verification"""
        pending = self.get_queryset().filter(
            Q(advisor_started_at__isnull=False, start_verified_by_delegator=False) |
            Q(advisor_completed_at__isnull=False, completion_verified_by_delegator=False)
        ).order_by('-updated_at')
        
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def report_start(self, request, pk=None):
        """Advisor starts the inspection"""
        inspection = self.get_object()
        
        if inspection.status != 'scheduled':
            return Response(
                {'error': 'Can only start scheduled inspections'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if inspection.advisor_started_at:
            return Response(
                {'error': 'Inspection already started'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Change status to in_progress immediately
        inspection.status = 'in_progress'
        inspection.advisor_started_at = timezone.now()
        inspection.started_at = timezone.now()
        inspection.advisor_notes = request.data.get('notes', '')
        inspection.save()
        
        # Notify Delegator
        Notification.objects.create(
            recipient=inspection.delegator,
            notification_type='inspection_started',
            title='Inspection Started',
            message=f'{request.user.get_full_name() or request.user.username} started inspection for {inspection.teacher.get_full_name() or inspection.teacher.username} on {inspection.scheduled_date.strftime("%B %d, %Y")}.',
            related_object_type='inspection',
            related_object_id=inspection.id
        )
        
        # Notify teacher
        Notification.objects.create(
            recipient=inspection.teacher,
            notification_type='inspection_started',
            title='Your Inspection Has Started',
            message=f'Advisor {request.user.get_full_name() or request.user.username} has started your {inspection.get_subject_display()} inspection.',
            related_object_type='inspection',
            related_object_id=inspection.id
        )
        
        serializer = self.get_serializer(inspection)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def report_completion(self, request, pk=None):
        """Advisor completes the inspection and submits report"""
        inspection = self.get_object()
        
        if inspection.status != 'in_progress':
            return Response(
                {'error': 'Inspection must be in progress'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if inspection.advisor_completed_at:
            return Response(
                {'error': 'Inspection already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the report from advisor
        report = request.data.get('report', '')
        if not report:
            return Response(
                {'error': 'Report is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Complete the inspection
        inspection.status = 'completed'
        inspection.advisor_completed_at = timezone.now()
        inspection.completed_at = timezone.now()
        inspection.advisor_notes = report
        inspection.save()
        
        # Notify Delegator to review
        Notification.objects.create(
            recipient=inspection.delegator,
            notification_type='inspection_completed',
            title='Inspection Report Submitted',
            message=f'{request.user.get_full_name() or request.user.username} completed inspection for {inspection.teacher.get_full_name() or inspection.teacher.username} and submitted a report. Please review and provide feedback.',
            related_object_type='inspection',
            related_object_id=inspection.id
        )
        
        # Notify teacher
        Notification.objects.create(
            recipient=inspection.teacher,
            notification_type='inspection_completed',
            title='Your Inspection Has Been Completed',
            message=f'Advisor {request.user.get_full_name() or request.user.username} has completed your {inspection.get_subject_display()} inspection. Awaiting Delegator review.',
            related_object_type='inspection',
            related_object_id=inspection.id
        )
        
        serializer = self.get_serializer(inspection)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_notes(self, request, pk=None):
        """Update advisor notes for the inspection"""
        inspection = self.get_object()
        
        inspection.advisor_notes = request.data.get('notes', '')
        inspection.save()
        
        serializer = self.get_serializer(inspection)
        return Response(serializer.data)


class AdvisorDashboardViewSet(viewsets.ViewSet):
    """
    Dashboard data and statistics for Advisors
    """
    permission_classes = [IsAuthenticated, IsAdvisor]
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get dashboard overview stats"""
        advisor = request.user
        
        # Get active assignments
        assignments = TeacherAdvisorAssignment.objects.filter(
            advisor=advisor,
            is_active=True
        )
        
        total_assigned = assignments.count()
        subjects_covered = list(assignments.values_list('subject', flat=True).distinct())
        
        # Get inspections
        upcoming_inspections = TeacherInspection.objects.filter(
            advisor=advisor,
            status='scheduled',
            scheduled_date__gte=timezone.now().date()
        ).count()
        
        completed_this_month = TeacherInspection.objects.filter(
            advisor=advisor,
            status='completed',
            advisor_completed_at__gte=timezone.now().replace(day=1)
        ).count()
        
        # Get pending reports (inspections not yet completed by advisor)
        pending_reports = TeacherInspection.objects.filter(
            advisor=advisor,
            status__in=['scheduled', 'in_progress']
        ).count()
        
        # Calculate average teacher performance (from inspection reviews)
        from accounts.models import InspectionReview
        reviews = InspectionReview.objects.filter(
            inspection__advisor=advisor,
            inspection__status='completed'
        )
        avg_rating = reviews.aggregate(avg=Avg('overall_score'))['avg'] or 0.0
        
        # Recent activity
        recent_inspections = TeacherInspection.objects.filter(
            advisor=advisor
        ).select_related('teacher').order_by('-updated_at')[:5]
        
        recent_activity = []
        for inspection in recent_inspections:
            teacher_name = inspection.teacher.get_full_name() if hasattr(inspection.teacher, 'get_full_name') else inspection.teacher.username
            recent_activity.append({
                'type': 'inspection',
                'description': f"{inspection.get_status_display()} inspection with {teacher_name}",
                'date': inspection.updated_at.isoformat()
            })
        
        return Response({
            'total_assigned_teachers': total_assigned,
            'active_assignments': total_assigned,
            'pending_reports': pending_reports,
            'upcoming_inspections': upcoming_inspections,
            'completed_inspections_this_month': completed_this_month,
            'average_teacher_performance': round(float(avg_rating), 2),
            'subjects_covered': subjects_covered,
            'recent_activity': recent_activity
        })
    
    @action(detail=False, methods=['get'])
    def assigned_teachers(self, request):
        """Get all teachers assigned to this advisor with basic stats"""
        advisor = request.user
        
        assignments = TeacherAdvisorAssignment.objects.filter(
            advisor=advisor,
            is_active=True
        ).select_related('teacher', 'school')
        
        serializer = TeacherAdvisorAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def teacher_stats(self, request):
        """Get detailed stats for a specific teacher"""
        teacher_id = request.query_params.get('teacher_id')
        if not teacher_id:
            return Response(
                {'error': 'teacher_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify advisor has access to this teacher
        assignment = TeacherAdvisorAssignment.objects.filter(
            advisor=request.user,
            teacher_id=teacher_id,
            is_active=True
        ).first()
        
        if not assignment:
            return Response(
                {'error': 'Teacher not assigned to you'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        teacher = assignment.teacher
        
        # Get teaching stats
        teaching_plans = TeachingPlan.objects.filter(teacher=teacher)
        completed_lessons = teaching_plans.filter(status='completed').count()
        total_lessons = teaching_plans.count()
        
        completion_rate = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
        
        # Get progress data
        progress_records = TeacherProgress.objects.filter(
            teacher=teacher,
            subject=assignment.subject
        )
        
        # Calculate average student scores from progress
        avg_score = 0  # This would need actual student score data
        
        # Get last activity
        last_activity = teaching_plans.order_by('-updated_at').first()
        last_activity_date = last_activity.updated_at if last_activity else None
        
        # Determine if teacher needs attention
        needs_attention = (
            completion_rate < 50 or
            (last_activity_date and (timezone.now() - last_activity_date).days > 7)
        )
        
        # Performance trend (simplified)
        performance_trend = 'stable'
        if completion_rate > 75:
            performance_trend = 'improving'
        elif completion_rate < 30:
            performance_trend = 'declining'
        
        return Response({
            'teacher_id': teacher.id,
            'teacher_name': teacher.get_full_name() or teacher.username,
            'subject': assignment.subject,
            'total_lessons': total_lessons,
            'completed_lessons': completed_lessons,
            'completion_rate': round(completion_rate, 2),
            'average_student_score': avg_score,
            'last_activity': last_activity_date.isoformat() if last_activity_date else None,
            'needs_attention': needs_attention,
            'performance_trend': performance_trend
        })
