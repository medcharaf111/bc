#!/usr/bin/env python
"""
Test script to check what the InspectorDashboard API returns
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from accounts.models import User
from core.inspection_models import InspectorRegionAssignment, InspectionVisit, InspectionReport
from django.utils import timezone

def test_inspector_api_data():
    inspector = User.objects.get(username='charafinspector')
    
    print("=" * 60)
    print(f"INSPECTOR: {inspector.username}")
    print("=" * 60)
    
    # Check region assignments
    print("\n1. REGION ASSIGNMENTS:")
    assignments = InspectorRegionAssignment.objects.filter(inspector=inspector)
    print(f"   Total: {assignments.count()}")
    for assignment in assignments:
        region = assignment.region
        school_count = region.get_school_count() if hasattr(region, 'get_school_count') else 0
        teacher_count = region.get_teacher_count() if hasattr(region, 'get_teacher_count') else 0
        print(f"   - {region.name} ({region.code})")
        print(f"     Schools: {school_count}, Teachers: {teacher_count}")
    
    # Check visits
    print("\n2. INSPECTION VISITS:")
    visits = InspectionVisit.objects.filter(inspector=inspector)
    print(f"   Total: {visits.count()}")
    upcoming = visits.filter(status='scheduled', visit_date__gte=timezone.now().date())
    print(f"   Upcoming: {upcoming.count()}")
    
    # Check reports  
    print("\n3. INSPECTION REPORTS:")
    reports = InspectionReport.objects.filter(inspector=inspector)
    print(f"   Total: {reports.count()}")
    pending = reports.filter(gpi_status='pending')
    print(f"   Pending GPI review: {pending.count()}")
    
    print("\n" + "=" * 60)
    print("DIAGNOSIS:")
    print("=" * 60)
    
    if assignments.count() == 0:
        print("❌ NO REGION ASSIGNMENTS - Dashboard will be empty!")
    elif all(region.get_school_count() == 0 for assignment in assignments for region in [assignment.region]):
        print("⚠️  Regions assigned but NO SCHOOLS - Dashboard will show regions but no data!")
    elif visits.count() == 0:
        print("⚠️  No visits created - Visit section will be empty")
    else:
        print("✓ Data looks good!")

if __name__ == '__main__':
    test_inspector_api_data()
