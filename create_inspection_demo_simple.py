#!/usr/bin/env python
"""
Create comprehensive inspection demo data - Simplified version
"""
import os
import django
from datetime import datetime, timedelta, time
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from accounts.models import School
from core.inspection_models import (
    Region, InspectorRegionAssignment, TeacherComplaint,
    InspectionVisit, InspectionReport, MonthlyReport
)

User = get_user_model()

def create_simple_demo_data():
    print("=" * 80)
    print("Creating Inspection System Demo Data")
    print("=" * 80)
    
    # Get users
    inspector = User.objects.get(username='inspector')
    gpi = User.objects.get(username='gpi')
    school = inspector.school
    region = Region.objects.get(code='TUN-TEST')
    
    print(f"\n✓ Inspector: {inspector.get_full_name()}")
    print(f"✓ GPI: {gpi.get_full_name()}")
    print(f"✓ School: {school.name}")
    print(f"✓ Region: {region.name}\n")
    
    # Create teachers
    teachers_data = [
        ('teacher_math', 'Karim', 'Ben Ahmed', 'math', 'M'),
        ('teacher_science', 'Amira', 'Mansouri', 'science', 'F'),
        ('teacher_arabic', 'Mohamed', 'Trabelsi', 'arabic', 'M'),
        ('teacher_english', 'Salma', 'Khelifi', 'english', 'F'),
        ('teacher_social', 'Youssef', 'Hamouda', 'social_studies', 'M'),
    ]
    
    teachers = []
    print("Creating Teachers:")
    for username, first, last, subject, gender in teachers_data:
        teacher, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@test.com',
                'first_name': first,
                'last_name': last,
                'role': 'teacher',
                'school': school,
                'subjects': [subject],
                'gender': gender,
                'is_active': True,
            }
        )
        if created:
            teacher.set_password('teacher123')
            teacher.save()
            print(f"  ✓ {first} {last} - {subject.title()}")
        teachers.append(teacher)
    
    # Create complaints
    print("\nCreating Complaints:")
    complaint1, _ = TeacherComplaint.objects.get_or_create(
        teacher=teachers[0],
        title='Tardiness Issues',
        defaults={
            'description': 'Teacher arrives late frequently',
            'severity': 'medium',
            'status': 'under_investigation',
            'category': 'Attendance',
            'filed_by': gpi,
            'assigned_inspector': inspector,
        }
    )
    print(f"  ✓ Complaint: {complaint1.title} - {complaint1.teacher.get_full_name()}")
    
    complaint2, _ = TeacherComplaint.objects.get_or_create(
        teacher=teachers[2],
        title='Teaching Method Concerns',
        defaults={
            'description': 'Students struggle to understand explanations',
            'severity': 'low',
            'status': 'pending',
            'category': 'Teaching Quality',
            'filed_by': gpi,
            'assigned_inspector': inspector,
        }
    )
    print(f"  ✓ Complaint: {complaint2.title} - {complaint2.teacher.get_full_name()}")
    
    # Create visits
    print("\nCreating Inspection Visits:")
    today = timezone.now().date()
    now_time = time(10, 0)
    
    # Visit 1: Completed routine visit
    visit1, created = InspectionVisit.objects.get_or_create(
        inspector=inspector,
        teacher=teachers[1],
        visit_date=today - timedelta(days=10),
        visit_time=now_time,
        defaults={
            'school': school,
            'inspection_type': 'routine',
            'status': 'completed',
            'notes': 'Regular quarterly inspection',
            'duration_minutes': 45,
            'completed_at': timezone.now() - timedelta(days=10),
        }
    )
    if created:
        print(f"  ✓ Routine Visit: {teachers[1].get_full_name()} (Completed)")
    
    # Visit 2: Completed class visit
    visit2, created = InspectionVisit.objects.get_or_create(
        inspector=inspector,
        teacher=teachers[3],
        visit_date=today - timedelta(days=5),
        visit_time=now_time,
        defaults={
            'school': school,
            'inspection_type': 'class_visit',
            'status': 'completed',
            'notes': 'Classroom observation',
            'duration_minutes': 50,
            'completed_at': timezone.now() - timedelta(days=5),
        }
    )
    if created:
        print(f"  ✓ Class Visit: {teachers[3].get_full_name()} (Completed)")
    
    # Visit 3: Complaint-based visit
    visit3, created = InspectionVisit.objects.get_or_create(
        inspector=inspector,
        teacher=teachers[0],
        visit_date=today - timedelta(days=3),
        visit_time=now_time,
        defaults={
            'school': school,
            'inspection_type': 'complaint_based',
            'status': 'completed',
            'notes': 'Investigation of tardiness complaint',
            'related_complaint': complaint1,
            'duration_minutes': 60,
            'completed_at': timezone.now() - timedelta(days=3),
        }
    )
    if created:
        print(f"  ✓ Complaint Visit: {teachers[0].get_full_name()} (Completed)")
    
    # Visit 4: Follow-up visit
    visit4, created = InspectionVisit.objects.get_or_create(
        inspector=inspector,
        teacher=teachers[0],
        visit_date=today - timedelta(days=1),
        visit_time=now_time,
        defaults={
            'school': school,
            'inspection_type': 'follow_up',
            'status': 'completed',
            'notes': 'Follow-up on previous concerns',
            'duration_minutes': 45,
            'completed_at': timezone.now() - timedelta(days=1),
        }
    )
    if created:
        print(f"  ✓ Follow-up Visit: {teachers[0].get_full_name()} (Completed)")
    
    # Visit 5: Scheduled future visit
    visit5, created = InspectionVisit.objects.get_or_create(
        inspector=inspector,
        teacher=teachers[2],
        visit_date=today + timedelta(days=2),
        visit_time=now_time,
        defaults={
            'school': school,
            'inspection_type': 'complaint_based',
            'status': 'scheduled',
            'notes': 'Scheduled complaint investigation',
            'related_complaint': complaint2,
        }
    )
    if created:
        print(f"  ✓ Scheduled Visit: {teachers[2].get_full_name()} (Upcoming)")
    
    # Visit 6: Another scheduled visit
    visit6, created = InspectionVisit.objects.get_or_create(
        inspector=inspector,
        teacher=teachers[4],
        visit_date=today + timedelta(days=5),
        visit_time=now_time,
        defaults={
            'school': school,
            'inspection_type': 'routine',
            'status': 'scheduled',
            'notes': 'Regular semester inspection',
        }
    )
    if created:
        print(f"  ✓ Scheduled Visit: {teachers[4].get_full_name()} (Upcoming)")
    
    # Create reports
    print("\nCreating Inspection Reports:")
    
    # Report 1: Approved - Excellent teacher
    report1, created = InspectionReport.objects.get_or_create(
        visit=visit1,
        defaults={
            'inspector': inspector,
            'teaching_quality_rating': 4.5,
            'classroom_management_rating': 4.8,
            'student_engagement_rating': 4.7,
            'lesson_planning_rating': 4.3,
            'assessment_methods_rating': 4.2,
            'professional_conduct_rating': 5.0,
            'strengths': 'Excellent use of visual aids and experiments. Students highly engaged.',
            'areas_for_improvement': 'Could use more technology integration.',
            'recommendations': 'Attend tech workshop. Continue excellent practices.',
            'final_rating': 4.5,
            'status': 'approved',
            'reviewed_by': gpi,
            'reviewed_at': timezone.now() - timedelta(hours=24),
            'gpi_feedback': 'Excellent report. Teacher shows high competency.',
        }
    )
    if created:
        print(f"  ✓ Report APPROVED: {visit1.teacher.get_full_name()} - Rating: 4.5/5.0")
    
    # Report 2: Approved - Good teacher
    report2, created = InspectionReport.objects.get_or_create(
        visit=visit2,
        defaults={
            'inspector': inspector,
            'teaching_quality_rating': 4.2,
            'classroom_management_rating': 4.0,
            'student_engagement_rating': 4.5,
            'lesson_planning_rating': 4.1,
            'assessment_methods_rating': 3.8,
            'professional_conduct_rating': 4.6,
            'strengths': 'Interactive teaching. Good student rapport.',
            'areas_for_improvement': 'Assessment variety needs expansion.',
            'recommendations': 'Explore different assessment techniques.',
            'final_rating': 4.2,
            'status': 'approved',
            'reviewed_by': gpi,
            'reviewed_at': timezone.now() - timedelta(hours=12),
            'gpi_feedback': 'Good report. Solid performance observed.',
        }
    )
    if created:
        print(f"  ✓ Report APPROVED: {visit2.teacher.get_full_name()} - Rating: 4.2/5.0")
    
    # Report 3: Pending review - Needs improvement
    report3, created = InspectionReport.objects.get_or_create(
        visit=visit3,
        defaults={
            'inspector': inspector,
            'teaching_quality_rating': 3.2,
            'classroom_management_rating': 2.8,
            'student_engagement_rating': 3.0,
            'lesson_planning_rating': 3.5,
            'assessment_methods_rating': 3.3,
            'professional_conduct_rating': 3.0,
            'strengths': 'Good subject knowledge. Follows curriculum.',
            'areas_for_improvement': 'Classroom management needs improvement. Student behavior issues. Tardiness affects flow.',
            'recommendations': 'Mandatory classroom management training. Improve punctuality. Follow-up in 30 days.',
            'final_rating': 3.1,
            'status': 'pending_review',
        }
    )
    if created:
        print(f"  ⏳ Report PENDING: {visit3.teacher.get_full_name()} - Rating: 3.1/5.0")
    
    # Report 4: Draft - Follow-up showing improvement
    report4, created = InspectionReport.objects.get_or_create(
        visit=visit4,
        defaults={
            'inspector': inspector,
            'teaching_quality_rating': 3.5,
            'classroom_management_rating': 3.2,
            'student_engagement_rating': 3.4,
            'lesson_planning_rating': 3.8,
            'assessment_methods_rating': 3.6,
            'professional_conduct_rating': 3.5,
            'strengths': 'Improvement in punctuality. Better lesson prep.',
            'areas_for_improvement': 'Still needs classroom management work.',
            'recommendations': 'Continue improvements. Another follow-up in 60 days.',
            'final_rating': 3.5,
            'status': 'draft',
        }
    )
    if created:
        print(f"  📝 Report DRAFT: {visit4.teacher.get_full_name()} - Rating: 3.5/5.0")
    
    # Create a rejected report example
    visit_rejected = InspectionVisit.objects.create(
        inspector=inspector,
        teacher=teachers[1],
        school=school,
        visit_date=today - timedelta(days=15),
        visit_time=now_time,
        inspection_type='routine',
        status='completed',
        notes='Earlier visit for rejected report example',
        completed_at=timezone.now() - timedelta(days=15),
    )
    
    report_rejected, created = InspectionReport.objects.get_or_create(
        visit=visit_rejected,
        defaults={
            'inspector': inspector,
            'teaching_quality_rating': 4.0,
            'classroom_management_rating': 4.0,
            'student_engagement_rating': 4.0,
            'lesson_planning_rating': 4.0,
            'assessment_methods_rating': 4.0,
            'professional_conduct_rating': 4.0,
            'strengths': 'Good performance.',
            'areas_for_improvement': 'Some areas need work.',
            'recommendations': 'Keep it up.',
            'final_rating': 4.0,
            'status': 'rejected',
            'reviewed_by': gpi,
            'reviewed_at': timezone.now() - timedelta(hours=6),
            'gpi_feedback': 'Report lacks detail. Provide specific examples. Observations too vague. Resubmit with comprehensive details.',
        }
    )
    if created:
        print(f"  ✗ Report REJECTED: {visit_rejected.teacher.get_full_name()} - Needs revision")
    
    # Create monthly reports
    print("\nCreating Monthly Reports:")
    last_month = timezone.now() - timedelta(days=30)
    
    monthly1, created = MonthlyReport.objects.get_or_create(
        inspector=inspector,
        month=last_month.month,
        year=last_month.year,
        defaults={
            'total_visits': 12,
            'total_reports_submitted': 12,
            'average_rating': 3.8,
            'summary': 'Productive month. Completed all scheduled visits. Addressed complaints promptly.',
            'challenges_faced': 'Weather caused two reschedulings.',
            'recommendations_for_teachers': 'Three teachers need management training.',
            'status': 'submitted',
            'submitted_at': last_month + timedelta(days=28),
            'reviewed_by': gpi,
            'reviewed_at': last_month + timedelta(days=29),
            'gpi_notes': 'Excellent work. Good coverage.',
        }
    )
    if created:
        print(f"  ✓ Monthly Report: {last_month.strftime('%B %Y')} - Visits: 12, Avg: 3.8")
    
    current = timezone.now()
    monthly2, created = MonthlyReport.objects.get_or_create(
        inspector=inspector,
        month=current.month,
        year=current.year,
        defaults={
            'total_visits': 7,
            'total_reports_submitted': 5,
            'average_rating': 3.9,
            'summary': 'Month in progress. On track with schedule.',
            'challenges_faced': 'One teacher sick - rescheduled.',
            'recommendations_for_teachers': 'Will complete by month end.',
            'status': 'draft',
        }
    )
    if created:
        print(f"  📝 Monthly Report: {current.strftime('%B %Y')} - Draft (In Progress)")
    
    # Statistics
    print("\n" + "=" * 80)
    print("Summary Statistics")
    print("=" * 80)
    
    visits_count = InspectionVisit.objects.filter(inspector=inspector).count()
    reports_count = InspectionReport.objects.filter(inspector=inspector).count()
    
    print(f"\nTeachers: {len(teachers)}")
    print(f"Complaints: {TeacherComplaint.objects.count()}")
    print(f"Visits: {visits_count} (Completed: {InspectionVisit.objects.filter(inspector=inspector, status='completed').count()})")
    print(f"Reports: {reports_count} (Approved: {InspectionReport.objects.filter(status='approved').count()}, Pending: {InspectionReport.objects.filter(status='pending_review').count()})")
    print(f"Monthly Reports: {MonthlyReport.objects.filter(inspector=inspector).count()}")
    
    print("\n" + "=" * 80)
    print("✅ Demo Data Created Successfully!")
    print("=" * 80)
    print("""
NEXT STEPS:

1. LOGIN AS INSPECTOR: http://localhost:8080/login
   Username: inspector  |  Password: inspector123
   
   Inspector can:
   • View all visits (completed & scheduled)
   • Create new inspection visits
   • Submit reports for completed visits
   • Edit draft reports
   • Track monthly statistics

2. LOGIN AS GPI: http://localhost:8080/login
   Username: gpi  |  Password: gpi123
   
   GPI can:
   • Review pending reports
   • Approve/reject with feedback
   • Monitor all inspectors
   • View regional statistics
   • Access all reports

3. TEST WORKFLOWS:
   ✓ View completed visits and reports
   ✓ Create a new inspection visit
   ✓ Submit a report (as inspector)
   ✓ Review and approve/reject (as GPI)
   ✓ Try Arabic/English language toggle
    """)
    print("=" * 80)

if __name__ == '__main__':
    create_simple_demo_data()
