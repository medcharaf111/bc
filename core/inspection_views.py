"""
ViewSets for Inspection System
Inspector and GPI (General Pedagogical Inspectorate) workflows
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Avg, Max
from django.utils import timezone
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404

from .models import (
    Region, InspectorRegionAssignment, TeacherComplaint,
    InspectionVisit, InspectionReport, MonthlyReport, TeacherRatingHistory
)
from accounts.models import User, School
from .serializers import (
    RegionSerializer, InspectorRegionAssignmentSerializer,
    TeacherComplaintSerializer, InspectionVisitSerializer,
    InspectionReportSerializer, InspectionReportDetailSerializer,
    MonthlyReportSerializer, TeacherRatingHistorySerializer,
    InspectorDashboardStatsSerializer, GPIDashboardStatsSerializer
)
from .permissions import (
    IsInspector, IsGPI, IsInspectorOrGPI, IsInspectorOrGPIOrAdmin,
    IsInspectorOfRegion, CanReviewReport
)


class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for regions - read-only for inspectors, managed by admin
    """
    queryset = Region.objects.filter(is_active=True)
    serializer_class = RegionSerializer
    permission_classes = [IsAuthenticated, IsInspectorOrGPIOrAdmin]
    
    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        
        # Inspectors only see their assigned regions
        if user.role == 'inspector':
            assigned_regions = InspectorRegionAssignment.objects.filter(
                inspector=user
            ).values_list('region_id', flat=True)
            queryset = queryset.filter(id__in=assigned_regions)
        
        return queryset.order_by('code')


class InspectorDashboardViewSet(viewsets.ViewSet):
    """
    Dashboard endpoint for inspectors
    Provides statistics, upcoming visits, pending reports, etc.
    """
    permission_classes = [IsAuthenticated, IsInspector]
    pagination_class = None  # We'll handle pagination manually if needed
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get inspector dashboard statistics"""
        inspector = request.user
        today = timezone.now().date()
        current_month = today.replace(day=1)
        
        # Get assigned regions
        assigned_regions = InspectorRegionAssignment.objects.filter(
            inspector=inspector
        ).select_related('region')
        
        regions_data = [
            {
                'id': assignment.region.id,
                'name': assignment.region.name,
                'code': assignment.region.code,
                'governorate': assignment.region.governorate,
                'school_count': assignment.region.get_school_count(),
                'teacher_count': assignment.region.get_teacher_count()
            }
            for assignment in assigned_regions
        ]
        
        # Visit statistics
        all_visits = InspectionVisit.objects.filter(inspector=inspector)
        total_visits = all_visits.count()
        completed_visits = all_visits.filter(status='completed').count()
        pending_visits = all_visits.filter(status='scheduled').count()
        upcoming_visits = all_visits.filter(
            status='scheduled',
            visit_date__gte=today
        ).count()
        
        # Report statistics
        all_reports = InspectionReport.objects.filter(inspector=inspector)
        reports_pending_review = all_reports.filter(gpi_status='pending').count()
        reports_approved = all_reports.filter(gpi_status='approved').count()
        reports_revision_needed = all_reports.filter(gpi_status='revision_needed').count()
        
        # Count teachers in assigned regions
        region_ids = [r['id'] for r in regions_data]
        assigned_teachers_count = User.objects.filter(
            role='teacher',
            school__region_id__in=region_ids
        ).count()
        
        # Check monthly report status
        monthly_report = MonthlyReport.objects.filter(
            inspector=inspector,
            month=current_month
        ).first()
        monthly_report_status = monthly_report.status if monthly_report else None
        
        stats = {
            'total_visits': total_visits,
            'completed_visits': completed_visits,
            'pending_visits': pending_visits,
            'upcoming_visits': upcoming_visits,
            'reports_pending_review': reports_pending_review,
            'reports_approved': reports_approved,
            'reports_revision_needed': reports_revision_needed,
            'assigned_regions': regions_data,
            'assigned_teachers_count': assigned_teachers_count,
            'monthly_report_status': monthly_report_status
        }
        
        serializer = InspectorDashboardStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming_visits(self, request):
        """Get upcoming scheduled visits"""
        inspector = request.user
        today = timezone.now().date()
        
        visits = InspectionVisit.objects.filter(
            inspector=inspector,
            status='scheduled',
            visit_date__gte=today
        ).select_related('teacher', 'school', 'related_complaint').order_by('visit_date', 'visit_time')[:10]
        
        serializer = InspectionVisitSerializer(visits, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def assigned_teachers(self, request):
        """Get teachers in assigned regions"""
        inspector = request.user
        
        # Get assigned regions
        region_ids = InspectorRegionAssignment.objects.filter(
            inspector=inspector
        ).values_list('region_id', flat=True)
        
        # Get teachers in those regions
        teachers = User.objects.filter(
            role='teacher',
            school__region_id__in=region_ids
        ).select_related('school').order_by('last_name', 'first_name')
        
        # Return teacher data (limit to 100 for performance)
        teachers_list = teachers[:100]
        
        data = [
            {
                'id': t.id,
                'full_name': t.get_full_name(),
                'email': t.email,
                'school': t.school.name if t.school else None,
                'subject': t.subjects[0] if t.subjects else None,
                'phone': t.phone
            }
            for t in teachers_list
        ]
        
        return Response({
            'count': teachers.count(),
            'results': data
        })


class GPIDashboardViewSet(viewsets.ViewSet):
    """
    Dashboard endpoint for GPI (General Pedagogical Inspectorate)
    Provides statistics, pending reviews, inspector management, etc.
    """
    permission_classes = [IsAuthenticated, IsGPI]
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get GPI dashboard statistics"""
        today = timezone.now().date()
        current_month_start = today.replace(day=1)
        
        # Inspector statistics
        all_inspectors = User.objects.filter(role='inspector')
        total_inspectors = all_inspectors.count()
        
        # Active inspectors (those who made visits this month)
        active_inspectors = InspectionVisit.objects.filter(
            visit_date__gte=current_month_start,
            inspector__role='inspector'
        ).values('inspector').distinct().count()
        
        # Report statistics
        total_reports_pending = InspectionReport.objects.filter(
            gpi_status='pending'
        ).count()
        
        total_monthly_reports_pending = MonthlyReport.objects.filter(
            status='submitted'
        ).count()
        
        # This month's reviews
        reports_approved_this_month = InspectionReport.objects.filter(
            gpi_status='approved',
            gpi_reviewed_at__gte=current_month_start
        ).count()
        
        reports_rejected_this_month = InspectionReport.objects.filter(
            gpi_status='rejected',
            gpi_reviewed_at__gte=current_month_start
        ).count()
        
        # Average rating this month
        avg_rating = InspectionReport.objects.filter(
            visit__visit_date__gte=current_month_start,
            visit__status='completed'
        ).aggregate(avg=Avg('final_rating'))['avg']
        
        # Total visits this month
        total_visits_this_month = InspectionVisit.objects.filter(
            visit_date__gte=current_month_start
        ).count()
        
        # Regions summary
        regions = Region.objects.filter(is_active=True)
        regions_summary = []
        for region in regions:
            inspector_count = InspectorRegionAssignment.objects.filter(region=region).count()
            visits_this_month = InspectionVisit.objects.filter(
                school__region=region,
                visit_date__gte=current_month_start
            ).count()
            
            regions_summary.append({
                'id': region.id,
                'name': region.name,
                'code': region.code,
                'inspector_count': inspector_count,
                'visits_this_month': visits_this_month,
                'school_count': region.get_school_count(),
                'teacher_count': region.get_teacher_count()
            })
        
        stats = {
            'total_inspectors': total_inspectors,
            'active_inspectors': active_inspectors,
            'total_reports_pending': total_reports_pending,
            'total_monthly_reports_pending': total_monthly_reports_pending,
            'reports_approved_this_month': reports_approved_this_month,
            'reports_rejected_this_month': reports_rejected_this_month,
            'average_rating_this_month': round(avg_rating, 2) if avg_rating else None,
            'total_visits_this_month': total_visits_this_month,
            'regions_summary': regions_summary
        }
        
        serializer = GPIDashboardStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_reports(self, request):
        """Get inspection reports pending GPI review"""
        reports = InspectionReport.objects.filter(
            gpi_status='pending'
        ).select_related('inspector', 'teacher', 'visit').order_by('-submitted_at')
        
        serializer = InspectionReportDetailSerializer(reports, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_monthly_reports(self, request):
        """Get monthly reports pending GPI review"""
        reports = MonthlyReport.objects.filter(
            status='submitted'
        ).select_related('inspector').order_by('-submitted_at')
        
        serializer = MonthlyReportSerializer(reports, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def inspectors(self, request):
        """Get list of all inspectors with statistics"""
        inspectors = User.objects.filter(role='inspector').select_related('school')
        
        data = []
        for inspector in inspectors:
            # Get assigned regions
            assigned_regions = InspectorRegionAssignment.objects.filter(
                inspector=inspector
            ).select_related('region')
            
            regions_list = [
                {'id': a.region.id, 'name': a.region.name, 'code': a.region.code}
                for a in assigned_regions
            ]
            
            # Statistics
            total_visits = InspectionVisit.objects.filter(inspector=inspector).count()
            completed_visits = InspectionVisit.objects.filter(
                inspector=inspector, status='completed'
            ).count()
            
            avg_rating = InspectionReport.objects.filter(
                inspector=inspector
            ).aggregate(avg=Avg('final_rating'))['avg']
            
            data.append({
                'id': inspector.id,
                'full_name': inspector.get_full_name(),
                'email': inspector.email,
                'phone': inspector.phone,
                'assigned_regions': regions_list,
                'total_visits': total_visits,
                'completed_visits': completed_visits,
                'average_rating': round(avg_rating, 2) if avg_rating else None
            })
        
        return Response(data)


class TeacherComplaintViewSet(viewsets.ModelViewSet):
    """
    ViewSet for teacher complaints
    - Anyone can file a complaint
    - Inspectors can view complaints in their regions
    - GPI can view all complaints
    """
    serializer_class = TeacherComplaintSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = TeacherComplaint.objects.select_related(
            'teacher', 'filed_by', 'assigned_inspector'
        )
        
        if user.role == 'inspector':
            # Inspectors see complaints in their regions or assigned to them
            region_ids = InspectorRegionAssignment.objects.filter(
                inspector=user
            ).values_list('region_id', flat=True)
            
            queryset = queryset.filter(
                Q(teacher__school__region_id__in=region_ids) |
                Q(assigned_inspector=user)
            )
        elif user.role == 'gpi' or user.role == 'admin':
            # GPI and admin see all complaints
            pass
        else:
            # Others only see complaints they filed or received
            queryset = queryset.filter(
                Q(filed_by=user) | Q(teacher=user)
            )
        
        return queryset.order_by('-filed_at')
    
    def perform_create(self, serializer):
        """Set filed_by to current user"""
        serializer.save(filed_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def assign_inspector(self, request, pk=None):
        """Assign an inspector to investigate the complaint (GPI only)"""
        if request.user.role not in ['gpi', 'admin']:
            return Response(
                {'error': 'Only GPI members can assign inspectors'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        complaint = self.get_object()
        inspector_id = request.data.get('inspector_id')
        
        if not inspector_id:
            return Response(
                {'error': 'inspector_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            inspector = User.objects.get(id=inspector_id, role='inspector')
        except User.DoesNotExist:
            return Response(
                {'error': 'Inspector not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        complaint.assigned_inspector = inspector
        complaint.status = 'under_investigation'
        complaint.save()
        
        serializer = self.get_serializer(complaint)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a complaint"""
        complaint = self.get_object()
        
        # Only assigned inspector, GPI, or admin can resolve
        if request.user.role not in ['gpi', 'admin'] and complaint.assigned_inspector != request.user:
            return Response(
                {'error': 'Only assigned inspector or GPI can resolve complaints'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        resolution_notes = request.data.get('resolution_notes', '')
        
        complaint.status = 'resolved'
        complaint.resolution_notes = resolution_notes
        complaint.resolved_at = timezone.now()
        complaint.save()
        
        serializer = self.get_serializer(complaint)
        return Response(serializer.data)


class InspectionVisitViewSet(viewsets.ModelViewSet):
    """
    ViewSet for inspection visits
    - Inspectors can create/manage visits in their regions
    - GPI can view all visits
    """
    serializer_class = InspectionVisitSerializer
    permission_classes = [IsAuthenticated, IsInspectorOrGPI]
    
    def get_queryset(self):
        user = self.request.user
        queryset = InspectionVisit.objects.select_related(
            'inspector', 'teacher', 'school', 'related_complaint'
        )
        
        if user.role == 'inspector':
            # Inspectors only see their own visits
            queryset = queryset.filter(inspector=user)
        
        return queryset.order_by('-visit_date', '-visit_time')
    
    def create(self, request, *args, **kwargs):
        """Override create to add debugging"""
        print(f"DEBUG - Creating visit with data: {request.data}")
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            print(f"DEBUG - Validation error: {e}")
            print(f"DEBUG - Serializer errors: {serializer.errors}")
            raise
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def perform_create(self, serializer):
        """Set inspector to current user and school from teacher"""
        print(f"DEBUG - Request data: {self.request.data}")
        print(f"DEBUG - Validated data: {serializer.validated_data}")
        teacher = serializer.validated_data.get('teacher')
        if teacher and teacher.school:
            serializer.save(inspector=self.request.user, school=teacher.school)
        else:
            print(f"DEBUG - No teacher or school found. Teacher: {teacher}")
            serializer.save(inspector=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """Mark visit as completed"""
        visit = self.get_object()
        
        if visit.inspector != request.user and request.user.role not in ['gpi', 'admin']:
            return Response(
                {'error': 'Only the assigned inspector can mark visit as completed'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        visit.mark_completed()
        
        serializer = self.get_serializer(visit)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a visit"""
        visit = self.get_object()
        
        if visit.inspector != request.user and request.user.role not in ['gpi', 'admin']:
            return Response(
                {'error': 'Only the assigned inspector can cancel visit'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        cancellation_reason = request.data.get('cancellation_reason', '')
        
        visit.status = 'cancelled'
        visit.cancellation_reason = cancellation_reason
        visit.save()
        
        serializer = self.get_serializer(visit)
        return Response(serializer.data)


class InspectionReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for inspection reports
    - Inspectors can create/edit their reports
    - GPI can review and approve/reject reports
    """
    permission_classes = [IsAuthenticated, IsInspectorOrGPI]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return InspectionReportDetailSerializer
        return InspectionReportSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = InspectionReport.objects.select_related(
            'inspector', 'teacher', 'visit', 'gpi_reviewer'
        )
        
        if user.role == 'inspector':
            # Inspectors only see their own reports
            queryset = queryset.filter(inspector=user)
        
        return queryset.order_by('-submitted_at')
    
    def perform_create(self, serializer):
        """Create report and link to visit"""
        visit = serializer.validated_data['visit']
        serializer.save(
            inspector=self.request.user,
            teacher=visit.teacher
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsGPI])
    def approve(self, request, pk=None):
        """Approve report (GPI only)"""
        report = self.get_object()
        feedback = request.data.get('feedback', '')
        
        report.approve(request.user, feedback)
        
        serializer = self.get_serializer(report)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsGPI])
    def reject(self, request, pk=None):
        """Reject report (GPI only)"""
        report = self.get_object()
        feedback = request.data.get('feedback')
        
        if not feedback:
            return Response(
                {'error': 'Feedback is required when rejecting a report'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        report.reject(request.user, feedback)
        
        serializer = self.get_serializer(report)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsGPI])
    def request_revision(self, request, pk=None):
        """Request revision from inspector (GPI only)"""
        report = self.get_object()
        feedback = request.data.get('feedback')
        
        if not feedback:
            return Response(
                {'error': 'Feedback is required when requesting revision'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        report.request_revision(request.user, feedback)
        
        serializer = self.get_serializer(report)
        return Response(serializer.data)


class MonthlyReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for monthly reports
    - Inspectors create and submit monthly reports
    - GPI reviews and approves monthly reports
    """
    serializer_class = MonthlyReportSerializer
    permission_classes = [IsAuthenticated, IsInspectorOrGPI]
    
    def get_queryset(self):
        user = self.request.user
        queryset = MonthlyReport.objects.select_related('inspector', 'gpi_reviewer')
        
        if user.role == 'inspector':
            # Inspectors only see their own reports
            queryset = queryset.filter(inspector=user)
        
        return queryset.order_by('-month')
    
    def perform_create(self, serializer):
        """Set inspector to current user"""
        serializer.save(inspector=self.request.user)
    
    @action(detail=True, methods=['post'])
    def generate_stats(self, request, pk=None):
        """Generate statistics from visits"""
        report = self.get_object()
        
        if report.inspector != request.user and request.user.role not in ['gpi', 'admin']:
            return Response(
                {'error': 'Only the report owner can generate statistics'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        stats = report.generate_statistics()
        
        serializer = self.get_serializer(report)
        return Response({
            'report': serializer.data,
            'generated_stats': stats
        })
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit report to GPI for review"""
        report = self.get_object()
        
        if report.inspector != request.user:
            return Response(
                {'error': 'Only the report owner can submit it'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if report.status != 'draft':
            return Response(
                {'error': 'Only draft reports can be submitted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        report.submit()
        
        serializer = self.get_serializer(report)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsGPI])
    def approve(self, request, pk=None):
        """Approve monthly report (GPI only)"""
        report = self.get_object()
        feedback = request.data.get('feedback', '')
        
        report.approve(request.user, feedback)
        
        serializer = self.get_serializer(report)
        return Response(serializer.data)


class TeacherRatingHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for teacher rating history
    Used for analytics and trend analysis
    """
    serializer_class = TeacherRatingHistorySerializer
    permission_classes = [IsAuthenticated, IsInspectorOrGPIOrAdmin]
    
    def get_queryset(self):
        queryset = TeacherRatingHistory.objects.select_related(
            'teacher', 'inspector', 'inspection_report'
        )
        
        # Filter by teacher if specified
        teacher_id = self.request.query_params.get('teacher_id')
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        
        # Filter by inspector if specified
        inspector_id = self.request.query_params.get('inspector_id')
        if inspector_id:
            queryset = queryset.filter(inspector_id=inspector_id)
        
        return queryset.order_by('-inspection_date')
    
    @action(detail=False, methods=['get'])
    def teacher_average(self, request):
        """Get average rating for a teacher"""
        teacher_id = request.query_params.get('teacher_id')
        if not teacher_id:
            return Response(
                {'error': 'teacher_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            teacher = User.objects.get(id=teacher_id, role='teacher')
        except User.DoesNotExist:
            return Response(
                {'error': 'Teacher not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        average = TeacherRatingHistory.get_teacher_average(teacher)
        
        return Response({
            'teacher_id': teacher.id,
            'teacher_name': teacher.get_full_name(),
            'average_rating': average
        })
    
    @action(detail=False, methods=['get'])
    def teacher_trend(self, request):
        """Get rating trend for a teacher"""
        teacher_id = request.query_params.get('teacher_id')
        months = int(request.query_params.get('months', 6))
        
        if not teacher_id:
            return Response(
                {'error': 'teacher_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            teacher = User.objects.get(id=teacher_id, role='teacher')
        except User.DoesNotExist:
            return Response(
                {'error': 'Teacher not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        trend = TeacherRatingHistory.get_teacher_trend(teacher, months)
        
        return Response({
            'teacher_id': teacher.id,
            'teacher_name': teacher.get_full_name(),
            'months': months,
            'trend': trend
        })
