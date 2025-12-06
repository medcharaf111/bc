#!/usr/bin/env python
"""
Create inspector and GPI test users for the NATIVE OS platform.
Run this script after activating your virtual environment:
    python create_inspection_test_users.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import School
from core.inspection_models import Region, InspectorRegionAssignment

User = get_user_model()

def create_inspection_test_users():
    # Create or get a test school
    school, created = School.objects.get_or_create(
        name="Test School",
        defaults={'address': '123 Test Street'}
    )
    if created:
        print(f"✓ Created school: {school.name}")
    else:
        print(f"✓ Using existing school: {school.name}")

    # Create or get a test region
    region, created = Region.objects.get_or_create(
        code="TUN-TEST",
        defaults={
            'name': 'Test Region',
            'name_ar': 'منطقة الاختبار',
            'governorate': 'Tunis',
            'description': 'Test region for inspection system',
            'is_active': True
        }
    )
    if created:
        print(f"✓ Created region: {region.name}")
    else:
        print(f"✓ Using existing region: {region.name}")
    
    # Assign school to region if not already assigned
    if not school.region:
        school.region = region
        school.save()
        print(f"✓ Assigned {school.name} to {region.name}")

    # Test inspection user credentials
    test_users = [
        {
            'username': 'inspector',
            'email': 'inspector@test.com',
            'password': 'inspector123',
            'role': 'inspector',
            'first_name': 'Ahmed',
            'last_name': 'Inspector'
        },
        {
            'username': 'gpi',
            'email': 'gpi@test.com',
            'password': 'gpi123',
            'role': 'gpi',
            'first_name': 'Fatima',
            'last_name': 'GPI'
        }
    ]

    print("\nCreating inspection test users...\n")
    created_inspector = None
    
    for user_data in test_users:
        username = user_data['username']
        password = user_data.pop('password')
        
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            print(f"⚠ User '{username}' already exists")
            if username == 'inspector':
                created_inspector = user
        else:
            user = User.objects.create_user(
                **user_data,
                school=school,
                is_active=True
            )
            user.set_password(password)
            user.save()
            print(f"✓ Created user: {username} (password: {password})")
            if username == 'inspector':
                created_inspector = user
    
    # Create inspector assignment to the test region
    if created_inspector:
        assignment, created = InspectorRegionAssignment.objects.get_or_create(
            inspector=created_inspector,
            region=region,
            defaults={
                'is_active': True,
                'notes': 'Test inspector assignment for development'
            }
        )
        if created:
            print(f"✓ Assigned inspector '{created_inspector.username}' to region '{region.name}'")
        else:
            print(f"⚠ Inspector '{created_inspector.username}' already assigned to region '{region.name}'")

    print("\n" + "="*60)
    print("Inspection Test Users Created Successfully!")
    print("="*60)
    print("\nLogin Credentials:")
    print("-" * 60)
    print("Inspector: username: inspector  password: inspector123")
    print("GPI:       username: gpi        password: gpi123")
    print("-" * 60)
    print(f"\nRegion: {region.name} ({region.code})")
    print(f"School: {school.name} (assigned to {region.name})")
    print("\nYou can now:")
    print("1. Login as 'inspector' to create inspection visits and reports")
    print("2. Login as 'gpi' to review and approve/reject reports")
    print("="*60)

if __name__ == '__main__':
    create_inspection_test_users()
