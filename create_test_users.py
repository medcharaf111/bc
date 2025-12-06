#!/usr/bin/env python
"""
Create test users for the NATIVE OS platform.
Run this script after activating your virtual environment:
    python create_test_users.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import School

User = get_user_model()

def create_test_users():
    # Create a test school if none exists
    school, created = School.objects.get_or_create(
        name="Test School",
        defaults={'address': '123 Test Street'}
    )
    if created:
        print(f"✓ Created school: {school.name}")
    else:
        print(f"✓ Using existing school: {school.name}")

    # Test user credentials
    test_users = [
        {
            'username': 'admin',
            'email': 'admin@test.com',
            'password': 'admin123',
            'role': 'admin',
            'first_name': 'Admin',
            'last_name': 'User'
        },
        {
            'username': 'teacher',
            'email': 'teacher@test.com',
            'password': 'teacher123',
            'role': 'teacher',
            'first_name': 'John',
            'last_name': 'Teacher'
        },
        {
            'username': 'student',
            'email': 'student@test.com',
            'password': 'student123',
            'role': 'student',
            'first_name': 'Jane',
            'last_name': 'Student'
        },
        {
            'username': 'parent',
            'email': 'parent@test.com',
            'password': 'parent123',
            'role': 'parent',
            'first_name': 'Bob',
            'last_name': 'Parent'
        }
    ]

    print("\nCreating test users...\n")
    for user_data in test_users:
        username = user_data['username']
        password = user_data.pop('password')
        
        if User.objects.filter(username=username).exists():
            print(f"⚠ User '{username}' already exists")
        else:
            user = User.objects.create_user(
                **user_data,
                school=school,
                is_active=True
            )
            user.set_password(password)
            user.save()
            print(f"✓ Created user: {username} (password: {password})")

    print("\n" + "="*50)
    print("Test Users Created Successfully!")
    print("="*50)
    print("\nLogin Credentials:")
    print("-" * 50)
    print("Admin:   username: admin    password: admin123")
    print("Teacher: username: teacher  password: teacher123")
    print("Student: username: student  password: student123")
    print("Parent:  username: parent   password: parent123")
    print("-" * 50)

if __name__ == '__main__':
    create_test_users()
