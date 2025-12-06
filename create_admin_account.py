#!/usr/bin/env python
"""
Create Administrator Test Account

This script creates a test administrator account for testing the administrator dashboard.
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from accounts.models import School, User

def create_admin_account():
    """Create a test administrator account"""
    
    # Get or create a test school
    school, created = School.objects.get_or_create(
        name='Test School for Admin',
        defaults={'address': '123 Admin Street, Test City'}
    )
    
    if created:
        print(f"✓ Created test school: {school.name}")
    else:
        print(f"✓ Using existing school: {school.name}")
    
    # Check if admin already exists
    admin_username = 'administrator'
    if User.objects.filter(username=admin_username).exists():
        print(f"! Administrator account '{admin_username}' already exists")
        admin = User.objects.get(username=admin_username)
    else:
        # Create administrator
        admin = User.objects.create_user(
            username=admin_username,
            email='admin@testschool.com',
            password='admin123',  # Change this in production!
            first_name='System',
            last_name='Administrator',
            role='admin',
            school=school,
            phone='+1-555-0100',
        )
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        print(f"✓ Created administrator account: {admin_username}")
    
    print("\n" + "="*60)
    print("ADMINISTRATOR ACCOUNT DETAILS")
    print("="*60)
    print(f"Username:  {admin.username}")
    print(f"Password:  admin123")
    print(f"Email:     {admin.email}")
    print(f"Role:      {admin.role}")
    print(f"School:    {admin.school.name}")
    print(f"Full Name: {admin.get_full_name()}")
    print("="*60)
    print("\nYou can now login with these credentials at: http://localhost:5173/login")
    print("Then navigate to: http://localhost:5173/admin")
    print("\nNote: Change the password in production!")
    print("="*60)

if __name__ == '__main__':
    print("Creating Administrator Test Account...")
    print("-" * 60)
    create_admin_account()
    print("\nDone!")
