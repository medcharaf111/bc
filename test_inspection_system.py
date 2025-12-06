#!/usr/bin/env python
"""
Test script for Inspection System

This script creates test data and verifies the inspection workflow.
Run with: python backend/test_inspection_system.py
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from accounts.models import School
from core.inspection_models import (
    Region, InspectorRegionAssignment, InspectionVisit,
    InspectionReport, MonthlyReport
)

User = get_user_model()

def create_test_data():
    """Create sample inspection data for testing"""
    print("🔧 Creating test data for Inspection System...\n")
    
    # 1. Get or create a region
    region, created = Region.objects.get_or_create(
        code='TUN',
        defaults={
            'name': 'Tunis',
            'description': 'Capital region'
        }
    )
    print(f"✅ Region: {region.name} ({'created' if created else 'existing'})")
    
    # 2. Create or get a school
    school, created = School.objects.get_or_create(
        name='Test Primary School',
        defaults={
            'region': region,
            'address': '123 Test Street',
            'school_code': 'TEST001'
        }
    )
    print(f"✅ School: {school.name} ({'created' if created else 'existing'})")
    
    # 3. Create or get an inspector
    inspector, created = User.objects.get_or_create(
        username='inspector_test',
        defaults={
            'email': 'inspector@test.com',
            'role': 'inspector',
            'first_name': 'Ahmed',
            'last_name': 'Inspector',
            'school': school
        }
    )
    if created:
        inspector.set_password('test123')
        inspector.save()
    print(f"✅ Inspector: {inspector.get_full_name()} ({'created' if created else 'existing'})")
    
    # 4. Create or get a GPI
    gpi, created = User.objects.get_or_create(
        username='gpi_test',
        defaults={
            'email': 'gpi@test.com',
            'role': 'gpi',
            'first_name': 'Fatima',
            'last_name': 'GPI',
            'school': school
        }
    )
    if created:
        gpi.set_password('test123')
        gpi.save()
    print(f"✅ GPI: {gpi.get_full_name()} ({'created' if created else 'existing'})")
    
    # 5. Create or get a teacher
    teacher, created = User.objects.get_or_create(
        username='teacher_test',
        defaults={
            'email': 'teacher@test.com',
            'role': 'teacher',
            'first_name': 'Mohamed',
            'last_name': 'Teacher',
            'school': school,
            'subjects': ['mathematics']
        }
    )
    if created:
        teacher.set_password('test123')
        teacher.save()
    print(f"✅ Teacher: {teacher.get_full_name()} ({'created' if created else 'existing'})")
    
    # 6. Assign inspector to region
    assignment, created = InspectorRegionAssignment.objects.get_or_create(
        inspector=inspector,
        region=region,
        defaults={'is_active': True}
    )
    print(f"✅ Inspector-Region Assignment ({'created' if created else 'existing'})")
    
    # 7. Create a scheduled visit
    visit_date = (timezone.now() + timedelta(days=7)).date()
    visit_time = timezone.now().time()
    visit, created = InspectionVisit.objects.get_or_create(
        inspector=inspector,
        teacher=teacher,
        school=school,
        visit_date=visit_date,
        defaults={
            'visit_time': visit_time,
            'inspection_type': 'routine',
            'notes': 'Focus on problem-solving techniques',
            'status': 'scheduled'
        }
    )
    print(f"✅ Scheduled Visit: {visit.visit_date} ({'created' if created else 'existing'})")
    
    # 8. Create a completed visit with report
    completed_visit_date = (timezone.now() - timedelta(days=3)).date()
    completed_visit, created = InspectionVisit.objects.get_or_create(
        inspector=inspector,
        teacher=teacher,
        school=school,
        visit_date=completed_visit_date,
        defaults={
            'visit_time': visit_time,
            'inspection_type': 'routine',
            'notes': 'Classroom observation',
            'status': 'completed',
            'completed_at': timezone.now() - timedelta(days=3)
        }
    )
    if created:
        print(f"✅ Completed Visit: {completed_visit.visit_date}")
    
    # 9. Create an inspection report
    report, created = InspectionReport.objects.get_or_create(
        visit=completed_visit,
        defaults={
            'inspector': inspector,
            'teacher': teacher,
            'summary': 'Overall excellent teaching performance with room for technology integration',
            'classroom_observations': 'Well-organized classroom, students attentive and engaged',
            'pedagogical_evaluation': 'Strong use of visual aids, effective questioning techniques',
            'teacher_strengths': 'Excellent use of visual aids, strong student rapport, clear explanations',
            'improvement_points': 'Limited differentiation for advanced learners, minimal technology integration',
            'recommendations': 'Introduce tiered activities for mixed-ability groups, explore interactive teaching tools',
            'final_rating': 4,
            'follow_up_required': False,
            'gpi_status': 'pending'
        }
    )
    print(f"✅ Inspection Report: Rating {report.final_rating}/5 ({'created' if created else 'existing'})")
    
    # 10. Create a monthly report
    from datetime import date
    current_month_date = date.today().replace(day=1)  # First day of current month
    monthly_report, created = MonthlyReport.objects.get_or_create(
        inspector=inspector,
        month=current_month_date,
        defaults={
            'total_visits': 5,
            'completed_visits': 4,
            'pending_visits': 1,
            'recurring_issues': 'Technology integration needs improvement across multiple classrooms',
            'positive_trends': 'Generally good teaching quality and student engagement',
            'recommendations': 'Provide training on interactive teaching tools',
            'status': 'draft'
        }
    )
    print(f"✅ Monthly Report: {monthly_report.month.strftime('%B %Y')} ({'created' if created else 'existing'})")
    
    return {
        'region': region,
        'school': school,
        'inspector': inspector,
        'gpi': gpi,
        'teacher': teacher,
        'visit': visit,
        'completed_visit': completed_visit,
        'report': report,
        'monthly_report': monthly_report
    }


def test_workflow(data):
    """Test the inspection workflow"""
    print("\n🧪 Testing Inspection Workflow...\n")
    
    inspector = data['inspector']
    gpi = data['gpi']
    report = data['report']
    
    # Test 1: Inspector has region assignment
    assert InspectorRegionAssignment.objects.filter(
        inspector=inspector,
        is_active=True
    ).exists(), "❌ Inspector should have region assignment"
    print("✅ Test 1: Inspector has active region assignment")
    
    # Test 2: Report status check
    if report.gpi_status == 'pending':
        print("✅ Test 2: Report status is pending")
        
        # Test 3: GPI can approve report
        report.approve(gpi, "Excellent observation with detailed recommendations")
        report.refresh_from_db()
        assert report.gpi_status == 'approved', "❌ Report should be approved"
        assert report.gpi_reviewer == gpi, "❌ GPI should be set as reviewer"
        print("✅ Test 3: GPI approved report successfully")
    else:
        print(f"✅ Test 2: Report already {report.gpi_status} (skipping approval test)")
    
    # Test 4: Final rating is set correctly
    assert 1 <= report.final_rating <= 5, "❌ Final rating should be between 1 and 5"
    print(f"✅ Test 4: Final rating is valid: {report.final_rating}/5")
    
    # Test 5: Visit is marked as completed
    visit = data['completed_visit']
    assert visit.status == 'completed', "❌ Visit should be completed"
    print("✅ Test 5: Visit marked as completed")
    
    # Test 6: Monthly report statistics
    monthly_report = data['monthly_report']
    assert monthly_report.status in ['draft', 'submitted', 'approved'], "❌ Monthly report should have valid status"
    print(f"✅ Test 6: Monthly report created: {monthly_report.total_visits} visits, {monthly_report.completed_visits} completed")
    
    print("\n✅ All tests passed!\n")


def print_summary(data):
    """Print a summary of created data"""
    print("📊 Test Data Summary:")
    print("=" * 60)
    print(f"Region: {data['region'].name} ({data['region'].code})")
    print(f"School: {data['school'].name}")
    print(f"Inspector: {data['inspector'].username} ({data['inspector'].get_full_name()})")
    print(f"GPI: {data['gpi'].username} ({data['gpi'].get_full_name()})")
    print(f"Teacher: {data['teacher'].username} ({data['teacher'].get_full_name()})")
    print(f"Scheduled Visit: {data['visit'].visit_date}")
    print(f"Completed Visit: {data['completed_visit'].visit_date}")
    print(f"Report: Final Rating {data['report'].final_rating}/5 (Status: {data['report'].gpi_status})")
    print(f"Monthly Report: {data['monthly_report'].month.strftime('%B %Y')} (Status: {data['monthly_report'].status})")
    print("=" * 60)
    print("\n🔐 Test Credentials:")
    print("  Inspector: inspector_test / test123")
    print("  GPI: gpi_test / test123")
    print("  Teacher: teacher_test / test123")
    print("\n🌐 Test URLs:")
    print("  Inspector Dashboard: http://localhost:3000/inspector")
    print("  GPI Dashboard: http://localhost:3000/gpi")
    print("  API Base: http://localhost:8000/api/inspection/")
    print("\n")


def main():
    """Main test execution"""
    print("\n" + "=" * 60)
    print("   INSPECTION SYSTEM TEST SCRIPT")
    print("=" * 60 + "\n")
    
    try:
        # Create test data
        data = create_test_data()
        
        # Run workflow tests
        test_workflow(data)
        
        # Print summary
        print_summary(data)
        
        print("✅ Inspection System test completed successfully!")
        print("\n💡 Next steps:")
        print("   1. Start backend: python backend/manage.py runserver")
        print("   2. Start frontend: cd frontend && npm run dev")
        print("   3. Login as inspector_test or gpi_test")
        print("   4. Explore the dashboards\n")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
