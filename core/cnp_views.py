"""
Views for CNP (Centre National Pédagogique) Dashboard
Handles teacher guide uploads and management
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q, Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import CNPTeacherGuide
from .serializers import CNPTeacherGuideSerializer
from .permissions import IsCNPAgent, IsAdminOrCNP


class CNPTeacherGuideViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing CNP teacher guide uploads
    
    Permissions:
    - List/Retrieve: CNP agents and admins can see all, teachers/advisors can see approved only
    - Create: CNP agents only
    - Update/Delete: CNP agents (own uploads) and admins (all)
    - Approve: Admins and senior CNP agents
    """
    queryset = CNPTeacherGuide.objects.all()
    serializer_class = CNPTeacherGuideSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['subject', 'grade_level', 'guide_type', 'status', 'academic_year']
    search_fields = ['title', 'description', 'keywords', 'topics_covered']
    ordering_fields = ['created_at', 'updated_at', 'usage_count', 'title']
    ordering = ['-created_at']
    
    def get_permissions(self):
        """
        Different permissions for different actions
        """
        if self.action in ['create', 'upload']:
            return [IsAuthenticated(), IsCNPAgent()]
        elif self.action in ['approve', 'archive']:
            return [IsAuthenticated(), IsAdminOrCNP()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """
        Filter queryset based on user role
        - CNP agents see all their uploads + approved ones
        - Admins see all
        - Teachers/Advisors see only approved guides
        """
        user = self.request.user
        
        if user.role == 'admin':
            return CNPTeacherGuide.objects.all()
        elif user.role == 'cnp':
            # CNP agents see their own uploads + all approved
            return CNPTeacherGuide.objects.filter(
                Q(uploaded_by=user) | Q(status='approved')
            )
        else:
            # Teachers, advisors only see approved
            return CNPTeacherGuide.objects.filter(status='approved')
    
    def perform_create(self, serializer):
        """Set the uploader to current user"""
        serializer.save(uploaded_by=self.request.user)
    
    def perform_update(self, instance, serializer):
        """Only allow updating own uploads or if admin"""
        user = self.request.user
        if user.role != 'admin' and instance.uploaded_by != user:
            return Response(
                {'error': 'You can only edit your own uploads'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer.save()
    
    @action(detail=False, methods=['GET'])
    def dashboard_stats(self, request):
        """
        Get statistics for CNP dashboard
        """
        user = request.user
        
        if user.role == 'cnp':
            my_uploads = CNPTeacherGuide.objects.filter(uploaded_by=user)
            
            stats = {
                'my_uploads': my_uploads.count(),
                'pending_review': my_uploads.filter(status='pending').count(),
                'approved': my_uploads.filter(status='approved').count(),
                'archived': my_uploads.filter(status='archived').count(),
                'total_usage': my_uploads.aggregate(total=Count('id'))['total'] or 0,
                'total_downloads': sum([g.download_count for g in my_uploads]),
                'by_subject': self._get_stats_by_field(my_uploads, 'subject'),
                'by_grade': self._get_stats_by_field(my_uploads, 'grade_level'),
                'by_type': self._get_stats_by_field(my_uploads, 'guide_type'),
                'recent_uploads': CNPTeacherGuideSerializer(
                    my_uploads.order_by('-created_at')[:5],
                    many=True,
                    context={'request': request}
                ).data
            }
        else:
            # Admin view - system-wide stats
            all_guides = CNPTeacherGuide.objects.all()
            stats = {
                'total_guides': all_guides.count(),
                'pending_review': all_guides.filter(status='pending').count(),
                'approved': all_guides.filter(status='approved').count(),
                'archived': all_guides.filter(status='archived').count(),
                'total_usage': sum([g.usage_count for g in all_guides]),
                'total_downloads': sum([g.download_count for g in all_guides]),
                'by_subject': self._get_stats_by_field(all_guides, 'subject'),
                'by_grade': self._get_stats_by_field(all_guides, 'grade_level'),
                'by_type': self._get_stats_by_field(all_guides, 'guide_type'),
                'pending_guides': CNPTeacherGuideSerializer(
                    all_guides.filter(status='pending').order_by('-created_at')[:10],
                    many=True,
                    context={'request': request}
                ).data
            }
        
        return Response(stats)
    
    def _get_stats_by_field(self, queryset, field):
        """Helper to get counts by a specific field"""
        from collections import Counter
        values = queryset.values_list(field, flat=True)
        counts = Counter(values)
        return [{'name': k, 'count': v} for k, v in counts.items()]
    
    @action(detail=True, methods=['POST'])
    def approve(self, request, pk=None):
        """
        Approve a teacher guide (admin or senior CNP only)
        """
        guide = self.get_object()
        
        if guide.status == 'approved':
            return Response(
                {'error': 'This guide is already approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        guide.status = 'approved'
        guide.approved_by = request.user
        guide.approved_at = timezone.now()
        
        # Save admin notes if provided
        if 'admin_notes' in request.data:
            guide.admin_notes = request.data['admin_notes']
        
        guide.save()
        
        serializer = self.get_serializer(guide)
        return Response({
            'message': 'Teacher guide approved successfully',
            'guide': serializer.data
        })
    
    @action(detail=True, methods=['POST'])
    def archive(self, request, pk=None):
        """
        Archive a teacher guide
        """
        guide = self.get_object()
        guide.status = 'archived'
        
        if 'admin_notes' in request.data:
            guide.admin_notes = request.data['admin_notes']
        
        guide.save()
        
        return Response({
            'message': 'Teacher guide archived successfully'
        })
    
    @action(detail=True, methods=['POST'])
    def increment_usage(self, request, pk=None):
        """
        Increment usage count when guide is used for lesson generation
        """
        guide = self.get_object()
        guide.usage_count += 1
        guide.save()
        return Response({'usage_count': guide.usage_count})
    
    @action(detail=True, methods=['POST'])
    def increment_download(self, request, pk=None):
        """
        Increment download count
        """
        guide = self.get_object()
        guide.download_count += 1
        guide.save()
        return Response({'download_count': guide.download_count})
    
    @action(detail=True, methods=['GET'])
    def download(self, request, pk=None):
        """
        Get download URL and increment counter
        """
        guide = self.get_object()
        guide.download_count += 1
        guide.save()
        
        return Response({
            'file_url': request.build_absolute_uri(guide.pdf_file.url),
            'file_name': guide.pdf_file.name.split('/')[-1],
            'file_size': guide.file_size,
            'download_count': guide.download_count
        })
    
    @action(detail=False, methods=['GET'])
    def available_for_generation(self, request):
        """
        Get approved guides available for lesson plan generation
        Filtered by subject and grade if provided
        """
        queryset = self.get_queryset().filter(status='approved')
        
        # Filter by subject if provided
        subject = request.query_params.get('subject')
        if subject:
            queryset = queryset.filter(subject=subject)
        
        # Filter by grade if provided
        grade = request.query_params.get('grade_level')
        if grade:
            queryset = queryset.filter(grade_level=grade)
        
        # Filter by guide type if provided
        guide_type = request.query_params.get('guide_type')
        if guide_type:
            queryset = queryset.filter(guide_type=guide_type)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'guides': serializer.data
        })
