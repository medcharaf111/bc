"""
Views for Delegation (Inspector/Advisor) functionality
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Avg, Count, F
from django.utils import timezone
from datetime import timedelta

from .models import (
    User, TeacherInspection, InspectionReview,
    DelegationTeacherMetrics, DelegationDashboardStats, TeacherAdvisorAssignment
)
from .mandobiya_serializers import (
    TeacherInspectionSerializer, InspectionReviewSerializer,
    TeacherMetricsSerializer, DelegationDashboardStatsSerializer,
    TeacherDetailForDelegationSerializer, TeacherBasicSerializer,
    CreateInspectionReviewSerializer, AdvisorBasicSerializer,
    TeacherAdvisorAssignmentSerializer
)


class IsDelegation(IsAuthenticated):
    """Permission class for Delegation role"""
    
    def has_permission(self, request, view):
        return (super().has_permission(request, view) and 
                request.user.role == 'delegation')


class IsAdvisor(IsAuthenticated):
    """Permission class for Advisor role"""
    
    def has_permission(self, request, view):
        return (super().has_permission(request, view) and 
                request.user.role == 'advisor')


class DelegationTeacherViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Delegation to view teachers in their school
    """
    permission_classes = [IsDelegation]
    serializer_class = TeacherBasicSerializer
    
    def get_queryset(self):
        # Get teachers from the same school as the Delegation
        return User.objects.filter(
            role='teacher',
            school=self.request.user.school
        ).order_by('last_name', 'first_name')
    
    def retrieve(self, request, *args, **kwargs):
        """Get detailed teacher information"""
        teacher = self.get_object()
        serializer = TeacherDetailForDelegationSerializer(teacher, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """Get or create teacher metrics"""
        teacher = self.get_object()
        metrics, created = DelegationTeacherMetrics.objects.get_or_create(teacher=teacher)
        
        if not created:
            # Refresh metrics
            metrics.update_metrics()
        
        serializer = TeacherMetricsSerializer(metrics)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def inspections(self, request, pk=None):
        """Get inspection history for a teacher"""
        teacher = self.get_object()
        inspections = TeacherInspection.objects.filter(teacher=teacher).order_by('-scheduled_date')
        serializer = TeacherInspectionSerializer(inspections, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def needing_attention(self, request):
        """Get teachers that need immediate attention"""
        teachers = User.objects.filter(
            role='teacher',
            school=request.user.school,
            delegation_metrics__needs_attention=True
        ).order_by('-delegation_metrics__average_inspection_score')
        
        serializer = self.get_serializer(teachers, many=True)
        return Response(serializer.data)


class TeacherInspectionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing teacher inspections
    """
    permission_classes = [IsDelegation]
    serializer_class = TeacherInspectionSerializer
    
    def get_queryset(self):
        queryset = TeacherInspection.objects.filter(
            delegator=self.request.user
        ).select_related('teacher', 'school', 'advisor', 'review').order_by('-scheduled_date')
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date:
            queryset = queryset.filter(scheduled_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(scheduled_date__lte=end_date)
        
        return queryset
    
    def perform_create(self, serializer):
        from .models import Notification
        
        inspection = serializer.save(
            delegator=self.request.user,
            school=self.request.user.school,
            created_by=self.request.user
        )
        
        # Create notification for teacher
        teacher_notification = Notification.objects.create(
            recipient=inspection.teacher,
            notification_type='inspection_scheduled',
            title='Inspection Scheduled',
            message=f'You have an inspection scheduled for {inspection.get_subject_display()} on {inspection.scheduled_date.strftime("%B %d, %Y")}' + 
                    (f' at {inspection.scheduled_time.strftime("%I:%M %p")}' if inspection.scheduled_time else '') + 
                    f'. Purpose: {inspection.purpose}',
            related_object_type='inspection',
            related_object_id=inspection.id
        )
        
        # Create notification for advisor if assigned
        if inspection.advisor:
            advisor_notification = Notification.objects.create(
                recipient=inspection.advisor,
                notification_type='inspection_scheduled',
                title='Inspection Assignment',
                message=f'You have been assigned to conduct an inspection for {inspection.teacher.get_full_name() or inspection.teacher.username} ' +
                        f'on {inspection.scheduled_date.strftime("%B %d, %Y")}' +
                        (f' at {inspection.scheduled_time.strftime("%I:%M %p")}' if inspection.scheduled_time else '') +
                        f'. Subject: {inspection.get_subject_display()}. Purpose: {inspection.purpose}',
                related_object_type='inspection',
                related_object_id=inspection.id
            )
    

    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an inspection"""
        inspection = self.get_object()
        
        if inspection.status == 'completed':
            return Response(
                {'error': 'Cannot cancel completed inspections'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        inspection.status = 'cancelled'
        inspection.save()
        
        serializer = self.get_serializer(inspection)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming inspections"""
        upcoming = self.get_queryset().filter(
            status='scheduled',
            scheduled_date__gte=timezone.now().date()
        ).order_by('scheduled_date', 'scheduled_time')
        
        serializer = self.get_serializer(upcoming, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_review(self, request):
        """Get completed inspections pending Delegation review (awaiting accept/decline)"""
        pending = self.get_queryset().filter(
            status='completed',
            completion_verified_by_delegator=False
        ).order_by('-advisor_completed_at')
        
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def accept_report(self, request, pk=None):
        """Delegation accepts the advisor's inspection report"""
        inspection = self.get_object()
        
        if inspection.status != 'completed':
            return Response(
                {'error': 'Inspection must be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if inspection.completion_verified_by_delegator:
            return Response(
                {'error': 'Report already reviewed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        feedback = request.data.get('feedback', '')
        
        inspection.completion_verified_by_delegator = True
        inspection.completion_verified_at = timezone.now()
        inspection.pre_inspection_notes = (inspection.pre_inspection_notes or '') + f'\n\nDelegation Feedback (Accepted): {feedback}'
        inspection.save()
        
        # Notify advisor
        if inspection.advisor:
            Notification.objects.create(
                recipient=inspection.advisor,
                notification_type='review_submitted',
                title='Inspection Report Accepted',
                message=f'Delegation accepted your inspection report for {inspection.teacher.get_full_name() or inspection.teacher.username}.' + (f' Feedback: {feedback}' if feedback else ''),
                related_object_type='inspection',
                related_object_id=inspection.id
            )
        
        # Notify teacher
        Notification.objects.create(
            recipient=inspection.teacher,
            notification_type='review_submitted',
            title='Inspection Report Approved',
            message=f'The inspection report has been approved by Delegation.',
            related_object_type='inspection',
            related_object_id=inspection.id
        )
        
        serializer = self.get_serializer(inspection)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def decline_report(self, request, pk=None):
        """Delegation declines the advisor's inspection report with feedback"""
        inspection = self.get_object()
        
        if inspection.status != 'completed':
            return Response(
                {'error': 'Inspection must be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if inspection.completion_verified_by_delegator:
            return Response(
                {'error': 'Report already reviewed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        feedback = request.data.get('feedback', '')
        if not feedback:
            return Response(
                {'error': 'Feedback is required when declining'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset completion status to allow resubmission
        inspection.status = 'in_progress'
        inspection.advisor_completed_at = None
        inspection.completed_at = None
        inspection.pre_inspection_notes = (inspection.pre_inspection_notes or '') + f'\n\nDelegation Feedback (Declined): {feedback}'
        inspection.save()
        
        # Notify advisor
        if inspection.advisor:
            Notification.objects.create(
                recipient=inspection.advisor,
                notification_type='review_submitted',
                title='Inspection Report Declined',
                message=f'Delegation declined your inspection report for {inspection.teacher.get_full_name() or inspection.teacher.username}. Feedback: {feedback}. Please revise and resubmit.',
                related_object_type='inspection',
                related_object_id=inspection.id
            )
        
        serializer = self.get_serializer(inspection)
        return Response(serializer.data)


class InspectionReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing inspection reviews
    """
    permission_classes = [IsDelegation]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateInspectionReviewSerializer
        return InspectionReviewSerializer
    
    def get_queryset(self):
        return InspectionReview.objects.filter(
            inspection__delegator=self.request.user
        ).select_related('inspection__teacher', 'inspection__school').order_by('-submitted_at')
    
    @action(detail=True, methods=['post'])
    def mark_viewed_by_teacher(self, request, pk=None):
        """Mark that teacher has viewed the review"""
        review = self.get_object()
        
        if not review.teacher_viewed_at:
            review.teacher_viewed_at = timezone.now()
            review.save()
        
        serializer = self.get_serializer(review)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def teacher_acknowledgement(self, request, pk=None):
        """Record teacher's acknowledgement and optional comments"""
        review = self.get_object()
        
        teacher_comments = request.data.get('comments', '')
        
        review.teacher_acknowledged = True
        review.teacher_comments = teacher_comments
        if not review.teacher_viewed_at:
            review.teacher_viewed_at = timezone.now()
        review.save()
        
        serializer = self.get_serializer(review)
        return Response(serializer.data)


class DelegationAdvisorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Delegation to view advisors in their school with stats
    """
    permission_classes = [IsDelegation]
    serializer_class = AdvisorBasicSerializer
    
    def get_queryset(self):
        # Get advisors from the same school as the Delegation
        return User.objects.filter(
            role='advisor',
            school=self.request.user.school
        ).order_by('last_name', 'first_name')
    
    def list(self, request, *args, **kwargs):
        """Override list to include stats for each advisor"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Enhance each advisor with stats
        advisors_with_stats = []
        for advisor_data in serializer.data:
            advisor = User.objects.get(id=advisor_data['id'])
            
            # Get assigned teachers count (active assignments only)
            assigned_teachers_count = TeacherAdvisorAssignment.objects.filter(
                advisor=advisor,
                is_active=True
            ).count()
            
            # Get completed inspections count
            completed_inspections = TeacherInspection.objects.filter(
                advisor=advisor,
                status='completed'
            ).count()
            
            # Get pending reviews (completed inspections without reviews)
            pending_reviews = TeacherInspection.objects.filter(
                advisor=advisor,
                status='completed',
                review__isnull=True
            ).count()
            
            # Get average teacher score from reviews
            avg_score = InspectionReview.objects.filter(
                inspection__advisor=advisor
            ).aggregate(avg_score=Avg('overall_score'))['avg_score'] or 0
            
            # Get inspections this month
            inspections_this_month = TeacherInspection.objects.filter(
                advisor=advisor,
                advisor_completed_at__month=timezone.now().month,
                advisor_completed_at__year=timezone.now().year
            ).count()
            
            # Get upcoming inspections
            upcoming_inspections = TeacherInspection.objects.filter(
                advisor=advisor,
                status__in=['scheduled', 'in_progress']
            ).count()
            
            advisor_data['stats'] = {
                'assigned_teachers_count': assigned_teachers_count,
                'completed_inspections': completed_inspections,
                'pending_reviews': pending_reviews,
                'avg_teacher_score': round(avg_score, 2),
                'inspections_this_month': inspections_this_month,
                'upcoming_inspections': upcoming_inspections,
            }
            
            advisors_with_stats.append(advisor_data)
        
        return Response(advisors_with_stats)


class TeacherAdvisorAssignmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing teacher-advisor assignments
    """
    permission_classes = [IsDelegation]
    serializer_class = TeacherAdvisorAssignmentSerializer
    
    def get_queryset(self):
        return TeacherAdvisorAssignment.objects.filter(
            school=self.request.user.school
        ).select_related('teacher', 'advisor', 'assigned_by').order_by('-assigned_at')
    
    def perform_create(self, serializer):
        serializer.save(
            assigned_by=self.request.user,
            school=self.request.user.school
        )
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate an assignment"""
        assignment = self.get_object()
        assignment.is_active = False
        assignment.deactivated_at = timezone.now()
        assignment.save()
        
        serializer = self.get_serializer(assignment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Reactivate an assignment"""
        assignment = self.get_object()
        assignment.is_active = True
        assignment.deactivated_at = None
        assignment.save()
        
        serializer = self.get_serializer(assignment)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_teacher(self, request):
        """Get assignments for a specific teacher"""
        teacher_id = request.query_params.get('teacher_id')
        if not teacher_id:
            return Response(
                {'error': 'teacher_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assignments = self.get_queryset().filter(teacher_id=teacher_id, is_active=True)
        serializer = self.get_serializer(assignments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_advisor(self, request):
        """Get assignments for a specific advisor"""
        advisor_id = request.query_params.get('advisor_id')
        if not advisor_id:
            return Response(
                {'error': 'advisor_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assignments = self.get_queryset().filter(advisor_id=advisor_id, is_active=True)
        serializer = self.get_serializer(assignments, many=True)
        return Response(serializer.data)


class DelegationDashboardViewSet(viewsets.ViewSet):
    """
    Dashboard data and statistics for Delegation
    """
    permission_classes = [IsDelegation]
    
    def list(self, request):
        """Get dashboard statistics"""
        delegator = request.user
        
        # Get or create stats
        stats, created = DelegationDashboardStats.objects.get_or_create(delegator=delegator)
        
        # Refresh if older than 1 hour
        if created or (timezone.now() - stats.updated_at) > timedelta(hours=1):
            stats.refresh_stats()
        
        serializer = DelegationDashboardStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Comprehensive dashboard overview"""
        delegator = request.user
        
        # Get stats
        stats, _ = DelegationDashboardStats.objects.get_or_create(delegator=delegator)
        stats.refresh_stats()
        
        # Get recent activity
        recent_inspections = TeacherInspection.objects.filter(
            delegator=delegator
        ).order_by('-created_at')[:5]
        
        # Get teachers needing attention
        teachers_attention = User.objects.filter(
            role='teacher',
            school=delegator.school,
            delegation_metrics__needs_attention=True
        )[:5]
        
        # Get upcoming inspections
        upcoming = TeacherInspection.objects.filter(
            delegator=delegator,
            status='scheduled',
            scheduled_date__gte=timezone.now().date()
        ).order_by('scheduled_date')[:5]
        
        return Response({
            'stats': DelegationDashboardStatsSerializer(stats).data,
            'recent_inspections': TeacherInspectionSerializer(recent_inspections, many=True).data,
            'teachers_needing_attention': TeacherBasicSerializer(teachers_attention, many=True).data,
            'upcoming_inspections': TeacherInspectionSerializer(upcoming, many=True).data,
        })
    
    @action(detail=False, methods=['get'])
    def performance_trends(self, request):
        """Get performance trends over time"""
        delegator = request.user
        
        # Get all completed inspections with reviews
        reviews = InspectionReview.objects.filter(
            inspection__delegator=delegator
        ).order_by('submitted_at')
        
        # Group by month
        from collections import defaultdict
        monthly_data = defaultdict(lambda: {'total_score': 0, 'count': 0})
        
        for review in reviews:
            month_key = review.submitted_at.strftime('%Y-%m')
            monthly_data[month_key]['total_score'] += review.overall_score
            monthly_data[month_key]['count'] += 1
        
        # Calculate averages
        trends = []
        for month, data in sorted(monthly_data.items()):
            trends.append({
                'month': month,
                'average_score': round(data['total_score'] / data['count'], 2),
                'inspection_count': data['count']
            })
        
        return Response({
            'trends': trends,
            'total_reviews': reviews.count()
        })
