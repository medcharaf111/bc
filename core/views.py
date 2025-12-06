from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, BasePermission
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import (
    Lesson, Test, Progress, Portfolio, QATest, QASubmission, TestSubmission, TeachingPlan,
    VaultLessonPlan, VaultLessonPlanUsage, VaultComment, VaultExercise, VaultMaterial,
    StudentNotebook, NotebookPage
)
from .serializers import (
    LessonSerializer, TestSerializer, ProgressSerializer, 
    PortfolioSerializer, QATestSerializer, QASubmissionSerializer,
    TestSubmissionSerializer, TeachingPlanSerializer,
    VaultLessonPlanSerializer, VaultLessonPlanUsageSerializer, VaultCommentSerializer,
    VaultExerciseSerializer, VaultMaterialSerializer, StudentNotebookSerializer, NotebookPageSerializer
)
from .ai_service import get_ai_service
from .analytics import MinisterAnalytics
import logging
import json

logger = logging.getLogger(__name__)


class IsAdminRole(BasePermission):
    """
    Custom permission to check if user has admin or minister role
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['admin', 'minister']

class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter lessons based on user role"""
        user = self.request.user
        queryset = self.queryset
        
        if user.role == 'teacher':
            # Teachers see only their own lessons
            queryset = queryset.filter(created_by=user)
        elif user.role == 'advisor':
            # Advisors see lessons from teachers in their subject (same school and subject)
            advisor_subject = user.subjects[0] if user.subjects else None
            logger.info(f"Advisor {user.username} subject: {advisor_subject}")
            logger.info(f"Advisor school: {user.school}")
            if advisor_subject:
                queryset = queryset.filter(
                    school=user.school,
                    subject=advisor_subject,
                    created_by__role='teacher'  # Only show lessons created by teachers
                )
                logger.info(f"Filtered lessons count: {queryset.count()}")
                for lesson in queryset:
                    logger.info(f"Lesson: {lesson.title} by {lesson.created_by.username} ({lesson.created_by.role})")
            else:
                queryset = queryset.none()
        elif user.role == 'student':
            # Students see lessons from their teachers (to access Q&A tests)
            from accounts.models import TeacherStudentRelationship
            teacher_ids = TeacherStudentRelationship.objects.filter(
                student=user, is_active=True
            ).values_list('teacher_id', flat=True)
            queryset = queryset.filter(created_by_id__in=teacher_ids)
            logger.info(f"Student {user.username} can see {queryset.count()} lessons from {len(teacher_ids)} teachers")
        elif user.role in ['admin', 'minister']:
            # Admins and ministers see all lessons in their school
            queryset = queryset.filter(school=user.school)
        
        return queryset

    def perform_create(self, serializer):
        # Validate that teacher is creating lesson for a subject they are assigned to
        if self.request.user.role == 'teacher':
            subject = serializer.validated_data.get('subject')
            
            # Check if teacher has active assignments for this subject
            from accounts.models import TeacherGradeAssignment
            assigned_subjects = TeacherGradeAssignment.objects.filter(
                teacher=self.request.user,
                is_active=True
            ).values_list('subject', flat=True).distinct()
            
            assigned_subjects_list = list(assigned_subjects)
            
            if not assigned_subjects_list:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({
                    'subject': 'You have no active subject assignments. Please contact your school director to assign you to grades and subjects.'
                })
            
            if subject not in assigned_subjects_list:
                from rest_framework.exceptions import ValidationError
                subject_names = [dict(self.request.user.SUBJECT_CHOICES).get(s, s) for s in assigned_subjects_list]
                raise ValidationError({
                    'subject': f'You can only create lessons for subjects you are assigned to: {", ".join(subject_names)}'
                })
        
        lesson = serializer.save(created_by=self.request.user, school=self.request.user.school)
        
        # Detect chapter progression for teachers
        if self.request.user.role == 'teacher':
            self._detect_chapter_change(lesson)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate AI lesson content"""
        prompt = request.data.get('prompt')
        if not prompt:
            return Response({'error': 'Prompt required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get subject and grade from request
            subject = request.data.get('subject', 'math')
            grade_level = request.data.get('grade_level', '1')
            
            # Validate that teacher can create lessons for this subject (must be assigned)
            if request.user.role == 'teacher':
                from accounts.models import TeacherGradeAssignment
                assigned_subjects = TeacherGradeAssignment.objects.filter(
                    teacher=request.user,
                    is_active=True
                ).values_list('subject', flat=True).distinct()
                
                assigned_subjects_list = list(assigned_subjects)
                
                if not assigned_subjects_list:
                    return Response({
                        'error': 'You have no active subject assignments. Please contact your school director to assign you to grades and subjects.'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                if subject not in assigned_subjects_list:
                    subject_names = [dict(request.user.SUBJECT_CHOICES).get(s, s) for s in assigned_subjects_list]
                    return Response({
                        'error': f'You can only create lessons for subjects you are assigned to: {", ".join(subject_names)}'
                    }, status=status.HTTP_403_FORBIDDEN)
            
            # Use AI service to generate lesson content
            ai_service = get_ai_service()
            content = ai_service.generate_lesson(prompt, subject, grade_level)
            
            # Create lesson in database
            lesson = Lesson.objects.create(
                title=request.data.get('title', f"AI Generated: {prompt[:50]}"),
                content=content,
                subject=subject,
                grade_level=grade_level,
                created_by=request.user,
                school=request.user.school
            )
            
            serializer = self.get_serializer(lesson)
            return Response({
                'lesson_id': lesson.id,
                'lesson': serializer.data,
                'content': content
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error generating lesson: {str(e)}")
            return Response({
                'error': f'Failed to generate lesson: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='generate-test')
    def generate_test(self, request):
        """Generate MCQ test questions from a lesson and save as pending"""
        lesson_id = request.data.get('lesson_id')
        num_questions = request.data.get('num_questions', 10)
        
        if not lesson_id:
            return Response({'error': 'lesson_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            lesson = get_object_or_404(Lesson, pk=lesson_id)
            ai_service = get_ai_service()
            
            # Generate questions using AI
            questions_text = ai_service.generate_test_questions(lesson.content, num_questions)
            
            # Parse JSON to validate format
            import json
            questions_data = json.loads(questions_text)
            
            # Create test in database with pending status
            test = Test.objects.create(
                lesson=lesson,
                title=request.data.get('title', f"MCQ Test: {lesson.title}"),
                questions=questions_data,
                num_questions=num_questions,
                status='pending',
                created_by=request.user
            )
            
            serializer = TestSerializer(test)
            return Response({
                'test_id': test.id,
                'test': serializer.data,
                'message': 'Test created and pending teacher review'
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error generating test: {str(e)}")
            return Response({
                'error': f'Failed to generate test: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _detect_chapter_change(self, lesson):
        """Detect if teacher moved to a new chapter using AI"""
        try:
            from accounts.models import TeacherProgress, ChapterProgressNotification, User
            
            teacher = lesson.created_by
            subject = lesson.subject
            grade_level = lesson.grade_level
            
            # Get or create teacher progress for this subject/grade
            progress, created = TeacherProgress.objects.get_or_create(
                teacher=teacher,
                subject=subject,
                grade_level=grade_level,
                defaults={
                    'current_chapter': lesson.title,
                    'chapter_number': 1,
                    'total_chapters': 10  # Default, can be updated
                }
            )
            
            # If progress was just created, no notification needed
            if created:
                logger.info(f"Created new progress tracking for {teacher.username} - {subject}")
                return
            
            # Use AI to detect if this is a new chapter
            ai_service = get_ai_service()
            
            prompt = f"""Analyze if this lesson indicates a new chapter/unit in the curriculum:

Previous Chapter: {progress.current_chapter}
New Lesson Title: {lesson.title}
Lesson Content (first 500 chars): {lesson.content[:500]}

Determine:
1. Is this a NEW chapter/unit (not just a continuation of the previous one)?
2. If yes, what is the new chapter name/number?
3. Your confidence level (0.0 to 1.0)

Respond ONLY with valid JSON:
{{
    "is_new_chapter": true/false,
    "new_chapter_name": "Chapter name",
    "new_chapter_number": number,
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}"""
            
            response = ai_service.model.generate_content(prompt)
            analysis = json.loads(response.text)
            
            if analysis.get('is_new_chapter') and analysis.get('confidence', 0) > 0.7:
                # Create notification for advisor
                # Find advisor for this subject in the school (SQLite doesn't support JSON __contains)
                all_advisors = User.objects.filter(
                    role='advisor',
                    school=teacher.school
                )
                # Filter by subject using Python
                advisors = [
                    a for a in all_advisors 
                    if a.subjects and subject in a.subjects
                ]
                
                for advisor in advisors:
                    notification = ChapterProgressNotification.objects.create(
                        teacher_progress=progress,
                        advisor=advisor,
                        previous_chapter=progress.current_chapter,
                        previous_chapter_number=progress.chapter_number,
                        new_chapter=analysis.get('new_chapter_name', lesson.title),
                        new_chapter_number=analysis.get('new_chapter_number', progress.chapter_number + 1),
                        ai_detected=True,
                        ai_confidence=analysis.get('confidence', 0),
                        status='pending'
                    )
                    logger.info(f"Created chapter notification for advisor {advisor.username}")
                
                # Update teacher progress (tentatively)
                progress.current_chapter = analysis.get('new_chapter_name', lesson.title)
                progress.chapter_number = analysis.get('new_chapter_number', progress.chapter_number + 1)
                progress.save()
                
        except Exception as e:
            logger.error(f"Error detecting chapter change: {str(e)}")
            # Don't fail lesson creation if chapter detection fails
    
    @action(detail=False, methods=['get'])
    def timeline(self, request):
        """
        Get lessons organized by scheduled date for timeline view.
        Returns lessons grouped by date, including unscheduled lessons.
        """
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Only teachers can view lesson timeline'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from datetime import datetime, timedelta
        from django.db.models import Q
        
        # Get date range from query params (default to current month)
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = self.get_queryset()
        
        if start_date and end_date:
            queryset = queryset.filter(
                Q(scheduled_date__isnull=True) |
                Q(scheduled_date__range=[start_date, end_date])
            )
        
        # Organize by scheduled date
        scheduled = queryset.filter(scheduled_date__isnull=False).order_by('scheduled_date')
        unscheduled = queryset.filter(scheduled_date__isnull=True).order_by('-created_at')
        
        serializer = self.get_serializer(scheduled, many=True)
        unscheduled_serializer = self.get_serializer(unscheduled, many=True)
        
        return Response({
            'scheduled': serializer.data,
            'unscheduled': unscheduled_serializer.data
        })
    
    @action(detail=True, methods=['patch'])
    def schedule(self, request, pk=None):
        """
        Schedule or reschedule a lesson to a specific date.
        """
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Only teachers can schedule lessons'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        lesson = self.get_object()
        scheduled_date = request.data.get('scheduled_date')
        
        if not scheduled_date:
            return Response(
                {'error': 'scheduled_date required (YYYY-MM-DD format)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        lesson.scheduled_date = scheduled_date
        lesson.save(update_fields=['scheduled_date'])
        
        serializer = self.get_serializer(lesson)
        return Response({
            'lesson': serializer.data,
            'message': f'Lesson scheduled for {scheduled_date}'
        })

class TestViewSet(viewsets.ModelViewSet):
    queryset = Test.objects.all()
    serializer_class = TestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter tests based on user role"""
        user = self.request.user
        queryset = self.queryset
        
        if user.role == 'teacher':
            # Teachers see only tests from their own lessons
            queryset = queryset.filter(lesson__created_by=user)
        elif user.role == 'advisor':
            # Advisors see tests from lessons in their subject (only from teachers)
            advisor_subject = user.subjects[0] if user.subjects else None
            if advisor_subject:
                queryset = queryset.filter(
                    lesson__school=user.school,
                    lesson__subject=advisor_subject,
                    lesson__created_by__role='teacher'  # Only tests from teacher lessons
                )
            else:
                queryset = queryset.none()
        elif user.role in ['admin', 'minister']:
            # Admins and ministers see all tests in their school
            queryset = queryset.filter(lesson__school=user.school)
        elif user.role == 'student':
            # Students only see approved tests they haven't completed
            # Exclude tests with final approved submissions
            completed_test_ids = TestSubmission.objects.filter(
                student=user,
                is_final=True
            ).values_list('test_id', flat=True)
            
            queryset = queryset.filter(
                lesson__school=user.school,
                status='approved'
            ).exclude(id__in=completed_test_ids)
        else:
            queryset = queryset.none()
        
        # Apply lesson filter if provided
        lesson_id = self.request.query_params.get('lesson')
        if lesson_id:
            queryset = queryset.filter(lesson_id=lesson_id)
        
        # Apply question_type filter if provided (mcq or qa)
        question_type = self.request.query_params.get('question_type')
        if question_type in ['mcq', 'qa']:
            queryset = queryset.filter(question_type=question_type)
        
        return queryset

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit MCQ test answers (student only)"""
        test = self.get_object()
        
        # Check if test is approved
        if test.status != 'approved':
            return Response(
                {'error': 'This test is not available for submission'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if student already has a final approved submission
        existing_final = TestSubmission.objects.filter(
            test=test,
            student=request.user,
            is_final=True
        ).first()
        
        if existing_final:
            return Response(
                {'error': 'You have already completed this test. Retakes are not allowed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get submission data
        answers = request.data.get('answers', {})
        score = request.data.get('score')
        
        if score is None:
            return Response(
                {'error': 'Score is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create submission
        submission = TestSubmission.objects.create(
            test=test,
            student=request.user,
            answers=answers,
            score=score,
            status='submitted'
        )
        
        serializer = TestSubmissionSerializer(submission)
        return Response({
            'message': 'Test submitted successfully. Awaiting teacher approval.',
            'submission': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def approve_submission(self, request, pk=None):
        """Approve a test submission (teacher only)"""
        if request.user.role not in ['teacher', 'admin']:
            return Response(
                {'error': 'Only teachers can approve submissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        submission_id = request.data.get('submission_id')
        if not submission_id:
            return Response(
                {'error': 'submission_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        submission = get_object_or_404(TestSubmission, id=submission_id)
        
        # Update submission status
        submission.status = 'approved'
        submission.is_final = True
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()
        submission.teacher_feedback = request.data.get('feedback', '')
        submission.save()
        
        # Update or create Progress entry
        Progress.objects.update_or_create(
            student=submission.student,
            lesson=submission.test.lesson,
            defaults={
                'score': submission.score,
                'completed_at': timezone.now(),
                'notes': f"MCQ Test Score: {submission.score}%"
            }
        )
        
        # Save to student's portfolio
        portfolio, created = Portfolio.objects.get_or_create(
            student=submission.student,
            defaults={
                'summary': f'Portfolio for {submission.student.username}',
                'achievements': [],
                'test_results': []
            }
        )
        portfolio.add_test_result(
            lesson_name=submission.test.lesson.title,
            test_title=submission.test.title,
            test_type='MCQ',
            score=submission.score,
            attempt=submission.attempt_number
        )
        
        serializer = TestSubmissionSerializer(submission)
        return Response({
            'message': 'Submission approved and marks saved successfully',
            'submission': serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def reject_submission(self, request, pk=None):
        """Reject a test submission - allows student to retake (teacher only)"""
        if request.user.role not in ['teacher', 'admin']:
            return Response(
                {'error': 'Only teachers can reject submissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        submission_id = request.data.get('submission_id')
        if not submission_id:
            return Response(
                {'error': 'submission_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        submission = get_object_or_404(TestSubmission, id=submission_id)
        
        # Update submission status
        submission.status = 'rejected'
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()
        submission.teacher_feedback = request.data.get('feedback', 'Please retake this test.')
        submission.save()
        
        serializer = TestSubmissionSerializer(submission)
        return Response({
            'message': 'Submission rejected. Student can retake the test.',
            'submission': serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def submissions(self, request):
        """Get all test submissions (teacher: own lessons, student: own)"""
        user = request.user
        
        if user.role == 'teacher':
            # Teachers see only submissions from their own lesson tests
            submissions = TestSubmission.objects.filter(
                test__lesson__created_by=user
            ).select_related('student', 'test', 'reviewed_by')
        elif user.role in ['admin', 'minister']:
            # Admins and ministers see all submissions in their school
            submissions = TestSubmission.objects.filter(
                test__lesson__school=user.school
            ).select_related('student', 'test', 'reviewed_by')
        elif user.role == 'student':
            # Students see only their own submissions
            submissions = TestSubmission.objects.filter(student=user)
        else:
            submissions = TestSubmission.objects.none()
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            submissions = submissions.filter(status=status_filter)
        
        serializer = TestSubmissionSerializer(submissions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a test and assign to selected students (teacher only)"""
        if request.user.role not in ['teacher', 'admin']:
            return Response(
                {'error': 'Only teachers can approve tests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        test = self.get_object()
        student_ids = request.data.get('student_ids', [])
        
        if not student_ids:
            return Response(
                {'error': 'Please select at least one student to assign this test to'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Approve the test
        test.status = 'approved'
        test.reviewed_by = request.user
        test.review_notes = request.data.get('notes', '')
        test.save()
        
        # Generate personalized versions for selected students
        from accounts.models import User
        from .models import Portfolio, PersonalizedTest
        from .ai_service import AIService
        import json
        
        ai_service = AIService()
        lesson = test.lesson
        subject = lesson.subject
        personalized_count = 0
        errors = []
        
        for student_id in student_ids:
            try:
                student = User.objects.get(id=student_id, role='student')
                
                # Check if personalized version already exists
                if PersonalizedTest.objects.filter(base_test=test, student=student).exists():
                    continue
                
                # Analyze student performance
                difficulty_level = "medium"
                performance_score = None
                performance_context = ""
                
                try:
                    portfolio = Portfolio.objects.get(student=student)
                    stats = portfolio.get_subject_statistics()
                    
                    if subject in stats and 'average_score' in stats[subject]:
                        performance_score = stats[subject]['average_score']
                        
                        # Determine difficulty level
                        if performance_score < 50:
                            difficulty_level = "easy"
                            performance_context = f"\n\nGenerate EASIER questions (performance: {performance_score:.1f}%):\n- Clear, straightforward language\n- Step-by-step guidance"
                        elif performance_score < 70:
                            difficulty_level = "medium"
                            performance_context = f"\n\nGenerate MEDIUM difficulty questions (performance: {performance_score:.1f}%):\n- Mix of straightforward and challenging"
                        elif performance_score < 85:
                            difficulty_level = "medium-hard"
                            performance_context = f"\n\nGenerate CHALLENGING questions (performance: {performance_score:.1f}%):\n- Test deep understanding"
                        else:
                            difficulty_level = "hard"
                            performance_context = f"\n\nGenerate ADVANCED questions (performance: {performance_score:.1f}%):\n- Complex scenarios"
                except Portfolio.DoesNotExist:
                    performance_context = "\n\nNo prior data. Generate medium difficulty questions."
                
                # Generate personalized questions
                lesson_content = lesson.content + performance_context
                
                if test.question_type == 'mcq':
                    questions_json = ai_service.generate_test_questions(lesson_content, test.num_questions)
                else:
                    questions_json = ai_service.generate_qa_questions(lesson_content, test.num_questions)
                
                questions_data = json.loads(questions_json)
                
                # Create personalized test
                PersonalizedTest.objects.create(
                    base_test=test,
                    student=student,
                    questions=questions_data,
                    difficulty_level=difficulty_level,
                    performance_score=performance_score
                )
                
                personalized_count += 1
                
            except User.DoesNotExist:
                errors.append(f"Student with ID {student_id} not found")
            except Exception as e:
                errors.append(f"Error creating personalized test for student {student_id}: {str(e)}")
        
        serializer = self.get_serializer(test)
        response_data = {
            'message': f'Test approved and assigned to {personalized_count} student(s)',
            'test': serializer.data,
            'personalized_count': personalized_count
        }
        
        if errors:
            response_data['errors'] = errors
        
        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def my_students(self, request):
        """Get list of students assigned to this teacher"""
        if request.user.role not in ['teacher', 'admin']:
            return Response(
                {'error': 'Only teachers can view their students'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from accounts.models import TeacherStudentRelationship, User
        
        # Get students assigned to this teacher
        relationships = TeacherStudentRelationship.objects.filter(
            teacher=request.user
        ).select_related('student')
        
        students = []
        for rel in relationships:
            student = rel.student
            students.append({
                'id': student.id,
                'username': student.username,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'full_name': student.get_full_name() or student.username,
                'email': student.email
            })
        
        return Response({'students': students}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a test (teacher only)"""
        if request.user.role not in ['teacher', 'admin']:
            return Response(
                {'error': 'Only teachers can reject tests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        test = self.get_object()
        test.status = 'rejected'
        test.reviewed_by = request.user
        test.review_notes = request.data.get('notes', 'Test rejected by teacher')
        test.save()
        
        serializer = self.get_serializer(test)
        return Response({
            'message': 'Test rejected',
            'test': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'])
    def update_questions(self, request, pk=None):
        """Update test questions (teacher only)"""
        if request.user.role not in ['teacher', 'admin']:
            return Response(
                {'error': 'Only teachers can edit tests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        test = self.get_object()
        questions = request.data.get('questions')
        
        if not questions:
            return Response(
                {'error': 'questions field required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        test.questions = questions
        test.save()
        
        serializer = self.get_serializer(test)
        return Response({
            'message': 'Questions updated successfully',
            'test': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get all pending tests (teacher only)"""
        if request.user.role not in ['teacher', 'admin']:
            return Response(
                {'error': 'Only teachers can view pending tests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        pending_tests = self.get_queryset().filter(status='pending')
        serializer = self.get_serializer(pending_tests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def generate_questions(self, request, pk=None):
        """Generate test questions from a lesson"""
        lesson = self.get_object().lesson if hasattr(self.get_object(), 'lesson') else get_object_or_404(Lesson, pk=pk)
        num_questions = request.data.get('num_questions', 5)
        
        try:
            ai_service = get_ai_service()
            questions = ai_service.generate_test_questions(lesson.content, num_questions)
            
            # Create test in database
            test = Test.objects.create(
                lesson=lesson,
                title=f"Test for {lesson.title}",
                questions=questions
            )
            
            serializer = self.get_serializer(test)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error generating test questions: {str(e)}")
            return Response({
                'error': f'Failed to generate questions: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def grade(self, request):
        """Grade a test using two PDFs: exam PDF and correction guide PDF"""
        exam_pdf = request.FILES.get('exam_pdf')
        guide_pdf = request.FILES.get('guide_pdf')
        
        if not exam_pdf or not guide_pdf:
            return Response({
                'error': 'Both exam_pdf and guide_pdf are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file types
        if not exam_pdf.name.endswith('.pdf') or not guide_pdf.name.endswith('.pdf'):
            return Response({
                'error': 'Both files must be PDF format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Use AI service to extract text and grade
            from .gemini_service import GeminiService
            ai_service = GeminiService()
            
            # Process both PDFs and grade
            grading_result = ai_service.grade_exam_with_guide(exam_pdf, guide_pdf)
            
            return Response({
                'success': True,
                'result': grading_result
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Failed to grade test: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProgressViewSet(viewsets.ModelViewSet):
    queryset = Progress.objects.all()
    serializer_class = ProgressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'teacher':
            # Teachers see only progress for their own lessons
            return self.queryset.filter(lesson__created_by=user)
        elif user.role in ['admin', 'minister']:
            # Admins and ministers see all progress in their school
            return self.queryset.filter(lesson__school=user.school)
        elif user.role == 'student':
            # Students see only their own progress
            return self.queryset.filter(student=user)
        return self.queryset.none()

class PortfolioViewSet(viewsets.ModelViewSet):
    queryset = Portfolio.objects.all()
    serializer_class = PortfolioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'student':
            return self.queryset.filter(student=self.request.user)
        return self.queryset
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get subject-based performance statistics for the current student"""
        user = request.user
        
        # Students can only see their own statistics - parents cannot access
        if user.role == 'student':
            student = user
        else:
            # Parents, teachers, and admins are not allowed to access statistics
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get or create portfolio for the student
        portfolio, created = Portfolio.objects.get_or_create(
            student=student,
            defaults={
                'summary': f'Portfolio for {student.username}',
                'achievements': [],
                'test_results': []
            }
        )
        
        # Get subject statistics
        statistics = portfolio.get_subject_statistics()
        
        return Response({
            'student': student.username,
            'statistics': statistics
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def progress_analysis(self, request):
        """Get historical weakness analysis and progress trends for student"""
        user = request.user
        
        # Allow students to see their own, teachers/admins can specify student_id
        # Parents are NOT allowed to access progress analysis
        if user.role == 'student':
            student = user
        elif user.role in ['teacher', 'admin']:
            student_id = request.query_params.get('student_id')
            if not student_id:
                return Response(
                    {'error': 'student_id parameter required for teachers'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            from accounts.models import User
            student = get_object_or_404(User, id=student_id, role='student')
        else:
            # Parents and other roles cannot access progress analysis
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get or create portfolio
        portfolio, created = Portfolio.objects.get_or_create(
            student=student,
            defaults={
                'summary': f'Portfolio for {student.username}',
                'achievements': [],
                'test_results': []
            }
        )
        
        # Get subject filter if provided
        subject = request.query_params.get('subject')
        
        # Get historical analysis
        analysis = portfolio.get_historical_weakness_analysis(subject=subject)
        
        return Response({
            'student': student.username,
            'student_id': student.id,
            'analysis': analysis
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def gamification(self, request):
        """Get gamification stats (XP, level, streak) for student"""
        user = request.user
        
        # Only students can access their own gamification data
        if user.role != 'student':
            return Response(
                {'error': 'Only students can access gamification data'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        student = user
        
        # Get or create portfolio
        portfolio, created = Portfolio.objects.get_or_create(
            student=student,
            defaults={
                'summary': f'Portfolio for {student.username}',
                'achievements': [],
                'test_results': []
            }
        )
        
        test_results = portfolio.test_results or []
        
        # Calculate XP and level
        xp_points = 0
        level = 1
        streak_days = 0
        
        if test_results:
            for test in test_results:
                score = test.get('score', 0)
                # XP calculation: 10 base + up to 40 bonus based on score
                base_xp = 10
                bonus_xp = int(score * 0.4)
                test_xp = base_xp + bonus_xp
                xp_points += test_xp
            
            # Level calculation: Every 200 XP = 1 level
            level = (xp_points // 200) + 1
            
            # Streak calculation
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
                    
                    days_since_last = (today - last_test_date).days
                    if days_since_last <= 7:
                        current_date = last_test_date
                        streak_days = 1
                        
                        for test in sorted_tests[1:]:
                            test_date = datetime.fromisoformat(test['date'].replace('Z', '+00:00'))
                            days_diff = (current_date - test_date).days
                            
                            if days_diff <= 7:
                                streak_days += 1
                                current_date = test_date
                            else:
                                break
                except (ValueError, KeyError, AttributeError):
                    streak_days = 0
        
        # Calculate XP needed for next level
        xp_for_next_level = (level * 200) - xp_points
        xp_progress_in_current_level = xp_points % 200
        
        return Response({
            'student': student.username,
            'xp_points': xp_points,
            'level': level,
            'streak_days': streak_days,
            'total_tests': len(test_results),
            'xp_for_next_level': xp_for_next_level,
            'xp_progress_in_current_level': xp_progress_in_current_level,
            'level_progress_percentage': (xp_progress_in_current_level / 200) * 100
        }, status=status.HTTP_200_OK)

class QATestViewSet(viewsets.ModelViewSet):
    queryset = QATest.objects.all()
    serializer_class = QATestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter Q&A tests based on user role"""
        user = self.request.user
        queryset = self.queryset
        
        if user.role == 'teacher':
            # Teachers see only tests from their own lessons
            queryset = queryset.filter(lesson__created_by=user)
        elif user.role == 'advisor':
            # Advisors see tests from lessons in their subject (only from teachers)
            advisor_subject = user.subjects[0] if user.subjects else None
            if advisor_subject:
                queryset = queryset.filter(
                    lesson__school=user.school,
                    lesson__subject=advisor_subject,
                    lesson__created_by__role='teacher'  # Only tests from teacher lessons
                )
            else:
                queryset = queryset.none()
        elif user.role in ['admin', 'minister']:
            # Admins and ministers see all tests in their school
            queryset = queryset.filter(lesson__school=user.school)
        elif user.role == 'student':
            # Students only see approved tests from their assigned teachers
            from accounts.models import TeacherStudentRelationship
            teacher_ids = TeacherStudentRelationship.objects.filter(
                student=user,
                is_active=True
            ).values_list('teacher_id', flat=True)
            
            logger.info(f"Student {user.username} has {len(teacher_ids)} teachers: {list(teacher_ids)}")
            
            queryset = queryset.filter(
                lesson__created_by_id__in=teacher_ids,
                status='approved'
            )
            
            logger.info(f"Student {user.username} can see {queryset.count()} approved Q&A tests")
        else:
            queryset = queryset.none()
        
        # Apply lesson filter if provided
        lesson_id = self.request.query_params.get('lesson')
        if lesson_id:
            queryset = queryset.filter(lesson_id=lesson_id)
        
        return queryset

    @action(detail=False, methods=['post'], url_path='generate-qa-test')
    def generate_qa_test(self, request):
        """Generate Q&A test questions from a lesson and save as pending"""
        lesson_id = request.data.get('lesson_id')
        num_questions = request.data.get('num_questions', 5)
        time_limit = request.data.get('time_limit', 30)
        
        if not lesson_id:
            return Response({'error': 'lesson_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            lesson = get_object_or_404(Lesson, pk=lesson_id)
            ai_service = get_ai_service()
            
            # Generate Q&A questions using AI
            questions_text = ai_service.generate_qa_questions(lesson.content, num_questions)
            questions_data = json.loads(questions_text)
            
            # Create Q&A test in database with pending status
            qa_test = QATest.objects.create(
                lesson=lesson,
                title=request.data.get('title', f"Q&A Test: {lesson.title}"),
                questions=questions_data,
                num_questions=num_questions,
                time_limit=time_limit,
                status='pending',
                created_by=request.user
            )
            
            serializer = self.get_serializer(qa_test)
            return Response({
                'test_id': qa_test.id,
                'test': serializer.data,
                'message': 'Q&A test created and pending teacher review'
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error generating Q&A test: {str(e)}")
            return Response({
                'error': f'Failed to generate Q&A test: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a Q&A test (teacher only)"""
        if request.user.role not in ['teacher', 'admin']:
            return Response(
                {'error': 'Only teachers can approve tests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        qa_test = self.get_object()
        qa_test.status = 'approved'
        qa_test.reviewed_by = request.user
        qa_test.review_notes = request.data.get('notes', '')
        qa_test.save()
        
        serializer = self.get_serializer(qa_test)
        return Response({
            'message': 'Q&A test approved successfully',
            'test': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a Q&A test (teacher only)"""
        if request.user.role not in ['teacher', 'admin']:
            return Response(
                {'error': 'Only teachers can reject tests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        qa_test = self.get_object()
        qa_test.status = 'rejected'
        qa_test.reviewed_by = request.user
        qa_test.review_notes = request.data.get('notes', 'Test rejected by teacher')
        qa_test.save()
        
        serializer = self.get_serializer(qa_test)
        return Response({
            'message': 'Q&A test rejected',
            'test': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'])
    def update_questions(self, request, pk=None):
        """Update Q&A test questions (teacher only)"""
        if request.user.role not in ['teacher', 'admin']:
            return Response(
                {'error': 'Only teachers can edit tests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        qa_test = self.get_object()
        questions = request.data.get('questions')
        
        if not questions:
            return Response(
                {'error': 'questions field required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        qa_test.questions = questions
        qa_test.save()
        
        serializer = self.get_serializer(qa_test)
        return Response({
            'message': 'Questions updated successfully',
            'test': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get all pending Q&A tests (teacher only)"""
        if request.user.role not in ['teacher', 'admin']:
            return Response(
                {'error': 'Only teachers can view pending tests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        pending_tests = self.get_queryset().filter(status='pending')
        serializer = self.get_serializer(pending_tests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class QASubmissionViewSet(viewsets.ModelViewSet):
    queryset = QASubmission.objects.all()
    serializer_class = QASubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter submissions based on user role"""
        user = self.request.user
        
        if user.role == 'teacher':
            # Teachers see only submissions from their own lesson tests
            return self.queryset.filter(test__lesson__created_by=user)
        elif user.role in ['admin', 'minister']:
            # Admins and ministers see all submissions in their school
            return self.queryset.filter(test__lesson__school=user.school)
        elif user.role == 'student':
            # Students only see their own submissions
            return self.queryset.filter(student=user)
        return self.queryset.none()

    @action(detail=False, methods=['post'])
    def submit(self, request):
        """Submit Q&A test answers for AI grading"""
        test_id = request.data.get('test_id')
        answers = request.data.get('answers', [])
        time_taken = request.data.get('time_taken')
        fullscreen_exits = request.data.get('fullscreen_exits', 0)
        
        if not test_id:
            return Response({'error': 'test_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            qa_test = get_object_or_404(QATest, pk=test_id, status='approved')
            
            # Check if student already submitted
            existing = QASubmission.objects.filter(test=qa_test, student=request.user).first()
            if existing:
                return Response(
                    {'error': 'You have already submitted this test'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Grade using AI
            ai_service = get_ai_service()
            grading_result = ai_service.grade_qa_submission(qa_test.questions, answers)
            
            # Generate comprehensive weakness analysis for teacher
            student_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
            weakness_analysis = ai_service.analyze_student_weaknesses(
                qa_test.questions, 
                answers,
                student_name
            )
            
            # Create submission with AI feedback and analysis
            submission = QASubmission.objects.create(
                test=qa_test,
                student=request.user,
                answers=answers,
                ai_feedback=grading_result,
                ai_analysis=weakness_analysis,
                time_taken=time_taken,
                fullscreen_exits=fullscreen_exits,
                status='ai_graded'
            )
            
            serializer = self.get_serializer(submission)
            return Response({
                'submission_id': submission.id,
                'submission': serializer.data,
                'message': 'Test submitted successfully. Awaiting teacher review.',
                'ai_score': grading_result.get('overall_score')
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error submitting Q&A test: {str(e)}")
            return Response({
                'error': f'Failed to submit test: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        """Finalize grading after teacher review (teacher only)"""
        if request.user.role not in ['teacher', 'admin']:
            return Response(
                {'error': 'Only teachers can finalize grades'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        submission = self.get_object()
        final_score = request.data.get('final_score')
        teacher_feedback = request.data.get('teacher_feedback', '')
        
        if final_score is None:
            return Response(
                {'error': 'final_score required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        submission.final_score = final_score
        submission.teacher_feedback = teacher_feedback
        submission.status = 'finalized'
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()
        submission.save()
        
        # Update Progress entry
        Progress.objects.update_or_create(
            student=submission.student,
            lesson=submission.test.lesson,
            defaults={
                'score': final_score,
                'completed_at': timezone.now(),
                'notes': f"Q&A Test Score: {final_score}%"
            }
        )
        
        # Save to student's portfolio
        portfolio, created = Portfolio.objects.get_or_create(
            student=submission.student,
            defaults={
                'summary': f'Portfolio for {submission.student.username}',
                'achievements': [],
                'test_results': []
            }
        )
        portfolio.add_test_result(
            lesson_name=submission.test.lesson.title,
            test_title=submission.test.title,
            test_type='QA',
            score=final_score,
            attempt=1  # QA tests don't have multiple attempts
        )
        
        serializer = self.get_serializer(submission)
        return Response({
            'message': 'Grade finalized successfully',
            'submission': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def pending_review(self, request):
        """Get all submissions pending teacher review (teacher only)"""
        if request.user.role not in ['teacher', 'admin']:
            return Response(
                {'error': 'Only teachers can view pending submissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        pending = self.get_queryset().filter(status='ai_graded')
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TeachingPlanViewSet(viewsets.ModelViewSet):
    """
    ViewSet for teaching plans/timeline.
    - Teachers can create, view, update, delete their own plans
    - Students can view plans from their assigned teachers
    - Advisors can view plans from teachers in their subject
    """
    queryset = TeachingPlan.objects.all()
    serializer_class = TeachingPlanSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter teaching plans based on user role"""
        user = self.request.user
        queryset = self.queryset
        
        if user.role == 'teacher':
            # Teachers see only their own plans
            queryset = queryset.filter(teacher=user)
        
        elif user.role == 'student':
            # Students see plans from their assigned teachers
            from accounts.models import TeacherStudentRelationship
            teacher_relationships = TeacherStudentRelationship.objects.filter(
                student=user,
                is_active=True
            ).values_list('teacher_id', flat=True)
            queryset = queryset.filter(teacher_id__in=teacher_relationships)
        
        elif user.role == 'advisor':
            # Advisors see plans from teachers in their subject and school
            advisor_subject = user.subjects[0] if user.subjects and len(user.subjects) > 0 else None
            if advisor_subject:
                from accounts.models import User
                # Get all teachers in same school, then filter by subject in Python
                # (SQLite doesn't support __contains on JSONField)
                all_teachers = User.objects.filter(
                    role='teacher',
                    school=user.school
                )
                # Filter teachers who have the advisor's subject in their subjects list
                teacher_ids = [t.id for t in all_teachers if advisor_subject in (t.subjects or [])]
                queryset = queryset.filter(teacher_id__in=teacher_ids)
            else:
                queryset = queryset.none()
        
        elif user.role in ['admin', 'minister']:
            # Admins and ministers see plans from their school
            queryset = queryset.filter(teacher__school=user.school)
        
        else:
            queryset = queryset.none()
        
        # Optional filters from query params
        teacher_id = self.request.query_params.get('teacher')
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        
        subject = self.request.query_params.get('subject')
        if subject:
            queryset = queryset.filter(subject=subject)
        
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        
        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.select_related('teacher', 'lesson')
    
    def perform_create(self, serializer):
        """Set the teacher to the current user"""
        serializer.save(teacher=self.request.user)
    
    def perform_update(self, serializer):
        """Only allow teacher to update their own plans"""
        if serializer.instance.teacher != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only edit your own teaching plans")
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only allow teacher to delete their own plans"""
        if instance.teacher != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only delete your own teaching plans")
        instance.delete()
    
    @action(detail=False, methods=['get'])
    def my_teachers(self, request):
        """
        Get teaching plans grouped by teacher (for students and advisors)
        Returns: {teacher_id: {teacher_info, plans: []}}
        """
        user = request.user
        
        if user.role == 'student':
            from accounts.models import TeacherStudentRelationship
            relationships = TeacherStudentRelationship.objects.filter(
                student=user,
                is_active=True
            ).select_related('teacher')
            teachers = [rel.teacher for rel in relationships]
        
        elif user.role == 'advisor':
            from accounts.models import User
            advisor_subject = user.subjects[0] if user.subjects and len(user.subjects) > 0 else None
            if advisor_subject:
                # Get all teachers in same school, then filter by subject in Python
                all_teachers = User.objects.filter(
                    role='teacher',
                    school=user.school
                )
                # Filter teachers who have the advisor's subject in their subjects list
                teachers = [t for t in all_teachers if advisor_subject in (t.subjects or [])]
            else:
                teachers = []
        
        else:
            return Response(
                {'error': 'Only students and advisors can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        result = {}
        for teacher in teachers:
            try:
                plans = TeachingPlan.objects.filter(teacher=teacher).order_by('-date')
                # Use first_name + last_name if available, otherwise username
                full_name = f"{teacher.first_name} {teacher.last_name}".strip() if teacher.first_name or teacher.last_name else teacher.username
                result[teacher.id] = {
                    'teacher_info': {
                        'id': teacher.id,
                        'username': teacher.username,
                        'full_name': full_name,
                        'subjects': teacher.subjects,
                    },
                    'plans': TeachingPlanSerializer(plans, many=True).data
                }
            except Exception as e:
                logger.error(f"Error fetching plans for teacher {teacher.id}: {str(e)}")
                # Skip this teacher if there's an error
                continue
        
        return Response(result, status=status.HTTP_200_OK)


class VaultLessonPlanViewSet(viewsets.ModelViewSet):
    """
    Vault system for sharing lesson plans by subject.
    - Advisors can create/edit/delete lesson plans for their subjects
    - Teachers can view lesson plans for subjects they teach
    - All users of the same subject see the same vault
    """
    queryset = VaultLessonPlan.objects.filter(is_active=True)
    serializer_class = VaultLessonPlanSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter vault lesson plans based on user role and subjects"""
        user = self.request.user
        queryset = self.queryset.filter(school=user.school)
        
        # Filter by subject if provided
        subject = self.request.query_params.get('subject')
        if subject:
            queryset = queryset.filter(subject=subject)
        elif user.role == 'teacher':
            # Teachers see lesson plans for subjects they teach
            if user.subjects:
                queryset = queryset.filter(subject__in=user.subjects)
            else:
                queryset = queryset.none()
        # Advisors can see all subjects in their school (no subject filter)
        
        # Filter by grade level if provided
        grade_level = self.request.query_params.get('grade_level')
        if grade_level:
            queryset = queryset.filter(grade_level=grade_level)
        
        # Filter by tags if provided
        tags = self.request.query_params.get('tags')
        if tags:
            tag_list = tags.split(',')
            for tag in tag_list:
                queryset = queryset.filter(tags__contains=[tag.strip()])
        
        return queryset.select_related('created_by', 'school').prefetch_related('comments', 'usages')
    
    def perform_create(self, serializer):
        """Only advisors can create vault lesson plans"""
        if self.request.user.role not in ['advisor', 'admin']:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only advisors can create vault lesson plans")
        
        serializer.save(created_by=self.request.user, school=self.request.user.school)
    
    def perform_update(self, serializer):
        """Only the creator or admins can update"""
        instance = self.get_object()
        if self.request.user.id != instance.created_by.id and self.request.user.role != 'admin':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only edit your own lesson plans")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only the creator or admins can delete (soft delete)"""
        if self.request.user.id != instance.created_by.id and self.request.user.role != 'admin':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only delete your own lesson plans")
        
        # Soft delete
        instance.is_active = False
        instance.save()
    
    @action(detail=True, methods=['post'])
    def increment_view(self, request, pk=None):
        """Increment view count when someone views the lesson plan"""
        lesson_plan = self.get_object()
        lesson_plan.view_count += 1
        lesson_plan.save(update_fields=['view_count'])
        return Response({'view_count': lesson_plan.view_count})
    
    @action(detail=True, methods=['post'])
    def use_plan(self, request, pk=None):
        """
        Mark that a teacher is using this lesson plan.
        Creates a usage record, increments use_count, and copies the lesson to teacher's lessons.
        """
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Only teachers can mark lesson plans as used'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        lesson_plan = self.get_object()
        
        # Create usage record
        usage = VaultLessonPlanUsage.objects.create(
            lesson_plan=lesson_plan,
            teacher=request.user,
            notes=request.data.get('notes', ''),
            rating=request.data.get('rating'),
            feedback=request.data.get('feedback', '')
        )
        
        # Increment use count
        lesson_plan.use_count += 1
        lesson_plan.save(update_fields=['use_count'])
        
        # Create a copy of the lesson for the teacher
        lesson = Lesson.objects.create(
            title=lesson_plan.title,
            content=lesson_plan.content,
            subject=lesson_plan.subject,
            grade_level=lesson_plan.grade_level,
            created_by=request.user,
            school=request.user.school
        )
        
        serializer = VaultLessonPlanUsageSerializer(usage)
        return Response({
            'usage': serializer.data,
            'lesson_id': lesson.id,
            'lesson_title': lesson.title,
            'message': 'Lesson plan copied to your lessons successfully'
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def generate_lesson(self, request, pk=None):
        """
        Generate a new lesson from a vault plan using AI for the teacher's timeline.
        Uses AI to enhance/customize the vault plan content.
        Optionally schedule it for a specific date.
        """
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Only teachers can generate lessons from vault plans'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        lesson_plan = self.get_object()
        scheduled_date = request.data.get('scheduled_date')  # Optional: YYYY-MM-DD format
        custom_instructions = request.data.get('custom_instructions', '')  # Optional customization
        
        try:
            # Use AI to generate enhanced lesson content based on vault plan
            ai_service = get_ai_service()
            
            # Build a comprehensive prompt using the vault plan as context
            prompt = f"""Based on the following lesson plan from our vault, generate a customized, 
detailed lesson for teaching. You can enhance, expand, or adapt the content as needed.

VAULT PLAN INFORMATION:
Title: {lesson_plan.title}
Description: {lesson_plan.description}
Subject: {lesson_plan.get_subject_display()}
Grade Level: {lesson_plan.get_grade_level_display()}

LEARNING OBJECTIVES:
{chr(10).join(['- ' + obj for obj in lesson_plan.objectives]) if lesson_plan.objectives else 'Not specified'}

ORIGINAL CONTENT:
{lesson_plan.content}

MATERIALS NEEDED:
{', '.join(lesson_plan.materials_needed) if lesson_plan.materials_needed else 'Not specified'}

DURATION: {lesson_plan.duration_minutes} minutes

"""
            
            # Add language-specific content if available (for English, French, Arabic)
            if lesson_plan.grammar:
                prompt += f"\nGRAMMAR POINTS:\n{chr(10).join(['- ' + point for point in lesson_plan.grammar])}\n"
            
            if lesson_plan.vocabulary:
                prompt += f"\nVOCABULARY:\n{chr(10).join(['- ' + word for word in lesson_plan.vocabulary])}\n"
            
            if lesson_plan.life_skills_and_values:
                prompt += f"\nLIFE SKILLS & VALUES:\n{chr(10).join(['- ' + skill for skill in lesson_plan.life_skills_and_values])}\n"
            
            # Add custom instructions if provided by teacher
            if custom_instructions:
                prompt += f"\nTEACHER'S CUSTOM INSTRUCTIONS:\n{custom_instructions}\n"
            
            prompt += """

Please generate a complete, ready-to-teach lesson that:
1. Expands on the content with clear explanations
2. Includes engaging examples and activities
3. Provides step-by-step teaching instructions
4. Adds practice exercises appropriate for the grade level
5. Includes assessment questions
6. Maintains the original learning objectives and key concepts

Format the lesson in a clear, well-structured manner suitable for classroom use.
"""
            
            # Generate enhanced content using AI
            logger.info(f"Generating lesson from vault plan {lesson_plan.id} using AI")
            enhanced_content = ai_service.generate_lesson(
                prompt=prompt,
                subject=lesson_plan.subject,
                grade_level=lesson_plan.grade_level
            )
            
            # Create a lesson with AI-enhanced content
            lesson = Lesson.objects.create(
                title=lesson_plan.title,
                content=enhanced_content,  # AI-generated content
                subject=lesson_plan.subject,
                grade_level=lesson_plan.grade_level,
                created_by=request.user,
                school=request.user.school,
                vault_source=lesson_plan,
                scheduled_date=scheduled_date if scheduled_date else None
            )
            
            # Increment use count
            lesson_plan.use_count += 1
            lesson_plan.save(update_fields=['use_count'])
            
            # Create usage record for tracking
            VaultLessonPlanUsage.objects.create(
                lesson_plan=lesson_plan,
                teacher=request.user,
                notes=request.data.get('notes', 'AI-generated lesson for timeline'),
                rating=request.data.get('rating'),
                feedback=request.data.get('feedback', '')
            )
            
            serializer = LessonSerializer(lesson)
            return Response({
                'lesson': serializer.data,
                'message': f'Lesson generated successfully using AI{" and scheduled for " + scheduled_date if scheduled_date else ""}',
                'ai_enhanced': True
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error generating lesson from vault plan {lesson_plan.id}: {str(e)}")
            # Fallback: create lesson with original content if AI fails
            lesson = Lesson.objects.create(
                title=lesson_plan.title,
                content=lesson_plan.content,  # Original content as fallback
                subject=lesson_plan.subject,
                grade_level=lesson_plan.grade_level,
                created_by=request.user,
                school=request.user.school,
                vault_source=lesson_plan,
                scheduled_date=scheduled_date if scheduled_date else None
            )
            
            lesson_plan.use_count += 1
            lesson_plan.save(update_fields=['use_count'])
            
            VaultLessonPlanUsage.objects.create(
                lesson_plan=lesson_plan,
                teacher=request.user,
                notes=request.data.get('notes', 'Generated lesson (AI failed, using original)'),
                rating=request.data.get('rating'),
                feedback=request.data.get('feedback', '')
            )
            
            serializer = LessonSerializer(lesson)
            return Response({
                'lesson': serializer.data,
                'message': f'Lesson generated successfully{" and scheduled for " + scheduled_date if scheduled_date else ""} (using original content)',
                'ai_enhanced': False,
                'ai_error': str(e)
            }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def by_subject(self, request):
        """Get vault lesson plans organized by subject (for teacher compartmentalized view)"""
        user = request.user
        
        if user.role != 'teacher' or not user.subjects:
            return Response({'error': 'Teachers only'}, status=status.HTTP_403_FORBIDDEN)
        
        result = {}
        for subject in user.subjects:
            plans = self.queryset.filter(
                school=user.school,
                subject=subject,
                is_active=True
            ).select_related('created_by')
            
            result[subject] = {
                'subject_display': dict(VaultLessonPlan.SUBJECT_CHOICES).get(subject, subject),
                'plans': VaultLessonPlanSerializer(plans, many=True).data
            }
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured lesson plans"""
        queryset = self.get_queryset().filter(is_featured=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_contributions(self, request):
        """Get lesson plans created by the current user"""
        if request.user.role not in ['advisor', 'admin']:
            return Response(
                {'error': 'Only advisors can view their contributions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = VaultLessonPlan.objects.filter(
            created_by=request.user,
            school=request.user.school
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def generate_yearly(self, request):
        """
        Generate yearly breakdown of lesson plans from PDF curriculum
        Advisor uploads PDF + provides subject, grade, and optional instructions
        """
        if request.user.role not in ['advisor', 'admin']:
            return Response(
                {'error': 'Only advisors can generate yearly breakdowns'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from .ai_service import get_ai_service
        from .models import YearlyBreakdown
        import os
        from django.utils import timezone
        
        # Get input data
        subject = request.data.get('subject')
        grade_level = request.data.get('grade_level')
        input_pdf = request.FILES.get('input_pdf')
        custom_instructions = request.data.get('custom_instructions', '')
        
        if not all([subject, grade_level, input_pdf]):
            return Response(
                {'error': 'subject, grade_level, and input_pdf are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create YearlyBreakdown record
        breakdown = YearlyBreakdown.objects.create(
            advisor=request.user,
            school=request.user.school,
            subject=subject,
            grade_level=grade_level,
            input_pdf=input_pdf,
            custom_instructions=custom_instructions,
            status='processing'
        )
        
        try:
            # Get AI service
            ai_service = get_ai_service()
            
            # Generate lesson plans from PDF
            lesson_plans_data = ai_service.generate_yearly_breakdown(
                pdf_path=breakdown.input_pdf.path,
                subject=subject,
                grade_level=grade_level,
                custom_instructions=custom_instructions
            )
            
            # Create VaultLessonPlan instances
            created_plans = []
            for plan_data in lesson_plans_data:
                lesson_plan = VaultLessonPlan.objects.create(
                    title=plan_data.get('title', ''),
                    description=plan_data.get('description', ''),
                    content=plan_data.get('content', ''),
                    subject=subject,
                    grade_level=grade_level,
                    objectives=plan_data.get('objectives', []),
                    materials_needed=plan_data.get('materials_needed', []),
                    duration_minutes=plan_data.get('duration_minutes'),
                    tags=plan_data.get('tags', []),
                    grammar=plan_data.get('grammar', []),
                    vocabulary=plan_data.get('vocabulary', []),
                    life_skills_and_values=plan_data.get('life_skills_and_values', []),
                    source_type='ai_yearly',
                    yearly_breakdown_file=breakdown.input_pdf,
                    ai_generation_prompt=custom_instructions,
                    created_by=request.user,
                    school=request.user.school
                )
                created_plans.append(lesson_plan)
            
            # Update breakdown status
            breakdown.status = 'completed'
            breakdown.generated_plans_count = len(created_plans)
            breakdown.processed_at = timezone.now()
            breakdown.save()
            
            return Response({
                'message': f'Successfully generated {len(created_plans)} lesson plans',
                'breakdown_id': breakdown.id,
                'plans_count': len(created_plans),
                'plans': VaultLessonPlanSerializer(created_plans, many=True).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            breakdown.status = 'failed'
            breakdown.error_message = str(e)
            breakdown.save()
            return Response(
                {'error': f'Failed to generate lesson plans: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def generate_single(self, request):
        """
        Generate a single lesson plan using teacher's guide PDF and custom text
        Advisor provides: grade_level, teacher_guide PDF, custom_text, subject
        """
        if request.user.role not in ['advisor', 'admin']:
            return Response(
                {'error': 'Only advisors can generate lesson plans'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from .ai_service import get_ai_service
        
        # Get input data
        grade_level = request.data.get('grade_level')
        teacher_guide = request.FILES.get('teacher_guide')
        custom_text = request.data.get('custom_text', '')
        subject = request.data.get('subject')
        
        if not all([grade_level, teacher_guide, custom_text, subject]):
            return Response(
                {'error': 'grade_level, teacher_guide, custom_text, and subject are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Save the teacher guide temporarily
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            import tempfile
            import os
            
            # Create a temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                for chunk in teacher_guide.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name
            
            # Get AI service and generate
            ai_service = get_ai_service()
            lesson_plan_data = ai_service.generate_single_lesson_plan(
                grade_level=grade_level,
                teacher_guide_path=temp_path,
                custom_text=custom_text,
                subject=subject
            )
            
            # Clean up temp file
            os.unlink(temp_path)
            
            # Create VaultLessonPlan
            lesson_plan = VaultLessonPlan.objects.create(
                title=lesson_plan_data.get('title', ''),
                description=lesson_plan_data.get('description', ''),
                content=lesson_plan_data.get('content', ''),
                subject=subject,
                grade_level=grade_level,
                objectives=lesson_plan_data.get('objectives', []),
                materials_needed=lesson_plan_data.get('materials_needed', []),
                duration_minutes=lesson_plan_data.get('duration_minutes'),
                tags=lesson_plan_data.get('tags', []),
                grammar=lesson_plan_data.get('grammar', []),
                vocabulary=lesson_plan_data.get('vocabulary', []),
                life_skills_and_values=lesson_plan_data.get('life_skills_and_values', []),
                source_type='ai_single',
                teacher_guide_file=teacher_guide,
                ai_generation_prompt=custom_text,
                created_by=request.user,
                school=request.user.school
            )
            
            return Response({
                'message': 'Lesson plan generated successfully',
                'plan': VaultLessonPlanSerializer(lesson_plan).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to generate lesson plan: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def import_from_teacher(self, request):
        """
        Import a lesson plan from a teacher into the vault
        Advisor provides: lesson_id (the teacher's original lesson)
        """
        if request.user.role not in ['advisor', 'admin']:
            return Response(
                {'error': 'Only advisors can import lesson plans'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from .models import Lesson
        
        lesson_id = request.data.get('lesson_id')
        if not lesson_id:
            return Response(
                {'error': 'lesson_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get the original teacher lesson
            original_lesson = Lesson.objects.get(id=lesson_id, school=request.user.school)
            
            # Create a copy in the vault
            vault_plan = VaultLessonPlan.objects.create(
                title=original_lesson.title,
                description=f"Imported from {original_lesson.created_by.get_full_name() or original_lesson.created_by.username}'s lesson",
                content=original_lesson.content,
                subject=original_lesson.subject,
                grade_level=str(original_lesson.grade_level) if original_lesson.grade_level else '1',
                objectives=[],  # Could parse from content if structured
                materials_needed=[],
                duration_minutes=None,
                tags=[],
                source_type='imported',
                source_teacher=original_lesson.created_by,
                created_by=request.user,
                school=request.user.school
            )
            
            return Response({
                'message': 'Lesson plan imported successfully',
                'plan': VaultLessonPlanSerializer(vault_plan).data
            }, status=status.HTTP_201_CREATED)
            
        except Lesson.DoesNotExist:
            return Response(
                {'error': 'Lesson not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to import lesson plan: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VaultLessonPlanUsageViewSet(viewsets.ModelViewSet):
    """Track usage of vault lesson plans by teachers"""
    queryset = VaultLessonPlanUsage.objects.all()
    serializer_class = VaultLessonPlanUsageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter usage records based on user"""
        user = self.request.user
        queryset = self.queryset
        
        if user.role == 'teacher':
            # Teachers see only their own usage
            queryset = queryset.filter(teacher=user)
        elif user.role == 'advisor':
            # Advisors see usage of their lesson plans
            queryset = queryset.filter(
                lesson_plan__created_by=user
            )
        
        # Filter by lesson plan if provided
        lesson_plan_id = self.request.query_params.get('lesson_plan')
        if lesson_plan_id:
            queryset = queryset.filter(lesson_plan_id=lesson_plan_id)
        
        return queryset.select_related('teacher', 'lesson_plan')
    
    def perform_create(self, serializer):
        """Only teachers can create usage records"""
        if self.request.user.role != 'teacher':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only teachers can record lesson plan usage")
        
        serializer.save(teacher=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_usage(self, request):
        """Get usage history for the current teacher"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Teachers only'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        usages = self.queryset.filter(teacher=request.user).order_by('-used_at')
        serializer = self.get_serializer(usages, many=True)
        return Response(serializer.data)


class VaultCommentViewSet(viewsets.ModelViewSet):
    """Comments and discussions on vault lesson plans"""
    queryset = VaultComment.objects.all()
    serializer_class = VaultCommentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter comments by lesson plan"""
        queryset = self.queryset
        
        lesson_plan_id = self.request.query_params.get('lesson_plan')
        if lesson_plan_id:
            queryset = queryset.filter(lesson_plan_id=lesson_plan_id)
        
        # Only show top-level comments by default
        include_replies = self.request.query_params.get('include_replies', 'false')
        if include_replies.lower() != 'true':
            queryset = queryset.filter(parent_comment__isnull=True)
        
        return queryset.select_related('user', 'lesson_plan', 'parent_comment')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def perform_update(self, serializer):
        """Only the comment author can edit"""
        instance = self.get_object()
        if self.request.user.id != instance.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only edit your own comments")
        
        serializer.save(is_edited=True)
    
    def perform_destroy(self, instance):
        """Only the comment author or admins can delete"""
        if self.request.user.id != instance.user.id and self.request.user.role != 'admin':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only delete your own comments")
        
        instance.delete()
    
    @action(detail=True, methods=['get'])
    def replies(self, request, pk=None):
        """Get all replies to a comment"""
        comment = self.get_object()
        replies = VaultComment.objects.filter(parent_comment=comment).order_by('created_at')
        serializer = self.get_serializer(replies, many=True)
        return Response(serializer.data)


class VaultExerciseViewSet(viewsets.ModelViewSet):
    """
    Exercises (MCQ and Q&A) for vault lesson plans.
    - Advisors and teachers can create exercises for vault lesson plans
    - All users can view exercises for lesson plans they have access to
    """
    queryset = VaultExercise.objects.filter(is_active=True)
    serializer_class = VaultExerciseSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter exercises based on user access to lesson plans"""
        user = self.request.user
        queryset = self.queryset
        
        # Filter by vault lesson plan if provided
        lesson_plan_id = self.request.query_params.get('vault_lesson_plan')
        if lesson_plan_id:
            queryset = queryset.filter(vault_lesson_plan_id=lesson_plan_id)
        else:
            # Filter by user's accessible subjects
            if user.role == 'teacher':
                if user.subjects:
                    queryset = queryset.filter(vault_lesson_plan__subject__in=user.subjects)
                else:
                    queryset = queryset.none()
        
        # Filter by exercise type if provided
        exercise_type = self.request.query_params.get('exercise_type')
        if exercise_type:
            queryset = queryset.filter(exercise_type=exercise_type)
        
        # Filter by difficulty level if provided
        difficulty = self.request.query_params.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty_level=difficulty)
        
        return queryset.select_related('vault_lesson_plan', 'created_by')
    
    def perform_create(self, serializer):
        """Teachers and advisors can create exercises"""
        if self.request.user.role not in ['teacher', 'advisor', 'admin']:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only teachers and advisors can create exercises")
        
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Only the creator or admins can update"""
        instance = self.get_object()
        if self.request.user.id != instance.created_by.id and self.request.user.role != 'admin':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only edit your own exercises")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only the creator or admins can delete (soft delete)"""
        if self.request.user.id != instance.created_by.id and self.request.user.role != 'admin':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only delete your own exercises")
        
        # Soft delete
        instance.is_active = False
        instance.save()
    
    @action(detail=True, methods=['post'])
    def increment_usage(self, request, pk=None):
        """Increment usage count when a teacher uses this exercise"""
        exercise = self.get_object()
        exercise.usage_count += 1
        exercise.save(update_fields=['usage_count'])
        return Response({'usage_count': exercise.usage_count})
    
    @action(detail=True, methods=['post'])
    def create_test_from_exercise(self, request, pk=None):
        """
        Create a Test from a Vault Exercise for students to take
        Request body:
        {
            "lesson_id": 123  # The lesson to attach the test to
        }
        """
        # Check teacher permission
        if request.user.role not in ['teacher', 'admin']:
            return Response(
                {'error': 'Only teachers can create tests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get exercise and lesson
        exercise = self.get_object()
        lesson_id = request.data.get('lesson_id')
        
        if not lesson_id:
            return Response(
                {'error': 'lesson_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .models import Lesson, Test
            lesson = Lesson.objects.get(id=lesson_id, created_by=request.user)
            
            # Check if test with same title already exists
            existing_test = Test.objects.filter(
                lesson=lesson,
                title=exercise.title
            ).first()
            
            if existing_test:
                return Response(
                    {'error': f'A test with title "{exercise.title}" already exists for this lesson'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create the test
            test = Test.objects.create(
                lesson=lesson,
                title=exercise.title,
                questions=exercise.questions,
                num_questions=exercise.num_questions,
                status='approved',  # Auto-approve since it's from vault
                created_by=request.user
            )
            
            # Increment usage count
            exercise.usage_count += 1
            exercise.save(update_fields=['usage_count'])
            
            return Response({
                'message': 'Test created successfully',
                'test_id': test.id,
                'test_title': test.title,
                'lesson_title': lesson.title,
                'num_questions': test.num_questions,
                'usage_count': exercise.usage_count
            }, status=status.HTTP_201_CREATED)
            
        except Lesson.DoesNotExist:
            return Response(
                {'error': 'Lesson not found or you do not have access'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def generate_with_ai(self, request):
        """
        Generate MCQ or Q&A exercise using AI based on lesson plan content
        Request body:
        {
            "vault_lesson_plan_id": 123,
            "exercise_type": "mcq" or "qa",
            "title": "Exercise title",
            "num_questions": 5,
            "difficulty_level": "easy/medium/hard"
        }
        """
        from .ai_service import get_ai_service
        
        # Validate user permissions
        if request.user.role not in ['teacher', 'advisor', 'admin']:
            return Response(
                {'error': 'Only teachers and advisors can generate exercises'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get and validate parameters
        lesson_plan_id = request.data.get('vault_lesson_plan_id')
        exercise_type = request.data.get('exercise_type', 'mcq')
        title = request.data.get('title', 'AI Generated Exercise')
        num_questions = int(request.data.get('num_questions', 5))
        difficulty = request.data.get('difficulty_level', 'medium')
        
        if not lesson_plan_id:
            return Response(
                {'error': 'vault_lesson_plan_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if exercise_type not in ['mcq', 'qa']:
            return Response(
                {'error': 'exercise_type must be "mcq" or "qa"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if difficulty not in ['easy', 'medium', 'hard']:
            return Response(
                {'error': 'difficulty_level must be "easy", "medium", or "hard"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get the lesson plan
            lesson_plan = VaultLessonPlan.objects.get(id=lesson_plan_id)
            
            # Check user has access to this subject
            if request.user.role == 'teacher' and request.user.subjects:
                if lesson_plan.subject not in request.user.subjects:
                    return Response(
                        {'error': 'You do not have access to this subject'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Prepare content for AI
            content = f"""
            Title: {lesson_plan.title}
            Description: {lesson_plan.description}
            
            Objectives:
            {chr(10).join('- ' + obj for obj in lesson_plan.objectives)}
            
            Content:
            {lesson_plan.content}
            """
            
            # Generate exercise with AI
            ai_service = get_ai_service()
            
            if exercise_type == 'mcq':
                exercise_data = ai_service.generate_vault_mcq_exercise(
                    lesson_plan_content=content,
                    title=title,
                    num_questions=num_questions,
                    difficulty=difficulty,
                    subject=lesson_plan.subject,
                    grade_level=lesson_plan.grade_level
                )
            else:  # qa
                exercise_data = ai_service.generate_vault_qa_exercise(
                    lesson_plan_content=content,
                    title=title,
                    num_questions=num_questions,
                    difficulty=difficulty,
                    subject=lesson_plan.subject,
                    grade_level=lesson_plan.grade_level
                )
            
            # Return the generated data without saving
            # Frontend can modify and then save
            response_data = {
                'vault_lesson_plan': lesson_plan_id,
                'title': exercise_data.get('title', title),
                'description': exercise_data.get('description', ''),
                'exercise_type': exercise_type,
                'questions': exercise_data['questions'],
                'num_questions': len(exercise_data['questions']),
                'difficulty_level': difficulty,
                'ai_generated': True
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except VaultLessonPlan.DoesNotExist:
            return Response(
                {'error': 'Lesson plan not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to generate exercise: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VaultMaterialViewSet(viewsets.ModelViewSet):
    """
    Course materials (PDFs, documents, etc.) for vault lesson plans.
    - Teachers and advisors can upload materials for vault lesson plans
    - All users can view/download materials for lesson plans they have access to
    """
    queryset = VaultMaterial.objects.filter(is_active=True)
    serializer_class = VaultMaterialSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter materials based on user access to lesson plans"""
        user = self.request.user
        queryset = self.queryset
        
        # Filter by vault lesson plan if provided
        lesson_plan_id = self.request.query_params.get('vault_lesson_plan')
        if lesson_plan_id:
            queryset = queryset.filter(vault_lesson_plan_id=lesson_plan_id)
        else:
            # Filter by user's accessible subjects
            if user.role == 'teacher':
                if user.subjects:
                    queryset = queryset.filter(vault_lesson_plan__subject__in=user.subjects)
                else:
                    queryset = queryset.none()
        
        # Filter by material type if provided
        material_type = self.request.query_params.get('material_type')
        if material_type:
            queryset = queryset.filter(material_type=material_type)
        
        return queryset.select_related('vault_lesson_plan', 'created_by')
    
    def perform_create(self, serializer):
        """Teachers and advisors can upload materials"""
        if self.request.user.role not in ['teacher', 'advisor', 'admin']:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only teachers and advisors can upload materials")
        
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Only the creator or admins can update"""
        instance = self.get_object()
        if self.request.user.id != instance.created_by.id and self.request.user.role != 'admin':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only edit your own materials")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only the creator or admins can delete (soft delete)"""
        if self.request.user.id != instance.created_by.id and self.request.user.role != 'admin':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only delete your own materials")
        
        # Soft delete
        instance.is_active = False
        instance.save()
    
    @action(detail=True, methods=['post'])
    def increment_download(self, request, pk=None):
        """Increment download count when someone downloads the material"""
        material = self.get_object()
        material.download_count += 1
        material.save(update_fields=['download_count'])
        return Response({'download_count': material.download_count})
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download the material file"""
        material = self.get_object()
        
        if not material.file:
            return Response(
                {'error': 'No file available for download'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Increment download count
        material.download_count += 1
        material.save(update_fields=['download_count'])
        
        # Return file URL
        return Response({
            'file_url': request.build_absolute_uri(material.file.url),
            'file_name': material.file.name.split('/')[-1],
            'file_size': material.file_size
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminRole])
def minister_analytics(request):
    """
    Comprehensive analytics endpoint for minister/admin dashboard
    Returns real-time system-wide analytics
    
    Permissions: Admin role only (role='admin')
    """
    try:
        analytics_data = MinisterAnalytics.get_comprehensive_dashboard_data()
        return Response(analytics_data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in minister_analytics: {str(e)}")
        return Response(
            {'error': 'Failed to generate analytics', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminRole])
def lesson_performance(request, lesson_id):
    """
    Detailed performance analytics for a specific lesson
    
    Permissions: Admin role only (role='admin')
    """
    try:
        performance_data = MinisterAnalytics.get_lesson_specific_performance(lesson_id)
        
        if performance_data is None:
            return Response(
                {'error': 'Lesson not found or no data available'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(performance_data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in lesson_performance for lesson {lesson_id}: {str(e)}")
        return Response(
            {'error': 'Failed to generate lesson analytics', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class StudentNotebookViewSet(viewsets.ModelViewSet):
    """
    ViewSet for student notebooks
    Students can access their own notebook
    Teachers can view notebooks of their students
    """
    serializer_class = StudentNotebookSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'student':
            # Students see only their own notebook
            return StudentNotebook.objects.filter(student=user)
        elif user.role == 'teacher':
            # Teachers see notebooks of their students
            from accounts.models import TeacherStudentRelationship
            student_ids = TeacherStudentRelationship.objects.filter(
                teacher=user
            ).values_list('student_id', flat=True)
            return StudentNotebook.objects.filter(student_id__in=student_ids)
        elif user.role in ['admin', 'minister']:
            # Admins and ministers see all notebooks
            return StudentNotebook.objects.all()
        
        return StudentNotebook.objects.none()
    
    @action(detail=False, methods=['get'])
    def my_notebook(self, request):
        """Get the current student's notebook"""
        if request.user.role != 'student':
            return Response(
                {'error': 'Only students can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        notebook, created = StudentNotebook.objects.get_or_create(student=request.user)
        serializer = self.get_serializer(notebook)
        return Response(serializer.data)


class NotebookPageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for notebook pages
    Students can create and edit their daily pages
    Teachers can view and comment on pages
    """
    serializer_class = NotebookPageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'student':
            # Students see only their own pages
            try:
                notebook = StudentNotebook.objects.get(student=user)
                return NotebookPage.objects.filter(notebook=notebook)
            except StudentNotebook.DoesNotExist:
                return NotebookPage.objects.none()
        elif user.role == 'teacher':
            # Teachers see pages of their students
            from accounts.models import TeacherStudentRelationship
            student_ids = TeacherStudentRelationship.objects.filter(
                teacher=user
            ).values_list('student_id', flat=True)
            return NotebookPage.objects.filter(notebook__student_id__in=student_ids)
        elif user.role in ['admin', 'minister']:
            # Admins and ministers see all pages
            return NotebookPage.objects.all()
        
        return NotebookPage.objects.none()
    
    def perform_create(self, serializer):
        """Create a page in the student's notebook"""
        if self.request.user.role != 'student':
            raise PermissionError('Only students can create notebook pages')
        
        notebook, _ = StudentNotebook.objects.get_or_create(student=self.request.user)
        serializer.save(notebook=notebook)
    
    @action(detail=False, methods=['get'])
    def my_pages(self, request):
        """Get all pages from the current student's notebook"""
        if request.user.role != 'student':
            return Response(
                {'error': 'Only students can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        notebook, _ = StudentNotebook.objects.get_or_create(student=request.user)
        pages = NotebookPage.objects.filter(notebook=notebook).order_by('-date')
        serializer = self.get_serializer(pages, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def today_page(self, request):
        """Get or create today's page"""
        if request.user.role != 'student':
            return Response(
                {'error': 'Only students can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        notebook, _ = StudentNotebook.objects.get_or_create(student=request.user)
        today = timezone.now().date()
        page, created = NotebookPage.objects.get_or_create(
            notebook=notebook,
            date=today,
            defaults={'lesson_name': ''}
        )
        
        serializer = self.get_serializer(page)
        return Response({
            'page': serializer.data,
            'created': created
        })
    
    @action(detail=False, methods=['post'])
    def create_student_page(self, request):
        """Teacher creates a page for a student with exercises"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Only teachers can create student pages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        student_id = request.data.get('student_id')
        date = request.data.get('date')
        lesson_name = request.data.get('lesson_name', '')
        exercises = request.data.get('exercises_set_by_teacher', '')
        
        if not student_id:
            return Response(
                {'error': 'student_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not date:
            return Response(
                {'error': 'date is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify teacher has access to this student
        from accounts.models import TeacherStudentRelationship, User
        if not TeacherStudentRelationship.objects.filter(
            teacher=request.user,
            student_id=student_id
        ).exists():
            return Response(
                {'error': 'You do not have access to this student'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            student = User.objects.get(id=student_id, role='student')
        except User.DoesNotExist:
            return Response(
                {'error': 'Student not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get or create student's notebook
        notebook, _ = StudentNotebook.objects.get_or_create(student=student)
        
        # Create or update the page
        page, created = NotebookPage.objects.update_or_create(
            notebook=notebook,
            date=date,
            defaults={
                'lesson_name': lesson_name,
                'exercises_set_by_teacher': exercises
            }
        )
        
        serializer = self.get_serializer(page)
        return Response({
            'page': serializer.data,
            'created': created
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_teacher_comment(self, request, pk=None):
        """Teacher adds a comment to a student's page"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Only teachers can add comments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        page = self.get_object()
        comment = request.data.get('comment', '')
        
        page.teacher_comment = comment
        page.teacher_viewed = True
        page.teacher_viewed_at = timezone.now()
        page.save()
        
        serializer = self.get_serializer(page)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_answer(self, request, pk=None):
        """Teacher marks student answer as correct/incorrect"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Only teachers can mark answers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        page = self.get_object()
        answer_status = request.data.get('answer_status')
        
        if answer_status not in ['pending', 'correct', 'incorrect', 'partial']:
            return Response(
                {'error': 'Invalid answer_status. Must be: pending, correct, incorrect, or partial'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        page.answer_status = answer_status
        page.teacher_viewed = True
        page.teacher_viewed_at = timezone.now()
        page.save()
        
        serializer = self.get_serializer(page)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def student_pages(self, request):
        """Teacher views pages for a specific student"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Only teachers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        student_id = request.query_params.get('student_id')
        if not student_id:
            return Response(
                {'error': 'student_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify teacher has access to this student
        from accounts.models import TeacherStudentRelationship
        if not TeacherStudentRelationship.objects.filter(
            teacher=request.user, student_id=student_id
        ).exists():
            return Response(
                {'error': 'You do not have access to this student\'s notebook'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            notebook = StudentNotebook.objects.get(student_id=student_id)
            pages = NotebookPage.objects.filter(notebook=notebook).order_by('-date')
            serializer = self.get_serializer(pages, many=True)
            return Response(serializer.data)
        except StudentNotebook.DoesNotExist:
            return Response([])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hr_overview(request):
    """
    GDHR Dashboard - Comprehensive HR Overview
    Returns all workers (teachers, advisors, directors, etc.), students, and parents
    
    Permissions: GDHR, Admin, Minister roles
    """
    if request.user.role not in ['gdhr', 'admin', 'minister']:
        return Response(
            {'error': 'Access denied. GDHR role required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        from accounts.models import User, TeacherStudentRelationship
        from django.db.models import Count, Avg
        
        # Count all users by role
        total_teachers = User.objects.filter(role='teacher', is_active=True).count()
        total_students = User.objects.filter(role='student', is_active=True).count()
        total_parents = User.objects.filter(role='parent', is_active=True).count()
        total_advisors = User.objects.filter(role='advisor', is_active=True).count()
        total_directors = User.objects.filter(role='director', is_active=True).count()
        total_cnp = User.objects.filter(role='cnp', is_active=True).count()
        total_delegation = User.objects.filter(role='delegation', is_active=True).count()
        total_gdhr = User.objects.filter(role='gdhr', is_active=True).count()
        total_admins = User.objects.filter(role='admin', is_active=True).count()
        
        # Calculate teacher-student ratio
        teacher_student_ratio = total_students / total_teachers if total_teachers > 0 else 0
        
        # Count active relationships
        active_relationships = TeacherStudentRelationship.objects.filter(is_active=True).count()
        
        # Count schools
        from accounts.models import School
        total_schools = School.objects.count()
        
        overview_data = {
            'total_teachers': total_teachers,
            'total_students': total_students,
            'total_parents': total_parents,
            'total_advisors': total_advisors,
            'total_directors': total_directors,
            'total_cnp': total_cnp,
            'total_delegation': total_delegation,
            'total_gdhr': total_gdhr,
            'total_admins': total_admins,
            'total_schools': total_schools,
            'teacher_student_ratio': round(teacher_student_ratio, 2),
            'active_relationships': active_relationships,
            'total_workers': total_teachers + total_advisors + total_directors + total_cnp + total_delegation + total_gdhr + total_admins,
        }
        
        return Response(overview_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in hr_overview: {str(e)}")
        return Response(
            {'error': 'Failed to generate HR overview', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hr_all_users(request):
    """
    GDHR Dashboard - Get all users with details
    Returns comprehensive list of all workers, students, and parents
    
    Query params:
    - role: filter by role (optional)
    - search: search by name/email (optional)
    
    Permissions: GDHR, Admin, Minister roles
    """
    if request.user.role not in ['gdhr', 'admin', 'minister']:
        return Response(
            {'error': 'Access denied. GDHR role required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        from accounts.models import User
        
        # Start with all active users
        users = User.objects.filter(is_active=True).select_related('school')
        
        # Apply role filter if provided
        role_filter = request.query_params.get('role')
        if role_filter:
            users = users.filter(role=role_filter)
        
        # Apply search filter if provided
        search_query = request.query_params.get('search')
        if search_query:
            from django.db.models import Q
            users = users.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        
        # Build user data
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name() or user.username,
                'role': user.role,
                'school_id': user.school.id if user.school else None,
                'school_name': user.school.name if user.school else 'N/A',
                'subjects': user.subjects if hasattr(user, 'subjects') else [],
                'phone': user.phone,
                'date_joined': user.date_joined.isoformat() if user.date_joined else None,
                'is_active': user.is_active,
            })
        
        return Response({
            'total': len(users_data),
            'users': users_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in hr_all_users: {str(e)}")
        return Response(
            {'error': 'Failed to fetch users', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hr_teacher_performance(request):
    """
    GDHR Dashboard - Comprehensive Teacher Performance Analytics
    Returns detailed performance metrics for all teachers
    
    Permissions: GDHR, Admin, Minister roles
    """
    if request.user.role not in ['gdhr', 'admin', 'minister']:
        return Response(
            {'error': 'Access denied. GDHR role required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        from accounts.models import User, TeacherStudentRelationship
        from django.db.models import Count, Avg, Q
        
        # Get all teachers with related data
        teachers = User.objects.filter(role='teacher', is_active=True).select_related('school')
        
        teachers_data = []
        for teacher in teachers:
            # Count students
            student_count = TeacherStudentRelationship.objects.filter(
                teacher=teacher, is_active=True
            ).count()
            
            # Count lessons created
            lessons_count = Lesson.objects.filter(created_by=teacher).count()
            
            # Count tests created (MCQ + QA)
            mcq_tests_count = Test.objects.filter(created_by=teacher).count()
            qa_tests_count = QATest.objects.filter(created_by=teacher).count()
            total_tests = mcq_tests_count + qa_tests_count
            
            # Calculate average student score from test submissions
            from django.db.models import Avg as DjangoAvg
            mcq_avg = TestSubmission.objects.filter(
                test__created_by=teacher,
                status='approved'
            ).aggregate(avg_score=DjangoAvg('score'))['avg_score'] or 0
            
            qa_avg = QASubmission.objects.filter(
                test__created_by=teacher,
                status='finalized'
            ).aggregate(avg_score=DjangoAvg('final_score'))['avg_score'] or 0
            
            # Combined average
            if mcq_avg > 0 and qa_avg > 0:
                avg_student_score = (mcq_avg + qa_avg) / 2
            elif mcq_avg > 0:
                avg_student_score = mcq_avg
            elif qa_avg > 0:
                avg_student_score = qa_avg
            else:
                avg_student_score = 0
            
            # Get average rating from students
            avg_rating = TeacherStudentRelationship.objects.filter(
                teacher=teacher,
                rating_by_student__isnull=False
            ).aggregate(avg=DjangoAvg('rating_by_student'))['avg'] or 0
            
            # Get advisor ratings
            from accounts.models import AdvisorReview
            advisor_avg = AdvisorReview.objects.filter(
                Q(lesson__created_by=teacher) | Q(mcq_test__created_by=teacher) | Q(qa_test__created_by=teacher),
                rating__isnull=False
            ).aggregate(avg=DjangoAvg('rating'))['avg'] or 0
            
            # Calculate quality score (0-100)
            quality_score = 0
            score_components = 0
            
            if lessons_count > 0:
                quality_score += min(lessons_count / 10 * 20, 20)  # Max 20 points for lessons
                score_components += 1
            
            if total_tests > 0:
                quality_score += min(total_tests / 5 * 20, 20)  # Max 20 points for tests
                score_components += 1
            
            if avg_student_score > 0:
                quality_score += avg_student_score * 0.3  # Max 30 points for student scores
                score_components += 1
            
            if avg_rating > 0:
                quality_score += avg_rating * 6  # Max 30 points for ratings (5 * 6 = 30)
                score_components += 1
            
            # Determine performance level
            if quality_score >= 75:
                level = 'excellent'
            elif quality_score >= 50:
                level = 'good'
            else:
                level = 'needs_improvement'
            
            teachers_data.append({
                'teacher_id': teacher.id,
                'teacher_name': teacher.get_full_name() or teacher.username,
                'email': teacher.email,
                'school_name': teacher.school.name if teacher.school else 'N/A',
                'subjects': teacher.subjects,
                'total_students': student_count,
                'total_lessons_created': lessons_count,
                'total_tests_created': total_tests,
                'mcq_tests': mcq_tests_count,
                'qa_tests': qa_tests_count,
                'avg_student_score': round(avg_student_score, 2),
                'avg_rating': round(avg_rating, 2),
                'avg_advisor_rating': round(advisor_avg, 2),
                'quality_score': round(quality_score, 2),
                'level': level,
            })
        
        # Sort by quality score descending
        teachers_data.sort(key=lambda x: x['quality_score'], reverse=True)
        
        # Calculate summary statistics
        total_teachers = len(teachers_data)
        excellent_count = len([t for t in teachers_data if t['level'] == 'excellent'])
        good_count = len([t for t in teachers_data if t['level'] == 'good'])
        needs_improvement_count = len([t for t in teachers_data if t['level'] == 'needs_improvement'])
        
        avg_quality_score = sum(t['quality_score'] for t in teachers_data) / total_teachers if total_teachers > 0 else 0
        
        # Group teachers by subject
        teachers_by_subject = {}
        for teacher in teachers_data:
            for subject in teacher['subjects']:
                if subject not in teachers_by_subject:
                    teachers_by_subject[subject] = {
                        'subject': subject,
                        'count': 0,
                        'teachers': [],
                        'avg_quality_score': 0,
                        'excellent': 0,
                        'good': 0,
                        'needs_improvement': 0,
                    }
                teachers_by_subject[subject]['count'] += 1
                teachers_by_subject[subject]['teachers'].append(teacher)
                
                if teacher['level'] == 'excellent':
                    teachers_by_subject[subject]['excellent'] += 1
                elif teacher['level'] == 'good':
                    teachers_by_subject[subject]['good'] += 1
                else:
                    teachers_by_subject[subject]['needs_improvement'] += 1
        
        # Calculate average quality score per subject
        for subject_data in teachers_by_subject.values():
            if subject_data['count'] > 0:
                total_score = sum(t['quality_score'] for t in subject_data['teachers'])
                subject_data['avg_quality_score'] = round(total_score / subject_data['count'], 2)
        
        # Convert to list and sort by teacher count
        subject_breakdown = sorted(teachers_by_subject.values(), key=lambda x: x['count'], reverse=True)
        
        return Response({
            'summary': {
                'total_teachers': total_teachers,
                'excellent_count': excellent_count,
                'good_count': good_count,
                'needs_improvement_count': needs_improvement_count,
                'avg_quality_score': round(avg_quality_score, 2),
            },
            'teachers': teachers_data,
            'top_performers': teachers_data[:10],  # Top 10
            'needs_support': [t for t in teachers_data if t['level'] == 'needs_improvement'][:10],  # Bottom 10
            'by_subject': subject_breakdown,
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in hr_teacher_performance: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return Response(
            {'error': 'Failed to fetch teacher performance', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hr_student_performance(request):
    """
    GDHR Dashboard - Student Demographics Statistics
    Returns demographic counts by age, region, gender, and grade level
    
    Permissions: GDHR, Admin, Minister roles
    """
    if request.user.role not in ['gdhr', 'admin', 'minister']:
        return Response(
            {'error': 'Access denied. GDHR role required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        from accounts.models import User
        from datetime import date
        from collections import defaultdict
        
        # Get all students
        students = User.objects.filter(role='student', is_active=True).select_related('school')
        total_students = students.count()
        
        # Count by age with gender breakdown
        age_distribution = defaultdict(lambda: {'total': 0, 'male': 0, 'female': 0})
        for student in students:
            if student.date_of_birth:
                today = date.today()
                age = today.year - student.date_of_birth.year - ((today.month, today.day) < (student.date_of_birth.month, student.date_of_birth.day))
                age_distribution[age]['total'] += 1
                if student.gender == 'M':
                    age_distribution[age]['male'] += 1
                elif student.gender == 'F':
                    age_distribution[age]['female'] += 1
        
        # Sort and format age data
        age_stats = []
        for age in sorted(age_distribution.keys()):
            data = age_distribution[age]
            age_stats.append({
                'age': age,
                'count': data['total'],
                'male': data['male'],
                'female': data['female']
            })
        
        # Count by region with gender breakdown
        region_distribution = defaultdict(lambda: {'total': 0, 'male': 0, 'female': 0})
        for student in students:
            region = student.school.delegation if student.school and student.school.delegation else 'N/A'
            region_distribution[region]['total'] += 1
            if student.gender == 'M':
                region_distribution[region]['male'] += 1
            elif student.gender == 'F':
                region_distribution[region]['female'] += 1
        
        # Sort by count descending
        region_stats = []
        for region in sorted(region_distribution.keys(), key=lambda x: region_distribution[x]['total'], reverse=True):
            data = region_distribution[region]
            region_stats.append({
                'region': region,
                'count': data['total'],
                'male': data['male'],
                'female': data['female']
            })
        
        # Count by gender
        gender_distribution = defaultdict(int)
        for student in students:
            gender = 'Male' if student.gender == 'M' else 'Female' if student.gender == 'F' else 'Unknown'
            gender_distribution[gender] += 1
        
        gender_stats = [{'gender': gender, 'count': count} for gender, count in sorted(gender_distribution.items())]
        
        # Count by grade level
        grade_distribution = defaultdict(lambda: {'total': 0, 'male': 0, 'female': 0})
        for student in students:
            grade = student.grade_level if student.grade_level else 'N/A'
            grade_distribution[grade]['total'] += 1
            if student.gender == 'M':
                grade_distribution[grade]['male'] += 1
            elif student.gender == 'F':
                grade_distribution[grade]['female'] += 1
        
        # Format grade data
        grade_stats = []
        for grade in sorted(grade_distribution.keys()):
            data = grade_distribution[grade]
            total = data['total']
            male = data['male']
            female = data['female']
            grade_stats.append({
                'grade': f'Grade {grade}' if grade != 'N/A' else 'No Grade',
                'grade_value': grade,
                'total': total,
                'male': male,
                'female': female,
                'male_percentage': round(male / total * 100, 1) if total > 0 else 0,
                'female_percentage': round(female / total * 100, 1) if total > 0 else 0,
            })
        
        return Response({
            'total_students': total_students,
            'by_age': age_stats,
            'by_region': region_stats,
            'by_gender': gender_stats,
            'by_grade': grade_stats,
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in hr_student_performance: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return Response(
            {'error': 'Failed to fetch student demographics', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminRole])
def ministry_hr_by_region(request):
    """
    Ministry HR statistics by region from mock_ministry_hr_220k_by_region_split.csv
    Returns comprehensive HR data including counts by role, region, and gender
    Teachers are split into: Primary, Preparatory, and Secondary levels
    
    Permissions: Admin role only (role='admin')
    """
    try:
        import csv
        import os
        from django.conf import settings
        
        # Path to the CSV file (updated to use split version)
        csv_path = os.path.join(settings.BASE_DIR, 'mock_ministry_hr_220k_by_region_split.csv')
        
        if not os.path.exists(csv_path):
            return Response(
                {'error': 'HR data file not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Read CSV data
        hr_data = []
        role_median_ages = {}  # Store median ages by role
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                role = row['role']
                median_age = int(row.get('median_age', 40))
                
                hr_data.append({
                    'region': row['region'],
                    'role': role,
                    'count': int(row['count']),
                    'male': int(row['male']),
                    'female': int(row['female']),
                    'male_female_ratio': row['male_female_ratio'],
                    'median_age': median_age
                })
                
                # Store median age for this role (same across regions)
                if role not in role_median_ages:
                    role_median_ages[role] = median_age
        
        # Aggregate statistics
        total_employees = sum(item['count'] for item in hr_data)
        total_male = sum(item['male'] for item in hr_data)
        total_female = sum(item['female'] for item in hr_data)
        
        # Count by role (aggregate all regions)
        role_counts = {}
        for item in hr_data:
            role = item['role']
            if role not in role_counts:
                role_counts[role] = {'count': 0, 'male': 0, 'female': 0}
            role_counts[role]['count'] += item['count']
            role_counts[role]['male'] += item['male']
            role_counts[role]['female'] += item['female']
        
        # Count by region (aggregate all roles)
        region_counts = {}
        for item in hr_data:
            region = item['region']
            if region not in region_counts:
                region_counts[region] = {'count': 0, 'male': 0, 'female': 0}
            region_counts[region]['count'] += item['count']
            region_counts[region]['male'] += item['male']
            region_counts[region]['female'] += item['female']
        
        # Format role statistics
        by_role = [
            {
                'role': role,
                'count': data['count'],
                'male': data['male'],
                'female': data['female'],
                'male_percentage': round(data['male'] / data['count'] * 100, 1) if data['count'] > 0 else 0,
                'female_percentage': round(data['female'] / data['count'] * 100, 1) if data['count'] > 0 else 0,
                'median_age': role_median_ages.get(role, 40),
            }
            for role, data in sorted(role_counts.items(), key=lambda x: x[1]['count'], reverse=True)
        ]
        
        # Format region statistics
        by_region = [
            {
                'region': region,
                'count': data['count'],
                'male': data['male'],
                'female': data['female'],
                'male_percentage': round(data['male'] / data['count'] * 100, 1) if data['count'] > 0 else 0,
                'female_percentage': round(data['female'] / data['count'] * 100, 1) if data['count'] > 0 else 0,
            }
            for region, data in sorted(region_counts.items(), key=lambda x: x[1]['count'], reverse=True)
        ]
        
        return Response({
            'total_employees': total_employees,
            'total_male': total_male,
            'total_female': total_female,
            'male_percentage': round(total_male / total_employees * 100, 1) if total_employees > 0 else 0,
            'female_percentage': round(total_female / total_employees * 100, 1) if total_employees > 0 else 0,
            'by_role': by_role,
            'by_region': by_region,
            'detailed_data': hr_data,
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in ministry_hr_by_region: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return Response(
            {'error': 'Failed to fetch ministry HR data', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def regional_education_search(request):
    """
    AI-powered regional education data search using Gemini.
    Provides education statistics, trends, and insights for a specific region and school.
    
    Expected POST data:
    - region: The CRE (regional education center)
    - delegation: The delegation name
    - school_type: Type of school (primary, preparatory, secondary)
    - school_name: Name of the specific school
    - school_code: School code
    - language: 'en' or 'ar' for response language
    - attendance_context: Optional attendance statistics for the school
    """
    try:
        import google.generativeai as genai
        from django.conf import settings
        
        # Get request data
        region = request.data.get('region', '')
        delegation = request.data.get('delegation', '')
        school_type = request.data.get('school_type', '')
        school_name = request.data.get('school_name', '')
        school_name_ar = request.data.get('school_name_ar', '')
        school_code = request.data.get('school_code', '')
        language = request.data.get('language', 'en')
        attendance_context = request.data.get('attendance_context', None)
        
        if not region or not delegation:
            return Response(
                {'error': 'Region and delegation are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Configure Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Determine school level for context
        school_level = 'primary'
        if school_type:
            st = school_type.lower()
            if 'prep' in st or 'college' in st or 'إعداد' in st:
                school_level = 'preparatory'
            elif 'sec' in st or 'lycee' in st or 'lycée' in st or 'ثانو' in st:
                school_level = 'secondary'
        
        # Build attendance context string if available
        attendance_info_ar = ""
        attendance_info_en = ""
        if attendance_context:
            teachers_total = attendance_context.get('teachers_total', 0)
            teachers_present = attendance_context.get('teachers_present', 0)
            students_total = attendance_context.get('students_total', 0)
            students_present = attendance_context.get('students_present', 0)
            advisors_total = attendance_context.get('advisors_total', 0)
            
            teacher_rate = round((teachers_present / teachers_total) * 100) if teachers_total > 0 else 0
            student_rate = round((students_present / students_total) * 100) if students_total > 0 else 0
            student_teacher_ratio = round(students_total / teachers_total) if teachers_total > 0 else 0
            
            attendance_info_ar = f"""
بيانات المدرسة الحالية:
- عدد المعلمين: {teachers_total}
- نسبة حضور المعلمين اليوم: {teacher_rate}%
- عدد التلاميذ: {students_total}
- نسبة حضور التلاميذ اليوم: {student_rate}%
- نسبة التلميذ/المعلم: {student_teacher_ratio}:1
- عدد المستشارين: {advisors_total}
"""
            attendance_info_en = f"""
Current School Data:
- Number of Teachers: {teachers_total}
- Today's Teacher Attendance Rate: {teacher_rate}%
- Number of Students: {students_total}
- Today's Student Attendance Rate: {student_rate}%
- Student-Teacher Ratio: {student_teacher_ratio}:1
- Number of Advisors: {advisors_total}
"""
        
        # Build the prompt with real Tunisian education context
        if language == 'ar':
            prompt = f"""أنت محلل تعليمي خبير متخصص في النظام التعليمي التونسي. قدم تحليلاً دقيقاً ومفصلاً عن:

المدرسة: {school_name}
{f'الاسم بالعربية: {school_name_ar}' if school_name_ar else ''}
رمز المدرسة: {school_code}
نوع المدرسة: {school_type}
المندوبية الجهوية: {delegation}
الإدارة الجهوية للتربية (CRE): {region}
{attendance_info_ar}
بناءً على معرفتك بالنظام التعليمي التونسي ومنطقة {delegation} تحديداً، وباستخدام البيانات المقدمة أعلاه، قدم تحليلاً شاملاً.

يرجى تقديم الرد بتنسيق JSON التالي باللغة العربية:
{{
    "summary": "ملخص تحليلي شامل (3-4 جمل) عن الوضع التعليمي في هذه المنطقة والمدرسة، مع ذكر خصوصيات المندوبية وتحليل البيانات المقدمة",
    "statistics": [
        "عدد المدارس {'الابتدائية' if school_level == 'primary' else 'الإعدادية' if school_level == 'preparatory' else 'الثانوية'} في مندوبية {delegation}: [رقم تقريبي واقعي]",
        "متوسط عدد التلاميذ لكل قسم في المنطقة: [رقم بين 25-35]",
        "نسبة النجاح في {'امتحان السيزيام' if school_level == 'primary' else 'امتحان النوفيام' if school_level == 'preparatory' else 'البكالوريا'} لسنة 2024: [نسبة واقعية]",
        "نسبة التأطير (معلم/تلميذ) في المنطقة: [نسبة واقعية]",
        "مقارنة حضور المعلمين بالمعدل الوطني (95%): [تحليل]",
        "مقارنة حضور التلاميذ بالمعدل الوطني (93%): [تحليل]"
    ],
    "trends": [
        "توجه حديث 1 خاص بالتعليم في تونس",
        "توجه حديث 2 متعلق بالمنطقة",
        "توجه حديث 3 خاص بالمستوى التعليمي",
        "توجه تكنولوجي أو منهجي حديث"
    ],
    "insights": [
        "تحليل نسبة الحضور وما تدل عليه",
        "تحليل نسبة التلميذ/المعلم ومقارنتها بالمعايير",
        "ملاحظة عن نقاط القوة في المؤسسة",
        "توصية عملية للتطوير بناءً على البيانات"
    ],
    "alerts": [
        {{"severity": "critical|warning|info", "title": "عنوان التنبيه", "description": "وصف المشكلة وأسبابها", "action": "الإجراء المطلوب لحل المشكلة"}}
    ],
    "sources": ["وزارة التربية التونسية", "الإدارة الجهوية للتربية {region}", "إحصائيات 2024", "بيانات المؤسسة"]
}}

قواعد التنبيهات (alerts):
- إذا كانت نسبة حضور المعلمين أقل من 90%: تنبيه حرج (critical)
- إذا كانت نسبة حضور المعلمين بين 90-95%: تنبيه تحذيري (warning)
- إذا كانت نسبة حضور التلاميذ أقل من 85%: تنبيه حرج (critical)
- إذا كانت نسبة حضور التلاميذ بين 85-90%: تنبيه تحذيري (warning)
- إذا كانت نسبة التلميذ/المعلم أكثر من 30:1: تنبيه حرج (critical)
- إذا كانت نسبة التلميذ/المعلم بين 25-30:1: تنبيه تحذيري (warning)
- أضف تنبيهات إضافية بناءً على تحليلك للبيانات

ملاحظات هامة:
- استخدم البيانات المقدمة أعلاه في تحليلك
- استخدم أرقام وإحصائيات واقعية ومنطقية للسياق التونسي
- اذكر خصوصيات منطقة {delegation} إن وجدت
- قدم معلومات عملية ومفيدة للمسؤولين التربويين
- أجب بتنسيق JSON فقط دون أي نص إضافي"""
        else:
            prompt = f"""You are an expert education analyst specializing in the Tunisian education system. Provide accurate and detailed analysis for:

School: {school_name}
{f'Arabic Name: {school_name_ar}' if school_name_ar else ''}
School Code: {school_code}
School Type: {school_type}
Regional Delegation: {delegation}
Regional Education Center (CRE): {region}
{attendance_info_en}
Based on your knowledge of the Tunisian education system and specifically the {delegation} region, and using the data provided above, provide a comprehensive analysis.

Please respond in the following JSON format:
{{
    "summary": "Comprehensive analytical summary (3-4 sentences) about the educational situation in this region and school, analyzing the provided data and mentioning specific characteristics of the delegation",
    "statistics": [
        "Number of {'primary' if school_level == 'primary' else 'preparatory' if school_level == 'preparatory' else 'secondary'} schools in {delegation} delegation: [realistic approximate number]",
        "Average students per classroom in the region: [number between 25-35]",
        "Success rate in {'6th grade national exam (Sixième)' if school_level == 'primary' else '9th grade exam (Neuvième)' if school_level == 'preparatory' else 'Baccalaureate'} for 2024: [realistic percentage]",
        "Teacher-student ratio in the region: [realistic ratio]",
        "Comparison of teacher attendance with national average (95%): [analysis]",
        "Comparison of student attendance with national average (93%): [analysis]"
    ],
    "trends": [
        "Recent trend 1 specific to Tunisian education",
        "Recent trend 2 related to the region",
        "Recent trend 3 specific to the education level",
        "Technological or methodological trend"
    ],
    "insights": [
        "Analysis of attendance rates and what they indicate",
        "Analysis of student-teacher ratio compared to standards",
        "Observation about institutional strengths",
        "Practical recommendation based on the data"
    ],
    "alerts": [
        {{"severity": "critical|warning|info", "title": "Alert title", "description": "Problem description and causes", "action": "Required action to fix the issue"}}
    ],
    "sources": ["Tunisian Ministry of Education", "Regional Education Center {region}", "2024 Statistics", "School Data"]
}}

Alert rules:
- If teacher attendance is below 90%: critical alert
- If teacher attendance is between 90-95%: warning alert
- If student attendance is below 85%: critical alert  
- If student attendance is between 85-90%: warning alert
- If student-teacher ratio is above 30:1: critical alert
- If student-teacher ratio is between 25-30:1: warning alert
- Add additional alerts based on your data analysis

Important notes:
- Use the data provided above in your analysis
- Use realistic and logical numbers and statistics for the Tunisian context
- Mention specific characteristics of the {delegation} region if applicable
- Provide practical and useful information for education officials
- Respond with JSON format only without any additional text"""        # Generate response
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Try to parse JSON from response
        try:
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            result = json.loads(response_text.strip())
            
            # Ensure all expected fields exist
            if 'summary' not in result:
                result['summary'] = f"Education overview for {delegation}, {region}"
            if 'statistics' not in result:
                result['statistics'] = []
            if 'trends' not in result:
                result['trends'] = []
            if 'insights' not in result:
                result['insights'] = []
            if 'alerts' not in result:
                result['alerts'] = []
            if 'sources' not in result:
                result['sources'] = ['Ministry of Education Tunisia', 'Regional Statistics']
                
            return Response(result, status=status.HTTP_200_OK)
            
        except json.JSONDecodeError:
            # If JSON parsing fails, return a structured response from the text
            return Response({
                'summary': response_text[:500] if len(response_text) > 500 else response_text,
                'statistics': [],
                'trends': [],
                'insights': [],
                'sources': ['AI Generated', 'Ministry of Education Tunisia']
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        logger.error(f"Error in regional_education_search: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return Response(
            {'error': 'Failed to search regional education data', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
