#!/usr/bin/env python
"""
Create a new inspector account with region assignments
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from accounts.models import User
from core.inspection_models import InspectorRegionAssignment, Region

def create_inspector():
    print("="*60)
    print("CREATE NEW INSPECTOR ACCOUNT")
    print("="*60)
    
    # Inspector details
    username = "inspector1"
    password = "inspector123"
    first_name = "Ahmed"
    last_name = "Ben Ali"
    email = "ahmed.benali@inspection.tn"
    
    # Get or create a dummy school for inspector (they need to be assigned to a school)
    from accounts.models import School
    dummy_school, _ = School.objects.get_or_create(
        name="Inspection Office",
        defaults={
            'address': 'Tunis, Tunisia',
            'school_type': 'administrative',
        }
    )
    
    # Create inspector user
    inspector, created = User.objects.get_or_create(
        username=username,
        defaults={
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'role': 'inspector',
            'school': dummy_school,
            'is_active': True,
        }
    )
    
    if created:
        inspector.set_password(password)
        inspector.save()
        print(f"✅ Created new inspector: {username}")
    else:
        print(f"⚠️  Inspector already exists: {username}")
        print("   Resetting password...")
        inspector.set_password(password)
        inspector.save()
    
    print(f"\nInspector Details:")
    print(f"  Name: {inspector.first_name} {inspector.last_name}")
    print(f"  Email: {inspector.email}")
    print(f"  Role: {inspector.role}")
    
    # Assign regions
    print(f"\n{'='*60}")
    print("ASSIGNING REGIONS")
    print('='*60)
    
    # Get existing regions with schools
    regions = Region.objects.filter(code__in=['TUN-01', 'SFA-01', 'ARI-01'])
    
    if regions.count() == 0:
        print("⚠️  No regions found! Creating default regions...")
        regions_data = [
            {'name': 'Tunis', 'code': 'TUN-01', 'governorate': 'Tunis'},
            {'name': 'Sfax', 'code': 'SFA-01', 'governorate': 'Sfax'},
            {'name': 'Ariana', 'code': 'ARI-01', 'governorate': 'Ariana'},
        ]
        
        for region_data in regions_data:
            region, created = Region.objects.get_or_create(
                code=region_data['code'],
                defaults={
                    'name': region_data['name'],
                    'governorate': region_data['governorate']
                }
            )
            if created:
                print(f"  Created region: {region.name}")
        
        regions = Region.objects.filter(code__in=['TUN-01', 'SFA-01', 'ARI-01'])
    
    # Clear old assignments
    InspectorRegionAssignment.objects.filter(inspector=inspector).delete()
    
    # Create new assignments
    for region in regions:
        assignment, created = InspectorRegionAssignment.objects.get_or_create(
            inspector=inspector,
            region=region,
            defaults={'is_active': True}
        )
        school_count = region.schools.count()
        teacher_count = User.objects.filter(role='teacher', school__region=region).count()
        print(f"  ✓ Assigned: {region.name} ({school_count} schools, {teacher_count} teachers)")
    
    # Update user's assigned_region field
    region_names = ', '.join([r.name for r in regions])
    inspector.assigned_region = region_names
    inspector.save()
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    print(f"Username: {username}")
    print(f"Password: {password}")
    print(f"Assigned Regions: {region_names}")
    print(f"\n✅ Inspector account ready!")
    print(f"\nLogin at: http://localhost:5173/login")

if __name__ == '__main__':
    create_inspector()
