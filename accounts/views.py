from rest_framework import viewsets, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.http import HttpResponse
import csv
import logging

logger = logging.getLogger(__name__)

from .models import (
    School, User, TeacherStudentRelationship, AdvisorReview, GroupChat, ChatMessage,
    ParentStudentRelationship, ParentTeacherChat, ParentTeacherMessage,
    TeacherProgress, ChapterProgressNotification, TeacherAnalytics, TeacherGradeAssignment,
    TeacherTimetable, InspectorAssignment
)
from .serializers import (
    SchoolSerializer, UserSerializer, TeacherStudentRelationshipSerializer,
    AdvisorReviewSerializer, GroupChatSerializer, ChatMessageSerializer, UserBasicSerializer,
    ParentStudentRelationshipSerializer, StudentPerformanceSerializer,
    ParentTeacherChatSerializer, ParentTeacherMessageSerializer,
    TeacherProgressSerializer, ChapterProgressNotificationSerializer, TeacherAnalyticsSerializer,
    AdminUserDetailSerializer, AdminSchoolStatsSerializer, AdminAdvisorPerformanceSerializer,
    AdminTeacherPerformanceSerializer, TeacherGradeAssignmentSerializer, TeacherTimetableSerializer,
    InspectorAssignmentSerializer
)

class SchoolViewSet(viewsets.ModelViewSet):
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    permission_classes = [IsAuthenticated]

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], permission_classes=[])
    def register(self, request):
        print(f"Registration data received: {request.data}")
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': serializer.data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        print(f"Validation errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[])
    def login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            serializer = UserSerializer(user)
            return Response({
                'user': serializer.data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=['get'], url_path='students')
    def list_students(self, request):
        """Get list of all students - useful for parents to find student IDs"""
        students = User.objects.filter(role='student').values('id', 'username', 'first_name', 'last_name', 'email')
        return Response(list(students), status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='assigned-subjects')
    def assigned_subjects(self, request):
        """Get subjects that the teacher is currently assigned to teach"""
        if request.user.role != 'teacher':
            return Response({'error': 'Only teachers can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)
        
        from .models import TeacherGradeAssignment
        
        # Get unique subjects from active assignments
        assignments = TeacherGradeAssignment.objects.filter(
            teacher=request.user,
            is_active=True
        ).select_related('teacher').distinct()
        
        # Get unique subjects with their grade levels
        subject_grades = {}
        all_grade_levels = set()
        
        for assignment in assignments:
            subject = assignment.subject
            grade_level = assignment.grade_level
            all_grade_levels.add(grade_level)
            
            if subject not in subject_grades:
                subject_grades[subject] = {
                    'subject': subject,
                    'subject_display': assignment.get_subject_display(),
                    'grades': []
                }
            subject_grades[subject]['grades'].append({
                'grade_level': grade_level,
                'grade_display': assignment.get_grade_level_display()
            })
        
        return Response({
            'assigned_subjects': list(subject_grades.values()),
            'subject_codes': list(subject_grades.keys()),
            'grade_codes': list(all_grade_levels),
            'has_assignments': len(subject_grades) > 0
        })
    
    @action(detail=False, methods=['get'])
    def delegator_map(self, request):
        """Get schools map for delegator's assigned delegation only"""
        # Check if user is a delegator
        if request.user.role != 'delegation':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only delegators can access this resource")
        
        # Get delegator's assigned delegation
        assigned_delegation = request.user.assigned_delegation
        if not assigned_delegation:
            return Response({
                'schools': [],
                'filter_options': {'types': [], 'cres': []},
                'total_count': 0,
                'message': 'No delegation assigned to this user'
            })
        
        # Get filter parameters
        school_type = request.query_params.get('type')
        cre_filter = request.query_params.get('cre')
        search = request.query_params.get('search')
        
        # Base queryset - only schools with geodata in assigned delegation
        # Note: "assigned_delegation" actually refers to CRE (regional education office)
        # The School.delegation field contains sub-delegations, School.cre contains the regional office
        schools = School.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            cre__iexact=assigned_delegation
        )
        
        # Apply filters
        if school_type:
            schools = schools.filter(school_type__icontains=school_type)
        if cre_filter:
            schools = schools.filter(delegation__icontains=cre_filter)
        if search:
            schools = schools.filter(
                Q(name__icontains=search) |
                Q(name_ar__icontains=search) |
                Q(school_code__icontains=search)
            )
        
        # Get unique filter values for dropdowns in this CRE region
        all_delegation_schools = School.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            cre__iexact=assigned_delegation
        )
        
        # Get types
        types = all_delegation_schools.exclude(
            Q(school_type__isnull=True) | Q(school_type='')
        ).values_list('school_type', flat=True).distinct()
        
        # Get delegations (sub-regions within the CRE)
        delegations = all_delegation_schools.exclude(
            Q(delegation__isnull=True) | Q(delegation='')
        ).values_list('delegation', flat=True).distinct()
        
        filter_options = {
            'types': sorted([t for t in types if t]),
            'cres': sorted([d for d in delegations if d])
        }
        
        # Use aggregation to count users efficiently
        from django.db.models import Count, Q as QExpr
        
        schools_with_counts = schools.annotate(
            total_users=Count('users', distinct=True),
            teachers=Count('users', filter=QExpr(users__role='teacher'), distinct=True),
            students=Count('users', filter=QExpr(users__role='student'), distinct=True),
            advisors=Count('users', filter=QExpr(users__role='advisor'), distinct=True)
        ).values(
            'id', 'name', 'name_ar', 'address', 'latitude', 'longitude',
            'school_code', 'school_type', 'delegation', 'cre',
            'total_users', 'teachers', 'students', 'advisors'
        )
        
        # Convert QuerySet to list for JSON response
        school_data = list(schools_with_counts)
        
        return Response({
            'schools': school_data,
            'filter_options': filter_options,
            'total_count': len(school_data),
            'assigned_delegation': assigned_delegation
        })
    
    @action(detail=False, methods=['get'])
    def inspector_map(self, request):
        """Get schools map for inspector's assigned region only"""
        # Check if user is an inspector (not GPI)
        if request.user.role != 'inspector':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only inspectors can access this resource")
        
        # Get inspector's assignments
        from .models import InspectorAssignment
        active_assignments = InspectorAssignment.objects.filter(
            inspector=request.user,
            is_active=True
        )
        
        if not active_assignments.exists():
            return Response({
                'schools': [],
                'filter_options': {'types': [], 'delegations': []},
                'total_count': 0,
                'assigned_info': 'No assignments configured',
                'assignments_count': 0,
                'message': 'You have not been assigned to any schools yet. Please contact your administrator to configure your inspector assignments in the Minister Dashboard under "Inspector Assignments" tab.'
            })
        
        # Get filter parameters
        school_type = request.query_params.get('type')
        delegation_filter = request.query_params.get('delegation')
        search = request.query_params.get('search')
        
        # Build school queryset based on all active assignments
        schools_query = Q()
        assigned_info = []
        
        for assignment in active_assignments:
            if assignment.school_level == 'primary':
                # Primary schools: filter by region and E.PRIMAIRE type
                if assignment.assigned_region:
                    schools_query |= Q(
                        cre__iexact=assignment.assigned_region,
                        school_type__iexact='E.PRIMAIRE'
                    )
                    assigned_info.append(f"Primary schools in {assignment.assigned_region}")
            elif assignment.school_level == 'middle':
                # Middle schools: filter by subject and middle school types
                if assignment.assigned_subject:
                    schools_query |= Q(
                        school_type__in=['E.PREP', 'E.PREP.TECH']
                    )
                    assigned_info.append(f"Middle schools - {assignment.assigned_subject}")
            elif assignment.school_level == 'secondary':
                # Secondary schools: filter by subject and lycee type
                if assignment.assigned_subject:
                    schools_query |= Q(
                        school_type__iexact='LYCEE'
                    )
                    assigned_info.append(f"Secondary schools - {assignment.assigned_subject}")
        
        # Base queryset - only schools with geodata matching assignments
        schools = School.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        ).filter(schools_query)
        
        # Apply filters
        if school_type:
            schools = schools.filter(school_type__icontains=school_type)
        if delegation_filter:
            schools = schools.filter(delegation__icontains=delegation_filter)
        if search:
            schools = schools.filter(
                Q(name__icontains=search) |
                Q(name_ar__icontains=search) |
                Q(school_code__icontains=search)
            )
        
        # Get unique filter values for dropdowns based on assigned schools
        all_assigned_schools = School.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        ).filter(schools_query)
        
        # Get types
        types = all_assigned_schools.exclude(
            Q(school_type__isnull=True) | Q(school_type='')
        ).values_list('school_type', flat=True).distinct()
        
        # Get delegations
        delegations = all_assigned_schools.exclude(
            Q(delegation__isnull=True) | Q(delegation='')
        ).values_list('delegation', flat=True).distinct()
        
        filter_options = {
            'types': sorted([t for t in types if t]),
            'delegations': sorted([d for d in delegations if d])
        }
        
        # Use aggregation to count users efficiently
        from django.db.models import Count, Q as QExpr
        
        schools_with_counts = schools.annotate(
            total_users=Count('users', distinct=True),
            teachers=Count('users', filter=QExpr(users__role='teacher'), distinct=True),
            students=Count('users', filter=QExpr(users__role='student'), distinct=True),
            advisors=Count('users', filter=QExpr(users__role='advisor'), distinct=True)
        ).values(
            'id', 'name', 'name_ar', 'address', 'latitude', 'longitude',
            'school_code', 'school_type', 'delegation', 'cre',
            'total_users', 'teachers', 'students', 'advisors'
        )
        
        # Convert QuerySet to list for JSON response
        school_data = list(schools_with_counts)
        
        return Response({
            'schools': school_data,
            'filter_options': filter_options,
            'total_count': len(school_data),
            'assigned_info': ', '.join(assigned_info) if assigned_info else 'No active assignments',
            'assignments_count': active_assignments.count()
        })
    
    @action(detail=False, methods=['get'])
    def gpi_map(self, request):
        """Get all schools map with inspector assignments for GPI"""
        # Check if user is GPI
        if request.user.role != 'gpi':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only GPI can access this resource")
        
        # Get filter parameters
        school_type = request.query_params.get('type')
        cre_filter = request.query_params.get('cre')
        delegation_filter = request.query_params.get('delegation')
        search = request.query_params.get('search')
        
        # Base queryset - all schools with geodata
        schools = School.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        )
        
        # Apply filters
        if school_type:
            schools = schools.filter(school_type__icontains=school_type)
        if cre_filter:
            schools = schools.filter(cre__icontains=cre_filter)
        if delegation_filter:
            schools = schools.filter(delegation__icontains=delegation_filter)
        if search:
            schools = schools.filter(
                Q(name__icontains=search) |
                Q(name_ar__icontains=search) |
                Q(school_code__icontains=search)
            )
        
        # Get unique filter values
        all_schools = School.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        )
        
        types = all_schools.exclude(
            Q(school_type__isnull=True) | Q(school_type='')
        ).values_list('school_type', flat=True).distinct()
        
        cres = all_schools.exclude(
            Q(cre__isnull=True) | Q(cre='')
        ).values_list('cre', flat=True).distinct()
        
        delegations = all_schools.exclude(
            Q(delegation__isnull=True) | Q(delegation='')
        ).values_list('delegation', flat=True).distinct()
        
        filter_options = {
            'types': sorted([t for t in types if t]),
            'cres': sorted([c for c in cres if c]),
            'delegations': sorted([d for d in delegations if d])
        }
        
        # Use aggregation to count users efficiently
        from django.db.models import Count, Q as QExpr
        
        schools_with_counts = schools.annotate(
            total_users=Count('users', distinct=True),
            teachers=Count('users', filter=QExpr(users__role='teacher'), distinct=True),
            students=Count('users', filter=QExpr(users__role='student'), distinct=True),
            advisors=Count('users', filter=QExpr(users__role='advisor'), distinct=True)
        ).values(
            'id', 'name', 'name_ar', 'address', 'latitude', 'longitude',
            'school_code', 'school_type', 'delegation', 'cre',
            'total_users', 'teachers', 'students', 'advisors'
        )
        
        # Convert QuerySet to list
        school_data = list(schools_with_counts)
        
        # Get inspector assignments by region (CRE)
        inspectors = User.objects.filter(
            role='inspector',
            assigned_region__isnull=False
        ).exclude(assigned_region='').values('id', 'username', 'first_name', 'last_name', 'assigned_region')
        
        # Create a mapping of region -> inspectors
        inspector_assignments = {}
        for inspector in inspectors:
            region = inspector['assigned_region']
            if region not in inspector_assignments:
                inspector_assignments[region] = []
            inspector_assignments[region].append({
                'id': inspector['id'],
                'username': inspector['username'],
                'name': f"{inspector['first_name']} {inspector['last_name']}".strip() or inspector['username']
            })
        
        return Response({
            'schools': school_data,
            'filter_options': filter_options,
            'total_count': len(school_data),
            'inspector_assignments': inspector_assignments
        })


class TeacherStudentRelationshipViewSet(viewsets.ModelViewSet):
    queryset = TeacherStudentRelationship.objects.all()
    serializer_class = TeacherStudentRelationshipSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter relationships based on user role"""
        user = self.request.user
        queryset = self.queryset.filter(is_active=True)
        
        if user.role == 'teacher':
            # Teachers see only their own student relationships
            queryset = queryset.filter(teacher=user)
        elif user.role == 'student':
            # Students see only their own teacher relationships
            queryset = queryset.filter(student=user)
        elif user.role in ['admin', 'minister']:
            # Admins and ministers see all relationships in their school
            queryset = queryset.filter(teacher__school=user.school)
        else:
            queryset = queryset.none()
        
        return queryset.select_related('teacher', 'student')
    
    @action(detail=False, methods=['get'], url_path='my-students')
    def my_students(self, request):
        """Get all students assigned to the logged-in teacher"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Only teachers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        relationships = self.get_queryset().filter(teacher=request.user)
        serializer = self.get_serializer(relationships, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='my-teachers')
    def my_teachers(self, request):
        """Get all teachers assigned to the logged-in student"""
        if request.user.role != 'student':
            return Response(
                {'error': 'Only students can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        relationships = self.get_queryset().filter(student=request.user)
        serializer = self.get_serializer(relationships, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post', 'patch'], url_path='rate-student')
    def rate_student(self, request, pk=None):
        """Teacher rates a student"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Only teachers can rate students'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        relationship = self.get_object()
        
        # Verify the teacher owns this relationship
        if relationship.teacher != request.user:
            return Response(
                {'error': 'You can only rate your own students'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        rating = request.data.get('rating')
        comments = request.data.get('comments', '')
        
        if rating is not None:
            if not (1 <= rating <= 5):
                return Response(
                    {'error': 'Rating must be between 1 and 5'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            relationship.rating_by_teacher = rating
        
        if comments is not None:
            relationship.comments_by_teacher = comments
        
        relationship.save()
        serializer = self.get_serializer(relationship)
        return Response({
            'message': 'Rating updated successfully',
            'relationship': serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post', 'patch'], url_path='rate-teacher')
    def rate_teacher(self, request, pk=None):
        """Student rates a teacher"""
        if request.user.role != 'student':
            return Response(
                {'error': 'Only students can rate teachers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        relationship = self.get_object()
        
        # Verify the student owns this relationship
        if relationship.student != request.user:
            return Response(
                {'error': 'You can only rate your own teachers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        rating = request.data.get('rating')
        comments = request.data.get('comments', '')
        
        if rating is not None:
            if not (1 <= rating <= 5):
                return Response(
                    {'error': 'Rating must be between 1 and 5'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            relationship.rating_by_student = rating
        
        if comments is not None:
            relationship.comments_by_student = comments
        
        relationship.save()
        serializer = self.get_serializer(relationship)
        return Response({
            'message': 'Rating updated successfully',
            'relationship': serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='available-students')
    def available_students(self, request):
        """Get list of students that can be assigned to the teacher"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Only teachers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get students in the same school not already assigned
        assigned_student_ids = TeacherStudentRelationship.objects.filter(
            teacher=request.user,
            is_active=True
        ).values_list('student_id', flat=True)
        
        available_students = User.objects.filter(
            school=request.user.school,
            role='student'
        ).exclude(id__in=assigned_student_ids)
        
        from .serializers import UserBasicSerializer
        serializer = UserBasicSerializer(available_students, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='assign-student')
    def assign_student(self, request):
        """Teacher or admin assigns a student to a teacher"""
        if request.user.role not in ['teacher', 'admin']:
            return Response(
                {'error': 'Only teachers and admins can assign students'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        student_id = request.data.get('student_id')
        teacher_id = request.data.get('teacher_id', request.user.id if request.user.role == 'teacher' else None)
        
        if not student_id or not teacher_id:
            return Response(
                {'error': 'Both student_id and teacher_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        teacher = get_object_or_404(User, id=teacher_id, role='teacher')
        student = get_object_or_404(User, id=student_id, role='student')
        
        # Verify same school
        if teacher.school != student.school:
            return Response(
                {'error': 'Teacher and student must be from the same school'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create or reactivate relationship
        relationship, created = TeacherStudentRelationship.objects.get_or_create(
            teacher=teacher,
            student=student,
            defaults={'is_active': True}
        )
        
        if not created:
            relationship.is_active = True
            relationship.save()
        
        serializer = self.get_serializer(relationship)
        return Response({
            'message': 'Student assigned successfully' if created else 'Relationship reactivated',
            'relationship': serializer.data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class AdvisorReviewViewSet(viewsets.ModelViewSet):
    queryset = AdvisorReview.objects.all()
    serializer_class = AdvisorReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter reviews based on user role"""
        user = self.request.user
        queryset = self.queryset.select_related('advisor', 'lesson', 'mcq_test', 'qa_test')
        
        if user.role == 'advisor':
            # Advisors see only their own reviews
            queryset = queryset.filter(advisor=user)
        elif user.role == 'teacher':
            # Teachers see reviews on their own content
            advisor_subject = user.subjects[0] if user.subjects else None
            queryset = queryset.filter(
                Q(lesson__created_by=user) |
                Q(mcq_test__lesson__created_by=user) |
                Q(qa_test__lesson__created_by=user)
            )
        elif user.role in ['admin', 'minister']:
            # Admins and ministers see all reviews in their school
            queryset = queryset.filter(advisor__school=user.school)
        else:
            queryset = queryset.none()
        
        return queryset
    
    def perform_create(self, serializer):
        """Automatically set advisor to current user"""
        serializer.save(advisor=self.request.user)
    
    @action(detail=False, methods=['get'], url_path='my-reviews')
    def my_reviews(self, request):
        """Get all reviews by the logged-in advisor"""
        if request.user.role != 'advisor':
            return Response(
                {'error': 'Only advisors can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reviews = self.get_queryset().filter(advisor=request.user)
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='reviews-on-my-content')
    def reviews_on_my_content(self, request):
        """Get all reviews on the logged-in teacher's content"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Only teachers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reviews = self.get_queryset().filter(
            Q(lesson__created_by=request.user) |
            Q(mcq_test__lesson__created_by=request.user) |
            Q(qa_test__lesson__created_by=request.user)
        )
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='advisor-analytics')
    def advisor_analytics(self, request):
        """Comprehensive analytics dashboard for advisors"""
        if request.user.role != 'advisor':
            return Response(
                {'error': 'Only advisors can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Try to get cached data
        cache_key = f'advisor_analytics_{request.user.id}'
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        
        from core.models import Lesson, Test, QATest, TestSubmission
        from django.db.models import Count, Avg, Q, F, Max
        from django.utils import timezone
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        
        advisor = request.user
        now = timezone.now()
        
        # Get advisor's subject (assuming first subject)
        advisor_subject = advisor.subjects[0] if advisor.subjects else None
        
        # Find all teachers in the same school
        # Note: Can't use __contains on JSONField with SQLite, so filter in Python
        all_school_teachers = User.objects.filter(
            school=advisor.school,
            role='teacher',
            is_active=True
        )
        
        # Filter teachers by subject in Python (SQLite doesn't support contains on JSON)
        if advisor_subject:
            supervised_teachers = [
                teacher for teacher in all_school_teachers 
                if teacher.subjects and advisor_subject in teacher.subjects
            ]
        else:
            supervised_teachers = list(all_school_teachers)
        
        # Review statistics
        all_reviews = AdvisorReview.objects.filter(advisor=advisor)
        total_reviews = all_reviews.count()
        
        # Reviews by type
        lesson_reviews = all_reviews.filter(review_type='lesson').count()
        mcq_reviews = all_reviews.filter(review_type='mcq_test').count()
        qa_reviews = all_reviews.filter(review_type='qa_test').count()
        
        # Average rating given
        avg_rating_given = all_reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        
        # Content approval rates (rating >= 3 is considered approved)
        approved_content = all_reviews.filter(rating__gte=3).count()
        approval_rate = (approved_content / total_reviews * 100) if total_reviews > 0 else 0
        
        # Response time analysis (time between content creation and review)
        response_times = []
        for review in all_reviews.select_related('lesson', 'mcq_test', 'qa_test'):
            if review.lesson:
                content_created = review.lesson.created_at
            elif review.mcq_test:
                content_created = review.mcq_test.created_at
            elif review.qa_test:
                content_created = review.qa_test.created_at
            else:
                continue
            
            time_diff = (review.created_at - content_created).total_seconds() / 3600  # hours
            response_times.append(time_diff)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Chapter progress notifications handled
        chapter_notifications = ChapterProgressNotification.objects.filter(advisor=advisor)
        total_notifications = chapter_notifications.count()
        confirmed_notifications = chapter_notifications.filter(status='confirmed').count()
        pending_notifications = chapter_notifications.filter(status='pending').count()
        
        # Teacher performance overview
        teacher_stats = []
        for teacher in supervised_teachers:
            lessons_created = Lesson.objects.filter(created_by=teacher).count()
            tests_created = Test.objects.filter(lesson__created_by=teacher).count() + \
                           QATest.objects.filter(lesson__created_by=teacher).count()
            
            # Average student score for this teacher's content
            teacher_submissions = TestSubmission.objects.filter(
                test__lesson__created_by=teacher,
                is_final=True
            )
            avg_student_score = teacher_submissions.aggregate(Avg('score'))['score__avg'] or 0
            
            # Reviews on this teacher's content
            teacher_reviews = all_reviews.filter(
                Q(lesson__created_by=teacher) |
                Q(mcq_test__lesson__created_by=teacher) |
                Q(qa_test__lesson__created_by=teacher)
            )
            avg_advisor_rating = teacher_reviews.aggregate(Avg('rating'))['rating__avg'] or 0
            
            # Student relationships
            student_count = TeacherStudentRelationship.objects.filter(
                teacher=teacher,
                is_active=True
            ).count()
            
            # Recent activity (last 30 days)
            recent_activity = Lesson.objects.filter(
                created_by=teacher,
                created_at__gte=now - timedelta(days=30)
            ).count() + Test.objects.filter(
                lesson__created_by=teacher,
                created_at__gte=now - timedelta(days=30)
            ).count()
            
            teacher_stats.append({
                'teacher_id': teacher.id,
                'teacher_name': f"{teacher.first_name} {teacher.last_name}",
                'email': teacher.email,
                'subjects': teacher.subjects,
                'lessons_created': lessons_created,
                'tests_created': tests_created,
                'students': student_count,
                'avg_student_score': round(avg_student_score, 2),
                'avg_advisor_rating': round(avg_advisor_rating, 2),
                'total_reviews': teacher_reviews.count(),
                'recent_activity_30d': recent_activity,
                'needs_attention': avg_advisor_rating < 3 or recent_activity == 0
            })
        
        # Sort by needs attention, then by rating
        teacher_stats.sort(key=lambda x: (not x['needs_attention'], -x['avg_advisor_rating']))
        
        # Monthly trends for last 12 months
        monthly_trends = []
        for i in range(11, -1, -1):
            month_start = (now - relativedelta(months=i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + relativedelta(months=1)) - timedelta(seconds=1)
            
            # Reviews given in month
            month_reviews = all_reviews.filter(
                created_at__gte=month_start,
                created_at__lte=month_end
            )
            reviews_count = month_reviews.count()
            month_avg_rating = month_reviews.aggregate(Avg('rating'))['rating__avg'] or 0
            
            # Content created by supervised teachers
            month_lessons = Lesson.objects.filter(
                created_by__in=supervised_teachers,
                created_at__gte=month_start,
                created_at__lte=month_end
            ).count()
            
            month_tests = Test.objects.filter(
                lesson__created_by__in=supervised_teachers,
                created_at__gte=month_start,
                created_at__lte=month_end
            ).count()
            
            # Student performance for supervised teachers
            month_submissions = TestSubmission.objects.filter(
                test__lesson__created_by__in=supervised_teachers,
                submitted_at__gte=month_start,
                submitted_at__lte=month_end,
                is_final=True
            )
            month_avg_score = month_submissions.aggregate(Avg('score'))['score__avg'] or 0
            
            monthly_trends.append({
                'month': month_start.strftime('%Y-%m'),
                'month_name': month_start.strftime('%b %Y'),
                'reviews_given': reviews_count,
                'avg_rating_given': round(month_avg_rating, 2),
                'lessons_created': month_lessons,
                'tests_created': month_tests,
                'avg_student_score': round(month_avg_score, 2),
                'submissions': month_submissions.count()
            })
        
        # Top performing teachers (highest student scores)
        top_teachers = sorted(teacher_stats, key=lambda x: x['avg_student_score'], reverse=True)[:5]
        
        # Teachers needing support
        needs_support = [t for t in teacher_stats if t['needs_attention']][:5]
        
        response_data = {
            'advisor_info': {
                'name': f"{advisor.first_name} {advisor.last_name}",
                'email': advisor.email,
                'subject': advisor_subject,
                'school': advisor.school.name if advisor.school else None
            },
            'overview': {
                'total_teachers_supervised': len(supervised_teachers),
                'total_reviews_given': total_reviews,
                'avg_rating_given': round(avg_rating_given, 2),
                'approval_rate': round(approval_rate, 2),
                'avg_response_time_hours': round(avg_response_time, 2),
                'pending_notifications': pending_notifications
            },
            'review_breakdown': {
                'lesson_reviews': lesson_reviews,
                'mcq_test_reviews': mcq_reviews,
                'qa_test_reviews': qa_reviews,
                'total': total_reviews
            },
            'teacher_performance': {
                'all_teachers': teacher_stats,
                'top_performers': top_teachers,
                'needs_support': needs_support
            },
            'monthly_trends': monthly_trends,
            'notifications': {
                'total': total_notifications,
                'confirmed': confirmed_notifications,
                'pending': pending_notifications,
                'confirmation_rate': round(confirmed_notifications / total_notifications * 100, 2) if total_notifications > 0 else 0
            }
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, response_data, 300)
        return Response(response_data)


class GroupChatViewSet(viewsets.ModelViewSet):
    queryset = GroupChat.objects.all()
    serializer_class = GroupChatSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter chats based on user role"""
        user = self.request.user
        queryset = self.queryset.select_related('advisor').prefetch_related('teachers', 'messages')
        
        if user.role == 'advisor':
            # Advisors see chats they created
            queryset = queryset.filter(advisor=user)
        elif user.role == 'teacher':
            # Teachers see chats they're part of
            queryset = queryset.filter(teachers=user)
        elif user.role in ['admin', 'minister']:
            # Admins and ministers see all chats in their school
            queryset = queryset.filter(advisor__school=user.school)
        else:
            queryset = queryset.none()
        
        return queryset.filter(is_active=True)
    
    def perform_create(self, serializer):
        """Automatically set advisor to current user"""
        serializer.save(advisor=self.request.user)
    
    @action(detail=False, methods=['get'], url_path='my-chats')
    def my_chats(self, request):
        """Get all chats for the logged-in user"""
        chats = self.get_queryset()
        serializer = self.get_serializer(chats, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='create-with-teachers')
    def create_with_teachers(self, request):
        """Advisor creates a new chat with selected teachers"""
        if request.user.role != 'advisor':
            return Response(
                {'error': 'Only advisors can create group chats'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        name = request.data.get('name')
        teacher_ids = request.data.get('teacher_ids', [])
        
        if not name:
            return Response(
                {'error': 'Chat name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not teacher_ids:
            return Response(
                {'error': 'At least one teacher must be added'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get advisor's subject
        advisor_subject = request.user.subjects[0] if request.user.subjects else None
        if not advisor_subject:
            return Response(
                {'error': 'Advisor must have a subject assigned'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate all teachers teach the same subject
        teachers = User.objects.filter(
            id__in=teacher_ids,
            role='teacher',
            school=request.user.school
        )
        
        for teacher in teachers:
            if advisor_subject not in (teacher.subjects or []):
                return Response(
                    {'error': f'Teacher {teacher.username} does not teach {advisor_subject}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Create the chat
        chat = GroupChat.objects.create(
            name=name,
            subject=advisor_subject,
            advisor=request.user
        )
        chat.teachers.set(teachers)
        
        serializer = self.get_serializer(chat)
        return Response({
            'message': 'Chat created successfully',
            'chat': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], url_path='subject-teachers')
    def subject_teachers(self, request):
        """Get all teachers in advisor's subject"""
        if request.user.role != 'advisor':
            return Response(
                {'error': 'Only advisors can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        advisor_subject = request.user.subjects[0] if request.user.subjects else None
        if not advisor_subject:
            return Response(
                {'error': 'Advisor must have a subject assigned'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all teachers in the same school
        all_teachers = User.objects.filter(
            role='teacher',
            school=request.user.school
        )
        
        # Filter teachers who teach the advisor's subject
        teachers = [
            teacher for teacher in all_teachers
            if teacher.subjects and advisor_subject in teacher.subjects
        ]
        
        serializer = UserBasicSerializer(teachers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], url_path='add-teacher')
    def add_teacher(self, request, pk=None):
        """Add a teacher to an existing chat (advisor only)"""
        chat = self.get_object()
        
        if request.user.role != 'advisor' or chat.advisor != request.user:
            return Response(
                {'error': 'Only the chat creator can add teachers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        teacher_id = request.data.get('teacher_id')
        if not teacher_id:
            return Response(
                {'error': 'teacher_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            teacher = User.objects.get(id=teacher_id, role='teacher', school=request.user.school)
            
            # Verify teacher teaches the chat subject
            if chat.subject not in (teacher.subjects or []):
                return Response(
                    {'error': f'Teacher does not teach {chat.get_subject_display()}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            chat.teachers.add(teacher)
            serializer = self.get_serializer(chat)
            return Response({
                'message': f'Teacher {teacher.username} added to chat',
                'chat': serializer.data
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response(
                {'error': 'Teacher not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'], url_path='remove-teacher')
    def remove_teacher(self, request, pk=None):
        """Remove a teacher from a chat (advisor only)"""
        chat = self.get_object()
        
        if request.user.role != 'advisor' or chat.advisor != request.user:
            return Response(
                {'error': 'Only the chat creator can remove teachers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        teacher_id = request.data.get('teacher_id')
        if not teacher_id:
            return Response(
                {'error': 'teacher_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            teacher = User.objects.get(id=teacher_id)
            
            if teacher not in chat.teachers.all():
                return Response(
                    {'error': 'Teacher is not in this chat'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            chat.teachers.remove(teacher)
            serializer = self.get_serializer(chat)
            return Response({
                'message': f'Teacher {teacher.username} removed from chat',
                'chat': serializer.data
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response(
                {'error': 'Teacher not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class ChatMessageViewSet(viewsets.ModelViewSet):
    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    
    def get_queryset(self):
        """Filter messages based on user's chat membership"""
        user = self.request.user
        queryset = self.queryset.select_related('chat', 'sender')
        
        if user.role == 'advisor':
            # Advisors see messages in chats they created
            queryset = queryset.filter(chat__advisor=user)
        elif user.role == 'teacher':
            # Teachers see messages in chats they're part of
            queryset = queryset.filter(chat__teachers=user)
        elif user.role in ['admin', 'minister']:
            # Admins and ministers see all messages in their school
            queryset = queryset.filter(chat__advisor__school=user.school)
        else:
            queryset = queryset.none()
        
        return queryset
    
    def perform_create(self, serializer):
        """Automatically set sender to current user"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Request data: {self.request.data}")
        logger.info(f"Request FILES: {self.request.FILES}")
        logger.info(f"Content type: {self.request.content_type}")
        serializer.save(sender=self.request.user)
    
    def perform_update(self, serializer):
        """Only allow users to edit their own messages"""
        message = self.get_object()
        if message.sender != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only edit your own messages")
        serializer.save(is_edited=True)
    
    def perform_destroy(self, instance):
        """Only allow users to delete their own messages"""
        if instance.sender != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only delete your own messages")
        instance.delete()
    
    @action(detail=False, methods=['get'], url_path='chat/(?P<chat_id>[^/.]+)')
    def chat_messages(self, request, chat_id=None):
        """Get all messages for a specific chat"""
        chat = get_object_or_404(GroupChat, id=chat_id)
        
        # Verify user has access to this chat
        if request.user.role == 'advisor' and chat.advisor != request.user:
            return Response(
                {'error': 'You do not have access to this chat'},
                status=status.HTTP_403_FORBIDDEN
            )
        elif request.user.role == 'teacher' and request.user not in chat.teachers.all():
            return Response(
                {'error': 'You do not have access to this chat'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        messages = self.get_queryset().filter(chat=chat).order_by('created_at')
        
        # Mark all messages in this chat as read by the current user (except their own)
        for message in messages:
            message.mark_as_read_by(request.user)
        
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='send')
    def send_message(self, request):
        """Send a message to a chat"""
        chat_id = request.data.get('chat_id')
        message_text = request.data.get('message')
        
        if not chat_id or not message_text:
            return Response(
                {'error': 'chat_id and message are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        chat = get_object_or_404(GroupChat, id=chat_id)
        
        # Verify user has access to this chat
        if request.user.role == 'advisor' and chat.advisor != request.user:
            return Response(
                {'error': 'You do not have access to this chat'},
                status=status.HTTP_403_FORBIDDEN
            )
        elif request.user.role == 'teacher' and request.user not in chat.teachers.all():
            return Response(
                {'error': 'You do not have access to this chat'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create the message
        chat_message = ChatMessage.objects.create(
            chat=chat,
            sender=request.user,
            message=message_text
        )
        
        # Update chat's updated_at timestamp
        chat.save()
        
        serializer = self.get_serializer(chat_message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        """Mark a message as read by the current user"""
        message = self.get_object()
        message.mark_as_read_by(request.user)
        
        serializer = self.get_serializer(message)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='mark-chat-read')
    def mark_chat_read(self, request):
        """Mark all messages in a chat as read by the current user"""
        chat_id = request.data.get('chat_id')
        
        if not chat_id:
            return Response(
                {'error': 'chat_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        chat = get_object_or_404(GroupChat, id=chat_id)
        
        # Verify user has access to this chat
        if request.user.role == 'advisor' and chat.advisor != request.user:
            return Response(
                {'error': 'You do not have access to this chat'},
                status=status.HTTP_403_FORBIDDEN
            )
        elif request.user.role == 'teacher' and request.user not in chat.teachers.all():
            return Response(
                {'error': 'You do not have access to this chat'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Mark all messages as read
        messages = self.get_queryset().filter(chat=chat)
        marked_count = 0
        for message in messages:
            if not message.is_read_by(request.user):
                message.mark_as_read_by(request.user)
                marked_count += 1
        
        return Response({
            'message': f'{marked_count} messages marked as read',
            'chat_id': chat_id
        }, status=status.HTTP_200_OK)


class ParentStudentRelationshipViewSet(viewsets.ModelViewSet):
    """Manage parent-student relationships"""
    queryset = ParentStudentRelationship.objects.all()
    serializer_class = ParentStudentRelationshipSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        if user.role == 'parent':
            return self.queryset.filter(parent=user, is_active=True)
        elif user.role == 'student':
            return self.queryset.filter(student=user, is_active=True)
        elif user.role in ['admin', 'teacher']:
            return self.queryset.all()
        return self.queryset.none()
    
    @action(detail=False, methods=['get'])
    def my_students(self, request):
        """Get all students tracked by the current parent"""
        if request.user.role != 'parent':
            return Response(
                {'error': 'Only parents can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        relationships = self.queryset.filter(parent=request.user, is_active=True)
        serializer = self.get_serializer(relationships, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def assign_student(self, request):
        """Assign a student to track"""
        if request.user.role != 'parent':
            return Response(
                {'error': 'Only parents can assign students'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        student_id = request.data.get('student_id')
        relationship_type = request.data.get('relationship_type', 'parent')
        is_primary = request.data.get('is_primary', False)
        
        if not student_id:
            return Response(
                {'error': 'student_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            student = User.objects.get(id=student_id, role='student')
        except User.DoesNotExist:
            return Response(
                {'error': 'Student not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create or update relationship
        relationship, created = ParentStudentRelationship.objects.get_or_create(
            parent=request.user,
            student=student,
            defaults={
                'relationship_type': relationship_type,
                'is_primary': is_primary,
                'is_active': True
            }
        )
        
        if not created:
            relationship.is_active = True
            relationship.save()
        
        serializer = self.get_serializer(relationship)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ParentDashboardViewSet(viewsets.ViewSet):
    """Parent dashboard with student performance data"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def student_performance(self, request):
        """Get comprehensive performance data for all tracked students"""
        if request.user.role != 'parent':
            return Response(
                {'error': 'Only parents can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get all tracked students
        relationships = ParentStudentRelationship.objects.filter(
            parent=request.user,
            is_active=True
        ).select_related('student')
        
        performance_data = []
        
        for rel in relationships:
            student = rel.student
            
            # Get portfolio data
            from core.models import Portfolio
            try:
                portfolio = Portfolio.objects.get(student=student)
                test_results = portfolio.test_results or []
            except Portfolio.DoesNotExist:
                test_results = []
            
            # Gamification: Calculate XP and level based on test performance
            xp_points = 0
            level = 1
            streak_days = 0
            
            if test_results:
                for test in test_results:
                    score = test.get('score', 0)
                    # XP calculation based on score:
                    # Base XP: 10 points per test
                    # Bonus XP: up to 40 points based on score (0-100%)
                    # Perfect score (100%): 50 XP total
                    # Good score (80-99%): 42-49 XP
                    # Average score (60-79%): 34-41 XP
                    # Below average (<60%): 10-33 XP
                    base_xp = 10
                    bonus_xp = int(score * 0.4)  # 0-40 bonus points
                    test_xp = base_xp + bonus_xp
                    xp_points += test_xp
                
                # Level calculation: Every 200 XP = 1 level
                # Level 1: 0-199 XP
                # Level 2: 200-399 XP
                # Level 3: 400-599 XP, etc.
                level = (xp_points // 200) + 1
                
                # Streak calculation: Check if student has tests in consecutive periods
                # Sort tests by date
                sorted_tests = sorted(
                    [t for t in test_results if t.get('date')],
                    key=lambda x: x.get('date', ''),
                    reverse=True
                )
                
                if sorted_tests:
                    from datetime import datetime, timedelta
                    try:
                        last_test_date = datetime.fromisoformat(sorted_tests[0]['date'].replace('Z', '+00:00'))
                        today = datetime.now(last_test_date.tzinfo)
                        
                        # Check if last test was within the last 7 days
                        days_since_last = (today - last_test_date).days
                        if days_since_last <= 7:
                            # Count consecutive weeks with at least one test
                            current_date = last_test_date
                            streak_days = 1
                            
                            for test in sorted_tests[1:]:
                                test_date = datetime.fromisoformat(test['date'].replace('Z', '+00:00'))
                                days_diff = (current_date - test_date).days
                                
                                # If test is within 7 days of previous, continue streak
                                if days_diff <= 7:
                                    streak_days += 1
                                    current_date = test_date
                                else:
                                    break
                    except (ValueError, KeyError, AttributeError):
                        streak_days = 0
            
            # Note: strengths and weaknesses are intentionally excluded for parent privacy
            
            # Calculate overall average
            if test_results:
                total_score = sum(test.get('score', 0) for test in test_results)
                overall_average = total_score / len(test_results)
            else:
                overall_average = 0
            
            # Get recent tests (last 5)
            recent_tests = sorted(test_results, key=lambda x: x.get('date', ''), reverse=True)[:5]
            
            # Get assigned teachers
            teacher_relationships = TeacherStudentRelationship.objects.filter(
                student=student,
                is_active=True
            ).select_related('teacher')
            
            assigned_teachers = []
            for tr in teacher_relationships:
                assigned_teachers.append({
                    'id': tr.teacher.id,
                    'name': tr.teacher.get_full_name() or tr.teacher.username,
                    'email': tr.teacher.email,
                    'subjects': tr.teacher.subjects,
                    'rating': tr.rating_by_teacher,
                    'comments': tr.comments_by_teacher
                })
            
            performance_data.append({
                'student': UserBasicSerializer(student).data,
                'overall_average': round(overall_average, 2),
                'total_tests': len(test_results),
                'recent_tests': recent_tests,
                'portfolio_summary': {
                    'total_achievements': len(portfolio.achievements) if hasattr(portfolio, 'achievements') else 0,
                    'summary': portfolio.summary if hasattr(portfolio, 'summary') else ''
                },
                'assigned_teachers': assigned_teachers,
                # strengths and weaknesses are intentionally excluded for privacy
                'xp_points': xp_points,
                'level': level,
                'streak_days': streak_days,
                'relationship_type': rel.get_relationship_type_display()
            })
        
        return Response(performance_data)
    
    @action(detail=False, methods=['get'], url_path='student/(?P<student_id>[^/.]+)')
    def student_detail(self, request, student_id=None):
        """Get detailed performance for a specific student"""
        if request.user.role != 'parent':
            return Response(
                {'error': 'Only parents can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify parent has access to this student
        try:
            relationship = ParentStudentRelationship.objects.get(
                parent=request.user,
                student_id=student_id,
                is_active=True
            )
        except ParentStudentRelationship.DoesNotExist:
            return Response(
                {'error': 'You do not have access to this student'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Return detailed performance (similar to above but for one student)
        # Implementation similar to student_performance but for single student
        return Response({'message': 'Detailed performance data'})


class ParentTeacherChatViewSet(viewsets.ModelViewSet):
    """Manage parent-teacher chats"""
    queryset = ParentTeacherChat.objects.all()
    serializer_class = ParentTeacherChatSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter chats based on user role"""
        user = self.request.user
        if user.role == 'parent':
            return self.queryset.filter(parent=user, is_active=True)
        elif user.role == 'teacher':
            return self.queryset.filter(teacher=user, is_active=True)
        return self.queryset.none()
    
    @action(detail=False, methods=['get'])
    def my_chats(self, request):
        """Get all active chats for current user"""
        chats = self.get_queryset()
        serializer = self.get_serializer(chats, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def start_chat(self, request):
        """Start a new chat with a teacher"""
        if request.user.role != 'parent':
            return Response(
                {'error': 'Only parents can start chats with teachers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        teacher_id = request.data.get('teacher_id')
        student_id = request.data.get('student_id')
        subject = request.data.get('subject', '')
        
        if not teacher_id or not student_id:
            return Response(
                {'error': 'teacher_id and student_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify parent has access to student
        try:
            ParentStudentRelationship.objects.get(
                parent=request.user,
                student_id=student_id,
                is_active=True
            )
        except ParentStudentRelationship.DoesNotExist:
            return Response(
                {'error': 'You do not have access to this student'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            teacher = User.objects.get(id=teacher_id, role='teacher')
            student = User.objects.get(id=student_id, role='student')
        except User.DoesNotExist:
            return Response(
                {'error': 'Teacher or student not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create or get existing chat
        chat, created = ParentTeacherChat.objects.get_or_create(
            parent=request.user,
            teacher=teacher,
            student=student,
            defaults={'subject': subject, 'is_active': True}
        )
        
        if not created:
            chat.is_active = True
            chat.save()
        
        serializer = self.get_serializer(chat)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get all messages in a chat"""
        chat = self.get_object()
        messages = chat.messages.all()
        serializer = ParentTeacherMessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message in the chat"""
        chat = self.get_object()
        message_text = request.data.get('message', '')
        file_attachment = request.FILES.get('file_attachment')
        
        if not message_text and not file_attachment:
            return Response(
                {'error': 'Message or file attachment is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message = ParentTeacherMessage.objects.create(
            chat=chat,
            sender=request.user,
            message=message_text,
            file_attachment=file_attachment
        )
        
        # Update chat timestamp
        chat.save()  # Triggers updated_at
        
        serializer = ParentTeacherMessageSerializer(message, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        """Mark all messages in chat as read"""
        chat = self.get_object()
        chat.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        return Response({'message': 'Messages marked as read'})


class ParentTeacherMessageViewSet(viewsets.ModelViewSet):
    """Manage individual parent-teacher messages"""
    queryset = ParentTeacherMessage.objects.all()
    serializer_class = ParentTeacherMessageSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    
    def get_queryset(self):
        """Filter messages based on chat access"""
        user = self.request.user
        if user.role == 'parent':
            return self.queryset.filter(chat__parent=user)
        elif user.role == 'teacher':
            return self.queryset.filter(chat__teacher=user)
        return self.queryset.none()
    
    @action(detail=True, methods=['patch'])
    def edit(self, request, pk=None):
        """Edit a message"""
        message = self.get_object()
        
        if message.sender != request.user:
            return Response(
                {'error': 'You can only edit your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_text = request.data.get('message')
        if new_text:
            message.message = new_text
            message.is_edited = True
            message.save()
        
        serializer = self.get_serializer(message)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        """Mark a specific message as read"""
        message = self.get_object()
        message.is_read = True
        message.save()
        
        serializer = self.get_serializer(message)
        return Response(serializer.data)


class TeacherProgressViewSet(viewsets.ModelViewSet):
    """Manage teacher curriculum progress"""
    queryset = TeacherProgress.objects.all()
    serializer_class = TeacherProgressSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        queryset = self.queryset
        
        if user.role == 'teacher':
            # Teachers see only their own progress
            queryset = queryset.filter(teacher=user)
        elif user.role == 'advisor':
            # Advisors see progress of teachers in their subject
            advisor_subject = user.subjects[0] if user.subjects else None
            if advisor_subject:
                queryset = queryset.filter(subject=advisor_subject, teacher__school=user.school)
            else:
                queryset = queryset.none()
        elif user.role in ['admin', 'minister']:
            # Admins and ministers see all progress in their school
            queryset = queryset.filter(teacher__school=user.school)
        else:
            queryset = queryset.none()
        
        # Filter by specific teacher if requested
        teacher_id = self.request.query_params.get('teacher', None)
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def my_progress(self, request):
        """Get current teacher's progress across all subjects"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Only teachers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        progress = self.queryset.filter(teacher=request.user)
        serializer = self.get_serializer(progress, many=True)
        return Response(serializer.data)


class ChapterProgressNotificationViewSet(viewsets.ModelViewSet):
    """Manage chapter progression notifications for advisors"""
    queryset = ChapterProgressNotification.objects.all()
    serializer_class = ChapterProgressNotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        queryset = self.queryset
        
        if user.role == 'advisor':
            # Advisors see only notifications assigned to them
            queryset = queryset.filter(advisor=user)
        elif user.role == 'teacher':
            # Teachers see notifications about their own progress
            queryset = queryset.filter(teacher_progress__teacher=user)
        elif user.role in ['admin', 'minister']:
            # Admins and ministers see all notifications in their school
            queryset = queryset.filter(teacher_progress__teacher__school=user.school)
        else:
            queryset = queryset.none()
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Advisor confirms chapter progression"""
        if request.user.role != 'advisor':
            return Response(
                {'error': 'Only advisors can confirm chapter progression'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        notification = self.get_object()
        
        if notification.advisor != request.user:
            return Response(
                {'error': 'You can only confirm your own notifications'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from django.utils import timezone
        notification.status = 'confirmed'
        notification.reviewed_at = timezone.now()
        notification.advisor_notes = request.data.get('notes', '')
        notification.save()
        
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Advisor rejects chapter progression and reverts"""
        if request.user.role != 'advisor':
            return Response(
                {'error': 'Only advisors can reject chapter progression'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        notification = self.get_object()
        
        if notification.advisor != request.user:
            return Response(
                {'error': 'You can only reject your own notifications'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from django.utils import timezone
        notification.status = 'rejected'
        notification.reviewed_at = timezone.now()
        notification.advisor_notes = request.data.get('notes', 'Reverted to previous chapter')
        notification.save()
        
        # Revert teacher progress to previous chapter
        progress = notification.teacher_progress
        progress.current_chapter = notification.previous_chapter
        progress.chapter_number = notification.previous_chapter_number
        progress.save()
        
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get all pending notifications for current advisor"""
        if request.user.role != 'advisor':
            return Response(
                {'error': 'Only advisors can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        notifications = self.get_queryset().filter(status='pending')
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)


class TeacherAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """View teacher analytics (read-only, auto-calculated)"""
    queryset = TeacherAnalytics.objects.all()
    serializer_class = TeacherAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        queryset = self.queryset
        
        if user.role == 'teacher':
            # Teachers see only their own analytics
            queryset = queryset.filter(teacher=user)
        elif user.role == 'advisor':
            # Advisors see analytics of teachers in their subject
            advisor_subject = user.subjects[0] if user.subjects else None
            if advisor_subject:
                # Get all teachers in the school (SQLite doesn't support JSON __contains)
                all_teachers = User.objects.filter(
                    role='teacher',
                    school=user.school
                )
                # Filter by subject using Python
                matching_teacher_ids = [
                    t.id for t in all_teachers 
                    if t.subjects and advisor_subject in t.subjects
                ]
                queryset = queryset.filter(teacher_id__in=matching_teacher_ids)
            else:
                queryset = queryset.none()
        elif user.role in ['admin', 'minister']:
            # Admins and ministers see all analytics in their school
            queryset = queryset.filter(teacher__school=user.school)
        else:
            queryset = queryset.none()
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def subject_teachers(self, request):
        """Get analytics for all teachers in advisor's subject"""
        if request.user.role != 'advisor':
            return Response(
                {'error': 'Only advisors can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        advisor_subject = request.user.subjects[0] if request.user.subjects else None
        
        if not advisor_subject:
            return Response([])
        
        # Get all teachers in advisor's subject
        # Note: We fetch all teachers and filter in Python because SQLite doesn't support JSON contains
        all_teachers = User.objects.filter(
            role='teacher',
            school=request.user.school
        )
        teachers = [t for t in all_teachers if t.subjects and advisor_subject in t.subjects]
        
        analytics_data = []
        for teacher in teachers:
            # Get or create analytics
            analytics, created = TeacherAnalytics.objects.get_or_create(teacher=teacher)
            
            # Ensure teacher has progress records for each subject they teach
            for subject in teacher.subjects or []:
                # Create progress for common grade levels if not exists
                for grade_level in ['grade_9', 'grade_10', 'grade_11', 'grade_12']:
                    TeacherProgress.objects.get_or_create(
                        teacher=teacher,
                        subject=subject,
                        grade_level=grade_level,
                        defaults={
                            'current_chapter': 'Introduction',
                            'chapter_number': 1,
                            'total_chapters': 12
                        }
                    )
            
            # Calculate fresh analytics
            from core.models import Lesson, Test, QATest
            analytics.total_lessons_created = Lesson.objects.filter(created_by=teacher).count()
            analytics.total_mcq_tests_created = Test.objects.filter(created_by=teacher).count()
            analytics.total_qa_tests_created = QATest.objects.filter(lesson__created_by=teacher).count()
            
            # Calculate student metrics
            student_relationships = TeacherStudentRelationship.objects.filter(teacher=teacher, is_active=True)
            analytics.total_students = student_relationships.count()
            
            # Calculate student ratings
            student_ratings = [r.rating_by_student for r in student_relationships if r.rating_by_student]
            if student_ratings:
                analytics.average_student_rating = sum(student_ratings) / len(student_ratings)
                analytics.total_student_ratings = len(student_ratings)
            else:
                analytics.average_student_rating = 0
                analytics.total_student_ratings = 0
            
            # Calculate advisor ratings
            advisor_reviews = AdvisorReview.objects.filter(
                Q(lesson__created_by=teacher) | Q(mcq_test__lesson__created_by=teacher) | Q(qa_test__lesson__created_by=teacher)
            )
            advisor_ratings = [r.rating for r in advisor_reviews]
            if advisor_ratings:
                analytics.average_advisor_rating = sum(advisor_ratings) / len(advisor_ratings)
                analytics.total_advisor_ratings = len(advisor_ratings)
            else:
                analytics.average_advisor_rating = 0
                analytics.total_advisor_ratings = 0
            
            # Calculate overall rating
            analytics.overall_rating = analytics.calculate_overall_rating()
            
            # Get last activity dates
            last_lesson = Lesson.objects.filter(created_by=teacher).order_by('-created_at').first()
            if last_lesson:
                analytics.last_lesson_created = last_lesson.created_at
            
            last_test = Test.objects.filter(created_by=teacher).order_by('-created_at').first()
            if last_test:
                analytics.last_test_created = last_test.created_at
            
            analytics.subjects_taught = teacher.subjects
            analytics.save()
            
            analytics_data.append(self.get_serializer(analytics).data)
        
        return Response(analytics_data)


class AdministratorViewSet(viewsets.ViewSet):
    """
    Comprehensive administrator viewset for super admin operations
    Supervises all schools, teachers, advisors, students, and parents
    """
    permission_classes = [IsAuthenticated]
    
    def _check_admin_permission(self, user):
        """Verify user is an administrator"""
        if user.role != 'admin':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only administrators can access this resource")
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get overall system statistics"""
        self._check_admin_permission(request.user)
        
        from core.models import Lesson, Test, QATest, TestSubmission, QASubmission
        from django.db.models import Count, Avg
        
        # Get school stats if admin belongs to a school, otherwise all schools
        schools = School.objects.all()
        if request.user.school:
            schools = schools.filter(id=request.user.school.id)
        
        stats = {
            'total_schools': schools.count(),
            'total_users': User.objects.filter(school__in=schools).count(),
            'total_teachers': User.objects.filter(school__in=schools, role='teacher').count(),
            'total_students': User.objects.filter(school__in=schools, role='student').count(),
            'total_advisors': User.objects.filter(school__in=schools, role='advisor').count(),
            'total_parents': User.objects.filter(school__in=schools, role='parent').count(),
            'total_lessons': Lesson.objects.filter(created_by__school__in=schools).count(),
            'total_mcq_tests': Test.objects.filter(created_by__school__in=schools).count(),
            'total_qa_tests': QATest.objects.filter(created_by__school__in=schools).count(),
            'total_test_submissions': TestSubmission.objects.filter(student__school__in=schools).count(),
            'total_advisor_reviews': AdvisorReview.objects.filter(advisor__school__in=schools).count(),
            'active_relationships': TeacherStudentRelationship.objects.filter(
                teacher__school__in=schools, is_active=True
            ).count(),
        }
        
        # Calculate average ratings
        teacher_ratings = TeacherStudentRelationship.objects.filter(
            teacher__school__in=schools, 
            rating_by_student__isnull=False
        ).aggregate(Avg('rating_by_student'))
        stats['avg_teacher_rating'] = teacher_ratings['rating_by_student__avg']
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def all_schools(self, request):
        """Get all schools with statistics"""
        self._check_admin_permission(request.user)
        
        from .serializers import AdminSchoolStatsSerializer
        schools = School.objects.all()
        serializer = AdminSchoolStatsSerializer(schools, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def schools_map(self, request):
        """Get all schools with geodata for map visualization - Optimized with aggregation"""
        # Allow admin and minister roles
        if request.user.role not in ['admin', 'minister']:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only administrators and ministers can access this resource")
        
        # Get filter parameters
        school_type = request.query_params.get('type')
        delegation = request.query_params.get('delegation')
        cre = request.query_params.get('cre')
        search = request.query_params.get('search')
        
        # Base queryset - only schools with geodata
        schools = School.objects.filter(
            latitude__isnull=False, 
            longitude__isnull=False
        )
        
        # Apply filters
        if school_type:
            schools = schools.filter(school_type__icontains=school_type)
        if delegation:
            schools = schools.filter(delegation__icontains=delegation)
        if cre:
            schools = schools.filter(cre__icontains=cre)
        if search:
            schools = schools.filter(
                Q(name__icontains=search) |
                Q(name_ar__icontains=search) |
                Q(school_code__icontains=search)
            )
        
        # Get unique filter values for dropdowns (sorted alphabetically)
        all_schools = School.objects.filter(latitude__isnull=False, longitude__isnull=False)
        
        # Get types - exclude empty and None values
        types = all_schools.exclude(
            Q(school_type__isnull=True) | Q(school_type='')
        ).values_list('school_type', flat=True).distinct()
        
        # Get delegations - exclude empty and None values
        delegations = all_schools.exclude(
            Q(delegation__isnull=True) | Q(delegation='')
        ).values_list('delegation', flat=True).distinct()
        
        # Get CREs - exclude empty and None values
        cres = all_schools.exclude(
            Q(cre__isnull=True) | Q(cre='')
        ).values_list('cre', flat=True).distinct()
        
        filter_options = {
            'types': sorted([t for t in types if t]),
            'delegations': sorted([d for d in delegations if d]),
            'cres': sorted([c for c in cres if c])
        }
        
        # Use aggregation to count users efficiently in a single query
        from django.db.models import Count, Q as QExpr
        
        schools_with_counts = schools.annotate(
            total_users=Count('users', distinct=True),
            teachers=Count('users', filter=QExpr(users__role='teacher'), distinct=True),
            students=Count('users', filter=QExpr(users__role='student'), distinct=True),
            advisors=Count('users', filter=QExpr(users__role='advisor'), distinct=True)
        ).values(
            'id', 'name', 'name_ar', 'address', 'latitude', 'longitude',
            'school_code', 'school_type', 'delegation', 'cre',
            'total_users', 'teachers', 'students', 'advisors'
        )
        
        # Convert QuerySet to list for JSON response
        school_data = list(schools_with_counts)
        
        return Response({
            'schools': school_data,
            'filter_options': filter_options,
            'total_count': len(school_data)
        })
    

    @action(detail=False, methods=['post'])
    def create_school(self, request):
        """Create a new school"""
        self._check_admin_permission(request.user)
        
        serializer = SchoolSerializer(data=request.data)
        if serializer.is_valid():
            school = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['put', 'patch'])
    def update_school(self, request, pk=None):
        """Update school information"""
        self._check_admin_permission(request.user)
        
        school = get_object_or_404(School, pk=pk)
        serializer = SchoolSerializer(school, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'])
    def delete_school(self, request, pk=None):
        """Delete a school"""
        self._check_admin_permission(request.user)
        
        school = get_object_or_404(School, pk=pk)
        school.delete()
        return Response({'message': 'School deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def all_users(self, request):
        """Get all users with detailed information"""
        self._check_admin_permission(request.user)
        
        from .serializers import AdminUserDetailSerializer
        
        # Filter parameters
        role = request.query_params.get('role', None)
        school_id = request.query_params.get('school_id', None)
        search = request.query_params.get('search', None)
        
        users = User.objects.all()
        
        # Apply filters
        if role:
            users = users.filter(role=role)
        if school_id:
            users = users.filter(school_id=school_id)
        if search:
            users = users.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        
        users = users.select_related('school').order_by('-date_joined')
        serializer = AdminUserDetailSerializer(users, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def create_user(self, request):
        """Create a new user (teacher, student, advisor, or parent)"""
        self._check_admin_permission(request.user)
        
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            from .serializers import AdminUserDetailSerializer
            return Response(
                AdminUserDetailSerializer(user).data, 
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['put', 'patch'])
    def update_user(self, request, pk=None):
        """Update user information"""
        self._check_admin_permission(request.user)
        
        user = get_object_or_404(User, pk=pk)
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            from .serializers import AdminUserDetailSerializer
            return Response(AdminUserDetailSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'])
    def delete_user(self, request, pk=None):
        """Delete a user"""
        self._check_admin_permission(request.user)
        
        user = get_object_or_404(User, pk=pk)
        user.delete()
        return Response({'message': 'User deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def teacher_performance(self, request):
        """Get comprehensive teacher performance metrics"""
        self._check_admin_permission(request.user)
        
        from core.models import Lesson, Test, QATest
        from django.db.models import Avg
        
        school_id = request.query_params.get('school_id', None)
        subject = request.query_params.get('subject', None)
        
        teachers = User.objects.filter(role='teacher')
        if school_id:
            teachers = teachers.filter(school_id=school_id)
        
        performance_data = []
        
        for teacher in teachers:
            # Skip if subject filter doesn't match
            if subject and (not teacher.subjects or subject not in teacher.subjects):
                continue
            
            # Get teacher's advisor
            advisor = None
            if teacher.subjects:
                teacher_subject = teacher.subjects[0]
                # Get all advisors in the school (SQLite doesn't support JSON __contains)
                all_advisors = User.objects.filter(
                    role='advisor',
                    school=teacher.school
                )
                # Filter by subject using Python
                matching_advisors = [
                    a for a in all_advisors 
                    if a.subjects and teacher_subject in a.subjects
                ]
                advisor = matching_advisors[0] if matching_advisors else None
            
            # Calculate stats
            total_students = teacher.student_relationships.filter(is_active=True).count()
            total_lessons = Lesson.objects.filter(created_by=teacher).count()
            total_mcq_tests = Test.objects.filter(created_by=teacher).count()
            total_qa_tests = QATest.objects.filter(created_by=teacher).count()
            
            # Average rating from students
            avg_rating_data = teacher.student_relationships.filter(
                rating_by_student__isnull=False
            ).aggregate(Avg('rating_by_student'))
            avg_rating = avg_rating_data['rating_by_student__avg'] or 0
            
            # Latest advisor review
            latest_review = AdvisorReview.objects.filter(
                Q(lesson__created_by=teacher) | 
                Q(mcq_test__lesson__created_by=teacher) |
                Q(qa_test__lesson__created_by=teacher)
            ).order_by('-created_at').first()
            
            # Progress percentage - get the latest progress
            progress = TeacherProgress.objects.filter(teacher=teacher).order_by('-updated_at').first()
            if progress:
                progress_percentage = progress.get_progress_percentage()
            else:
                progress_percentage = 0
            
            performance_data.append({
                'teacher_id': teacher.id,
                'teacher_name': teacher.get_full_name() or teacher.username,
                'subjects': teacher.subjects or [],
                'total_students': total_students,
                'total_lessons_created': total_lessons,
                'total_tests_created': total_mcq_tests + total_qa_tests,
                'avg_rating': round(avg_rating, 2),
                'advisor_name': advisor.get_full_name() if advisor else 'N/A',
                'latest_advisor_review': latest_review.remarks if latest_review else None,
                'progress_percentage': progress_percentage,
            })
        
        from .serializers import AdminTeacherPerformanceSerializer
        serializer = AdminTeacherPerformanceSerializer(performance_data, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def advisor_performance(self, request):
        """Get comprehensive advisor performance metrics"""
        self._check_admin_permission(request.user)
        
        from django.db.models import Avg
        from datetime import timedelta
        
        school_id = request.query_params.get('school_id', None)
        
        advisors = User.objects.filter(role='advisor')
        if school_id:
            advisors = advisors.filter(school_id=school_id)
        
        performance_data = []
        
        for advisor in advisors:
            advisor_subject = advisor.subjects[0] if advisor.subjects else None
            
            # Get teachers supervised
            teachers = User.objects.filter(
                role='teacher',
                school=advisor.school
            )
            if advisor_subject:
                teachers = [t for t in teachers if t.subjects and advisor_subject in t.subjects]
            
            # Get reviews given
            total_reviews = advisor.advisor_reviews.count()
            
            # Get notifications reviewed
            notifications_reviewed = ChapterProgressNotification.objects.filter(
                advisor=advisor,
                status__in=['approved', 'rejected']
            ).count()
            
            # Calculate average response time
            notifications = ChapterProgressNotification.objects.filter(
                advisor=advisor,
                reviewed_at__isnull=False
            )
            
            response_times = []
            for notif in notifications:
                delta = notif.reviewed_at - notif.created_at
                response_times.append(delta.total_seconds() / 3600)  # Convert to hours
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            # Teachers list
            teachers_list = [{
                'id': t.id,
                'name': t.get_full_name() or t.username,
                'subjects': t.subjects
            } for t in teachers]
            
            performance_data.append({
                'advisor_id': advisor.id,
                'advisor_name': advisor.get_full_name() or advisor.username,
                'advisor_subject': advisor_subject or 'N/A',
                'total_teachers_supervised': len(teachers),
                'total_reviews_given': total_reviews,
                'total_notifications_reviewed': notifications_reviewed,
                'average_response_time_hours': round(avg_response_time, 2),
                'teachers_list': teachers_list,
            })
        
        from .serializers import AdminAdvisorPerformanceSerializer
        serializer = AdminAdvisorPerformanceSerializer(performance_data, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def all_reviews(self, request):
        """Get all reviews from all users"""
        self._check_admin_permission(request.user)
        
        # Filter parameters
        review_type = request.query_params.get('type', None)  # advisor, student, teacher
        school_id = request.query_params.get('school_id', None)
        
        reviews = []
        
        # Advisor reviews
        if not review_type or review_type == 'advisor':
            advisor_reviews = AdvisorReview.objects.all()
            if school_id:
                advisor_reviews = advisor_reviews.filter(advisor__school_id=school_id)
            
            for review in advisor_reviews.select_related('advisor'):
                reviews.append({
                    'id': review.id,
                    'type': 'advisor_review',
                    'reviewer': review.advisor.get_full_name() or review.advisor.username,
                    'reviewer_role': 'advisor',
                    'review_type': review.review_type,
                    'rating': review.rating,
                    'remarks': review.remarks,
                    'created_at': review.created_at,
                    'school': review.advisor.school.name,
                })
        
        # Teacher-Student relationship reviews
        if not review_type or review_type in ['teacher', 'student']:
            relationships = TeacherStudentRelationship.objects.select_related(
                'teacher', 'student', 'teacher__school'
            )
            if school_id:
                relationships = relationships.filter(teacher__school_id=school_id)
            
            for rel in relationships:
                # Teacher's review of student
                if rel.rating_by_teacher and (not review_type or review_type == 'teacher'):
                    reviews.append({
                        'id': f'ts-{rel.id}',
                        'type': 'teacher_review',
                        'reviewer': rel.teacher.get_full_name() or rel.teacher.username,
                        'reviewer_role': 'teacher',
                        'reviewed': rel.student.get_full_name() or rel.student.username,
                        'reviewed_role': 'student',
                        'rating': rel.rating_by_teacher,
                        'comments': rel.comments_by_teacher,
                        'created_at': rel.updated_at,
                        'school': rel.teacher.school.name,
                    })
                
                # Student's review of teacher
                if rel.rating_by_student and (not review_type or review_type == 'student'):
                    reviews.append({
                        'id': f'st-{rel.id}',
                        'type': 'student_review',
                        'reviewer': rel.student.get_full_name() or rel.student.username,
                        'reviewer_role': 'student',
                        'reviewed': rel.teacher.get_full_name() or rel.teacher.username,
                        'reviewed_role': 'teacher',
                        'rating': rel.rating_by_student,
                        'comments': rel.comments_by_student,
                        'created_at': rel.updated_at,
                        'school': rel.teacher.school.name,
                    })
        
        # Sort by date (most recent first)
        reviews.sort(key=lambda x: x['created_at'], reverse=True)
        
        return Response(reviews)
    
    @action(detail=False, methods=['get'])
    def advisor_teachers_notes(self, request):
        """Get all advisor notes/reviews on teachers"""
        self._check_admin_permission(request.user)
        
        advisor_id = request.query_params.get('advisor_id', None)
        teacher_id = request.query_params.get('teacher_id', None)
        
        reviews = AdvisorReview.objects.select_related('advisor').all()
        
        if advisor_id:
            reviews = reviews.filter(advisor_id=advisor_id)
        
        notes_data = []
        for review in reviews:
            # Get the teacher who created the content
            teacher = None
            content_title = None
            
            if review.lesson:
                teacher = review.lesson.created_by
                content_title = review.lesson.title
            elif review.mcq_test:
                teacher = review.mcq_test.lesson.created_by if review.mcq_test.lesson else None
                content_title = review.mcq_test.title
            elif review.qa_test:
                teacher = review.qa_test.lesson.created_by if review.qa_test.lesson else None
                content_title = review.qa_test.title
            
            if teacher and (not teacher_id or teacher.id == int(teacher_id)):
                notes_data.append({
                    'review_id': review.id,
                    'advisor_id': review.advisor.id,
                    'advisor_name': review.advisor.get_full_name() or review.advisor.username,
                    'teacher_id': teacher.id,
                    'teacher_name': teacher.get_full_name() or teacher.username,
                    'content_type': review.review_type,
                    'content_title': content_title,
                    'rating': review.rating,
                    'remarks': review.remarks,
                    'created_at': review.created_at,
                })
        
        return Response(notes_data)
    
    @action(detail=False, methods=['get'])
    def advisor_teacher_assignments(self, request):
        """Get which teachers are assigned to which advisors"""
        self._check_admin_permission(request.user)
        
        school_id = request.query_params.get('school_id', None)
        
        advisors = User.objects.filter(role='advisor')
        if school_id:
            advisors = advisors.filter(school_id=school_id)
        
        assignments = []
        
        for advisor in advisors:
            advisor_subject = advisor.subjects[0] if advisor.subjects else None
            
            # Get teachers in same subject
            teachers = User.objects.filter(role='teacher', school=advisor.school)
            if advisor_subject:
                matching_teachers = [
                    t for t in teachers 
                    if t.subjects and advisor_subject in t.subjects
                ]
            else:
                matching_teachers = []
            
            teachers_info = [{
                'id': t.id,
                'name': t.get_full_name() or t.username,
                'subjects': t.subjects,
                'total_students': t.student_relationships.filter(is_active=True).count(),
            } for t in matching_teachers]
            
            assignments.append({
                'advisor_id': advisor.id,
                'advisor_name': advisor.get_full_name() or advisor.username,
                'subject': advisor_subject or 'N/A',
                'school': advisor.school.name,
                'total_teachers': len(matching_teachers),
                'teachers': teachers_info,
            })
        
        return Response(assignments)
    
    @action(detail=False, methods=['get'])
    def national_kpi_dashboard(self, request):
        """Get national KPI metrics with trends"""
        self._check_admin_permission(request.user)
        
        # Try to get cached data
        cache_key = 'analytics_national_kpi'
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        
        from core.models import Lesson, Test, QATest, TestSubmission
        from django.db.models import Count, Avg, Q
        from django.utils import timezone
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        
        now = timezone.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Active users (users who logged in or created content in last 7 days)
        active_users_week = User.objects.filter(
            Q(last_login__gte=week_ago) |
            Q(lessons__created_at__gte=week_ago) |
            Q(created_tests__created_at__gte=week_ago)
        ).distinct().count()
        
        # Platform adoption by region (schools with active users)
        active_schools_by_region = School.objects.filter(
            users__last_login__gte=week_ago
        ).values('cre').annotate(
            active_schools=Count('id', distinct=True),
            total_users=Count('users', distinct=True)
        ).order_by('-active_schools')
        
        # Student-teacher ratios
        student_teacher_ratios = School.objects.annotate(
            student_count=Count('users', filter=Q(users__role='student')),
            teacher_count=Count('users', filter=Q(users__role='teacher'))
        ).exclude(teacher_count=0).values('id', 'name', 'student_count', 'teacher_count')
        
        ratios_data = [{
            'school_id': s['id'],
            'school_name': s['name'],
            'ratio': round(s['student_count'] / s['teacher_count'], 2) if s['teacher_count'] > 0 else 0
        } for s in student_teacher_ratios]
        
        # Content creation velocity
        lessons_this_week = Lesson.objects.filter(created_at__gte=week_ago).count()
        lessons_last_week = Lesson.objects.filter(
            created_at__gte=week_ago - timedelta(days=7),
            created_at__lt=week_ago
        ).count()
        
        tests_this_week = Test.objects.filter(created_at__gte=week_ago).count()
        
        # Assessment completion rates
        total_tests = Test.objects.count()
        completed_submissions = TestSubmission.objects.filter(status='submitted').count()
        total_submissions = TestSubmission.objects.count()
        completion_rate = (completed_submissions / total_submissions * 100) if total_submissions > 0 else 0
        
        response_data = {
            'active_users': {
                'daily': User.objects.filter(last_login__gte=today).count(),
                'weekly': active_users_week,
                'monthly': User.objects.filter(last_login__gte=month_ago).count(),
            },
            'platform_adoption': {
                'by_region': list(active_schools_by_region),
                'total_active_schools': School.objects.filter(users__last_login__gte=week_ago).distinct().count(),
                'adoption_rate': round(School.objects.filter(users__last_login__gte=week_ago).distinct().count() / School.objects.count() * 100, 2) if School.objects.count() > 0 else 0
            },
            'student_teacher_ratios': {
                'average': round(sum(r['ratio'] for r in ratios_data) / len(ratios_data), 2) if ratios_data else 0,
                'by_school': ratios_data[:20]  # Top 20 schools
            },
            'content_creation': {
                'lessons_this_week': lessons_this_week,
                'lessons_last_week': lessons_last_week,
                'growth': round((lessons_this_week - lessons_last_week) / lessons_last_week * 100, 2) if lessons_last_week > 0 else 0,
                'tests_this_week': tests_this_week
            },
            'assessment_completion': {
                'rate': round(completion_rate, 2),
                'completed': completed_submissions,
                'total': total_submissions
            }
        }
        
        # Add historical data for last 12 months
        historical_data = []
        for i in range(11, -1, -1):  # 12 months ago to current month
            month_start = (now - relativedelta(months=i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + relativedelta(months=1)) - timedelta(seconds=1)
            
            # Active users in that month
            month_active_users = User.objects.filter(
                Q(last_login__gte=month_start, last_login__lte=month_end) |
                Q(lessons__created_at__gte=month_start, lessons__created_at__lte=month_end) |
                Q(created_tests__created_at__gte=month_start, created_tests__created_at__lte=month_end)
            ).distinct().count()
            
            # Content created in that month
            month_lessons = Lesson.objects.filter(
                created_at__gte=month_start, created_at__lte=month_end
            ).count()
            
            month_tests = Test.objects.filter(
                created_at__gte=month_start, created_at__lte=month_end
            ).count()
            
            # Submissions in that month
            month_submissions = TestSubmission.objects.filter(
                submitted_at__gte=month_start, submitted_at__lte=month_end, is_final=True
            )
            month_avg_score = month_submissions.aggregate(Avg('score'))['score__avg'] or 0
            
            historical_data.append({
                'month': month_start.strftime('%Y-%m'),
                'month_name': month_start.strftime('%b %Y'),
                'active_users': month_active_users,
                'lessons_created': month_lessons,
                'tests_created': month_tests,
                'submissions': month_submissions.count(),
                'avg_score': round(month_avg_score, 2)
            })
        
        response_data['historical_trends'] = historical_data
        
        # Cache for 5 minutes
        cache.set(cache_key, response_data, 300)
        return Response(response_data)
    
    @action(detail=False, methods=['get'])
    def regional_performance(self, request):
        """Get regional performance analysis"""
        self._check_admin_permission(request.user)
        
        # Try to get cached data
        cache_key = 'analytics_regional_performance'
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        
        from core.models import TestSubmission
        from django.db.models import Avg, Count, Q
        
        # Performance by wilaya/CRE
        regional_stats = School.objects.values('cre', 'delegation').annotate(
            total_schools=Count('id'),
            total_students=Count('users', filter=Q(users__role='student')),
            total_teachers=Count('users', filter=Q(users__role='teacher')),
            total_lessons=Count('lessons', distinct=True),
            total_tests=Count('lessons__tests', distinct=True)
        ).order_by('-total_students')
        
        # Average test scores by region
        regional_performance = []
        for region in School.objects.values('cre').distinct():
            cre = region['cre']
            if not cre:
                continue
                
            schools_in_region = School.objects.filter(cre=cre)
            students_in_region = User.objects.filter(school__in=schools_in_region, role='student')
            
            submissions = TestSubmission.objects.filter(
                student__in=students_in_region,
                is_final=True
            )
            
            avg_score = submissions.aggregate(Avg('score'))['score__avg'] or 0
            
            regional_performance.append({
                'region': cre,
                'schools': schools_in_region.count(),
                'students': students_in_region.count(),
                'avg_score': round(avg_score, 2),
                'total_submissions': submissions.count()
            })
        
        # Sort by average score
        regional_performance.sort(key=lambda x: x['avg_score'], reverse=True)
        
        response_data = {
            'regional_stats': list(regional_stats),
            'performance_rankings': regional_performance,
            'top_performers': regional_performance[:5],
            'needs_support': regional_performance[-5:] if len(regional_performance) > 5 else []
        }
        
        # Add historical trends for top 5 regions
        from django.utils import timezone
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        
        now = timezone.now()
        top_regions = [r['region'] for r in regional_performance[:5]]
        
        regional_trends = {}
        for region_name in top_regions:
            monthly_data = []
            for i in range(11, -1, -1):
                month_start = (now - relativedelta(months=i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                month_end = (month_start + relativedelta(months=1)) - timedelta(seconds=1)
                
                schools = School.objects.filter(cre=region_name)
                students = User.objects.filter(school__in=schools, role='student')
                
                submissions = TestSubmission.objects.filter(
                    student__in=students,
                    is_final=True,
                    submitted_at__gte=month_start,
                    submitted_at__lte=month_end
                )
                
                avg_score = submissions.aggregate(Avg('score'))['score__avg'] or 0
                
                monthly_data.append({
                    'month': month_start.strftime('%Y-%m'),
                    'month_name': month_start.strftime('%b %Y'),
                    'avg_score': round(avg_score, 2),
                    'submissions': submissions.count()
                })
            
            regional_trends[region_name] = monthly_data
        
        response_data['regional_trends'] = regional_trends
        
        # Cache for 5 minutes
        cache.set(cache_key, response_data, 300)
        return Response(response_data)
    
    @action(detail=False, methods=['get'])
    def curriculum_effectiveness(self, request):
        """Analyze curriculum effectiveness"""
        self._check_admin_permission(request.user)
        
        # Try to get cached data
        cache_key = 'analytics_curriculum_effectiveness'
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        
        from core.models import Lesson, Test, TestSubmission
        from django.db.models import Avg, Count

        # Subject difficulty analysis
        subject_performance = []
        # derive available subject keys from Lesson choices to avoid mismatches
        subjects = [choice[0] for choice in Lesson.SUBJECT_CHOICES]

        for subject in subjects:
            lessons = Lesson.objects.filter(subject=subject)
            # Tests are linked to lessons, so filter via lesson__subject
            tests = Test.objects.filter(lesson__subject=subject)
            # Submissions are linked to tests -> lesson via test__lesson
            submissions = TestSubmission.objects.filter(
                test__lesson__subject=subject
            )

            avg_score = submissions.aggregate(Avg('score'))['score__avg'] or 0
            # completion defined as proportion of finalized/approved MCQ submissions
            completion_rate = (
                submissions.filter(is_final=True).count() / submissions.count() * 100
                if submissions.count() > 0 else 0
            )

            subject_performance.append({
                'subject': subject,
                'lessons_count': lessons.count(),
                'tests_count': tests.count(),
                'avg_score': round(avg_score, 2),
                'completion_rate': round(completion_rate, 2),
                'total_submissions': submissions.count()
            })
        
        # Sort by difficulty (lowest scores = hardest)
        subject_performance.sort(key=lambda x: x['avg_score'])
        
        # Most/least effective content
        # annotate using the correct related names: 'tests' on Lesson and 'submissions' on Test
        lesson_effectiveness = Lesson.objects.annotate(
            test_count=Count('tests'),
            avg_test_score=Avg('tests__submissions__score')
        ).filter(test_count__gt=0).order_by('-avg_test_score')[:10]
        
        response_data = {
            'subject_analysis': subject_performance,
            'hardest_subjects': subject_performance[:3],
            'easiest_subjects': subject_performance[-3:],
            'most_effective_lessons': [{
                'id': lesson.id,
                'title': lesson.title,
                'subject': lesson.subject,
                'avg_score': round(lesson.avg_test_score or 0, 2)
            } for lesson in lesson_effectiveness]
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, response_data, 300)
        return Response(response_data)
    
    @action(detail=False, methods=['get'])
    def at_risk_students(self, request):
        """Identify at-risk students"""
        self._check_admin_permission(request.user)
        
        # Try to get cached data
        cache_key = 'analytics_at_risk_students'
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        
        from core.models import TestSubmission
        from django.db.models import Avg, Count

        # Students with low performance (avg score < 50%)
        at_risk = []
        students = User.objects.filter(role='student')

        for student in students:
            # consider finalized/approved MCQ submissions for risk calculation
            submissions = TestSubmission.objects.filter(
                student=student,
                is_final=True
            )

            if submissions.count() < 3:  # Need at least 3 submissions
                continue

            avg_score = submissions.aggregate(Avg('score'))['score__avg'] or 0

            if avg_score < 50:
                # Check for declining trend (newest first)
                recent_scores = list(submissions.order_by('-submitted_at')[:5].values_list('score', flat=True))
                is_declining = len(recent_scores) >= 3 and recent_scores[0] < recent_scores[-1]

                at_risk.append({
                    'student_id': student.id,
                    'student_name': f"{student.first_name} {student.last_name}",
                    'school': student.school.name if getattr(student, 'school', None) else 'N/A',
                    'avg_score': round(avg_score, 2),
                    'total_tests': submissions.count(),
                    'is_declining': is_declining,
                    'recent_scores': recent_scores,
                    'risk_level': 'high' if avg_score < 30 else 'medium'
                })
        
        # Sort by risk level and score
        at_risk.sort(key=lambda x: (x['risk_level'] == 'high', x['avg_score']))
        
        response_data = {
            'total_at_risk': len(at_risk),
            'high_risk': len([s for s in at_risk if s['risk_level'] == 'high']),
            'medium_risk': len([s for s in at_risk if s['risk_level'] == 'medium']),
            'students': at_risk[:50],  # Return top 50
            'recommendations': [
                'Schedule intervention sessions for high-risk students',
                'Assign additional support teachers',
                'Monitor declining performance trends weekly',
                'Contact parents of at-risk students'
            ]
        }
        
        # Cache for 3 minutes (more frequent updates for at-risk students)
        cache.set(cache_key, response_data, 180)
        return Response(response_data)
    
    @action(detail=False, methods=['get'])
    def export_regional_performance(self, request):
        """Export regional performance data as CSV"""
        self._check_admin_permission(request.user)
        
        from core.models import TestSubmission
        from django.db.models import Avg, Count, Q
        
        # Get the data
        regional_stats = School.objects.values('cre', 'delegation').annotate(
            total_schools=Count('id'),
            total_students=Count('users', filter=Q(users__role='student')),
            total_teachers=Count('users', filter=Q(users__role='teacher')),
            total_lessons=Count('lessons', distinct=True),
            total_tests=Count('lessons__tests', distinct=True)
        ).order_by('-total_students')
        
        # Calculate performance
        regional_performance = []
        for region in School.objects.values('cre').distinct():
            cre = region['cre']
            if not cre:
                continue
            
            schools_in_region = School.objects.filter(cre=cre)
            students_in_region = User.objects.filter(school__in=schools_in_region, role='student')
            submissions = TestSubmission.objects.filter(
                student__in=students_in_region,
                is_final=True
            )
            avg_score = submissions.aggregate(Avg('score'))['score__avg'] or 0
            
            regional_performance.append({
                'region': cre,
                'schools': schools_in_region.count(),
                'students': students_in_region.count(),
                'avg_score': round(avg_score, 2),
                'total_submissions': submissions.count()
            })
        
        # Create CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="regional_performance.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Region', 'Schools', 'Students', 'Average Score', 'Total Submissions'])
        
        for item in regional_performance:
            writer.writerow([
                item['region'],
                item['schools'],
                item['students'],
                item['avg_score'],
                item['total_submissions']
            ])
        
        return response
    
    @action(detail=False, methods=['get'])
    def export_curriculum_effectiveness(self, request):
        """Export curriculum effectiveness data as CSV"""
        self._check_admin_permission(request.user)
        
        from core.models import Lesson, Test, TestSubmission
        from django.db.models import Avg, Count
        
        # Get subject performance data
        subject_performance = []
        subjects = [choice[0] for choice in Lesson.SUBJECT_CHOICES]
        
        for subject in subjects:
            lessons = Lesson.objects.filter(subject=subject)
            tests = Test.objects.filter(lesson__subject=subject)
            submissions = TestSubmission.objects.filter(test__lesson__subject=subject)
            
            avg_score = submissions.aggregate(Avg('score'))['score__avg'] or 0
            completion_rate = (
                submissions.filter(is_final=True).count() / submissions.count() * 100
                if submissions.count() > 0 else 0
            )
            
            subject_performance.append({
                'subject': subject,
                'lessons_count': lessons.count(),
                'tests_count': tests.count(),
                'avg_score': round(avg_score, 2),
                'completion_rate': round(completion_rate, 2),
                'total_submissions': submissions.count()
            })
        
        # Create CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="curriculum_effectiveness.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Subject', 'Lessons', 'Tests', 'Average Score', 'Completion Rate %', 'Total Submissions'])
        
        for item in subject_performance:
            writer.writerow([
                item['subject'],
                item['lessons_count'],
                item['tests_count'],
                item['avg_score'],
                item['completion_rate'],
                item['total_submissions']
            ])
        
        return response
    
    @action(detail=False, methods=['get'])
    def export_at_risk_students(self, request):
        """Export at-risk students data as CSV"""
        self._check_admin_permission(request.user)
        
        from core.models import TestSubmission
        from django.db.models import Avg
        
        # Get at-risk students
        at_risk = []
        students = User.objects.filter(role='student')
        
        for student in students:
            submissions = TestSubmission.objects.filter(
                student=student,
                is_final=True
            )
            
            if submissions.count() < 3:
                continue
            
            avg_score = submissions.aggregate(Avg('score'))['score__avg'] or 0
            
            if avg_score < 50:
                recent_scores = list(submissions.order_by('-submitted_at')[:5].values_list('score', flat=True))
                is_declining = len(recent_scores) >= 3 and recent_scores[0] < recent_scores[-1]
                
                at_risk.append({
                    'student_id': student.id,
                    'student_name': f"{student.first_name} {student.last_name}",
                    'school': student.school.name if getattr(student, 'school', None) else 'N/A',
                    'avg_score': round(avg_score, 2),
                    'total_tests': submissions.count(),
                    'is_declining': 'Yes' if is_declining else 'No',
                    'risk_level': 'High' if avg_score < 30 else 'Medium'
                })
        
        # Sort by risk
        at_risk.sort(key=lambda x: (x['risk_level'] == 'High', x['avg_score']))
        
        # Create CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="at_risk_students.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Student ID', 'Student Name', 'School', 'Average Score', 'Total Tests', 'Declining Trend', 'Risk Level'])
        
        for item in at_risk:
            writer.writerow([
                item['student_id'],
                item['student_name'],
                item['school'],
                item['avg_score'],
                item['total_tests'],
                item['is_declining'],
                item['risk_level']
            ])
        
        return response
    
    @action(detail=False, methods=['get'])
    def teacher_quality_metrics(self, request):
        """Detailed teacher performance analytics"""
        self._check_admin_permission(request.user)
        
        # Try cache first
        cache_key = 'analytics_teacher_quality_metrics'
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        
        from core.models import Lesson, Test, TestSubmission, QATest, QASubmission
        from django.db.models import Avg, Count, Q
        
        teachers = User.objects.filter(role='teacher').select_related('school')
        teacher_metrics = []
        
        for teacher in teachers:
            # Content created
            lessons_count = Lesson.objects.filter(created_by=teacher).count()
            tests_count = Test.objects.filter(lesson__created_by=teacher).count()
            qa_tests_count = QATest.objects.filter(lesson__created_by=teacher).count()
            
            # Student performance on teacher's content
            mcq_submissions = TestSubmission.objects.filter(
                test__lesson__created_by=teacher,
                is_final=True
            )
            avg_student_score = mcq_submissions.aggregate(Avg('score'))['score__avg'] or 0
            
            # Content approval rate
            total_tests = Test.objects.filter(lesson__created_by=teacher).count()
            approved_tests = Test.objects.filter(
                lesson__created_by=teacher,
                status='approved'
            ).count()
            approval_rate = (approved_tests / total_tests * 100) if total_tests > 0 else 0
            
            # Advisor ratings
            advisor_reviews = AdvisorReview.objects.filter(
                Q(lesson__created_by=teacher) |
                Q(mcq_test__lesson__created_by=teacher) |
                Q(qa_test__lesson__created_by=teacher)
            )
            avg_advisor_rating = advisor_reviews.aggregate(Avg('rating'))['rating__avg'] or 0
            
            # Student engagement (number of unique students who completed tests)
            unique_students = mcq_submissions.values('student').distinct().count()
            
            # Activity level - content created in last 30 days
            from django.utils import timezone
            from datetime import timedelta
            thirty_days_ago = timezone.now() - timedelta(days=30)
            recent_lessons = Lesson.objects.filter(
                created_by=teacher,
                created_at__gte=thirty_days_ago
            ).count()
            
            # Calculate quality score (0-100)
            quality_score = (
                (avg_student_score * 0.3) +  # 30% weight on student performance
                (approval_rate * 0.25) +  # 25% weight on content approval
                (min(avg_advisor_rating * 20, 100) * 0.20) +  # 20% weight on advisor ratings
                (min(unique_students / 10, 1) * 100 * 0.15) +  # 15% weight on engagement
                (min(recent_lessons / 5, 1) * 100 * 0.10)  # 10% weight on activity
            )
            
            teacher_metrics.append({
                'teacher_id': teacher.id,
                'teacher_name': f"{teacher.first_name} {teacher.last_name}",
                'school': teacher.school.name if teacher.school else 'N/A',
                'subjects': teacher.subjects or [],
                'quality_score': round(quality_score, 2),
                'metrics': {
                    'lessons_created': lessons_count,
                    'tests_created': tests_count + qa_tests_count,
                    'avg_student_score': round(avg_student_score, 2),
                    'approval_rate': round(approval_rate, 2),
                    'advisor_rating': round(avg_advisor_rating, 2),
                    'unique_students_reached': unique_students,
                    'recent_activity': recent_lessons,
                },
                'level': 'excellent' if quality_score >= 80 else 'good' if quality_score >= 60 else 'needs_improvement'
            })
        
        # Sort by quality score
        teacher_metrics.sort(key=lambda x: x['quality_score'], reverse=True)
        
        response_data = {
            'total_teachers': len(teachers),
            'top_performers': teacher_metrics[:10],
            'needs_development': [t for t in teacher_metrics if t['level'] == 'needs_improvement'][:10],
            'average_quality_score': round(sum(t['quality_score'] for t in teacher_metrics) / len(teacher_metrics), 2) if teacher_metrics else 0,
            'metrics_breakdown': {
                'excellent': len([t for t in teacher_metrics if t['level'] == 'excellent']),
                'good': len([t for t in teacher_metrics if t['level'] == 'good']),
                'needs_improvement': len([t for t in teacher_metrics if t['level'] == 'needs_improvement']),
            }
        }
        
        # Cache for 10 minutes
        cache.set(cache_key, response_data, 600)
        return Response(response_data)


class TeacherGradeAssignmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing teacher-grade assignments by school directors.
    Allows directors to assign teachers to specific grades and subjects.
    """
    queryset = TeacherGradeAssignment.objects.all()
    serializer_class = TeacherGradeAssignmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter assignments based on user role"""
        user = self.request.user
        queryset = self.queryset.select_related('teacher', 'school', 'assigned_by')
        
        if user.role == 'director':
            # Directors see only assignments in their school
            queryset = queryset.filter(school=user.school)
        elif user.role in ['admin', 'minister']:
            # Admins and ministers see all assignments
            pass
        elif user.role == 'teacher':
            # Teachers see only their own assignments
            queryset = queryset.filter(teacher=user)
        else:
            # Other roles can't see assignments
            queryset = queryset.none()
        
        # Optional filters from query params
        grade_level = self.request.query_params.get('grade_level')
        subject = self.request.query_params.get('subject')
        academic_year = self.request.query_params.get('academic_year')
        is_active = self.request.query_params.get('is_active')
        
        if grade_level:
            queryset = queryset.filter(grade_level=grade_level)
        if subject:
            queryset = queryset.filter(subject=subject)
        if academic_year:
            queryset = queryset.filter(academic_year=academic_year)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset
    
    def perform_create(self, serializer):
        """Set assigned_by and school automatically"""
        user = self.request.user
        
        if user.role != 'director':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only school directors can create assignments")
        
        logger.info(f"Director {user.username} creating assignment for teacher {serializer.validated_data.get('teacher')}")
        serializer.save(assigned_by=user, school=user.school)
    
    def perform_update(self, serializer):
        """Only directors can update assignments"""
        user = self.request.user
        assignment = self.get_object()
        
        if user.role != 'director' or assignment.school != user.school:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only the school director can modify assignments")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only directors can delete assignments"""
        user = self.request.user
        
        if user.role != 'director' or instance.school != user.school:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only the school director can delete assignments")
        
        instance.delete()
    
    @action(detail=False, methods=['get'], url_path='overview')
    def assignments_overview(self, request):
        """Get overview of all assignments in the school"""
        if request.user.role != 'director':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only school directors can view this data")
        
        school = request.user.school
        cache_key = f'director_assignments_overview_{school.id}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        # Get all active assignments in the school
        assignments = TeacherGradeAssignment.objects.filter(
            school=school,
            is_active=True
        ).select_related('teacher')
        
        # Get all teachers in the school
        all_teachers = User.objects.filter(role='teacher', school=school)
        
        # Group assignments by grade level
        assignments_by_grade = {}
        for choice_value, choice_label in TeacherGradeAssignment.GRADE_CHOICES:
            grade_assignments = assignments.filter(grade_level=choice_value)
            assignments_by_grade[choice_value] = {
                'grade_label': choice_label,
                'total_assignments': grade_assignments.count(),
                'subjects_covered': list(set(a.subject for a in grade_assignments)),
                'teachers': [
                    {
                        'assignment_id': a.id,
                        'teacher_id': a.teacher.id,
                        'name': a.teacher.get_full_name() or a.teacher.username,
                        'subject': a.subject,
                        'subject_display': a.get_subject_display(),
                    }
                    for a in grade_assignments
                ]
            }
        
        # Teachers without assignments
        assigned_teacher_ids = set(a.teacher_id for a in assignments)
        unassigned_teachers = [
            {
                'id': t.id,
                'name': t.get_full_name() or t.username,
                'subjects': t.subjects or [],
            }
            for t in all_teachers if t.id not in assigned_teacher_ids
        ]
        
        response_data = {
            'school_name': school.name,
            'total_teachers': all_teachers.count(),
            'total_assignments': assignments.count(),
            'unassigned_teachers_count': len(unassigned_teachers),
            'unassigned_teachers': unassigned_teachers,
            'assignments_by_grade': assignments_by_grade,
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, response_data, 300)
        return Response(response_data)
    
    @action(detail=False, methods=['get'], url_path='teachers')
    def available_teachers(self, request):
        """Get list of teachers available for assignment"""
        if request.user.role != 'director':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only school directors can view this data")
        
        school = request.user.school
        subject_filter = request.query_params.get('subject')
        
        teachers = User.objects.filter(role='teacher', school=school)
        
        teachers_data = []
        for teacher in teachers:
            # Get teacher's current assignments
            current_assignments = TeacherGradeAssignment.objects.filter(
                teacher=teacher,
                is_active=True
            )
            
            teacher_info = {
                'id': teacher.id,
                'username': teacher.username,
                'full_name': teacher.get_full_name() or teacher.username,
                'email': teacher.email,
                'subjects': teacher.subjects or [],
                'current_assignments_count': current_assignments.count(),
                'current_assignments': [
                    {
                        'id': a.id,
                        'grade_level': a.grade_level,
                        'grade_display': a.get_grade_level_display(),
                        'subject': a.subject,
                        'subject_display': a.get_subject_display(),
                    }
                    for a in current_assignments
                ]
            }
            
            # Filter by subject if requested
            if subject_filter:
                if subject_filter in (teacher.subjects or []):
                    teachers_data.append(teacher_info)
            else:
                teachers_data.append(teacher_info)
        
        return Response({
            'total_teachers': len(teachers_data),
            'teachers': teachers_data
        })
    
    @action(detail=False, methods=['post'], url_path='bulk-assign')
    def bulk_assign(self, request):
        """Bulk assign multiple teachers to grades/subjects"""
        if request.user.role != 'director':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only school directors can create assignments")
        
        assignments_data = request.data.get('assignments', [])
        if not assignments_data:
            return Response(
                {'error': 'No assignments provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_assignments = []
        errors = []
        
        for idx, assignment_data in enumerate(assignments_data):
            assignment_data['school'] = request.user.school.id
            serializer = TeacherGradeAssignmentSerializer(
                data=assignment_data,
                context={'request': request}
            )
            
            if serializer.is_valid():
                try:
                    assignment = serializer.save(
                        assigned_by=request.user,
                        school=request.user.school
                    )
                    created_assignments.append(serializer.data)
                except Exception as e:
                    errors.append({
                        'index': idx,
                        'data': assignment_data,
                        'error': str(e)
                    })
            else:
                errors.append({
                    'index': idx,
                    'data': assignment_data,
                    'errors': serializer.errors
                })
        
        # Clear cache
        cache_key = f'director_assignments_overview_{request.user.school.id}'
        cache.delete(cache_key)
        
        return Response({
            'created_count': len(created_assignments),
            'created_assignments': created_assignments,
            'errors_count': len(errors),
            'errors': errors
        }, status=status.HTTP_201_CREATED if created_assignments else status.HTTP_400_BAD_REQUEST)


class TeacherTimetableViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing teacher timetables/schedules.
    Directors can assign weekly working hours to teachers for automatic attendance tracking.
    """
    queryset = TeacherTimetable.objects.all()
    serializer_class = TeacherTimetableSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter timetables based on user role"""
        user = self.request.user
        queryset = self.queryset.select_related('teacher', 'created_by')
        
        if user.role == 'director':
            # Directors see only timetables for teachers in their school
            queryset = queryset.filter(teacher__school=user.school)
        elif user.role == 'teacher':
            # Teachers see only their own timetable
            queryset = queryset.filter(teacher=user)
        elif user.role in ['admin', 'minister']:
            # Admins and ministers see all timetables
            pass
        else:
            # Other roles can't see timetables
            queryset = queryset.none()
        
        # Optional filters
        teacher_id = self.request.query_params.get('teacher_id')
        day_of_week = self.request.query_params.get('day_of_week')
        is_active = self.request.query_params.get('is_active')
        
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        if day_of_week is not None:
            queryset = queryset.filter(day_of_week=day_of_week)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.order_by('teacher', 'day_of_week', 'start_time')
    
    def perform_create(self, serializer):
        """Set created_by automatically"""
        user = self.request.user
        
        if user.role != 'director':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only school directors can create timetables")
        
        logger.info(f"Director {user.username} creating timetable for teacher {serializer.validated_data.get('teacher')}")
        serializer.save(created_by=user)
    
    def perform_update(self, serializer):
        """Only directors can update timetables"""
        user = self.request.user
        timetable = self.get_object()
        
        if user.role != 'director' or timetable.teacher.school != user.school:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only the school director can modify timetables")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only directors can delete timetables"""
        user = self.request.user
        
        if user.role != 'director' or instance.teacher.school != user.school:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only the school director can delete timetables")
        
        instance.delete()
    
    @action(detail=False, methods=['get'], url_path='by-teacher/(?P<teacher_id>[0-9]+)')
    def get_teacher_timetable(self, request, teacher_id=None):
        """Get complete weekly timetable for a specific teacher"""
        user = request.user
        
        # Permission check
        teacher = get_object_or_404(User, id=teacher_id, role='teacher')
        
        if user.role == 'director' and teacher.school != user.school:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only view timetables for teachers in your school")
        elif user.role == 'teacher' and user.id != teacher.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only view your own timetable")
        
        timetables = TeacherTimetable.objects.filter(
            teacher=teacher,
            is_active=True
        ).order_by('day_of_week', 'start_time')
        
        serializer = self.get_serializer(timetables, many=True)
        
        # Organize by day of week
        weekly_schedule = {i: [] for i in range(7)}
        for timetable_data in serializer.data:
            day = timetable_data['day_of_week']
            weekly_schedule[day].append(timetable_data)
        
        return Response({
            'teacher_id': teacher.id,
            'teacher_name': teacher.get_full_name() or teacher.username,
            'weekly_schedule': weekly_schedule,
            'total_schedules': len(serializer.data)
        })
    
    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create_timetable(self, request):
        """Bulk create weekly timetable for a teacher"""
        if request.user.role != 'director':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only school directors can create timetables")
        
        schedules_data = request.data.get('schedules', [])
        if not schedules_data:
            return Response(
                {'error': 'No schedules provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_schedules = []
        errors = []
        
        for idx, schedule_data in enumerate(schedules_data):
            serializer = TeacherTimetableSerializer(
                data=schedule_data,
                context={'request': request}
            )
            
            if serializer.is_valid():
                try:
                    schedule = serializer.save(created_by=request.user)
                    created_schedules.append(serializer.data)
                except Exception as e:
                    errors.append({
                        'index': idx,
                        'data': schedule_data,
                        'error': str(e)
                    })
            else:
                errors.append({
                    'index': idx,
                    'data': schedule_data,
                    'errors': serializer.errors
                })
        
        return Response({
            'created_count': len(created_schedules),
            'created_schedules': created_schedules,
            'errors_count': len(errors),
            'errors': errors
        }, status=status.HTTP_201_CREATED if created_schedules else status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='my-schedule')
    def my_schedule(self, request):
        """Get current user's (teacher's) weekly schedule"""
        if request.user.role != 'teacher':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only teachers can view their schedule")
        
        timetables = TeacherTimetable.objects.filter(
            teacher=request.user,
            is_active=True
        ).order_by('day_of_week', 'start_time')
        
        serializer = self.get_serializer(timetables, many=True)
        
        # Organize by day of week
        weekly_schedule = {i: [] for i in range(7)}
        for timetable_data in serializer.data:
            day = timetable_data['day_of_week']
            weekly_schedule[day].append(timetable_data)
        
        return Response({
            'teacher_id': request.user.id,
            'teacher_name': request.user.get_full_name() or request.user.username,
            'weekly_schedule': weekly_schedule,
            'total_schedules': len(serializer.data)
        })


class InspectorAssignmentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing inspector assignments"""
    queryset = InspectorAssignment.objects.all()
    serializer_class = InspectorAssignmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter assignments based on user role"""
        user = self.request.user
        
        if user.role in ['minister', 'secretary']:
            # Minister/Secretary see all assignments
            return self.queryset.select_related('inspector', 'assigned_by')
        elif user.role == 'inspector':
            # Inspectors see only their own assignments
            return self.queryset.filter(inspector=user, is_active=True).select_related('assigned_by')
        elif user.role == 'gpi':
            # GPI sees all active assignments
            return self.queryset.filter(is_active=True).select_related('inspector', 'assigned_by')
        else:
            return self.queryset.none()
    
    def perform_create(self, serializer):
        """Save assignment with the user who created it"""
        if self.request.user.role not in ['minister', 'secretary']:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only minister or secretary can create assignments")
        serializer.save(assigned_by=self.request.user)
    
    def perform_update(self, serializer):
        """Only minister/secretary can update assignments"""
        if self.request.user.role not in ['minister', 'secretary']:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only minister or secretary can update assignments")
        serializer.save()
    
    @action(detail=False, methods=['get'], url_path='my-assignments')
    def my_assignments(self, request):
        """Get assignments for the logged-in inspector"""
        if request.user.role != 'inspector':
            return Response(
                {'error': 'Only inspectors can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        assignments = self.get_queryset().filter(inspector=request.user, is_active=True)
        serializer = self.get_serializer(assignments, many=True)
        
        return Response({
            'inspector_id': request.user.id,
            'inspector_name': request.user.get_full_name() or request.user.username,
            'assignments': serializer.data,
            'total_assignments': assignments.count()
        })
    
    @action(detail=False, methods=['get'], url_path='by-inspector/(?P<inspector_id>[^/.]+)')
    def by_inspector(self, request, inspector_id=None):
        """Get all assignments for a specific inspector"""
        if request.user.role not in ['minister', 'secretary', 'gpi']:
            return Response(
                {'error': 'Insufficient permissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            inspector = User.objects.get(id=inspector_id, role='inspector')
        except User.DoesNotExist:
            return Response(
                {'error': 'Inspector not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        assignments = self.queryset.filter(inspector=inspector, is_active=True)
        serializer = self.get_serializer(assignments, many=True)
        
        return Response({
            'inspector_id': inspector.id,
            'inspector_name': inspector.get_full_name() or inspector.username,
            'assignments': serializer.data,
            'total_assignments': assignments.count()
        })
    
    @action(detail=False, methods=['get'], url_path='available-inspectors')
    def available_inspectors(self, request):
        """Get list of all inspectors for assignment"""
        if request.user.role not in ['minister', 'secretary']:
            return Response(
                {'error': 'Only minister or secretary can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        inspectors = User.objects.filter(role='inspector', is_active=True)
        
        # Add assignment count for each inspector
        inspector_data = []
        for inspector in inspectors:
            active_assignments = InspectorAssignment.objects.filter(
                inspector=inspector,
                is_active=True
            ).count()
            
            inspector_data.append({
                'id': inspector.id,
                'username': inspector.username,
                'name': inspector.get_full_name() or inspector.username,
                'email': inspector.email,
                'active_assignments': active_assignments
            })
        
        return Response({
            'inspectors': inspector_data,
            'total_inspectors': len(inspector_data)
        })
    
    @action(detail=False, methods=['get'], url_path='assignment-options')
    def assignment_options(self, request):
        """Get available options for creating assignments (regions, subjects, school levels)"""
        if request.user.role not in ['minister', 'secretary']:
            return Response(
                {'error': 'Only minister or secretary can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get all unique regions from schools
        regions = School.objects.exclude(cre='').values_list('cre', flat=True).distinct().order_by('cre')
        
        # Get subject choices
        subjects = [{'value': code, 'label': label} for code, label in User.SUBJECT_CHOICES]
        
        # Get school level choices
        school_levels = [
            {'value': code, 'label': label} 
            for code, label in InspectorAssignment.SCHOOL_LEVEL_CHOICES
        ]
        
        # Get assignment type choices
        assignment_types = [
            {'value': code, 'label': label}
            for code, label in InspectorAssignment.ASSIGNMENT_TYPE_CHOICES
        ]
        
        return Response({
            'regions': list(regions),
            'subjects': subjects,
            'school_levels': school_levels,
            'assignment_types': assignment_types
        })
    
    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, pk=None):
        """Deactivate an inspector assignment (soft delete)"""
        if request.user.role not in ['minister', 'secretary']:
            return Response(
                {'error': 'Only minister or secretary can deactivate assignments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        assignment = self.get_object()
        assignment.is_active = False
        assignment.save()
        
        serializer = self.get_serializer(assignment)
        return Response({
            'message': 'Assignment deactivated successfully',
            'assignment': serializer.data
        })
    
    @action(detail=True, methods=['post'], url_path='reactivate')
    def reactivate(self, request, pk=None):
        """Reactivate a deactivated inspector assignment"""
        if request.user.role not in ['minister', 'secretary']:
            return Response(
                {'error': 'Only minister or secretary can reactivate assignments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        assignment = self.get_object()
        assignment.is_active = True
        assignment.save()
        
        serializer = self.get_serializer(assignment)
        return Response({
            'message': 'Assignment reactivated successfully',
            'assignment': serializer.data
        })
    
    @action(detail=True, methods=['get'], url_path='assigned-schools')
    def assigned_schools(self, request, pk=None):
        """Get all schools that match this assignment"""
        assignment = self.get_object()
        schools = assignment.get_assigned_schools()
        
        from .serializers import SchoolSerializer
        serializer = SchoolSerializer(schools, many=True)
        
        return Response({
            'assignment_id': assignment.id,
            'assignment_details': self.get_serializer(assignment).data,
            'schools': serializer.data,
            'total_schools': schools.count()
        })
