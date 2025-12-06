#!/usr/bin/env python
"""
Test inspector and GPI login functionality
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from django.contrib.auth import get_user_model, authenticate
from core.inspection_models import Region, InspectorRegionAssignment

User = get_user_model()

def test_accounts():
    print("=" * 60)
    print("Testing Inspector and GPI Accounts")
    print("=" * 60)
    
    # Test inspector account
    print("\n1. Testing Inspector Account:")
    print("-" * 60)
    inspector_user = User.objects.filter(username='inspector').first()
    if inspector_user:
        print(f"✓ Inspector user found: {inspector_user.username}")
        print(f"  - Email: {inspector_user.email}")
        print(f"  - Role: {inspector_user.role}")
        print(f"  - Full Name: {inspector_user.get_full_name()}")
        print(f"  - Is Active: {inspector_user.is_active}")
        print(f"  - School: {inspector_user.school.name}")
        
        # Check authentication
        auth_user = authenticate(username='inspector', password='inspector123')
        if auth_user:
            print(f"✓ Authentication successful")
        else:
            print(f"✗ Authentication failed")
        
        # Check region assignments
        assignments = InspectorRegionAssignment.objects.filter(inspector=inspector_user, is_active=True)
        print(f"  - Region Assignments: {assignments.count()}")
        for assignment in assignments:
            print(f"    → {assignment.region.name} ({assignment.region.code})")
    else:
        print("✗ Inspector user not found")
    
    # Test GPI account
    print("\n2. Testing GPI Account:")
    print("-" * 60)
    gpi_user = User.objects.filter(username='gpi').first()
    if gpi_user:
        print(f"✓ GPI user found: {gpi_user.username}")
        print(f"  - Email: {gpi_user.email}")
        print(f"  - Role: {gpi_user.role}")
        print(f"  - Full Name: {gpi_user.get_full_name()}")
        print(f"  - Is Active: {gpi_user.is_active}")
        print(f"  - School: {gpi_user.school.name}")
        
        # Check authentication
        auth_user = authenticate(username='gpi', password='gpi123')
        if auth_user:
            print(f"✓ Authentication successful")
        else:
            print(f"✗ Authentication failed")
    else:
        print("✗ GPI user not found")
    
    # Check regions
    print("\n3. Regions Available:")
    print("-" * 60)
    regions = Region.objects.filter(is_active=True)
    print(f"Total active regions: {regions.count()}")
    for region in regions[:5]:  # Show first 5
        schools_count = region.schools.count()
        inspectors_count = region.inspector_assignments.filter(is_active=True).count()
        print(f"  - {region.name} ({region.code})")
        print(f"    Schools: {schools_count}, Inspectors: {inspectors_count}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    print("\nNext Steps:")
    print("1. Open http://localhost:8080/login")
    print("2. Login with:")
    print("   - Username: inspector, Password: inspector123")
    print("   - OR Username: gpi, Password: gpi123")
    print("3. Inspector can access: http://localhost:8080/inspector")
    print("4. GPI can access: http://localhost:8080/gpi")
    print("=" * 60)

if __name__ == '__main__':
    test_accounts()
