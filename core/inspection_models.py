"""
Inspector and GPI (General Pedagogical Inspectorate) Models
Handles inspection visits, reports, and regional management
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Region(models.Model):
    """
    Geographic regions for inspector assignments
    Maps to Tunisia's delegations/governorates
    """
    name = models.CharField(max_length=100, unique=True)
    name_ar = models.CharField(max_length=100, blank=True, verbose_name='Arabic Name')
    code = models.CharField(max_length=20, unique=True, help_text='Region code (e.g., TUN-01)')
    governorate = models.CharField(max_length=100, blank=True, help_text='Parent governorate')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Region'
        verbose_name_plural = 'Regions'
    
    def __str__(self):
        return self.name
    
    def get_school_count(self):
        """Count schools in this region"""
        return self.schools.count()
    
    def get_teacher_count(self):
        """Count teachers in schools in this region"""
        from accounts.models import User
        return User.objects.filter(role='teacher', school__region=self).count()
    
    def get_teachers_count(self):
        """Count teachers in this region (alias for compatibility)"""
        return self.get_teacher_count()
    
    def get_inspectors_count(self):
        """Count inspectors assigned to this region"""
        return self.inspector_assignments.filter(is_active=True).count()


class InspectorRegionAssignment(models.Model):
    """
    Many-to-Many relationship between Inspectors and Regions
    An inspector can be assigned to multiple regions
    """
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='region_assignments',
        limit_choices_to={'role': 'inspector'}
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name='inspector_assignments'
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_inspectors',
        limit_choices_to={'role__in': ['gpi', 'admin']}
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['inspector', 'region']
        ordering = ['-assigned_at']
        verbose_name = 'Inspector Region Assignment'
        verbose_name_plural = 'Inspector Region Assignments'
    
    def __str__(self):
        return f"{self.inspector.get_full_name() or self.inspector.username} → {self.region.name}"


class TeacherComplaint(models.Model):
    """
    Complaints filed against teachers
    Can trigger complaint-based inspections
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('under_investigation', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='complaints_received',
        limit_choices_to={'role': 'teacher'}
    )
    filed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='complaints_filed'
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    category = models.CharField(
        max_length=50,
        blank=True,
        help_text='e.g., Behavior, Attendance, Teaching Quality'
    )
    evidence = models.TextField(blank=True, help_text='Any supporting evidence or documentation')
    assigned_inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_complaints',
        limit_choices_to={'role': 'inspector'}
    )
    resolution_notes = models.TextField(blank=True)
    filed_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-filed_at']
        verbose_name = 'Teacher Complaint'
        verbose_name_plural = 'Teacher Complaints'
    
    def __str__(self):
        return f"Complaint against {self.teacher.get_full_name()} - {self.title}"


class InspectionVisit(models.Model):
    """
    Scheduled inspection visits to teachers
    """
    INSPECTION_TYPE_CHOICES = [
        ('class_visit', 'Classroom Observation'),
        ('follow_up', 'Follow-up Visit'),
        ('complaint_based', 'Complaint Investigation'),
        ('evaluation_renewal', 'Evaluation Renewal'),
        ('routine', 'Routine Inspection'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
    ]
    
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inspection_visits',
        limit_choices_to={'role': 'inspector'}
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_inspections',
        limit_choices_to={'role': 'teacher'}
    )
    school = models.ForeignKey(
        'accounts.School',
        on_delete=models.CASCADE,
        related_name='inspection_visits'
    )
    related_complaint = models.ForeignKey(
        TeacherComplaint,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_visits',
        help_text='If this is a complaint-based inspection'
    )
    
    visit_date = models.DateField()
    visit_time = models.TimeField()
    inspection_type = models.CharField(max_length=30, choices=INSPECTION_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # Scheduling details
    duration_minutes = models.IntegerField(default=90, help_text='Expected duration in minutes')
    notes = models.TextField(blank=True, help_text='Pre-visit notes and preparation')
    cancellation_reason = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-visit_date', '-visit_time']
        verbose_name = 'Inspection Visit'
        verbose_name_plural = 'Inspection Visits'
        indexes = [
            models.Index(fields=['inspector', 'visit_date']),
            models.Index(fields=['teacher', 'visit_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.get_inspection_type_display()} - {self.teacher.get_full_name()} on {self.visit_date}"
    
    def mark_completed(self):
        """Mark visit as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
    
    def can_write_report(self):
        """Check if report can be written for this visit"""
        return self.status == 'completed' and not hasattr(self, 'report')


class InspectionReport(models.Model):
    """
    Detailed report written by inspector after visit
    """
    GPI_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('revision_needed', 'Revision Needed'),
    ]
    
    visit = models.OneToOneField(
        InspectionVisit,
        on_delete=models.CASCADE,
        related_name='report'
    )
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='written_reports',
        limit_choices_to={'role': 'inspector'}
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inspection_reports',
        limit_choices_to={'role': 'teacher'}
    )
    
    # Report content
    summary = models.TextField(help_text='Overall visit summary')
    classroom_observations = models.TextField(
        blank=True,
        help_text='Detailed classroom observation notes'
    )
    pedagogical_evaluation = models.TextField(
        blank=True,
        help_text='Assessment of teaching methods and effectiveness'
    )
    teacher_strengths = models.TextField(blank=True, help_text='Identified strengths')
    improvement_points = models.TextField(blank=True, help_text='Areas for improvement')
    student_engagement = models.TextField(blank=True, help_text='Student participation and engagement')
    material_quality = models.TextField(blank=True, help_text='Quality of teaching materials')
    
    # Rating (1-5 scale)
    final_rating = models.FloatField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Overall rating from 1 (Poor) to 5 (Excellent)'
    )
    
    # Recommendations
    recommendations = models.TextField(blank=True, help_text='Specific recommendations for improvement')
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    
    # Attachments (stored as JSON array of file paths)
    attachments = models.JSONField(default=list, blank=True, help_text='File paths to uploaded documents')
    
    # GPI review
    gpi_status = models.CharField(
        max_length=20,
        choices=GPI_STATUS_CHOICES,
        default='pending'
    )
    gpi_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_reports',
        limit_choices_to={'role': 'gpi'}
    )
    gpi_feedback = models.TextField(blank=True)
    gpi_reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Inspection Report'
        verbose_name_plural = 'Inspection Reports'
        indexes = [
            models.Index(fields=['inspector', 'submitted_at']),
            models.Index(fields=['teacher', 'submitted_at']),
            models.Index(fields=['gpi_status']),
        ]
    
    def __str__(self):
        return f"Report: {self.teacher.get_full_name()} - {self.visit.visit_date}"
    
    def approve(self, gpi_user, feedback=''):
        """Approve report by GPI"""
        self.gpi_status = 'approved'
        self.gpi_reviewer = gpi_user
        self.gpi_feedback = feedback
        self.gpi_reviewed_at = timezone.now()
        self.save()
    
    def reject(self, gpi_user, feedback):
        """Reject report by GPI"""
        self.gpi_status = 'rejected'
        self.gpi_reviewer = gpi_user
        self.gpi_feedback = feedback
        self.gpi_reviewed_at = timezone.now()
        self.save()
    
    def request_revision(self, gpi_user, feedback):
        """Request revision from inspector"""
        self.gpi_status = 'revision_needed'
        self.gpi_reviewer = gpi_user
        self.gpi_feedback = feedback
        self.gpi_reviewed_at = timezone.now()
        self.save()


class MonthlyReport(models.Model):
    """
    Monthly summary report submitted by inspector to GPI
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('revision_needed', 'Revision Needed'),
    ]
    
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='monthly_reports',
        limit_choices_to={'role': 'inspector'}
    )
    month = models.DateField(help_text='First day of the month being reported')
    
    # Statistics (auto-generated)
    total_visits = models.IntegerField(default=0)
    completed_visits = models.IntegerField(default=0)
    cancelled_visits = models.IntegerField(default=0)
    pending_visits = models.IntegerField(default=0)
    
    # Rating distribution (JSON: {1: count, 2: count, ...})
    rating_distribution = models.JSONField(
        default=dict,
        help_text='Distribution of ratings given: {1: 2, 2: 5, 3: 10, 4: 8, 5: 3}'
    )
    
    # Qualitative analysis
    recurring_issues = models.TextField(
        blank=True,
        help_text='Common problems identified across multiple visits'
    )
    positive_trends = models.TextField(
        blank=True,
        help_text='Positive developments and improvements observed'
    )
    recommendations = models.TextField(
        blank=True,
        help_text='Recommendations for regional improvement'
    )
    challenges_faced = models.TextField(
        blank=True,
        help_text='Challenges encountered during inspections'
    )
    
    # GPI review
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    gpi_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_monthly_reports',
        limit_choices_to={'role': 'gpi'}
    )
    gpi_feedback = models.TextField(blank=True)
    gpi_reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-month']
        unique_together = ['inspector', 'month']
        verbose_name = 'Monthly Report'
        verbose_name_plural = 'Monthly Reports'
        indexes = [
            models.Index(fields=['inspector', 'month']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.inspector.get_full_name()} - {self.month.strftime('%B %Y')}"
    
    def generate_statistics(self):
        """Auto-generate statistics from visits in the month"""
        from datetime import datetime
        
        # Get all visits for this inspector in this month
        year = self.month.year
        month_num = self.month.month
        
        visits = InspectionVisit.objects.filter(
            inspector=self.inspector,
            visit_date__year=year,
            visit_date__month=month_num
        )
        
        self.total_visits = visits.count()
        self.completed_visits = visits.filter(status='completed').count()
        self.cancelled_visits = visits.filter(status='cancelled').count()
        self.pending_visits = visits.filter(status='scheduled').count()
        
        # Calculate rating distribution from completed reports
        reports = InspectionReport.objects.filter(
            inspector=self.inspector,
            visit__visit_date__year=year,
            visit__visit_date__month=month_num,
            visit__status='completed'
        )
        
        rating_dist = {}
        for rating in range(1, 6):
            count = reports.filter(final_rating=rating).count()
            if count > 0:
                rating_dist[rating] = count
        
        self.rating_distribution = rating_dist
        self.save()
        
        return {
            'total': self.total_visits,
            'completed': self.completed_visits,
            'cancelled': self.cancelled_visits,
            'pending': self.pending_visits,
            'ratings': rating_dist
        }
    
    def submit(self):
        """Submit report to GPI"""
        self.status = 'submitted'
        self.submitted_at = timezone.now()
        self.save()
    
    def approve(self, gpi_user, feedback=''):
        """Approve monthly report"""
        self.status = 'approved'
        self.gpi_reviewer = gpi_user
        self.gpi_feedback = feedback
        self.gpi_reviewed_at = timezone.now()
        self.save()


class TeacherRatingHistory(models.Model):
    """
    Historical record of teacher ratings from inspections
    Used for trend analysis and performance tracking
    """
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rating_history',
        limit_choices_to={'role': 'teacher'}
    )
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='given_ratings',
        limit_choices_to={'role': 'inspector'}
    )
    inspection_report = models.OneToOneField(
        InspectionReport,
        on_delete=models.CASCADE,
        related_name='rating_record'
    )
    
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    inspection_date = models.DateField()
    inspection_type = models.CharField(max_length=30)
    
    # Contextual information
    subject_taught = models.CharField(max_length=50, blank=True)
    grade_level = models.CharField(max_length=10, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-inspection_date']
        verbose_name = 'Teacher Rating History'
        verbose_name_plural = 'Teacher Rating Histories'
        indexes = [
            models.Index(fields=['teacher', 'inspection_date']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"{self.teacher.get_full_name()} - Rating: {self.rating}/5 on {self.inspection_date}"
    
    @classmethod
    def get_teacher_average(cls, teacher):
        """Calculate average rating for a teacher"""
        from django.db.models import Avg
        result = cls.objects.filter(teacher=teacher).aggregate(avg=Avg('rating'))
        return round(result['avg'], 2) if result['avg'] else None
    
    @classmethod
    def get_teacher_trend(cls, teacher, months=6):
        """Get rating trend for last N months"""
        from datetime import datetime, timedelta
        from django.db.models import Avg
        
        cutoff_date = datetime.now().date() - timedelta(days=months * 30)
        ratings = cls.objects.filter(
            teacher=teacher,
            inspection_date__gte=cutoff_date
        ).order_by('inspection_date')
        
        return [
            {
                'date': r.inspection_date,
                'rating': r.rating,
                'inspector': r.inspector.get_full_name()
            }
            for r in ratings
        ]
