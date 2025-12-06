#!/usr/bin/env python
"""
Comprehensive Inspection System Testing

Tests the complete workflow from visit creation to GPI approval.
Run with: python backend/test_inspection_workflow.py
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
from datetime import timedelta, date
from accounts.models import School
from core.inspection_models import (
    Region, InspectorRegionAssignment, InspectionVisit,
    InspectionReport, MonthlyReport, TeacherComplaint
)

User = get_user_model()


def test_inspector_dashboard_stats():
    """Test inspector dashboard statistics calculation"""
    print("\n🧪 Test 1: Inspector Dashboard Statistics")
    
    inspector = User.objects.filter(role='inspector').first()
    if not inspector:
        print("  ⚠️  No inspector found - skipping test")
        return False
    
    # Get assigned regions
    assignments = InspectorRegionAssignment.objects.filter(
        inspector=inspector,
        is_active=True
    )
    
    # Count visits
    total_visits = InspectionVisit.objects.filter(inspector=inspector).count()
    upcoming_visits = InspectionVisit.objects.filter(
        inspector=inspector,
        status='scheduled',
        visit_date__gte=date.today()
    ).count()
    
    # Count reports
    pending_reports = InspectionReport.objects.filter(
        inspector=inspector,
        gpi_status='pending'
    ).count()
    
    # Count assigned teachers
    assigned_regions = [a.region for a in assignments]
    teachers_count = User.objects.filter(
        role='teacher',
        school__region__in=assigned_regions
    ).count()
    
    print(f"  ✅ Inspector: {inspector.get_full_name()}")
    print(f"  📊 Assigned Regions: {assignments.count()}")
    print(f"  📊 Total Visits: {total_visits}")
    print(f"  📊 Upcoming Visits: {upcoming_visits}")
    print(f"  📊 Pending Reports: {pending_reports}")
    print(f"  📊 Assigned Teachers: {teachers_count}")
    
    assert assignments.exists(), "Inspector should have region assignments"
    assert total_visits >= 0, "Total visits should be non-negative"
    
    print("  ✅ Inspector dashboard stats working correctly")
    return True


def test_gpi_dashboard_stats():
    """Test GPI dashboard statistics calculation"""
    print("\n🧪 Test 2: GPI Dashboard Statistics")
    
    # Count inspectors
    inspectors_count = User.objects.filter(role='inspector').count()
    
    # Count pending reports
    pending_reviews = InspectionReport.objects.filter(
        gpi_status='pending'
    ).count()
    
    # Count visits this month
    current_month_start = date.today().replace(day=1)
    visits_this_month = InspectionVisit.objects.filter(
        visit_date__gte=current_month_start
    ).count()
    
    # Calculate average rating
    from django.db.models import Avg
    avg_rating = InspectionReport.objects.filter(
        gpi_status='approved'
    ).aggregate(avg=Avg('final_rating'))['avg'] or 0
    
    print(f"  📊 Active Inspectors: {inspectors_count}")
    print(f"  📊 Pending Reviews: {pending_reviews}")
    print(f"  📊 Visits This Month: {visits_this_month}")
    print(f"  📊 Average Rating: {avg_rating:.2f}/5")
    
    assert inspectors_count >= 0, "Inspector count should be non-negative"
    assert pending_reviews >= 0, "Pending reviews should be non-negative"
    
    print("  ✅ GPI dashboard stats working correctly")
    return True


def test_visit_creation_and_completion():
    """Test creating and completing a visit"""
    print("\n🧪 Test 3: Visit Creation and Completion")
    
    inspector = User.objects.filter(role='inspector').first()
    teacher = User.objects.filter(role='teacher', school__region__isnull=False).first()
    
    if not inspector or not teacher:
        print("  ⚠️  Missing inspector or teacher - skipping test")
        return False
    
    # Create a visit
    visit = InspectionVisit.objects.create(
        inspector=inspector,
        teacher=teacher,
        school=teacher.school,
        visit_date=date.today() + timedelta(days=1),
        visit_time=timezone.now().time(),
        inspection_type='routine',
        notes='Test visit for workflow validation',
        status='scheduled'
    )
    
    print(f"  ✅ Created visit: {visit.id}")
    assert visit.status == 'scheduled', "Visit should be scheduled"
    
    # Mark as completed
    visit.mark_completed()
    visit.refresh_from_db()
    
    print(f"  ✅ Visit marked as completed")
    assert visit.status == 'completed', "Visit should be completed"
    assert visit.completed_at is not None, "Completion time should be set"
    
    # Clean up
    visit.delete()
    print("  🧹 Test visit cleaned up")
    
    return True


def test_report_creation_and_approval():
    """Test creating a report and GPI approval workflow"""
    print("\n🧪 Test 4: Report Creation and GPI Approval")
    
    inspector = User.objects.filter(role='inspector').first()
    gpi = User.objects.filter(role='gpi').first()
    teacher = User.objects.filter(role='teacher', school__region__isnull=False).first()
    
    if not inspector or not gpi or not teacher:
        print("  ⚠️  Missing required users - skipping test")
        return False
    
    # Create a completed visit
    visit = InspectionVisit.objects.create(
        inspector=inspector,
        teacher=teacher,
        school=teacher.school,
        visit_date=date.today(),
        visit_time=timezone.now().time(),
        inspection_type='routine',
        notes='Test visit for report workflow',
        status='completed',
        completed_at=timezone.now()
    )
    
    print(f"  ✅ Created completed visit: {visit.id}")
    
    # Create report
    report = InspectionReport.objects.create(
        visit=visit,
        inspector=inspector,
        teacher=teacher,
        summary='Test report for workflow validation',
        teacher_strengths='Good teaching methods',
        improvement_points='Could improve time management',
        recommendations='Attend time management workshop',
        final_rating=4,
        gpi_status='pending'
    )
    
    print(f"  ✅ Created report: {report.id}")
    assert report.gpi_status == 'pending', "Report should be pending"
    
    # GPI approves report
    report.approve(gpi, "Excellent observation and detailed recommendations")
    report.refresh_from_db()
    
    print(f"  ✅ GPI approved report")
    assert report.gpi_status == 'approved', "Report should be approved"
    assert report.gpi_reviewer == gpi, "GPI should be set as reviewer"
    assert report.gpi_feedback, "GPI feedback should be provided"
    
    # Clean up
    report.delete()
    visit.delete()
    print("  🧹 Test report and visit cleaned up")
    
    return True


def test_report_rejection():
    """Test report rejection workflow"""
    print("\n🧪 Test 5: Report Rejection Workflow")
    
    inspector = User.objects.filter(role='inspector').first()
    gpi = User.objects.filter(role='gpi').first()
    teacher = User.objects.filter(role='teacher', school__region__isnull=False).first()
    
    if not inspector or not gpi or not teacher:
        print("  ⚠️  Missing required users - skipping test")
        return False
    
    # Create visit and report
    visit = InspectionVisit.objects.create(
        inspector=inspector,
        teacher=teacher,
        school=teacher.school,
        visit_date=date.today(),
        visit_time=timezone.now().time(),
        inspection_type='routine',
        status='completed',
        completed_at=timezone.now()
    )
    
    report = InspectionReport.objects.create(
        visit=visit,
        inspector=inspector,
        teacher=teacher,
        summary='Incomplete report for testing rejection',
        final_rating=3,
        gpi_status='pending'
    )
    
    print(f"  ✅ Created report for rejection test: {report.id}")
    
    # GPI rejects report
    report.reject(gpi, "Please provide more detailed observations and specific recommendations")
    report.refresh_from_db()
    
    print(f"  ✅ GPI rejected report")
    assert report.gpi_status == 'rejected', "Report should be rejected"
    assert report.gpi_feedback, "Rejection feedback should be provided"
    
    # Clean up
    report.delete()
    visit.delete()
    print("  🧹 Test data cleaned up")
    
    return True


def test_monthly_report_generation():
    """Test monthly report generation and statistics"""
    print("\n🧪 Test 6: Monthly Report Generation")
    
    inspector = User.objects.filter(role='inspector').first()
    
    if not inspector:
        print("  ⚠️  No inspector found - skipping test")
        return False
    
    # Create monthly report
    current_month = date.today().replace(day=1)
    monthly_report, created = MonthlyReport.objects.get_or_create(
        inspector=inspector,
        month=current_month,
        defaults={
            'status': 'draft'
        }
    )
    
    if created:
        print(f"  ✅ Created monthly report for {current_month.strftime('%B %Y')}")
    else:
        print(f"  ✅ Using existing monthly report for {current_month.strftime('%B %Y')}")
    
    # Generate statistics
    stats = monthly_report.generate_statistics()
    
    print(f"  📊 Total Visits: {stats.get('total', 0)}")
    print(f"  📊 Completed Visits: {stats.get('completed', 0)}")
    print(f"  📊 Pending Visits: {stats.get('pending', 0)}")
    print(f"  📊 Rating Distribution: {stats.get('ratings', {})}")
    
    assert 'total' in stats, "Stats should include total visits"
    assert 'completed' in stats, "Stats should include completed visits"
    
    print("  ✅ Monthly report generation working correctly")
    
    # Don't delete - keep for inspection
    return True


def test_complaint_workflow():
    """Test teacher complaint creation and resolution"""
    print("\n🧪 Test 7: Complaint Workflow")
    
    inspector = User.objects.filter(role='inspector').first()
    teacher = User.objects.filter(role='teacher', school__region__isnull=False).first()
    reporter = User.objects.filter(role='student').first()
    
    if not inspector or not teacher or not reporter:
        print("  ⚠️  Missing required users - skipping test")
        return False
    
    # Create complaint
    complaint = TeacherComplaint.objects.create(
        teacher=teacher,
        filed_by=reporter,
        title='Workflow Test Complaint',
        description='Test complaint for workflow validation',
        severity='medium',
        status='pending'
    )
    
    print(f"  ✅ Created complaint: {complaint.id}")
    assert complaint.status == 'pending', "Complaint should be pending"
    
    # Assign to inspector
    complaint.assigned_inspector = inspector
    complaint.status = 'under_investigation'
    complaint.save()
    
    print(f"  ✅ Assigned complaint to inspector")
    assert complaint.assigned_inspector == inspector, "Inspector should be assigned"
    
    # Resolve complaint
    complaint.status = 'resolved'
    complaint.resolution_notes = 'Investigation completed. Issue addressed through coaching session.'
    complaint.resolved_at = timezone.now()
    complaint.save()
    
    print(f"  ✅ Complaint resolved")
    assert complaint.status == 'resolved', "Complaint should be resolved"
    
    # Clean up
    complaint.delete()
    print("  🧹 Test complaint cleaned up")
    
    return True


def test_region_assignment():
    """Test inspector region assignment"""
    print("\n🧪 Test 8: Inspector Region Assignment")
    
    inspector = User.objects.filter(role='inspector').first()
    regions = Region.objects.all()
    
    if not inspector or not regions.exists():
        print("  ⚠️  Missing inspector or regions - skipping test")
        return False
    
    # Check existing assignments
    assignments = InspectorRegionAssignment.objects.filter(
        inspector=inspector,
        is_active=True
    )
    
    print(f"  📊 Inspector has {assignments.count()} active region assignment(s)")
    
    for assignment in assignments:
        print(f"  ✅ Assigned to: {assignment.region.name}")
        
        # Get teachers in region
        teachers = User.objects.filter(
            role='teacher',
            school__region=assignment.region
        ).count()
        
        print(f"      - {teachers} teachers in region")
    
    assert assignments.exists(), "Inspector should have at least one region assignment"
    
    print("  ✅ Region assignment working correctly")
    return True


def print_summary(results):
    """Print test results summary"""
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"\nTests Passed: {passed}/{total} ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n✅ All tests passed! Inspection system is fully functional.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed or skipped.")
    
    print("\n💡 System Status:")
    print(f"  - Inspectors: {User.objects.filter(role='inspector').count()}")
    print(f"  - GPIs: {User.objects.filter(role='gpi').count()}")
    print(f"  - Teachers with regions: {User.objects.filter(role='teacher', school__region__isnull=False).count()}")
    print(f"  - Total Regions: {Region.objects.count()}")
    print(f"  - Total Visits: {InspectionVisit.objects.count()}")
    print(f"  - Total Reports: {InspectionReport.objects.count()}")
    print(f"  - Pending Reports: {InspectionReport.objects.filter(gpi_status='pending').count()}")
    print()


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("   INSPECTION SYSTEM - WORKFLOW TESTING")
    print("=" * 60)
    
    results = []
    
    try:
        # Run all tests
        results.append(test_inspector_dashboard_stats())
        results.append(test_gpi_dashboard_stats())
        results.append(test_visit_creation_and_completion())
        results.append(test_report_creation_and_approval())
        results.append(test_report_rejection())
        results.append(test_monthly_report_generation())
        results.append(test_complaint_workflow())
        results.append(test_region_assignment())
        
        # Print summary
        print_summary(results)
        
        if all(results):
            print("✅ Inspection system workflow testing complete!")
            sys.exit(0)
        else:
            print("⚠️  Some tests failed or were skipped.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test execution failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
