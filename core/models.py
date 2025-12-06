from django.db import models
from django.conf import settings

# Import inspection models
from .inspection_models import (
    Region,
    InspectorRegionAssignment,
    TeacherComplaint,
    InspectionVisit,
    InspectionReport,
    MonthlyReport,
    TeacherRatingHistory
)

class Lesson(models.Model):
    SUBJECT_CHOICES = [
        ('math', 'Mathematics'),
        ('science', 'Science'),
        ('english', 'English'),
        ('arabic', 'Arabic'),
        ('social_studies', 'Social Studies'),
        ('art', 'Art'),
        ('music', 'Music'),
        ('physical_education', 'Physical Education'),
        ('computer_science', 'Computer Science'),
        ('religious_studies', 'Religious Studies'),
    ]
    
    GRADE_CHOICES = [
        ('1', '1st Grade'),
        ('2', '2nd Grade'),
        ('3', '3rd Grade'),
        ('4', '4th Grade'),
        ('5', '5th Grade'),
        ('6', '6th Grade'),
    ]
    
    title = models.CharField(max_length=255)
    content = models.TextField()
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES, default='math')
    grade_level = models.CharField(max_length=2, choices=GRADE_CHOICES, default='1')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lessons')
    school = models.ForeignKey('accounts.School', on_delete=models.CASCADE, related_name='lessons')
    
    # Timeline scheduling
    scheduled_date = models.DateField(null=True, blank=True, help_text='When this lesson is scheduled to be taught')
    
    # Vault source tracking
    vault_source = models.ForeignKey(
        'VaultLessonPlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_lessons',
        help_text='Vault lesson plan this was generated from'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.get_subject_display()} - {self.get_grade_level_display()})"

class Test(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    QUESTION_TYPE_CHOICES = [
        ('mcq', 'Multiple Choice'),
        ('qa', 'Question & Answer'),
    ]
    
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='tests')
    title = models.CharField(max_length=255)
    questions = models.JSONField()  # Store questions as JSON
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES, default='mcq')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_tests', null=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_tests')
    review_notes = models.TextField(blank=True)
    num_questions = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

class PersonalizedTest(models.Model):
    """
    A personalized version of a test for a specific student
    Questions are customized based on the student's performance level
    """
    base_test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='personalized_versions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='personalized_tests')
    questions = models.JSONField()  # Student-specific questions
    difficulty_level = models.CharField(max_length=20, default='medium')  # easy, medium, medium-hard, hard
    performance_score = models.FloatField(null=True, blank=True)  # The student's avg performance that determined difficulty
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['base_test', 'student']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.base_test.title} - {self.student.username} ({self.difficulty_level})"

class Progress(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress')
    score = models.FloatField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.student.username} - {self.lesson.title}"

class Portfolio(models.Model):
    student = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='portfolio')
    summary = models.TextField()
    achievements = models.JSONField(default=list)
    test_results = models.JSONField(
        default=list,
        help_text='List of all test results with lesson names: [{lesson_name, test_title, test_type, score, date, attempt}]'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Portfolio of {self.student.username}"
    
    def add_test_result(self, lesson_name, test_title, test_type, score, attempt=1):
        """Add a test result to the portfolio"""
        from django.utils import timezone
        result = {
            'lesson_name': lesson_name,
            'test_title': test_title,
            'test_type': test_type,  # 'MCQ' or 'QA'
            'score': score,
            'date': timezone.now().isoformat(),
            'attempt': attempt
        }
        self.test_results.append(result)
        self.save()
        return result
    
    def get_subject_statistics(self):
        """
        Calculate student performance statistics per subject based on all test submissions.
        Returns a dict with subject names as keys and average scores as values.
        """
        from collections import defaultdict
        from django.db.models import Avg
        
        subject_scores = defaultdict(list)
        
        # Get all approved MCQ submissions
        mcq_submissions = TestSubmission.objects.filter(
            student=self.student,
            is_final=True
        ).select_related('test__lesson')
        
        for submission in mcq_submissions:
            subject = submission.test.lesson.subject
            subject_scores[subject].append(submission.score)
        
        # Get all finalized Q&A submissions
        qa_submissions = QASubmission.objects.filter(
            student=self.student,
            status='finalized'
        ).select_related('test__lesson')
        
        for submission in qa_submissions:
            subject = submission.test.lesson.subject
            subject_scores[subject].append(submission.final_score)
        
        # Calculate average per subject
        statistics = {}
        for subject, scores in subject_scores.items():
            if scores:
                avg_score = sum(scores) / len(scores)
                statistics[subject] = {
                    'average_score': round(avg_score, 2),
                    'test_count': len(scores),
                    'subject_display': dict(Lesson.SUBJECT_CHOICES).get(subject, subject)
                }
        
        return statistics
    
    def get_historical_weakness_analysis(self, subject=None):
        """
        Aggregate all AI weakness analyses from Q&A submissions to track student progress over time.
        Shows improvement patterns, recurring issues, and learning trends.
        
        Args:
            subject (str): Optional subject filter to analyze specific subject only
            
        Returns:
            dict: Comprehensive historical analysis including:
                - weakness_trends: How weaknesses change over time
                - improvement_areas: What has gotten better
                - persistent_issues: What keeps recurring
                - recommendations_history: All recommendations given
                - overall_progress: Summary of learning journey
        """
        from collections import defaultdict
        from datetime import datetime
        
        # Get all finalized Q&A submissions with AI analysis
        qa_submissions = QASubmission.objects.filter(
            student=self.student,
            status='finalized',
            ai_analysis__isnull=False
        ).select_related('test__lesson').order_by('submitted_at')
        
        # Filter by subject if specified
        if subject:
            qa_submissions = qa_submissions.filter(test__lesson__subject=subject)
        
        if not qa_submissions.exists():
            return {
                'has_data': False,
                'message': 'No Q&A test analyses available yet'
            }
        
        # Aggregate data
        spelling_issues_over_time = []
        comprehension_issues_over_time = []
        critical_thinking_levels = []
        all_strengths = []
        all_recommendations = []
        persistent_spelling_errors = defaultdict(int)
        persistent_comprehension_problems = defaultdict(int)
        subject_breakdown = defaultdict(list)
        
        for submission in qa_submissions:
            analysis = submission.ai_analysis
            if not analysis:
                continue
            
            date = submission.submitted_at.strftime('%Y-%m-%d')
            subject_name = submission.test.lesson.subject
            
            # Track spelling/grammar over time
            spelling_data = analysis.get('spelling_grammar', {})
            if spelling_data.get('has_issues'):
                spelling_issues_over_time.append({
                    'date': date,
                    'severity': spelling_data.get('severity'),
                    'count': spelling_data.get('count', 0),
                    'subject': subject_name
                })
                # Track recurring errors
                for error in spelling_data.get('examples', [])[:3]:
                    persistent_spelling_errors[error] += 1
            
            # Track comprehension over time
            comprehension_data = analysis.get('comprehension', {})
            if comprehension_data.get('has_issues'):
                comprehension_issues_over_time.append({
                    'date': date,
                    'severity': comprehension_data.get('severity'),
                    'problems_count': len(comprehension_data.get('problems', [])),
                    'subject': subject_name
                })
                # Track recurring comprehension issues
                for problem in comprehension_data.get('problems', [])[:3]:
                    persistent_comprehension_problems[problem] += 1
            
            # Track critical thinking progression
            ct_data = analysis.get('critical_thinking', {})
            critical_thinking_levels.append({
                'date': date,
                'level': ct_data.get('level', 'unknown'),
                'subject': subject_name
            })
            
            # Collect all strengths
            strengths = analysis.get('strengths', [])
            for strength in strengths:
                all_strengths.append({
                    'strength': strength,
                    'date': date,
                    'subject': subject_name
                })
            
            # Collect all recommendations
            recommendations = analysis.get('recommendations_for_teacher', [])
            for rec in recommendations:
                all_recommendations.append({
                    'recommendation': rec,
                    'date': date,
                    'subject': subject_name
                })
            
            # Subject breakdown
            subject_breakdown[subject_name].append({
                'date': date,
                'analysis': analysis
            })
        
        # Analyze trends
        spelling_improving = False
        comprehension_improving = False
        critical_thinking_improving = False
        
        if len(spelling_issues_over_time) >= 2:
            recent_severity = spelling_issues_over_time[-1]['severity']
            earlier_severity = spelling_issues_over_time[0]['severity']
            severity_map = {'minor': 1, 'moderate': 2, 'severe': 3}
            spelling_improving = severity_map.get(recent_severity, 2) < severity_map.get(earlier_severity, 2)
        
        if len(comprehension_issues_over_time) >= 2:
            recent_count = comprehension_issues_over_time[-1]['problems_count']
            earlier_count = comprehension_issues_over_time[0]['problems_count']
            comprehension_improving = recent_count < earlier_count
        
        if len(critical_thinking_levels) >= 2:
            level_map = {'weak': 1, 'developing': 2, 'good': 3, 'strong': 4}
            recent_level = level_map.get(critical_thinking_levels[-1]['level'], 1)
            earlier_level = level_map.get(critical_thinking_levels[0]['level'], 1)
            critical_thinking_improving = recent_level > earlier_level
        
        # Find most persistent issues
        top_spelling_errors = sorted(
            persistent_spelling_errors.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        top_comprehension_problems = sorted(
            persistent_comprehension_problems.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            'has_data': True,
            'total_analyses': len(qa_submissions),
            'date_range': {
                'first': qa_submissions.first().submitted_at.strftime('%Y-%m-%d'),
                'last': qa_submissions.last().submitted_at.strftime('%Y-%m-%d')
            },
            'improvement_trends': {
                'spelling_grammar': {
                    'improving': spelling_improving,
                    'history': spelling_issues_over_time
                },
                'comprehension': {
                    'improving': comprehension_improving,
                    'history': comprehension_issues_over_time
                },
                'critical_thinking': {
                    'improving': critical_thinking_improving,
                    'history': critical_thinking_levels
                }
            },
            'persistent_issues': {
                'spelling_errors': [{'error': error, 'occurrences': count} for error, count in top_spelling_errors],
                'comprehension_problems': [{'problem': prob, 'occurrences': count} for prob, count in top_comprehension_problems]
            },
            'strengths_identified': all_strengths[-10:],  # Last 10 strengths
            'recommendations_history': all_recommendations[-10:],  # Last 10 recommendations
            'by_subject': {
                subject: {
                    'test_count': len(analyses),
                    'recent_analysis': analyses[-1]['analysis'] if analyses else None
                }
                for subject, analyses in subject_breakdown.items()
            }
        }

class TestSubmission(models.Model):
    """Student submission for MCQ test"""
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mcq_submissions')
    answers = models.JSONField(help_text='Student answers for the test')
    score = models.FloatField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    attempt_number = models.IntegerField(default=1)
    is_final = models.BooleanField(default=False, help_text='True when teacher approves - prevents retakes')
    teacher_feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_mcq_submissions'
    )

    class Meta:
        ordering = ['-submitted_at']
        unique_together = ['test', 'student', 'attempt_number']

    def __str__(self):
        return f"{self.student.username} - {self.test.title} (Attempt {self.attempt_number})"

    def save(self, *args, **kwargs):
        # Auto-increment attempt number for new submissions
        if not self.pk:
            last_attempt = TestSubmission.objects.filter(
                test=self.test,
                student=self.student
            ).order_by('-attempt_number').first()
            
            if last_attempt:
                self.attempt_number = last_attempt.attempt_number + 1
        
        super().save(*args, **kwargs)

class QATest(models.Model):
    """Timed Q&A Test with open-ended questions"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='qa_tests')
    title = models.CharField(max_length=255)
    questions = models.JSONField()  # LastArray of {question: str, expected_points: str}
    time_limit = models.IntegerField(default=30)  # Time limit in minutes
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_qa_tests', null=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_qa_tests')
    review_notes = models.TextField(blank=True)
    num_questions = models.IntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

class QASubmission(models.Model):
    """Student submission for Q&A test"""
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('ai_graded', 'AI Graded'),
        ('teacher_review', 'Teacher Review'),
        ('finalized', 'Finalized'),
    ]
    
    test = models.ForeignKey(QATest, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='qa_submissions')
    answers = models.JSONField()  # Array of {question_index: int, answer: str}
    ai_feedback = models.JSONField(null=True, blank=True)  # AI grading results
    ai_analysis = models.JSONField(
        null=True, 
        blank=True,
        help_text='Detailed AI analysis of student weaknesses: spelling, comprehension, completeness, etc.'
    )  # Comprehensive student weakness analysis for teachers
    teacher_feedback = models.TextField(blank=True)
    final_score = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    time_taken = models.IntegerField(null=True, blank=True)  # Time taken in seconds
    fullscreen_exits = models.IntegerField(default=0)  # Track fullscreen violations
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_submissions')

    class Meta:
        ordering = ['-submitted_at']
        unique_together = ['test', 'student']

    def __str__(self):
        return f"{self.student.username} - {self.test.title} ({self.get_status_display()})"


class TeachingPlan(models.Model):
    """
    Teaching timeline/calendar for teachers to plan and track lessons.
    Visible to students and advisors for transparency.
    """
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('taught', 'Taught'),
        ('cancelled', 'Cancelled'),
    ]
    
    SUBJECT_CHOICES = [
        ('math', 'Mathematics'),
        ('science', 'Science'),
        ('english', 'English'),
        ('arabic', 'Arabic'),
        ('social_studies', 'Social Studies'),
        ('art', 'Art'),
        ('music', 'Music'),
        ('physical_education', 'Physical Education'),
        ('computer_science', 'Computer Science'),
        ('religious_studies', 'Religious Studies'),
    ]
    
    GRADE_CHOICES = [
        ('grade_1', 'Grade 1'),
        ('grade_2', 'Grade 2'),
        ('grade_3', 'Grade 3'),
        ('grade_4', 'Grade 4'),
        ('grade_5', 'Grade 5'),
        ('grade_6', 'Grade 6'),
        ('grade_7', 'Grade 7'),
        ('grade_8', 'Grade 8'),
        ('grade_9', 'Grade 9'),
        ('grade_10', 'Grade 10'),
        ('grade_11', 'Grade 11'),
        ('grade_12', 'Grade 12'),
    ]
    
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teaching_plans',
        limit_choices_to={'role': 'teacher'}
    )
    title = models.CharField(max_length=255, help_text='Title/topic of the session')
    description = models.TextField(blank=True, help_text='What will be covered')
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES)
    grade_level = models.CharField(max_length=20, choices=GRADE_CHOICES)
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='teaching_plans',
        help_text='Optional: Link to an existing lesson'
    )
    date = models.DateField(help_text='Date of the session')
    time = models.TimeField(null=True, blank=True, help_text='Time of day for the session')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    duration_minutes = models.IntegerField(null=True, blank=True, help_text='Expected duration in minutes')
    notes = models.TextField(blank=True, help_text='Additional notes or preparation details')
    completion_notes = models.TextField(blank=True, help_text='Notes after teaching (what went well, challenges, etc.)')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-time']
        indexes = [
            models.Index(fields=['teacher', 'date']),
            models.Index(fields=['teacher', 'subject']),
        ]
    
    def __str__(self):
        return f"{self.teacher.username} - {self.title} ({self.date})"


class VaultLessonPlan(models.Model):
    """
    Lesson plans shared in the vault system.
    Advisors can add lesson plans to their subject's vault.
    Teachers can view and use lesson plans from vaults of subjects they teach.
    """
    SUBJECT_CHOICES = [
        ('math', 'Mathematics'),
        ('science', 'Science'),
        ('english', 'English'),
        ('french', 'French'),
        ('arabic', 'Arabic'),
        ('social_studies', 'Social Studies'),
        ('art', 'Art'),
        ('music', 'Music'),
        ('physical_education', 'Physical Education'),
        ('computer_science', 'Computer Science'),
        ('religious_studies', 'Religious Studies'),
    ]
    
    GRADE_CHOICES = [
        ('1', '1st Grade'),
        ('2', '2nd Grade'),
        ('3', '3rd Grade'),
        ('4', '4th Grade'),
        ('5', '5th Grade'),
        ('6', '6th Grade'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField(help_text='Brief description of the lesson plan')
    content = models.TextField(help_text='Full lesson plan content')
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES)
    grade_level = models.CharField(max_length=2, choices=GRADE_CHOICES)
    
    # Metadata
    objectives = models.JSONField(default=list, blank=True, help_text='Learning objectives')
    materials_needed = models.JSONField(default=list, blank=True, help_text='Required materials')
    duration_minutes = models.IntegerField(null=True, blank=True, help_text='Estimated duration')
    tags = models.JSONField(default=list, blank=True, help_text='Tags for easier search')
    
    # Language-specific fields (for English, French, Arabic)
    grammar = models.JSONField(default=list, blank=True, help_text='Grammar points (for language subjects)')
    vocabulary = models.JSONField(default=list, blank=True, help_text='Vocabulary words/phrases (for language subjects)')
    life_skills_and_values = models.JSONField(default=list, blank=True, help_text='Life skills and values covered')
    
    # Source tracking (how this lesson plan was created)
    SOURCE_TYPE_CHOICES = [
        ('manual', 'Manually Created'),
        ('ai_yearly', 'AI Generated - Yearly Breakdown'),
        ('ai_single', 'AI Generated - Single Lesson'),
        ('imported', 'Imported from Teacher'),
    ]
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES, default='manual')
    source_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='imported_vault_plans',
        help_text='Original teacher if this was imported from their lesson'
    )
    
    # File attachments for AI generation
    teacher_guide_file = models.FileField(
        upload_to='vault/teacher_guides/',
        null=True,
        blank=True,
        help_text='Teacher guide PDF used for AI generation'
    )
    yearly_breakdown_file = models.FileField(
        upload_to='vault/yearly_breakdowns/',
        null=True,
        blank=True,
        help_text='Yearly breakdown PDF input for AI generation'
    )
    ai_generation_prompt = models.TextField(
        blank=True,
        help_text='Custom text/prompt provided for AI generation'
    )
    
    # Ownership and visibility
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vault_lesson_plans',
        limit_choices_to={'role__in': ['advisor', 'admin']}
    )
    school = models.ForeignKey('accounts.School', on_delete=models.CASCADE, related_name='vault_lesson_plans')
    
    # Status
    is_active = models.BooleanField(default=True, help_text='Whether this lesson plan is visible in the vault')
    is_featured = models.BooleanField(default=False, help_text='Featured lesson plans appear at the top')
    
    # Engagement metrics
    view_count = models.IntegerField(default=0)
    use_count = models.IntegerField(default=0, help_text='Number of times teachers have used this')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_featured', '-created_at']
        indexes = [
            models.Index(fields=['subject', 'grade_level']),
            models.Index(fields=['school', 'subject']),
            models.Index(fields=['is_active', 'subject']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_subject_display()} ({self.get_grade_level_display()})"


class VaultLessonPlanUsage(models.Model):
    """
    Track when teachers use vault lesson plans
    """
    lesson_plan = models.ForeignKey(VaultLessonPlan, on_delete=models.CASCADE, related_name='usages')
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vault_usage',
        limit_choices_to={'role': 'teacher'}
    )
    used_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text='Teacher notes about using this lesson plan')
    rating = models.IntegerField(null=True, blank=True, help_text='1-5 rating')
    feedback = models.TextField(blank=True, help_text='Feedback about the lesson plan')
    
    class Meta:
        ordering = ['-used_at']
        indexes = [
            models.Index(fields=['teacher', 'lesson_plan']),
            models.Index(fields=['lesson_plan', 'used_at']),
        ]
    
    def __str__(self):
        return f"{self.teacher.username} used {self.lesson_plan.title}"


class VaultComment(models.Model):
    """
    Comments and discussions on vault lesson plans
    """
    lesson_plan = models.ForeignKey(VaultLessonPlan, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vault_comments')
    comment = models.TextField()
    parent_comment = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='replies',
        help_text='For threaded comments'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.user.username} on {self.lesson_plan.title}"


class YearlyBreakdown(models.Model):
    """
    Track AI-generated yearly breakdowns
    Advisors upload a PDF and get a full year's worth of lesson plans
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    advisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='yearly_breakdowns',
        limit_choices_to={'role__in': ['advisor', 'admin']}
    )
    school = models.ForeignKey('accounts.School', on_delete=models.CASCADE, related_name='yearly_breakdowns')
    subject = models.CharField(max_length=50, choices=VaultLessonPlan.SUBJECT_CHOICES)
    grade_level = models.CharField(max_length=2, choices=VaultLessonPlan.GRADE_CHOICES)
    
    # Input
    input_pdf = models.FileField(upload_to='vault/yearly_inputs/', help_text='PDF containing curriculum/yearly plan')
    custom_instructions = models.TextField(blank=True, help_text='Additional instructions for AI generation')
    
    # Processing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    
    # Results
    generated_plans_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['advisor', 'status']),
            models.Index(fields=['school', 'subject']),
        ]
    
    def __str__(self):
        return f"Yearly Breakdown - {self.get_subject_display()} Grade {self.grade_level} ({self.status})"


class VaultExercise(models.Model):
    """
    Exercises (MCQ or Q&A) associated with vault lesson plans.
    Teachers can add practice exercises to vault lessons.
    """
    EXERCISE_TYPE_CHOICES = [
        ('mcq', 'Multiple Choice Questions'),
        ('qa', 'Question & Answer'),
    ]
    
    vault_lesson_plan = models.ForeignKey(
        VaultLessonPlan,
        on_delete=models.CASCADE,
        related_name='exercises'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, help_text='Brief description of the exercise')
    exercise_type = models.CharField(max_length=10, choices=EXERCISE_TYPE_CHOICES)
    
    # Exercise content (structure depends on type)
    # For MCQ: [{question: str, options: [str], correct_answer: int}]
    # For Q&A: [{question: str, expected_points: str, sample_answer: str}]
    questions = models.JSONField(help_text='Array of questions with their structure')
    
    # Settings
    time_limit = models.IntegerField(null=True, blank=True, help_text='Time limit in minutes (optional)')
    num_questions = models.IntegerField(help_text='Number of questions')
    difficulty_level = models.CharField(
        max_length=20,
        choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')],
        default='medium'
    )
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vault_exercises'
    )
    is_active = models.BooleanField(default=True)
    usage_count = models.IntegerField(default=0, help_text='Times this exercise was used')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vault_lesson_plan', 'exercise_type']),
            models.Index(fields=['is_active', 'exercise_type']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_exercise_type_display()}) - {self.vault_lesson_plan.title}"


class VaultMaterial(models.Model):
    """
    Course materials (PDFs, documents, images) associated with vault lesson plans.
    Teachers can upload supplementary materials to share with other teachers.
    """
    MATERIAL_TYPE_CHOICES = [
        ('pdf', 'PDF Document'),
        ('doc', 'Word Document'),
        ('ppt', 'PowerPoint Presentation'),
        ('image', 'Image'),
        ('video_link', 'Video Link'),
        ('other', 'Other'),
    ]
    
    vault_lesson_plan = models.ForeignKey(
        VaultLessonPlan,
        on_delete=models.CASCADE,
        related_name='materials'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, help_text='Brief description of the material')
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPE_CHOICES)
    
    # File upload
    file = models.FileField(
        upload_to='vault/materials/%Y/%m/',
        null=True,
        blank=True,
        help_text='Upload file (PDF, DOC, PPT, images, etc.)'
    )
    
    # External link (for videos, online resources)
    external_link = models.URLField(
        blank=True,
        help_text='External URL (for videos, websites, etc.)'
    )
    
    # File metadata
    file_size = models.IntegerField(null=True, blank=True, help_text='File size in bytes')
    mime_type = models.CharField(max_length=100, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vault_materials'
    )
    is_active = models.BooleanField(default=True)
    download_count = models.IntegerField(default=0, help_text='Number of downloads')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vault_lesson_plan', 'material_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_material_type_display()}) - {self.vault_lesson_plan.title}"
    
    def save(self, *args, **kwargs):
        # Auto-detect material type from file extension if not set
        if self.file and not self.material_type:
            filename = self.file.name.lower()
            if filename.endswith('.pdf'):
                self.material_type = 'pdf'
            elif filename.endswith(('.doc', '.docx')):
                self.material_type = 'doc'
            elif filename.endswith(('.ppt', '.pptx')):
                self.material_type = 'ppt'
            elif filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                self.material_type = 'image'
            else:
                self.material_type = 'other'
        
        # Get file size
        if self.file and not self.file_size:
            self.file_size = self.file.size
        
        super().save(*args, **kwargs)


class StudentNotebook(models.Model):
    """Student's personal notebook"""
    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notebook',
        limit_choices_to={'role': 'student'}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notebook of {self.student.get_full_name()}"


class NotebookPage(models.Model):
    """Daily page in student's notebook"""
    notebook = models.ForeignKey(
        StudentNotebook,
        on_delete=models.CASCADE,
        related_name='pages'
    )
    date = models.DateField(help_text='Date of this notebook page')
    lesson_name = models.CharField(
        max_length=255,
        help_text='Name of the lesson for this page',
        blank=True,
        default=''
    )
    
    # Teacher sets exercises, students answer
    exercises_set_by_teacher = models.TextField(
        help_text='Exercises/activities assigned by teacher',
        blank=True
    )
    exercises_answers = models.TextField(
        help_text='Student answers to the exercises',
        blank=True
    )
    
    notes = models.TextField(
        blank=True,
        help_text='Additional notes or observations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Teacher interaction
    teacher_viewed = models.BooleanField(default=False)
    teacher_comment = models.TextField(blank=True)
    teacher_viewed_at = models.DateTimeField(null=True, blank=True)
    
    # Answer grading
    answer_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Review'),
            ('correct', 'Correct'),
            ('incorrect', 'Incorrect'),
            ('partial', 'Partially Correct'),
        ],
        default='pending',
        help_text='Teacher evaluation of student answers'
    )

    class Meta:
        ordering = ['-date']
        unique_together = ['notebook', 'date']
        indexes = [
            models.Index(fields=['notebook', '-date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.notebook.student.get_full_name()} - {self.date}"


# ============================================================
# FORUM MODELS - Professional Discussion Forum
# ============================================================

class ForumCategory(models.Model):
    """
    Categories for organizing forum discussions
    """
    CATEGORY_CHOICES = [
        ('teaching_methods', 'Teaching Methods'),
        ('lesson_sharing', 'Lesson Sharing'),
        ('subject_discussion', 'Subject Discussion'),
        ('best_practices', 'Best Practices'),
        ('technology', 'Technology & Tools'),
        ('regional_exchange', 'Regional Exchange'),
        ('general', 'General Discussion'),
    ]
    
    name = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    description_ar = models.TextField(blank=True)
    category_type = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='general')
    icon = models.CharField(max_length=50, blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Forum Categories'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class ForumTopic(models.Model):
    """
    Discussion topics created by teachers, advisors, or admins
    """
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('pinned', 'Pinned'),
        ('archived', 'Archived'),
    ]
    
    category = models.ForeignKey(ForumCategory, on_delete=models.CASCADE, related_name='topics')
    title = models.CharField(max_length=255)
    content = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='forum_topics')
    
    # Optional attachments/references
    related_lesson = models.ForeignKey('Lesson', on_delete=models.SET_NULL, null=True, blank=True, related_name='forum_topics')
    related_subject = models.CharField(max_length=50, blank=True)
    
    # Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    is_pinned = models.BooleanField(default=False)
    views_count = models.IntegerField(default=0)
    
    # Regional context
    region = models.CharField(max_length=100, blank=True)
    school_level = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_pinned', '-last_activity']
        indexes = [
            models.Index(fields=['-last_activity']),
            models.Index(fields=['category', '-created_at']),
        ]
    
    def __str__(self):
        return self.title
    
    def increment_views(self):
        """Increment view count"""
        self.views_count += 1
        self.save(update_fields=['views_count'])
    
    def get_reply_count(self):
        """Get total number of replies"""
        return self.replies.count()
    
    def get_last_reply(self):
        """Get the most recent reply"""
        return self.replies.order_by('-created_at').first()


class ForumReply(models.Model):
    """
    Replies to forum topics
    """
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='forum_replies')
    content = models.TextField()
    
    # Optional parent reply for nested discussions
    parent_reply = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_replies')
    
    # Moderation
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_solution = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name_plural = 'Forum Replies'
    
    def __str__(self):
        return f"Reply by {self.author.username} on {self.topic.title}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update topic's last activity
        from django.utils import timezone
        self.topic.last_activity = timezone.now()
        self.topic.save(update_fields=['last_activity'])


class ForumLike(models.Model):
    """
    Likes/helpful marks for topics and replies
    """
    CONTENT_TYPE_CHOICES = [
        ('topic', 'Topic'),
        ('reply', 'Reply'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPE_CHOICES)
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, null=True, blank=True, related_name='likes')
    reply = models.ForeignKey(ForumReply, on_delete=models.CASCADE, null=True, blank=True, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [
            ['user', 'topic'],
            ['user', 'reply'],
        ]
    
    def __str__(self):
        if self.topic:
            return f"{self.user.username} likes topic {self.topic.id}"
        return f"{self.user.username} likes reply {self.reply.id}"


class ForumBookmark(models.Model):
    """
    Users can bookmark topics for later reference
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='forum_bookmarks')
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'topic']
    
    def __str__(self):
        return f"{self.user.username} bookmarked {self.topic.title}"


class ForumTag(models.Model):
    """
    Tags for better topic categorization and search
    """
    name = models.CharField(max_length=50, unique=True)
    name_ar = models.CharField(max_length=50, blank=True)
    usage_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-usage_count', 'name']
    
    def __str__(self):
        return self.name


class TopicTag(models.Model):
    """
    Many-to-many relationship between topics and tags
    """
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, related_name='topic_tags')
    tag = models.ForeignKey(ForumTag, on_delete=models.CASCADE, related_name='tagged_topics')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['topic', 'tag']
    
    def __str__(self):
        return f"{self.topic.title} - {self.tag.name}"


class ForumNotification(models.Model):
    """
    Notifications for forum activities
    """
    NOTIFICATION_TYPES = [
        ('reply', 'New Reply'),
        ('mention', 'Mentioned'),
        ('like', 'Like Received'),
        ('solution', 'Solution Marked'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='forum_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE)
    reply = models.ForeignKey(ForumReply, on_delete=models.CASCADE, null=True, blank=True)
    triggered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='triggered_notifications')
    
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.notification_type}"


class ChatConversation(models.Model):
    """
    AI Chat conversation session
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_conversations')
    title = models.CharField(max_length=255, default='New Conversation')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"


class ChatMessage(models.Model):
    """
    Individual message in a chat conversation
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    
    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    
    # Optional metadata for function calls
    function_name = models.CharField(max_length=100, null=True, blank=True)
    function_args = models.JSONField(null=True, blank=True)
    function_result = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class CNPTeacherGuide(models.Model):
    """
    Teacher guides uploaded by CNP (Centre National Pédagogique) agents
    These PDFs are used as source material for AI lesson plan generation
    """
    SUBJECT_CHOICES = [
        ('math', 'Mathematics'),
        ('science', 'Science'),
        ('english', 'English'),
        ('arabic', 'Arabic'),
        ('french', 'French'),
        ('social_studies', 'Social Studies'),
        ('islamic_education', 'Islamic Education'),
        ('history', 'History'),
        ('geography', 'Geography'),
        ('civics', 'Civics'),
        ('technology', 'Technology'),
        ('computer_science', 'Computer Science'),
        ('art', 'Art'),
        ('music', 'Music'),
        ('physical_education', 'Physical Education'),
    ]
    
    GRADE_CHOICES = [
        ('grade_1', '1st Grade'),
        ('grade_2', '2nd Grade'),
        ('grade_3', '3rd Grade'),
        ('grade_4', '4th Grade'),
        ('grade_5', '5th Grade'),
        ('grade_6', '6th Grade'),
        ('grade_7', '7th Grade'),
        ('grade_8', '8th Grade'),
        ('grade_9', '9th Grade'),
        ('grade_10', '10th Grade'),
        ('grade_11', '11th Grade'),
        ('grade_12', '12th Grade'),
    ]
    
    GUIDE_TYPE_CHOICES = [
        ('yearly', 'Yearly Program/Curriculum'),
        ('unit', 'Unit/Chapter Guide'),
        ('lesson', 'Single Lesson Guide'),
        ('assessment', 'Assessment/Evaluation Guide'),
        ('resource', 'Additional Resources'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('archived', 'Archived'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=300, help_text='Title of the teacher guide')
    description = models.TextField(blank=True, help_text='Description of contents and purpose')
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES)
    grade_level = models.CharField(max_length=10, choices=GRADE_CHOICES)
    guide_type = models.CharField(max_length=20, choices=GUIDE_TYPE_CHOICES, default='lesson')
    academic_year = models.CharField(max_length=20, default='2024-2025', help_text='e.g., 2024-2025')
    
    # File
    pdf_file = models.FileField(
        upload_to='cnp/teacher_guides/%Y/%m/',
        help_text='Teacher guide PDF file'
    )
    file_size = models.BigIntegerField(null=True, blank=True, help_text='File size in bytes')
    page_count = models.IntegerField(null=True, blank=True, help_text='Number of pages in PDF')
    
    # Metadata
    keywords = models.JSONField(
        default=list,
        blank=True,
        help_text='Keywords/tags for searchability: ["fractions", "geometry", etc.]'
    )
    topics_covered = models.JSONField(
        default=list,
        blank=True,
        help_text='List of topics covered in this guide'
    )
    learning_objectives = models.JSONField(
        default=list,
        blank=True,
        help_text='Learning objectives from the guide'
    )
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cnp_uploads',
        limit_choices_to={'role': 'cnp'}
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cnp_approvals',
        limit_choices_to={'role__in': ['admin', 'cnp']}
    )
    
    # Usage tracking
    usage_count = models.IntegerField(
        default=0,
        help_text='Number of times used for lesson generation'
    )
    download_count = models.IntegerField(
        default=0,
        help_text='Number of times downloaded'
    )
    
    # Notes
    cnp_notes = models.TextField(
        blank=True,
        help_text='Internal notes from CNP agent'
    )
    admin_notes = models.TextField(
        blank=True,
        help_text='Admin review notes'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subject', 'grade_level']),
            models.Index(fields=['guide_type', 'status']),
            models.Index(fields=['academic_year', 'subject']),
        ]
        verbose_name = 'CNP Teacher Guide'
        verbose_name_plural = 'CNP Teacher Guides'
    
    def __str__(self):
        return f"{self.title} - {self.get_subject_display()} ({self.get_grade_level_display()})"
    
    def save(self, *args, **kwargs):
        # Calculate file size if file exists
        if self.pdf_file and not self.file_size:
            try:
                self.file_size = self.pdf_file.size
            except:
                pass
        super().save(*args, **kwargs)


