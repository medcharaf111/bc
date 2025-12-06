#!/usr/bin/env python
"""
Quick test script for Parent Platform features
Creates sample data and demonstrates all endpoints
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from accounts.models import User, School, ParentStudentRelationship, TeacherStudentRelationship, ParentTeacherChat, ParentTeacherMessage
from core.models import Portfolio

def create_test_data():
    """Create sample users and relationships"""
    print("🏫 Creating test data for Parent Platform...\n")
    
    # Get or create school
    school, _ = School.objects.get_or_create(
        name='Test School',
        defaults={'address': '123 Test St'}
    )
    print(f"✅ School: {school.name}")
    
    # Create parent
    parent, created = User.objects.get_or_create(
        username='test_parent',
        defaults={
            'email': 'parent@test.com',
            'role': 'parent',
            'school': school,
            'first_name': 'John',
            'last_name': 'Parent'
        }
    )
    if created:
        parent.set_password('password123')
        parent.save()
    print(f"✅ Parent: {parent.username} (password: password123)")
    
    # Create teacher
    teacher, created = User.objects.get_or_create(
        username='test_teacher',
        defaults={
            'email': 'teacher@test.com',
            'role': 'teacher',
            'school': school,
            'first_name': 'Ms.',
            'last_name': 'Johnson',
            'subjects': ['math', 'science']
        }
    )
    if created:
        teacher.set_password('password123')
        teacher.save()
    print(f"✅ Teacher: {teacher.username} (password: password123)")
    
    # Create student
    student, created = User.objects.get_or_create(
        username='test_student',
        defaults={
            'email': 'student@test.com',
            'role': 'student',
            'school': school,
            'first_name': 'Sarah',
            'last_name': 'Student'
        }
    )
    if created:
        student.set_password('password123')
        student.save()
    print(f"✅ Student: {student.username} (password: password123)")
    
    # Create parent-student relationship
    rel, created = ParentStudentRelationship.objects.get_or_create(
        parent=parent,
        student=student,
        defaults={
            'relationship_type': 'parent',
            'is_primary': True,
            'can_view_grades': True,
            'can_chat_teachers': True
        }
    )
    print(f"✅ Parent-Student Relationship: {parent.username} → {student.username}")
    
    # Create teacher-student relationship
    ts_rel, created = TeacherStudentRelationship.objects.get_or_create(
        teacher=teacher,
        student=student,
        defaults={
            'rating_by_teacher': 5,
            'comments_by_teacher': 'Excellent student, very engaged!',
            'is_active': True
        }
    )
    print(f"✅ Teacher-Student Relationship: {teacher.username} → {student.username}")
    
    # Create student portfolio with test data
    portfolio, created = Portfolio.objects.get_or_create(
        student=student,
        defaults={
            'summary': 'Great progress in all subjects',
            'achievements': ['Perfect Score', 'Week Warrior'],
            'test_results': [
                {
                    'lesson_name': 'Mathematics',
                    'test_title': 'Algebra Quiz',
                    'test_type': 'MCQ',
                    'score': 92.0,
                    'date': '2025-10-20T14:30:00Z',
                    'attempt': 1
                },
                {
                    'lesson_name': 'Science',
                    'test_title': 'Biology Test',
                    'test_type': 'QA',
                    'score': 88.0,
                    'date': '2025-10-19T10:00:00Z',
                    'attempt': 1
                },
                {
                    'lesson_name': 'English',
                    'test_title': 'Grammar Test',
                    'test_type': 'MCQ',
                    'score': 85.0,
                    'date': '2025-10-18T09:00:00Z',
                    'attempt': 1
                }
            ]
        }
    )
    print(f"✅ Portfolio created for {student.username} with 3 test results")
    
    # Note: StudentProfile (gamification) is part of the portfolio feature branch
    # For now, portfolio data is sufficient for testing parent platform
    print(f"ℹ️  Student Profile: Basic data in portfolio")
    
    # Create parent-teacher chat
    chat, created = ParentTeacherChat.objects.get_or_create(
        parent=parent,
        teacher=teacher,
        student=student,
        defaults={
            'subject': 'math',
            'is_active': True
        }
    )
    print(f"✅ Parent-Teacher Chat created")
    
    # Create sample messages
    if created:
        msg1 = ParentTeacherMessage.objects.create(
            chat=chat,
            sender=parent,
            message="Hello Ms. Johnson, how is Sarah doing in your class?"
        )
        msg2 = ParentTeacherMessage.objects.create(
            chat=chat,
            sender=teacher,
            message="Hi! Sarah is doing excellent! She's very engaged and always participates.",
            is_read=True
        )
        msg3 = ParentTeacherMessage.objects.create(
            chat=chat,
            sender=parent,
            message="That's wonderful to hear! Thank you for the update.",
            is_read=True
        )
        print(f"✅ Sample messages created (3 messages)")
    
    print("\n" + "="*60)
    print("✅ TEST DATA CREATED SUCCESSFULLY!")
    print("="*60)
    print("\n📝 Test Accounts:")
    print(f"   Parent:  username='test_parent'  password='password123'")
    print(f"   Teacher: username='test_teacher' password='password123'")
    print(f"   Student: username='test_student' password='password123'")
    print("\n🧪 Test the API:")
    print(f"   1. Login as parent:")
    print(f"      POST /api/users/login/")
    print(f"      {{'username': 'test_parent', 'password': 'password123'}}")
    print(f"   2. Get student performance:")
    print(f"      GET /api/parent-dashboard/student_performance/")
    print(f"   3. Get chats:")
    print(f"      GET /api/parent-teacher-chats/my_chats/")
    print(f"   4. View messages:")
    print(f"      GET /api/parent-teacher-chats/{chat.id}/messages/")
    print("\n🌐 Admin Panel: http://localhost:8000/admin/")
    print("="*60 + "\n")

if __name__ == '__main__':
    create_test_data()
