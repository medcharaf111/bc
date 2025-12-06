#!/usr/bin/env python
"""
Create comprehensive inspection demo data:
- Multiple teachers
- Multiple inspection visits (various types)
- Multiple inspection reports (various statuses)
- Complaints
- Monthly reports
- GPI feedback examples

This demonstrates the full workflow of the inspection system.
"""
import os
import django
from datetime import datetime, timedelta
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

def create_demo_data():
    print("=" * 80)
    print("Creating Comprehensive Inspection System Demo Data")
    print("=" * 80)
    
    # Get or create users
    inspector = User.objects.get(username='inspector')
    gpi = User.objects.get(username='gpi')
    school = inspector.school
    region = Region.objects.get(code='TUN-TEST')
    
    print(f"\n✓ Using Inspector: {inspector.get_full_name()}")
    print(f"✓ Using GPI: {gpi.get_full_name()}")
    print(f"✓ Using School: {school.name}")
    print(f"✓ Using Region: {region.name}")
    
    # Create multiple teachers
    print("\n" + "=" * 80)
    print("1. Creating Teachers")
    print("=" * 80)
    
    teachers_data = [
        {
            'username': 'teacher_math',
            'email': 'math.teacher@test.com',
            'first_name': 'Karim',
            'last_name': 'Ben Ahmed',
            'subjects': ['math'],
            'gender': 'M',
        },
        {
            'username': 'teacher_science',
            'email': 'science.teacher@test.com',
            'first_name': 'Amira',
            'last_name': 'Mansouri',
            'subjects': ['science'],
            'gender': 'F',
        },
        {
            'username': 'teacher_arabic',
            'email': 'arabic.teacher@test.com',
            'first_name': 'Mohamed',
            'last_name': 'Trabelsi',
            'subjects': ['arabic'],
            'gender': 'M',
        },
        {
            'username': 'teacher_english',
            'email': 'english.teacher@test.com',
            'first_name': 'Salma',
            'last_name': 'Khelifi',
            'subjects': ['english'],
            'gender': 'F',
        },
        {
            'username': 'teacher_social',
            'email': 'social.teacher@test.com',
            'first_name': 'Youssef',
            'last_name': 'Hamouda',
            'subjects': ['social_studies'],
            'gender': 'M',
        },
    ]
    
    teachers = []
    for teacher_data in teachers_data:
        teacher, created = User.objects.get_or_create(
            username=teacher_data['username'],
            defaults={
                'email': teacher_data['email'],
                'first_name': teacher_data['first_name'],
                'last_name': teacher_data['last_name'],
                'role': 'teacher',
                'school': school,
                'subjects': teacher_data['subjects'],
                'gender': teacher_data['gender'],
                'is_active': True,
            }
        )
        if created:
            teacher.set_password('teacher123')
            teacher.save()
            print(f"  ✓ Created: {teacher.get_full_name()} - {teacher_data['subjects'][0].title()}")
        else:
            print(f"  ⚠ Exists: {teacher.get_full_name()}")
        teachers.append(teacher)
    
    # Create teacher complaints (to trigger complaint-based visits)
    print("\n" + "=" * 80)
    print("2. Creating Teacher Complaints")
    print("=" * 80)
    
    complaints_data = [
        {
            'teacher': teachers[0],  # Math teacher
            'title': 'Tardiness and Lesson Cancellations',
            'severity': 'medium',
            'description': 'Teacher frequently arrives late to class and sometimes cancels lessons without notice.',
            'status': 'under_investigation',
            'category': 'Attendance',
        },
        {
            'teacher': teachers[2],  # Arabic teacher
            'title': 'Teaching Methodology Concerns',
            'severity': 'low',
            'description': 'Teaching methodology could be improved. Students find it difficult to understand explanations.',
            'status': 'pending',
            'category': 'Teaching Quality',
        },
    ]
    
    complaints = []
    for complaint_data in complaints_data:
        complaint, created = TeacherComplaint.objects.get_or_create(
            teacher=complaint_data['teacher'],
            title=complaint_data['title'],
            defaults={
                'filed_by': gpi,  # Filed by GPI for demo purposes
                'description': complaint_data['description'],
                'severity': complaint_data['severity'],
                'status': complaint_data['status'],
                'category': complaint_data['category'],
                'assigned_inspector': inspector,
            }
        )
        if created:
            print(f"  ✓ Complaint filed against {complaint.teacher.get_full_name()}")
            print(f"    Title: {complaint.title}")
            print(f"    Severity: {complaint.severity} | Category: {complaint.category}")
        complaints.append(complaint)
    
    # Create inspection visits (various types and statuses)
    print("\n" + "=" * 80)
    print("3. Creating Inspection Visits")
    print("=" * 80)
    
    visits_data = [
        # Regular scheduled visits
        {
            'teacher': teachers[1],  # Science teacher
            'inspection_type': 'routine',
            'visit_date': (timezone.now() - timedelta(days=10)).date(),
            'visit_time': timezone.now().time(),
            'status': 'completed',
            'notes': 'Regular inspection visit - quarterly check',
            'duration_minutes': 45,
            'visit_notes': 'Excellent classroom management. Students engaged and responsive.',
        },
        {
            'teacher': teachers[3],  # English teacher
            'visit_type': 'regular',
            'scheduled_date': timezone.now() - timedelta(days=5),
            'status': 'completed',
            'notes': 'Regular inspection visit',
            'duration_minutes': 50,
            'visit_notes': 'Good teaching methods. Interactive activities observed.',
        },
        # Complaint-based visit
        {
            'teacher': teachers[0],  # Math teacher (has complaint)
            'visit_type': 'complaint_based',
            'scheduled_date': timezone.now() - timedelta(days=3),
            'status': 'completed',
            'notes': 'Investigation visit following parent complaint about tardiness',
            'complaint': complaints[0],
            'duration_minutes': 60,
            'visit_notes': 'Arrived on time. Observed full lesson. Class management could be improved.',
        },
        # Follow-up visit
        {
            'teacher': teachers[0],  # Math teacher
            'visit_type': 'follow_up',
            'scheduled_date': timezone.now() - timedelta(days=1),
            'status': 'completed',
            'notes': 'Follow-up visit to check improvement areas identified in previous visit',
            'duration_minutes': 45,
            'visit_notes': 'Some improvement noted in punctuality and lesson preparation.',
        },
        # Scheduled upcoming visits
        {
            'teacher': teachers[2],  # Arabic teacher
            'visit_type': 'complaint_based',
            'scheduled_date': timezone.now() + timedelta(days=2),
            'status': 'scheduled',
            'notes': 'Visit scheduled to address teaching methodology concerns',
            'complaint': complaints[1],
        },
        {
            'teacher': teachers[4],  # Social studies teacher
            'visit_type': 'regular',
            'scheduled_date': timezone.now() + timedelta(days=5),
            'status': 'scheduled',
            'notes': 'Regular inspection visit - first semester evaluation',
        },
        # In-progress visit
        {
            'teacher': teachers[1],  # Science teacher
            'visit_type': 'follow_up',
            'scheduled_date': timezone.now(),
            'status': 'in_progress',
            'notes': 'Follow-up to observe new teaching materials implementation',
        },
    ]
    
    visits = []
    for visit_data in visits_data:
        complaint = visit_data.pop('complaint', None)
        visit_notes = visit_data.pop('visit_notes', None)
        duration = visit_data.pop('duration_minutes', None)
        
        visit, created = InspectionVisit.objects.get_or_create(
            inspector=inspector,
            teacher=visit_data['teacher'],
            scheduled_date=visit_data['scheduled_date'],
            defaults={
                'visit_type': visit_data['visit_type'],
                'status': visit_data['status'],
                'notes': visit_data['notes'],
                'complaint': complaint,
            }
        )
        
        if created:
            # Update completed visits with additional details
            if visit.status == 'completed' and visit_notes:
                visit.actual_start_time = visit.scheduled_date
                visit.actual_end_time = visit.scheduled_date + timedelta(minutes=duration)
                visit.visit_notes = visit_notes
                visit.save()
            
            status_icon = "✓" if visit.status == "completed" else "◷" if visit.status == "scheduled" else "⟳"
            print(f"  {status_icon} {visit.visit_type.title()}: {visit.teacher.get_full_name()}")
            print(f"    Date: {visit.scheduled_date.strftime('%Y-%m-%d %H:%M')} | Status: {visit.status}")
        
        visits.append(visit)
    
    # Create inspection reports (various statuses)
    print("\n" + "=" * 80)
    print("4. Creating Inspection Reports")
    print("=" * 80)
    
    reports_data = [
        # Approved report
        {
            'visit': visits[0],  # Science teacher - completed
            'teaching_quality': 4.5,
            'classroom_management': 4.8,
            'student_engagement': 4.7,
            'lesson_planning': 4.3,
            'assessment_methods': 4.2,
            'professional_conduct': 5.0,
            'strengths': 'Excellent use of visual aids and hands-on experiments. Students are highly engaged and demonstrate clear understanding of concepts.',
            'areas_for_improvement': 'Could incorporate more technology-based learning tools. Consider digital simulations for complex topics.',
            'recommendations': 'Attend workshop on educational technology integration. Continue current excellent practices.',
            'final_rating': 4.5,
            'status': 'approved',
            'gpi_feedback': 'Excellent report. Teacher demonstrates high competency. Recommendations are appropriate.',
        },
        # Another approved report
        {
            'visit': visits[1],  # English teacher - completed
            'teaching_quality': 4.2,
            'classroom_management': 4.0,
            'student_engagement': 4.5,
            'lesson_planning': 4.1,
            'assessment_methods': 3.8,
            'professional_conduct': 4.6,
            'strengths': 'Interactive teaching methods. Good rapport with students. Effective use of group activities.',
            'areas_for_improvement': 'Assessment variety could be expanded. More frequent quizzes recommended.',
            'recommendations': 'Explore different assessment techniques. Continue interactive approach.',
            'final_rating': 4.2,
            'status': 'approved',
            'gpi_feedback': 'Good report. Teacher shows solid performance. Consider providing more specific examples in observations.',
        },
        # Pending review report
        {
            'visit': visits[2],  # Math teacher - complaint-based
            'teaching_quality': 3.2,
            'classroom_management': 2.8,
            'student_engagement': 3.0,
            'lesson_planning': 3.5,
            'assessment_methods': 3.3,
            'professional_conduct': 3.0,
            'strengths': 'Good subject knowledge. Follows curriculum guidelines.',
            'areas_for_improvement': 'Classroom management needs significant improvement. Student behavior issues observed. Late arrival affects lesson flow.',
            'recommendations': 'Mandatory classroom management training. Punctuality must improve. Follow-up visit in 30 days.',
            'final_rating': 3.1,
            'status': 'pending_review',
        },
        # Draft report
        {
            'visit': visits[3],  # Math teacher - follow-up
            'teaching_quality': 3.5,
            'classroom_management': 3.2,
            'student_engagement': 3.4,
            'lesson_planning': 3.8,
            'assessment_methods': 3.6,
            'professional_conduct': 3.5,
            'strengths': 'Improvement noted in punctuality. Better lesson preparation observed.',
            'areas_for_improvement': 'Still needs work on classroom management. Student engagement could be higher.',
            'recommendations': 'Continue improvement efforts. Another follow-up visit recommended in 60 days.',
            'final_rating': 3.5,
            'status': 'draft',
        },
        # Rejected report (needs revision)
        {
            'visit': visits[0],  # Create a duplicate for demonstration
            'teaching_quality': 4.0,
            'classroom_management': 4.0,
            'student_engagement': 4.0,
            'lesson_planning': 4.0,
            'assessment_methods': 4.0,
            'professional_conduct': 4.0,
            'strengths': 'Good performance overall.',
            'areas_for_improvement': 'Some areas need work.',
            'recommendations': 'Keep up the good work.',
            'final_rating': 4.0,
            'status': 'rejected',
            'gpi_feedback': 'Report lacks sufficient detail. Please provide specific examples of observed behaviors. Strengths and weaknesses are too vague. Resubmit with more comprehensive observations.',
        },
    ]
    
    reports = []
    for i, report_data in enumerate(reports_data):
        gpi_feedback = report_data.pop('gpi_feedback', None)
        
        # For the rejected example, create a new visit
        if i == 4:  # Last report (rejected example)
            visit = InspectionVisit.objects.create(
                inspector=inspector,
                teacher=visits[0].teacher,
                visit_type='regular',
                scheduled_date=timezone.now() - timedelta(days=15),
                status='completed',
                notes='Earlier visit for demonstration',
            )
        else:
            visit = report_data.pop('visit')
        
        report, created = InspectionReport.objects.get_or_create(
            visit=visit,
            defaults={
                'inspector': inspector,
                'teaching_quality_rating': report_data['teaching_quality'],
                'classroom_management_rating': report_data['classroom_management'],
                'student_engagement_rating': report_data['student_engagement'],
                'lesson_planning_rating': report_data['lesson_planning'],
                'assessment_methods_rating': report_data['assessment_methods'],
                'professional_conduct_rating': report_data['professional_conduct'],
                'strengths': report_data['strengths'],
                'areas_for_improvement': report_data['areas_for_improvement'],
                'recommendations': report_data['recommendations'],
                'final_rating': report_data['final_rating'],
                'status': report_data['status'],
            }
        )
        
        if created:
            # Add GPI review for approved/rejected reports
            if gpi_feedback:
                report.reviewed_by = gpi
                report.reviewed_at = timezone.now() - timedelta(hours=random.randint(1, 48))
                report.gpi_feedback = gpi_feedback
                report.save()
            
            status_icons = {
                'approved': '✓',
                'rejected': '✗',
                'pending_review': '⏳',
                'draft': '📝'
            }
            icon = status_icons.get(report.status, '•')
            print(f"  {icon} Report for {visit.teacher.get_full_name()}")
            print(f"    Rating: {report.final_rating}/5.0 | Status: {report.status}")
            if gpi_feedback:
                print(f"    GPI: {gpi_feedback[:60]}...")
        
        reports.append(report)
    
    # Create monthly reports
    print("\n" + "=" * 80)
    print("5. Creating Inspector Monthly Reports")
    print("=" * 80)
    
    # Previous month report (completed & approved)
    last_month = timezone.now() - timedelta(days=30)
    monthly_report_1, created = MonthlyReport.objects.get_or_create(
        inspector=inspector,
        month=last_month.month,
        year=last_month.year,
        defaults={
            'total_visits': 12,
            'regular_visits': 8,
            'complaint_visits': 2,
            'follow_up_visits': 2,
            'reports_submitted': 12,
            'average_rating': 3.8,
            'summary': 'Productive month. Completed all scheduled visits. Addressed two complaints promptly. Most teachers show good performance.',
            'challenges_faced': 'Transportation delays affected two scheduled visits. Weather caused rescheduling.',
            'recommendations': 'Recommend additional training for 3 teachers in classroom management. One teacher needs follow-up.',
            'status': 'approved',
            'submitted_at': last_month + timedelta(days=28),
        }
    )
    
    if created:
        monthly_report_1.reviewed_by = gpi
        monthly_report_1.reviewed_at = last_month + timedelta(days=29)
        monthly_report_1.gpi_feedback = 'Excellent work. Good coverage of assigned schools. Follow-ups are appropriate.'
        monthly_report_1.save()
        print(f"  ✓ Monthly Report: {last_month.strftime('%B %Y')}")
        print(f"    Visits: 12 | Reports: 12 | Avg Rating: 3.8 | Status: Approved")
    
    # Current month report (in progress)
    current_month = timezone.now()
    monthly_report_2, created = MonthlyReport.objects.get_or_create(
        inspector=inspector,
        month=current_month.month,
        year=current_month.year,
        defaults={
            'total_visits': 7,
            'regular_visits': 4,
            'complaint_visits': 2,
            'follow_up_visits': 1,
            'reports_submitted': 5,
            'average_rating': 3.9,
            'summary': 'Month in progress. Good pace on scheduled visits. Two complaints being investigated.',
            'challenges_faced': 'One teacher unavailable due to sick leave - visit rescheduled.',
            'recommendations': 'Will complete remaining scheduled visits by month end.',
            'status': 'draft',
        }
    )
    
    if created:
        print(f"  📝 Monthly Report: {current_month.strftime('%B %Y')}")
        print(f"    Visits: 7 | Reports: 5 | Avg Rating: 3.9 | Status: Draft (In Progress)")
    
    # Generate statistics
    print("\n" + "=" * 80)
    print("6. Summary Statistics")
    print("=" * 80)
    
    total_visits = InspectionVisit.objects.filter(inspector=inspector).count()
    completed_visits = InspectionVisit.objects.filter(inspector=inspector, status='completed').count()
    scheduled_visits = InspectionVisit.objects.filter(inspector=inspector, status='scheduled').count()
    
    total_reports = InspectionReport.objects.filter(inspector=inspector).count()
    approved_reports = InspectionReport.objects.filter(inspector=inspector, status='approved').count()
    pending_reports = InspectionReport.objects.filter(inspector=inspector, status='pending_review').count()
    rejected_reports = InspectionReport.objects.filter(inspector=inspector, status='rejected').count()
    
    print(f"\n  Teachers Created: {len(teachers)}")
    print(f"  Complaints Filed: {len(complaints)}")
    print(f"\n  Inspection Visits:")
    print(f"    Total: {total_visits}")
    print(f"    Completed: {completed_visits}")
    print(f"    Scheduled: {scheduled_visits}")
    print(f"    In Progress: {total_visits - completed_visits - scheduled_visits}")
    
    print(f"\n  Inspection Reports:")
    print(f"    Total: {total_reports}")
    print(f"    Approved: {approved_reports}")
    print(f"    Pending Review: {pending_reports}")
    print(f"    Rejected: {rejected_reports}")
    print(f"    Draft: {total_reports - approved_reports - pending_reports - rejected_reports}")
    
    print(f"\n  Monthly Reports: {MonthlyReport.objects.filter(inspector=inspector).count()}")
    
    # Print workflow examples
    print("\n" + "=" * 80)
    print("7. Workflow Examples Created")
    print("=" * 80)
    
    print("""
  ✓ Regular Inspection Workflow:
    1. Inspector schedules regular visit
    2. Conducts observation
    3. Creates detailed report
    4. Submits for GPI review
    5. GPI approves with feedback
    
  ✓ Complaint-Based Workflow:
    1. Complaint filed against teacher
    2. Inspector schedules complaint-based visit
    3. Investigates concerns during visit
    4. Creates report with findings
    5. GPI reviews and determines actions
    
  ✓ Follow-Up Workflow:
    1. Initial visit identifies issues
    2. Recommendations provided
    3. Follow-up visit scheduled
    4. Inspector checks improvements
    5. Reports progress to GPI
    
  ✓ Monthly Reporting Workflow:
    1. Inspector tracks all activities
    2. Compiles monthly summary
    3. Submits to GPI
    4. GPI reviews and approves
    5. Used for performance evaluation
    """)
    
    print("\n" + "=" * 80)
    print("Demo Data Creation Complete! 🎉")
    print("=" * 80)
    
    print("""
Next Steps:

1. LOGIN AS INSPECTOR (username: inspector, password: inspector123)
   Dashboard: http://localhost:8080/inspector
   
   You can:
   • View all scheduled visits
   • See completed visits
   • Create new inspection visits
   • Submit reports for completed visits
   • Update draft reports
   • View monthly statistics
   • Generate monthly reports

2. LOGIN AS GPI (username: gpi, password: gpi123)
   Dashboard: http://localhost:8080/gpi
   
   You can:
   • Review pending inspection reports
   • Approve/reject reports with feedback
   • Monitor inspector performance
   • View regional statistics
   • Access all reports across inspectors
   • Review monthly reports
   • Track complaint resolutions

3. TEST WORKFLOWS:
   • Complete a scheduled visit
   • Create and submit a new report
   • Review and approve/reject as GPI
   • Submit monthly report as inspector
   • Review monthly report as GPI

4. VIEW DIFFERENT REPORT TYPES:
   • High-performing teacher (Science - 4.5 rating)
   • Average performer (English - 4.2 rating)
   • Needs improvement (Math - 3.1 rating)
   • Follow-up progress (Math - 3.5 rating)
   • Rejected report example (needs revision)
    """)
    
    print("=" * 80)

if __name__ == '__main__':
    create_demo_data()
